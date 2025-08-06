import enum


class LLMTypeEnum(enum.Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class ProviderTypeEnum(enum.Enum):
    PUBLIC_CLOUD = "PUBLIC_CLOUD"
    THIRD_PARTY = "THIRD_PARTY"
    PRIVATE = "PRIVATE"


class ParamTypeEnum(enum.Enum):
    HYPERPARAMETER = "hyperparameter"
    CONFIG = "config"
    OTHER = "other"
