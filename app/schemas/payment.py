# app/schemas/payment.py
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, field_validator


class SettlementInput(BaseModel):
    split_id:       int
    settled_amount: Decimal

    @field_validator("settled_amount")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("settled_amount must be > 0")
        return v


class PaymentCreate(BaseModel):
    payer_id:      Optional[int]              = None
    payee_id:      int
    amount:        Decimal
    currency_code: Optional[str]              = "PKR"
    note:          Optional[str]              = None
    status_id:     Optional[int]              = 1
    settlements:   Optional[List[SettlementInput]] = []

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be > 0")
        return v


class PaymentStatusUpdate(BaseModel):
    status_id: int   # 1=pending 2=completed 3=cancelled


class SettlementOut(BaseModel):
    id:             int
    split_id:       int
    settled_amount: Decimal

    model_config = {"from_attributes": True}


class PaymentOut(BaseModel):
    id:            int
    group_id:      int
    payer_id:      int
    payee_id:      int
    amount:        Decimal
    currency_code: str
    status_id:     int
    note:          Optional[str]
    paid_at:       Optional[datetime]
    created_at:    datetime
    settlements:   List[SettlementOut] = []

    model_config = {"from_attributes": True}
