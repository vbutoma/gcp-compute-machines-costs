from pydantic import BaseModel

from .sku_regex_mapping_model import SKURegexMappingModel


class GPUInfoModel(BaseModel):
    skus: SKURegexMappingModel


__all__ = [
    'GPUInfoModel'
]