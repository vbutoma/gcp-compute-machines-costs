from typing import Optional

from pydantic import BaseModel, model_validator

from .sku_regex_mapping_model import SKURegexMappingModel


class ComputeFamilySKUModel(BaseModel):
    cpu: Optional[SKURegexMappingModel] = None
    ram: Optional[SKURegexMappingModel] = None
    instance: Optional[SKURegexMappingModel] = None

    @model_validator(mode='after')
    def validate_model(self) -> 'ComputeFamilySKUModel':
        if self.instance and (self.cpu or self.ram):
            raise ValueError('instance SKUs can be provided only for f1/g1 machines.')
        return self


__all__ = [
    'ComputeFamilySKUModel'
]
