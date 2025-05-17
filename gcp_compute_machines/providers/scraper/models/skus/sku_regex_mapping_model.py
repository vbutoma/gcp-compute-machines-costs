from pydantic import BaseModel, ConfigDict
from typing import Optional


class SKURegexMappingModel(BaseModel):

    ondemand: str
    cud1y: Optional[str] = None
    cud3y: Optional[str] = None
    spot: Optional[str] = None

    def get_usage_type(self, usage_type) -> Optional[str]:
        return self.model_dump().get(usage_type, None)

__all__ = [
    'SKURegexMappingModel'
]
