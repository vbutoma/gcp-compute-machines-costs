from pydantic import BaseModel, Field
from gcp_compute_machines.providers.base.models.helper_types import IntOrNone, FloatOrNone

class GCPMachineType(BaseModel):

    # machine
    name: str
    # family
    series: str
    # family_type
    family: str

    description: str | None = ''

    cpu_count: float = Field(alias='VCPUs')
    ram: float

    # https://cloud.google.com/compute/docs/cpu-platforms
    cpu_platforms: str | None = ""

    gpu_support: bool | None = None
    gpu_count_by_default: IntOrNone = None
    default_gpu: str | None = None

    #  https://cloud.google.com/network-tiers/docs/overview
    network_bandwidth: int = Field(alias='default_network_bandwidth')
    tier1_network_bandwidth: IntOrNone = None

    # region Scrapper auto-filled data

    # pricing model
    ondemand: FloatOrNone = None
    spot: FloatOrNone = None
    sud: FloatOrNone = None
    cud1y: FloatOrNone = None
    cud3y: FloatOrNone = None

    region: str | None = None

    # endregion


__all__ = [
    "GCPMachineType"
]
