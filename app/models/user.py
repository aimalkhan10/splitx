# app/models/user.py
from sqlalchemy import Column, Integer, String, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer,     primary_key=True, autoincrement=True, index=True)
    first_name    = Column(String(60),  nullable=False)
    last_name     = Column(String(60),  nullable=False)
    email         = Column(String(150), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    phone         = Column(String(20),  nullable=True)
    avatar_url    = Column(String(500), nullable=True)
    created_at    = Column(TIMESTAMP,   server_default=func.now(), nullable=False)
    updated_at    = Column(TIMESTAMP,   server_default=func.now(),
                           onupdate=func.now(), nullable=False)

    # Relationships
    created_groups  = relationship("Group",       back_populates="creator",
                                   foreign_keys="Group.created_by")
    group_members   = relationship("GroupMember", back_populates="user",
                                   cascade="all, delete-orphan")
    expenses_paid   = relationship("Expense",     back_populates="payer",
                                   foreign_keys="Expense.paid_by")
    splits          = relationship("Split",        back_populates="user")
    payments_sent   = relationship("Payment",     back_populates="payer",
                                   foreign_keys="Payment.payer_id")
    payments_received = relationship("Payment",   back_populates="payee",
                                   foreign_keys="Payment.payee_id")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
