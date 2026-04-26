# app/models/expense.py
from sqlalchemy import (
    Column, Integer, SmallInteger, String, Text,
    DECIMAL, CHAR, DATE, TIMESTAMP, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id            = Column(Integer,      primary_key=True, autoincrement=True)
    group_id      = Column(Integer,      ForeignKey("groups.id",
                           ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    paid_by       = Column(Integer,      ForeignKey("users.id",
                           ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    title         = Column(String(200),  nullable=False)
    description   = Column(Text,         nullable=True)
    amount        = Column(DECIMAL(12,2), nullable=False)
    currency_code = Column(CHAR(3),      ForeignKey("currencies.code",
                           ondelete="RESTRICT", onupdate="CASCADE"),
                           nullable=False, default="PKR")
    category_id   = Column(SmallInteger, ForeignKey("expense_categories.id",
                           ondelete="RESTRICT", onupdate="CASCADE"),
                           nullable=False, default=7)
    split_type_id = Column(SmallInteger, ForeignKey("split_types.id",
                           ondelete="RESTRICT", onupdate="CASCADE"),
                           nullable=False, default=1)
    expense_date  = Column(DATE,         nullable=False)
    created_at    = Column(TIMESTAMP,    server_default=func.now(), nullable=False)
    updated_at    = Column(TIMESTAMP,    server_default=func.now(),
                           onupdate=func.now(), nullable=False)

    # Relationships
    group      = relationship("Group",           back_populates="expenses")
    payer      = relationship("User",            back_populates="expenses_paid",
                              foreign_keys=[paid_by])
    currency   = relationship("Currency",        back_populates="expenses")
    category   = relationship("ExpenseCategory", back_populates="expenses")
    split_type = relationship("SplitType",       back_populates="expenses")
    splits     = relationship("Split",            back_populates="expense",
                              cascade="all, delete-orphan")
