# app/routers/expenses.py
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.group import Group, GroupMember
from app.models.expense import Expense
from app.models.split import Split
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseOut

router = APIRouter(prefix="/groups/{group_id}/expenses", tags=["Expenses"])


# ── helpers ────────────────────────────────────────────────────
def _require_member(group_id: int, user_id: int, db: Session):
    member = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="You are not a member of this group")
    return member


def _get_group_or_404(group_id: int, db: Session) -> Group:
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def _get_expense_or_404(expense_id: int, group_id: int, db: Session) -> Expense:
    expense = (
        db.query(Expense)
        .filter(Expense.id == expense_id, Expense.group_id == group_id)
        .first()
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


def _build_equal_splits(amount: Decimal, member_ids: List[int]) -> List[dict]:
    """Divide amount equally among members, fix rounding on last person."""
    n = len(member_ids)
    share = round(amount / n, 2)
    splits = [{"user_id": uid, "owed_amount": share} for uid in member_ids]
    # fix rounding remainder on last entry
    total_assigned = share * n
    diff = round(amount - total_assigned, 2)
    if diff != 0:
        splits[-1]["owed_amount"] = round(splits[-1]["owed_amount"] + diff, 2)
    return splits


# ── endpoints ──────────────────────────────────────────────────
@router.post("/", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    group_id: int,
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create an expense in a group.
    - split_type_id=1 (equal): owed_amount in splits can be omitted — auto-calculated.
    - split_type_id=2 (exact): provide exact owed_amount per user.
    - split_type_id=3 (percentage): provide percentage as owed_amount per user (must sum to 100),
      backend converts to actual amounts.
    """
    _get_group_or_404(group_id, db)
    _require_member(group_id, current_user.id, db)

    # Validate all split users are group members
    member_rows = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
    member_ids  = {m.user_id for m in member_rows}
    for s in payload.splits:
        if s.user_id not in member_ids:
            raise HTTPException(
                status_code=400,
                detail=f"User {s.user_id} is not a member of this group",
            )

    # Build expense
    expense = Expense(
        group_id      = group_id,
        paid_by       = current_user.id,
        title         = payload.title,
        description   = payload.description,
        amount        = payload.amount,
        currency_code = payload.currency_code,
        category_id   = payload.category_id,
        split_type_id = payload.split_type_id,
        expense_date  = payload.expense_date,
    )
    db.add(expense)
    db.flush()   # get expense.id

    # Build splits based on split_type
    split_type_id = payload.split_type_id

    if split_type_id == 1:
        # Equal split — ignore provided owed_amounts, recalculate
        split_user_ids = [s.user_id for s in payload.splits]
        split_data = _build_equal_splits(payload.amount, split_user_ids)

    elif split_type_id == 2:
        # Exact split — validate totals match
        total = sum(s.owed_amount for s in payload.splits)
        if round(total, 2) != round(payload.amount, 2):
            raise HTTPException(
                status_code=400,
                detail=f"Split amounts ({total}) must equal expense amount ({payload.amount})",
            )
        split_data = [{"user_id": s.user_id, "owed_amount": s.owed_amount} for s in payload.splits]

    elif split_type_id == 3:
        # Percentage split — owed_amount field holds percentage; convert to actual amount
        total_pct = sum(s.owed_amount for s in payload.splits)
        if round(total_pct, 2) != Decimal("100.00"):
            raise HTTPException(
                status_code=400,
                detail=f"Percentages must sum to 100, got {total_pct}",
            )
        split_data = [
            {
                "user_id":     s.user_id,
                "owed_amount": round(payload.amount * s.owed_amount / 100, 2),
            }
            for s in payload.splits
        ]
    else:
        raise HTTPException(status_code=400, detail="Invalid split_type_id")

    for sd in split_data:
        db.add(Split(
            expense_id  = expense.id,
            user_id     = sd["user_id"],
            owed_amount = sd["owed_amount"],
        ))

    db.commit()
    db.refresh(expense)
    return expense


@router.get("/", response_model=List[ExpenseOut])
def list_expenses(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all expenses in a group."""
    _get_group_or_404(group_id, db)
    _require_member(group_id, current_user.id, db)
    return db.query(Expense).filter(Expense.group_id == group_id).all()


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(
    group_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single expense with its splits."""
    _get_group_or_404(group_id, db)
    _require_member(group_id, current_user.id, db)
    return _get_expense_or_404(expense_id, group_id, db)


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(
    group_id: int,
    expense_id: int,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update expense metadata. Only the person who paid can update."""
    _get_group_or_404(group_id, db)
    _require_member(group_id, current_user.id, db)
    expense = _get_expense_or_404(expense_id, group_id, db)

    if expense.paid_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the payer can edit this expense")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(expense, field, value)

    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    group_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an expense. Only the payer can delete it."""
    _get_group_or_404(group_id, db)
    _require_member(group_id, current_user.id, db)
    expense = _get_expense_or_404(expense_id, group_id, db)

    if expense.paid_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the payer can delete this expense")

    db.delete(expense)
    db.commit()
