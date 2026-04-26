# app/models/split.py
from sqlalchemy import (
    Column, Integer, DECIMAL, TIMESTAMP, ForeignKey,
    Boolean, func, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Split(Base):
    __tablename__ = "splits"
    __table_args__ = (
        UniqueConstraint("expense_id", "user_id", name="uq_split_expense_user"),
    )

    id          = Column(Integer,       primary_key=True, autoincrement=True)
    expense_id  = Column(Integer,       ForeignKey("expenses.id",
                         ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id     = Column(Integer,       ForeignKey("users.id",
                         ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    owed_amount = Column(DECIMAL(12,2), nullable=False)
    is_settled  = Column(Boolean,       nullable=False, default=False)
    created_at  = Column(TIMESTAMP,     server_default=func.now(), nullable=False)
    updated_at  = Column(TIMESTAMP,     server_default=func.now(),
                         onupdate=func.now(), nullable=False)

    # Relationships
    expense      = relationship("Expense",         back_populates="splits")
    user         = relationship("User",            back_populates="splits")
    settlements  = relationship("SplitSettlement", back_populates="split",
                                cascade="all, delete-orphan")


class SplitSettlement(Base):
    __tablename__ = "split_settlements"
    __table_args__ = (
        UniqueConstraint("payment_id", "split_id", name="uq_settlement"),
    )

    id             = Column(Integer,       primary_key=True, autoincrement=True)
    payment_id     = Column(Integer,       ForeignKey("payments.id",
                            ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    split_id       = Column(Integer,       ForeignKey("splits.id",
                            ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    settled_amount = Column(DECIMAL(12,2), nullable=False)

    # Relationships
    payment = relationship("Payment", back_populates="settlements")
    split   = relationship("Split",   back_populates="settlements")
