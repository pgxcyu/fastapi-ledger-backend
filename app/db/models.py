from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String, UniqueConstraint, func, ForeignKey, Float, CheckConstraint, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domains.enums import FileStatus, TransactionType, UserStatus, MenuType, ResourceType

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
    default_role_id: Mapped[str] = mapped_column(String(32), ForeignKey("roles.role_id"), nullable=True)
    
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="user_role_scopes",
        back_populates="users",
        lazy="selectin",
        # 只加载有效的角色
        primaryjoin="and_(User.userid == UserRoleScope.userid, UserRoleScope.status == 1)",
        secondaryjoin="and_(UserRoleScope.role_id == Role.role_id, Role.status == 1)"
    )

class Role(ModelBase, TimestampMixin):
    __tablename__ = "roles"

    role_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: uuid4().hex, primary_key=True)
    role_name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    role_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False) #状态,1:正常,0:禁用

    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="user_role_scopes",
        back_populates="roles",
        lazy="selectin"
    )

class Area(ModelBase, TimestampMixin):
    __tablename__ = "areas"

    area_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: uuid4().hex, primary_key=True)  # 区域ID
    area_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)  # 区域编码
    area_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 区域名称
    parent_code: Mapped[str] = mapped_column(String(20), index=True, nullable=True)  # 父级区域编码
    level: Mapped[int] = mapped_column(Integer, nullable=False)  # 层级：1-省，2-市，3-区县
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 状态：1-正常，0-禁用


class Resource(ModelBase, TimestampMixin):
    __tablename__ = "resources"
    __table_args__ = (
        # 确保当资源类型为menu时，menu_type字段必须有值
        CheckConstraint(
            'rtype != "menu" OR menu_type IS NOT NULL',
            name='check_menu_menutype_required'
        ),
        # 确保当资源类型为button时，必须有父级
        CheckConstraint(
            'rtype != "button" OR parent_id IS NOT NULL',
            name='check_button_parent_required'
        ),
    )

    rid: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: uuid4().hex, primary_key=True)
    rname: Mapped[str] = mapped_column(String(50), nullable=False)
    rcode: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    rtype: Mapped[ResourceType] = mapped_column(SqlEnum(ResourceType), nullable=False) #资源类型,menu:菜单,button:按钮
    parent_id: Mapped[str] = mapped_column(String(32), ForeignKey("resources.rid"), index=True, nullable=True) #父资源ID

    # 通用字段
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False) #状态,1:正常,0:禁用

    # 菜单独有字段
    icon: Mapped[str] = mapped_column(String(50), nullable=True)
    path: Mapped[str] = mapped_column(String(255), nullable=True)
    menu_type: Mapped[MenuType] = mapped_column(SqlEnum(MenuType), nullable=True) #菜单类型, grid:九宫格,list:列表,chart:图表

    # 自引用关系
    parent: Mapped["Resource"] = relationship("Resource", remote_side=[rid], backref="children", lazy="selectin")


