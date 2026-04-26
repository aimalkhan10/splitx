# app/models/payment.py
from sqlalchemy import (
    Column, Integer, SmallInteger, DECIMAL, CHAR,
    String, TIMESTAMP, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id            = Column(Integer,       primary_key=True, autoincrement=True)
    group_id      = Column(Integer,       ForeignKey("groups.id",
                           ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    payer_id      = Column(Integer,       ForeignKey("users.id",
                           ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    payee_id      = Column(Integer,       ForeignKey("users.id",
                           ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    amount        = Column(DECIMAL(12,2), nullable=False)
    currency_code = Column(CHAR(3),       ForeignKey("currencies.code",
                           ondelete="RESTRICT", onupdate="CASCADE"),
                           nullable=False, default="PKR")
    status_id     = Column(SmallInteger,  ForeignKey("payment_statuses.id",
                           ondelete="RESTRICT", onupdate="CASCADE"),
                           nullable=False, default=1)
    note          = Column(String(300),   nullable=True)
    paid_at       = Column(TIMESTAMP,     nullable=True)
    created_at    = Column(TIMESTAMP,     server_default=func.now(), nullable=False)
    updated_at    = Column(TIMESTAMP,     server_default=func.now(),
                           onupdate=func.now(), nullable=False)

    # Relationships
    group       = relationship("Group",         back_populates="payments")
    payer       = relationship("User",          back_populates="payments_sent",
                               foreign_keys=[payer_id])
    payee       = relationship("User",          back_populates="payments_received",
                               foreign_keys=[payee_id])
    currency    = relationship("Currency",      back_populates="payments")
    status      = relationship("PaymentStatus", back_populates="payments")
    settlements = relationship("SplitSettlement", back_populates="payment",
                               cascade="all, delete-orphan")
