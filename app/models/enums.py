import enum


class StorageType(str, enum.Enum):

    PERSONAL = "personal"
    GLOBAL = "global"


class GlobalGrantType(str, enum.Enum):

    CAN_CREATE_GLOBAL_STORAGE = "CAN_CREATE_GLOBAL_STORAGE"
    CAN_MANAGE_USERS = "CAN_MANAGE_USERS"


class StorageGrantType(str, enum.Enum):

    STORAGE_READ = "STORAGE_READ"
    STORAGE_WRITE = "STORAGE_WRITE"
    STORAGE_DELETE = "STORAGE_DELETE"
    STORAGE_MANAGE_ACCESS = "STORAGE_MANAGE_ACCESS"