class UserRoleScope(ModelBase, TimestampMixin):
    __tablename__ = "user_role_scopes"
    __table_args__ = (
        UniqueConstraint("userid", "role_id", "area_id", name="unique_user_role_area"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    userid: Mapped[str] = mapped_column(String(32), ForeignKey("users.userid"), index=True)
    role_id: Mapped[str] = mapped_column(String(32), ForeignKey("roles.role_id"), index=True)
    area_id: Mapped[str] = mapped_column(String(32), ForeignKey("areas.area_id"), index=True, nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False) #状态,1:正常,0:禁用


class RoleAreaGrant(ModelBase, TimestampMixin):
    __tablename__ = "role_area_grants"
    __table_args__ = (
        UniqueConstraint("role_id", "area_id", name="unique_role_area"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[str] = mapped_column(String(32), ForeignKey("roles.role_id"), index=True, nullable=False)
    area_id: Mapped[str] = mapped_column(String(32), ForeignKey("areas.area_id"), index=True, nullable=True)
    rid: Mapped[str] = mapped_column(String(32), ForeignKey("resources.rid"), index=True, nullable=False) #资源ID
    is_grant: Mapped[int] = mapped_column(Integer, default=0, nullable=False) #是否授权 1:授权,0:未授权

    
# 审计日志表 - 简化版企业级审计设计
class AuditLog(ModelBase, TimestampMixin):
    """
    简化版企业级审计日志表
    保留核心审计功能，避免过度复杂化
    """
    __tablename__ = 'audit_logs'
    
    # === 基础标识字段 ===
    audit_id: Mapped[str] = mapped_column(String(32), primary_key=True, comment='审计唯一标识')
    
    # === 用户和会话信息 ===
    user_id: Mapped[str] = mapped_column(String(32), nullable=True, comment='操作用户ID')
    user_name: Mapped[str] = mapped_column(String(100), nullable=True, comment='操作用户名')
    session_id: Mapped[str] = mapped_column(String(32), nullable=True, comment='会话ID')
    role_id: Mapped[str] = mapped_column(String(32), nullable=True, comment='角色ID')
    request_id: Mapped[str] = mapped_column(String(32), nullable=True, comment='请求ID')
    
    # === 请求信息 ===
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True, comment='客户端IP地址')
    user_agent: Mapped[str] = mapped_column(String(500), nullable=True, comment='用户代理')
    request_method: Mapped[str] = mapped_column(String(10), nullable=True, comment='HTTP请求方法')
    request_path: Mapped[str] = mapped_column(String(255), nullable=True, comment='请求路径')
    response_status: Mapped[int] = mapped_column(Integer, nullable=True, comment='HTTP响应状态码')
    response_time: Mapped[float] = mapped_column(Float, nullable=True, comment='响应时间(秒)')
    country: Mapped[str] = mapped_column(String(100), nullable=True, comment='国家')
    region: Mapped[str] = mapped_column(String(100), nullable=True, comment='地区/省份')
    city: Mapped[str] = mapped_column(String(100), nullable=True, comment='城市')
    device_fingerprint: Mapped[str] = mapped_column(String(255), nullable=True, comment='设备指纹')
    browser_type: Mapped[str] = mapped_column(String(50), nullable=True, comment='浏览器类型')
    os_type: Mapped[str] = mapped_column(String(50), nullable=True, comment='操作系统类型')
    
    # === 操作信息 ===
    operation_type: Mapped[str] = mapped_column(String(20), nullable=False, comment='操作类型(CREATE/UPDATE/DELETE/READ/LOGIN/LOGOUT)')
    operation_module: Mapped[str] = mapped_column(String(50), nullable=False, comment='操作模块')
    operation_description: Mapped[str] = mapped_column(String(200), nullable=False, comment='操作描述')
    
    # === 资源信息 ===
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, comment='资源类型(USER/TRANSACTION/ROLE/SYSTEM)')
    resource_id: Mapped[str] = mapped_column(String(32), nullable=True, comment='资源ID')
    resource_name: Mapped[str] = mapped_column(String(200), nullable=True, comment='资源名称')
    
    # === 审计级别和风险 ===
    audit_level: Mapped[str] = mapped_column(String(20), nullable=False, default='INFO', comment='审计级别(INFO/WARNING/ERROR/CRITICAL)')
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default='LOW', comment='风险级别(LOW/MEDIUM/HIGH/CRITICAL)')
    sensitive_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment='敏感操作标记')
    
    # === 操作结果 ===
    operation_result: Mapped[str] = mapped_column(String(20), nullable=False, default='SUCCESS', comment='操作结果(SUCCESS/FAILURE)')
    error_message: Mapped[str] = mapped_column(Text, nullable=True, comment='错误信息')
    
    # === 数据变更 ===
    before_data: Mapped[str] = mapped_column(Text, nullable=True, comment='操作前数据(JSON)')
    after_data: Mapped[str] = mapped_column(Text, nullable=True, comment='操作后数据(JSON)')
    
    # === 业务上下文 ===
    business_context: Mapped[str] = mapped_column(Text, nullable=True, comment='业务上下文')

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


# 添加事件监听器来验证button资源的父级必须是menu类型
from sqlalchemy import event, select

@event.listens_for(Resource, 'before_insert')
@event.listens_for(Resource, 'before_update')
def validate_button_parent(mapper, connection, target):
    """
    验证当资源类型为button时，其父级资源的类型必须为menu
    """
    if target.rtype == ResourceType.BUTTON:
        # 检查是否有父级ID
        if not target.parent_id:
            raise ValueError("Button resource must have a parent_id")
        
        # 使用原始SQL查询来获取父级资源的类型，避免潜在的循环引用问题
        from sqlalchemy import text
        result = connection.execute(
            text("SELECT rtype FROM resources WHERE rid = :parent_id"),
            {"parent_id": target.parent_id}
        )
        parent_row = result.fetchone()
        
        # 验证父级资源是否存在且类型为menu
        if not parent_row:
            raise ValueError(f"Button resource parent not found with id: {target.parent_id}")
        
        parent_rtype = parent_row[0]
        # 确保比较时考虑大小写和字符串值
        if str(parent_rtype).lower() != ResourceType.MENU.value.lower():
            raise ValueError(f"Button resource must have a parent with type 'menu', got '{parent_rtype}'")
