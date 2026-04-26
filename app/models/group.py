# app/models/group.py
from sqlalchemy import (
    Column, Integer, SmallInteger, String, TIMESTAMP, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Group(Base):
    __tablename__ = "groups"

    id          = Column(Integer,      primary_key=True, autoincrement=True)
    name        = Column(String(150),  nullable=False)
    description = Column(String(500),  nullable=True)
    category_id = Column(SmallInteger, ForeignKey("group_categories.id",
                         ondelete="RESTRICT", onupdate="CASCADE"),
                         nullable=False, default=5)
    created_by  = Column(Integer,      ForeignKey("users.id",
                         ondelete="RESTRICT", onupdate="CASCADE"),
                         nullable=False)
    created_at  = Column(TIMESTAMP,    server_default=func.now(), nullable=False)
    updated_at  = Column(TIMESTAMP,    server_default=func.now(),
                         onupdate=func.now(), nullable=False)

    # Relationships
    creator  = relationship("User",          back_populates="created_groups",
                            foreign_keys=[created_by])
    category = relationship("GroupCategory", back_populates="groups")
    members  = relationship("GroupMember",   back_populates="group",
                            cascade="all, delete-orphan")
    expenses = relationship("Expense",       back_populates="group",
                            cascade="all, delete-orphan")
    payments = relationship("Payment",       back_populates="group",
                            cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"

    id        = Column(Integer,      primary_key=True, autoincrement=True)
    group_id  = Column(Integer,      ForeignKey("groups.id",
                       ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id   = Column(Integer,      ForeignKey("users.id",
                       ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    role_id   = Column(SmallInteger, ForeignKey("member_roles.id",
                       ondelete="RESTRICT", onupdate="CASCADE"),
                       nullable=False, default=2)
    joined_at = Column(TIMESTAMP,    server_default=func.now(), nullable=False)

    # Relationships
    group = relationship("Group",      back_populates="members")
    user  = relationship("User",       back_populates="group_members")
    role  = relationship("MemberRole", back_populates="group_members")
