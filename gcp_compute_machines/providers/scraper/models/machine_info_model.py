from typing import Optional

from pydantic import field_validator, Field

from gcp_compute_machines.providers.base.models.base_machine_info_model import GCPMachineType


class ScrapedMachineInfoModel(GCPMachineType):

    local_ssd_support: bool
    local_ssd_enabled_by_default: bool
    local_ssd_default_size: Optional[int] = None

    # https://cloud.google.com/compute/docs/instances/nested-virtualization/overview
    nested_virtualization: bool = Field(alias='nested_virtualization_support')


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
