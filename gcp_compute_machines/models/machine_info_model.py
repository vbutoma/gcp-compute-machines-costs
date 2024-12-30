from typing import Optional

from pydantic import BaseModel, field_validator, Field


class MachineInfoModel(BaseModel):

    machine: str
    family: str
    family_type: str
    cpu_count: float = Field(alias='VCPUs')
    ram: float

    local_ssd_support: bool
    local_ssd_enabled_by_default: bool
    local_ssd_default_size: Optional[int] = None

    cpu_platforms: str

    gpu_support: bool = False
    gpu_count_by_default: Optional[int] = None
    default_gpu: Optional[str] = None

    network_bandwidth: int = Field(alias='default_network_bandwidth')
    tier1_network_bandwidth: Optional[int] = None

    nested_virtualization: bool = Field(alias='nested_virtualization_support')

    # region Scrapper auto-filled data

    # pricing model
    ondemand: Optional[float] = None
    spot: Optional[float] = None
    sud: Optional[float] = None
    cud1y: Optional[float] = None
    cud3y: Optional[float] = None

    region: Optional[str] = None

    #endregion


    @field_validator('tier1_network_bandwidth', mode='before')
    @classmethod
    def convert_and_validate_tier1_network_bandwidth(cls, v) -> Optional[int]:
        if isinstance(v, int):
            return v
        if isinstance(v, str) and len(v) == 0:
            return None
        if v is None:
            return None
        return int(v)

    @field_validator('nested_virtualization', mode='before')
    @classmethod
    def convert_and_validate_nested_virtualization(cls, v) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str) and len(v) == 0:
            return False
        return bool(int(v))

    @field_validator('local_ssd_default_size', mode='before')
    @classmethod
    def convert_and_validate_local_ssd_default_size(cls, v) -> Optional[int]:
        if isinstance(v, int):
            return v
        if isinstance(v, str) and len(v) == 0:
            return None
        if v is None:
            return None
        return int(v)

    @field_validator('default_gpu', mode='before')
    @classmethod
    def convert_and_validate_default_gpu(cls, v) -> Optional[str]:
        if isinstance(v, str) and len(v) == 0:
            return None
        if v is None:
            return None
        return v
