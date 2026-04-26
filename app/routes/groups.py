# app/routers/groups.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.group import Group, GroupMember
from app.schemas.group import (
    GroupCreate, GroupUpdate, GroupOut,
    GroupDetailOut, GroupMemberOut, AddMemberRequest,
)

router = APIRouter(prefix="/groups", tags=["Groups"])


# ── helpers ────────────────────────────────────────────────────
def _get_group_or_404(group_id: int, db: Session) -> Group:
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def _require_member(group_id: int, user_id: int, db: Session) -> GroupMember:
    member = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="You are not a member of this group")
    return member


def _require_admin(group_id: int, user_id: int, db: Session) -> GroupMember:
    member = _require_member(group_id, user_id, db)
    if member.role_id != 1:   # 1 = admin
        raise HTTPException(status_code=403, detail="Admin access required")
    return member


# ── endpoints ──────────────────────────────────────────────────
@router.post("/", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a group. Creator is automatically added as admin."""
    group = Group(
        name        = payload.name,
        description = payload.description,
        category_id = payload.category_id,
        created_by  = current_user.id,
    )
    db.add(group)
    db.flush()   # get group.id before committing

    # Add creator as admin (role_id=1)
    db.add(GroupMember(group_id=group.id, user_id=current_user.id, role_id=1))
    db.commit()
    db.refresh(group)
    return group


@router.get("/", response_model=List[GroupOut])
def list_my_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all groups the current user belongs to."""
    memberships = (
        db.query(GroupMember)
        .filter(GroupMember.user_id == current_user.id)
        .all()
    )
    group_ids = [m.group_id for m in memberships]
    return db.query(Group).filter(Group.id.in_(group_ids)).all()


@router.get("/{group_id}", response_model=GroupDetailOut)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get group details with member list."""
    group = _get_group_or_404(group_id, db)
    _require_member(group_id, current_user.id, db)
    return group


@router.put("/{group_id}", response_model=GroupOut)
def update_group(
    group_id: int,
    payload: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update group info. Admin only."""
    group = _get_group_or_404(group_id, db)
    _require_admin(group_id, current_user.id, db)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a group. Admin only."""
    group = _get_group_or_404(group_id, db)
    _require_admin(group_id, current_user.id, db)
    db.delete(group)
    db.commit()


# ── Member management ──────────────────────────────────────────
@router.post("/{group_id}/members", response_model=GroupMemberOut, status_code=201)
def add_member(
    group_id: int,
    payload: AddMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a user to a group. Admin only."""
    _get_group_or_404(group_id, db)
    _require_admin(group_id, current_user.id, db)

    # Check target user exists
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")

    # Check already a member
    existing = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == payload.user_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User is already a member")

    member = GroupMember(
        group_id = group_id,
        user_id  = payload.user_id,
        role_id  = payload.role_id,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from a group. Admin only (or self-leave)."""
    _get_group_or_404(group_id, db)

    # Allow self-leave OR admin removal
    if current_user.id != user_id:
        _require_admin(group_id, current_user.id, db)

    member = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(member)
    db.commit()
