from uuid import UUID
from sqlmodel import Field, SQLModel


class UserUserTypeLink(SQLModel, table=True):
    __tablename__ = "user_user_type_link"

    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    user_type_id: UUID = Field(foreign_key="user_type.id", primary_key=True)
