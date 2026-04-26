# app/schemas/group.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.schemas.user import UserOut


class GroupCreate(BaseModel):
    name:        str
    description: Optional[str] = None
    category_id: Optional[int] = 5   # default = 'other'


class GroupUpdate(BaseModel):
    name:        Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None


class GroupMemberOut(BaseModel):
    id:        int
    user_id:   int
    role_id:   int
    role_name: Optional[str] = None
    joined_at: datetime

    model_config = {"from_attributes": True}


class GroupOut(BaseModel):
    id:            int
    name:          str
    description:   Optional[str]
    category_id:   int
    category_name: Optional[str] = None
    created_by:    int
    created_at:    datetime
    updated_at:    datetime

    model_config = {"from_attributes": True}


class GroupDetailOut(GroupOut):
    members: List[GroupMemberOut] = []


class AddMemberRequest(BaseModel):
    user_id: int
    role_id: Optional[int] = 2   # default = 'member'
