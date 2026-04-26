# app/routers/balances.py
"""
Balance calculation for a group.
Shows net amount each member owes or is owed.
"""
from collections import defaultdict
from typing import Dict, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.group import Group, GroupMember
from app.models.expense import Expense
from app.models.split import Split
from app.models.payment import Payment

router = APIRouter(prefix="/groups/{group_id}/balances", tags=["Balances"])


class UserBalance(BaseModel):
    user_id:    int
    first_name: str
    last_name:  str
    net_balance: float   # positive = is owed money, negative = owes money


class SettleDebt(BaseModel):
    from_user_id:   int
    from_user_name: str
    to_user_id:     int
    to_user_name:   str
    amount:         float


class GroupBalanceOut(BaseModel):
    group_id:     int
    balances:     List[UserBalance]
    settlements:  List[SettleDebt]    # simplified list of who should pay whom


@router.get("/", response_model=GroupBalanceOut)
def get_group_balances(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calculate net balances for each member in the group.
    Also returns a simplified settlement list (minimum transactions).
    """
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Must be a member
    member = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == current_user.id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    # Get all members
    members = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
    member_ids = [m.user_id for m in members]

    # net[user_id] = how much they are NET owed (positive) or owe (negative)
    net: Dict[int, Decimal] = defaultdict(Decimal)

    # 1. Process expenses — payer is owed the full amount
    #    each split user owes their share
    expenses = db.query(Expense).filter(Expense.group_id == group_id).all()
    for expense in expenses:
        net[expense.paid_by] += expense.amount
        splits = db.query(Split).filter(Split.expense_id == expense.id).all()
        for split in splits:
            net[split.user_id] -= split.owed_amount

    # 2. Process completed payments — payer loses, payee gains
    payments = (
        db.query(Payment)
        .filter(Payment.group_id == group_id, Payment.status_id == 2)  # completed
        .all()
    )
    for payment in payments:
        net[payment.payer_id] += payment.amount
        net[payment.payee_id] -= payment.amount

    # Build UserBalance list
    user_cache: Dict[int, User] = {}
    def get_user(uid: int) -> User:
        if uid not in user_cache:
            user_cache[uid] = db.get(User, uid)
        return user_cache[uid]

    balances = []
    for uid in member_ids:
        u = get_user(uid)
        if u:
            balances.append(UserBalance(
                user_id     = uid,
                first_name  = u.first_name,
                last_name   = u.last_name,
                net_balance = float(round(net[uid], 2)),
            ))

    # Simplified settlements (greedy minimum-transactions algorithm)
    # creditors = people owed money, debtors = people who owe money
    creditors = sorted(
        [(uid, float(round(net[uid], 2))) for uid in member_ids if net[uid] > 0],
        key=lambda x: -x[1],
    )
    debtors = sorted(
        [(uid, float(round(-net[uid], 2))) for uid in member_ids if net[uid] < 0],
        key=lambda x: -x[1],
    )

    settlements = []
    i, j = 0, 0
    creditors = list(creditors)
    debtors   = list(debtors)

    while i < len(creditors) and j < len(debtors):
        cred_uid, cred_amt = creditors[i]
        debt_uid, debt_amt = debtors[j]

        transfer = min(cred_amt, debt_amt)
        if transfer > 0.001:
            cu = get_user(cred_uid)
            du = get_user(debt_uid)
            settlements.append(SettleDebt(
                from_user_id   = debt_uid,
                from_user_name = f"{du.first_name} {du.last_name}" if du else str(debt_uid),
                to_user_id     = cred_uid,
                to_user_name   = f"{cu.first_name} {cu.last_name}" if cu else str(cred_uid),
                amount         = round(transfer, 2),
            ))

        creditors[i] = (cred_uid, round(cred_amt - transfer, 2))
        debtors[j]   = (debt_uid, round(debt_amt - transfer, 2))

        if creditors[i][1] < 0.001:
            i += 1
        if debtors[j][1] < 0.001:
            j += 1

    return GroupBalanceOut(
        group_id    = group_id,
        balances    = balances,
        settlements = settlements,
    )
