# app/models/lookup.py
"""
ORM models for all lookup / reference tables.
These replace the ENUM columns for proper 3NF normalization.
"""
from sqlalchemy import Column, String, SmallInteger
from sqlalchemy.orm import relationship
from app.core.database import Base


class Currency(Base):
    __tablename__ = "currencies"

    code   = Column(String(3),  primary_key=True)
    name   = Column(String(60), nullable=False)
    symbol = Column(String(10), nullable=False)

    expenses = relationship("Expense", back_populates="currency")
    payments = relationship("Payment", back_populates="currency")


class GroupCategory(Base):
    __tablename__ = "group_categories"

    id   = Column(SmallInteger, primary_key=True, autoincrement=True)
    name = Column(String(50),   nullable=False, unique=True)

    groups = relationship("Group", back_populates="category")


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id   = Column(SmallInteger, primary_key=True, autoincrement=True)
    name = Column(String(50),   nullable=False, unique=True)

    expenses = relationship("Expense", back_populates="category")


class SplitType(Base):
    __tablename__ = "split_types"

    id   = Column(SmallInteger, primary_key=True, autoincrement=True)
    name = Column(String(30),   nullable=False, unique=True)

    expenses = relationship("Expense", back_populates="split_type")


class PaymentStatus(Base):
    __tablename__ = "payment_statuses"

    id   = Column(SmallInteger, primary_key=True, autoincrement=True)
    name = Column(String(30),   nullable=False, unique=True)

    payments = relationship("Payment", back_populates="status")


class MemberRole(Base):
    __tablename__ = "member_roles"

    id   = Column(SmallInteger, primary_key=True, autoincrement=True)
    name = Column(String(30),   nullable=False, unique=True)

    group_members = relationship("GroupMember", back_populates="role")
