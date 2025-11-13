from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String, UniqueConstraint, func, ForeignKey, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domains.enums import FileStatus, TransactionType, UserStatus, MenuType

class ModelBase(DeclarativeBase):
    pass

class ViewBase(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

class User(ModelBase, TimestampMixin):
    __tablename__ = "users"

    userid: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: uuid4().hex, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=True) #用户姓名
    status: Mapped[UserStatus] = mapped_column(SqlEnum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    idcard: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=True)
    area_id: Mapped[str] = mapped_column(String(32), ForeignKey("areas.area_id"), index=True, nullable=True) #区域ID
    # 关系
    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles",
        backref="users", # 反向关系，方便从角色查询用户，可选但推荐
        lazy="selectin" # 加载策略，根据需求选择
    )
    areainfo: Mapped["Area"] = relationship("Area", backref="users")

class Role(ModelBase, TimestampMixin):
    __tablename__ = "roles"

    role_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: uuid4().hex, primary_key=True)
    role_name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    role_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False) #状态,1:正常,0:禁用

class Area(ModelBase, TimestampMixin):
    __tablename__ = "areas"

    area_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: uuid4().hex, primary_key=True)  # 区域ID
    area_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)  # 区域编码
    area_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 区域名称
    parent_code: Mapped[str] = mapped_column(String(20), index=True, nullable=True)  # 父级区域编码
    level: Mapped[int] = mapped_column(Integer, nullable=False)  # 层级：1-省，2-市，3-区县
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 状态：1-正常，0-禁用

class Menu(ModelBase, TimestampMixin):
    __tablename__ = "menus"

    menu_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: uuid4().hex, primary_key=True)
    parent_id: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    menu_name: Mapped[str] = mapped_column(String(50), nullable=False)
    menu_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=True)
    path: Mapped[str] = mapped_column(String(255), nullable=True)
    type: Mapped[MenuType] = mapped_column(SqlEnum(MenuType), default=MenuType.GRID, nullable=False) #菜单类型,1:目录,2:菜单,3:按钮
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False) #状态,1:正常,0:禁用
    # 关系
    buttons: Mapped[list["Button"]] = relationship("Button", backref="menu")

class Button(ModelBase, TimestampMixin):
    __tablename__ = "buttons"

    button_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: uuid4().hex, primary_key=True)
    button_name: Mapped[str] = mapped_column(String(50), nullable=False)
    button_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False) #状态,1:正常,0:禁用
    menu_id: Mapped[str] = mapped_column(String(32), ForeignKey("menus.menu_id"), index=True, nullable=False) #菜单ID

class UserRole(ModelBase, TimestampMixin):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("userid", "role_id", name="unique_user_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    userid: Mapped[str] = mapped_column(String(32), ForeignKey("users.userid"), index=True)
    role_id: Mapped[str] = mapped_column(String(32), ForeignKey("roles.role_id"), index=True)

class RoleMenu(ModelBase, TimestampMixin):
    __tablename__ = "role_menus"
    __table_args__ = (
        UniqueConstraint("role_id", "menu_id", name="unique_role_menu"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[str] = mapped_column(String(32), ForeignKey("roles.role_id"), index=True)
    menu_id: Mapped[str] = mapped_column(String(32), ForeignKey("menus.menu_id"), index=True)

class RoleButton(ModelBase, TimestampMixin):
    __tablename__ = "role_buttons"
    __table_args__ = (
        UniqueConstraint("role_id", "button_id", name="unique_role_button"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[str] = mapped_column(String(32), ForeignKey("roles.role_id"), index=True)
    button_id: Mapped[str] = mapped_column(String(32), ForeignKey("buttons.button_id"), index=True)

class AreaRoleMenu(ModelBase, TimestampMixin):
    __tablename__ = "area_role_menus"
    __table_args__ = (
        UniqueConstraint("role_id", "area_id", "menu_id", name="unique_area_role_menu"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[str] = mapped_column(String(32), ForeignKey("roles.role_id"), index=True)
    area_id: Mapped[str] = mapped_column(String(32), ForeignKey("areas.area_id"), index=True)
    menu_id: Mapped[str] = mapped_column(String(32), ForeignKey("menus.menu_id"), index=True)

class AreaRoleButton(ModelBase, TimestampMixin):
    __tablename__ = "area_role_buttons"
    __table_args__ = (
        UniqueConstraint("role_id", "area_id", "button_id", name="unique_area_role_button"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[str] = mapped_column(String(32), ForeignKey("roles.role_id"), index=True)
    area_id: Mapped[str] = mapped_column(String(32), ForeignKey("areas.area_id"), index=True)
    button_id: Mapped[str] = mapped_column(String(32), ForeignKey("buttons.button_id"), index=True)

class Logger(ModelBase, TimestampMixin):
    __tablename__ = "loggers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    userid: Mapped[str] = mapped_column(String(32), ForeignKey("users.userid"), index=True)
    action: Mapped[str] = mapped_column(String(255))
    info: Mapped[str] = mapped_column(String(1000))  # 增加长度限制以存储更多的JSON数据

class Transaction(ModelBase, TimestampMixin):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: uuid4().hex, primary_key=True)
    create_userid: Mapped[str] = mapped_column(String(32), ForeignKey("users.userid"), index=True)
    update_userid: Mapped[str] = mapped_column(String(32), ForeignKey("users.userid"), nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    type: Mapped[TransactionType] = mapped_column(SqlEnum(TransactionType))
    remark: Mapped[str] = mapped_column(String(255), nullable=True)

class Fileassets(ModelBase, TimestampMixin):
    __tablename__ = "fileassets"

    fileid: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: uuid4().hex, primary_key=True)
    filepath: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=True)
    business_id: Mapped[str] = mapped_column(String(32), index=True)
    userid: Mapped[str] = mapped_column(String(32), ForeignKey("users.userid"), index=True)
    status: Mapped[FileStatus] = mapped_column(SqlEnum(FileStatus), default=FileStatus.ACTIVE, nullable=False)
    update_userid: Mapped[str] = mapped_column(String(32), nullable=True)

# 定义用户交易摘要视图
class UserTransactionSummaryView(ViewBase):
    __tablename__ = "user_transaction_summary"
    __table_args__ = {"info": {"is_view": True}}

    userid: Mapped[str] = mapped_column(String(32), primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), index=True)
    total_transactions: Mapped[int] = mapped_column(Integer, default=0)
    total_income: Mapped[float] = mapped_column(Float, default=0)
    total_expense: Mapped[float] = mapped_column(Float, default=0)
