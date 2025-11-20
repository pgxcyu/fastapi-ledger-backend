from enum import Enum

class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    FROZEN = "FROZEN"
    PENDING = "PENDING"
    DELETED = "DELETED"

class TransactionType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

class FileStatus(str, Enum):
    ACTIVE = "ACTIVE"
    QUARANTINE = "QUARANTINE"
    DELETED = "DELETED"
    MISSING = "MISSING"

class MenuType(str, Enum):
    GRID = "GRID"
    LIST = "LIST"
    CHART = "CHART"
    DIR = "DIR"

class ResourceType(str, Enum):
    MENU = "MENU"
    BUTTON = "BUTTON"