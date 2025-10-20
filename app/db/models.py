from datetime import datetime, timezone
from ntpath import isdir
from re import M
import string
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domains.enums import TransactionType, UserStatus, FileStatus

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    userid: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: uuid4().hex)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    status: Mapped[UserStatus] = mapped_column(SqlEnum(UserStatus), default=UserStatus.ACTIVE, nullable=False)

class Logger(Base, TimestampMixin):
    __tablename__ = "loggers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    userid: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(255))
    info: Mapped[str] = mapped_column(String(1000))  # 增加长度限制以存储更多的JSON数据

class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transaction_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: uuid4().hex)
    create_userid: Mapped[str] = mapped_column(String(32), index=True)
    update_userid: Mapped[str] = mapped_column(String(32), nullable=True)
    amount: Mapped[float] = mapped_column(Integer, default=0, nullable=False)
    type: Mapped[TransactionType] = mapped_column(SqlEnum(TransactionType))
    remark: Mapped[str] = mapped_column(String(255), nullable=True)

class Fileassets(Base, TimestampMixin):
    __tablename__ = "fileassets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fileid: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: uuid4().hex)
    filepath: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(20), nullable=True)
    business_id: Mapped[str] = mapped_column(String(32), index=True)
    userid: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[FileStatus] = mapped_column(SqlEnum(FileStatus), default=FileStatus.ACTIVE, nullable=False)
    update_userid: Mapped[str] = mapped_column(String(32), nullable=True)
