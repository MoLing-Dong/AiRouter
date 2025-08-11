from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class LLMModelCreate(BaseModel):
    name: str
    llm_type: str
    description: Optional[str] = None
    is_enabled: bool = True


class LLMModelUpdate(BaseModel):
    name: Optional[str] = None
    llm_type: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None


class LLMProviderCreate(BaseModel):
    name: str
    provider_type: str
    official_endpoint: Optional[str] = None
    third_party_endpoint: Optional[str] = None
    description: Optional[str] = None
    is_enabled: bool = True


class LLMProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    official_endpoint: Optional[str] = None
    third_party_endpoint: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None


class LLMProviderApiKeyCreate(BaseModel):
    provider_id: int
    name: Optional[str] = None
    api_key: str
    base_url: Optional[str] = None
    is_enabled: bool = True
    is_preferred: bool = False
    weight: int = 10
    daily_quota: Optional[int] = None
    description: Optional[str] = None


class LLMProviderApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_preferred: Optional[bool] = None
    weight: Optional[int] = None
    daily_quota: Optional[int] = None
    description: Optional[str] = None


class LLMModelProviderCreate(BaseModel):
    llm_id: int
    provider_id: int
    weight: int = 10
    is_preferred: bool = False
    is_enabled: bool = True


class LLMModelProviderUpdate(BaseModel):
    llm_id: Optional[int] = None
    provider_id: Optional[int] = None
    weight: Optional[int] = None
    is_preferred: Optional[bool] = None
    is_enabled: Optional[bool] = None


class LLMModelParamCreate(BaseModel):
    llm_id: int
    provider_id: Optional[int] = None
    param_key: str
    param_value: Dict[str, Any]  # JSON格式
    param_type: Optional[str] = None
    description: Optional[str] = None
    is_enabled: bool = True
