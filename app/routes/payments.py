# app/routers/payments.py
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.group import Group, GroupMember
from app.models.payment import Payment
from app.models.split import Split, SplitSettlement
from app.schemas.payment import PaymentCreate, PaymentStatusUpdate, PaymentOut

router = APIRouter(prefix="/groups/{group_id}/payments", tags=["Payments"])


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


def _get_payment_or_404(payment_id: int, group_id: int, db: Session) -> Payment:
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id, Payment.group_id == group_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


# ── endpoints ──────────────────────────────────────────────────
@router.post("/", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    group_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record a payment between two members of a group.
    If the creator is the payee, it auto-completes (status=2) since they verified receipt.
    """
    _get_group_or_404(group_id, db)
    _require_member(group_id, current_user.id, db)

    actual_payer_id = payload.payer_id if payload.payer_id else current_user.id

    if actual_payer_id == payload.payee_id:
        raise HTTPException(status_code=400, detail="Cannot pay yourself")

    # Verify payer is a group member
    payer_member = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == actual_payer_id)
        .first()
    )
    if not payer_member:
        raise HTTPException(status_code=400, detail="Payer is not a member of this group")

    # Verify payee is a group member
    payee_member = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == payload.payee_id)
        .first()
    )
    if not payee_member:
        raise HTTPException(status_code=400, detail="Payee is not a member of this group")

    # If the payee is creating this payment, it means they already received the cash, so auto-complete.
    actual_status = payload.status_id or 1
    if current_user.id == payload.payee_id:
        actual_status = 2

    # Or if caller explicitly asked for 2, allow it (e.g. payer recording cash). Let's trust group members for now.
    
    payment = Payment(
        group_id      = group_id,
        payer_id      = actual_payer_id,
        payee_id      = payload.payee_id,
        amount        = payload.amount,
        currency_code = payload.currency_code,
        status_id     = actual_status,
        note          = payload.note,
    )
    if actual_status == 2:
        payment.paid_at = datetime.now(timezone.utc)

    db.add(payment)
    db.flush()   # get payment.id

    # Link settlements if provided
    for s in (payload.settlements or []):
        split = db.get(Split, s.split_id)
        if not split:
            raise HTTPException(status_code=404, detail=f"Split {s.split_id} not found")
        
        if actual_status == 2:
            split.is_settled = True

        db.add(SplitSettlement(
            payment_id     = payment.id,
            split_id       = s.split_id,
            settled_amount = s.settled_amount,
        ))

    db.commit()
    db.refresh(payment)
    return payment


@router.get("/", response_model=List[PaymentOut])
def list_payments(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all payments in a group."""
    _get_group_or_404(group_id, db)
    _require_member(group_id, current_user.id, db)
    return db.query(Payment).filter(Payment.group_id == group_id).all()


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(
    group_id: int,
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single payment with its settlements."""
    _get_group_or_404(group_id, db)
    _require_member(group_id, current_user.id, db)
    return _get_payment_or_404(payment_id, group_id, db)


@router.patch("/{payment_id}/status", response_model=PaymentOut)
def update_payment_status(
    group_id: int,
    payment_id: int,
    payload: PaymentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update payment status.
    - Only the payer can mark as completed or cancelled.
    - When completed, paid_at is stamped and linked splits are marked settled.
    """
    _get_group_or_404(group_id, db)
    _require_member(group_id, current_user.id, db)
    payment = _get_payment_or_404(payment_id, group_id, db)

    if payment.payer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the payer can update payment status")

    if payload.status_id not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Invalid status_id (1=pending,2=completed,3=cancelled)")

    payment.status_id = payload.status_id

    # When completed — stamp paid_at and auto-settle linked splits
    if payload.status_id == 2:
        payment.paid_at = datetime.now(timezone.utc)
        for settlement in payment.settlements:
            split = db.get(Split, settlement.split_id)
            if split:
                split.is_settled = True

    db.commit()
    db.refresh(payment)
    return payment


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(
    group_id: int,
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a payment. Only the payer can delete a pending payment."""
    _get_group_or_404(group_id, db)
    _require_member(group_id, current_user.id, db)
    payment = _get_payment_or_404(payment_id, group_id, db)

    if payment.payer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the payer can delete a payment")

    if payment.status_id == 2:
        raise HTTPException(status_code=400, detail="Cannot delete a completed payment")

    db.delete(payment)
    db.commit()
