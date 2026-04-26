# app/schemas/expense.py
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, field_validator


class SplitInput(BaseModel):
    user_id:     int
    owed_amount: Decimal

    @field_validator("owed_amount")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("owed_amount must be >= 0")
        return v


class ExpenseCreate(BaseModel):
    title:         str
    description:   Optional[str]  = None
    amount:        Decimal
    currency_code: Optional[str]  = "PKR"
    category_id:   Optional[int]  = 7     # default = 'other'
    split_type_id: Optional[int]  = 1     # default = 'equal'
    expense_date:  date
    splits:        List[SplitInput]        # must be provided

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be > 0")
        return v

    @field_validator("splits")
    @classmethod
    def splits_not_empty(cls, v: List[SplitInput]) -> List[SplitInput]:
        if not v:
            raise ValueError("At least one split is required")
        return v


class ExpenseUpdate(BaseModel):
    title:         Optional[str]     = None
    description:   Optional[str]     = None
    amount:        Optional[Decimal] = None
    currency_code: Optional[str]     = None
    category_id:   Optional[int]     = None
    expense_date:  Optional[date]    = None


class SplitOut(BaseModel):
    id:          int
    user_id:     int
    owed_amount: Decimal
    is_settled:  bool
    created_at:  datetime

    model_config = {"from_attributes": True}


class ExpenseOut(BaseModel):
    id:            int
    group_id:      int
    paid_by:       int
    title:         str
    description:   Optional[str]
    amount:        Decimal
    currency_code: str
    category_id:   int
    split_type_id: int
    expense_date:  date
    created_at:    datetime
    splits:        List[SplitOut] = []

    model_config = {"from_attributes": True}
