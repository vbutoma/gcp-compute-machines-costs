from pydantic import BaseModel

from .sku_regex_mapping_model import SKURegexMappingModel


class BaseSKUModel(BaseModel):
    skus: SKURegexMappingModel


__all__ = [
    'BaseSKUModel'
]
