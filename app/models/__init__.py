# app/models/__init__.py
# Import all model modules so SQLAlchemy registers every ORM class
# before create_all() or any relationship resolution happens.

from app.models import lookup    # GroupCategory, MemberRole, Currency, etc.
from app.models import user      # User
from app.models import group     # Group, GroupMember
from app.models import expense   # Expense
from app.models import split     # Split, SplitSettlement
from app.models import payment   # Payment

__all__ = [
    "lookup",
    "user",
    "group",
    "expense",
    "split",
    "payment",
]
