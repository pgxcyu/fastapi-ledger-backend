from enum import Enum

class UserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    FROZEN = "frozen"
    PENDING = "pending"
    DELETED = "deleted"

class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"

class FileStatus(str, Enum):
    ACTIVE = "active"
    QUARANTINE = "quarantine"
    DELETED = "deleted"
    MISSING = "missing"

class MenuType(str, Enum):
    GRID = "grid"
    LIST = "list"
    CHART = "chart"
    DIR = "dir"

class ResourceType(str, Enum):
    MENU = "menu"
    BUTTON = "button"