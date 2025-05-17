import math
from gcp_compute_machines.providers.base.models.base_machine_info_model import GCPMachineType
from gcp_compute_machines.providers.base.models.helper_types import FloatOrNone, IntOrNone
from pydantic import BaseModel, field_validator, Field
from gcp_compute_machines.constants import AVG_HOURS_PER_MONTH


class GcloudComputeMachineInfoModel(GCPMachineType):
    """
    Pydantic model for data from: https://gcloud-compute.com/machine-types-regions.csv
    """

    ram: float = Field(alias="memoryGB")

    # https://cloud.google.com/compute/docs/cpu-platforms
    cpu_platforms: str = Field(alias="availableCpuPlatform")

    gpu_count_by_default: IntOrNone = Field(default=None, alias="acceleratorCount")

    # pricing model
    ondemand: FloatOrNone = Field(default=None, alias="month")
    spot: FloatOrNone = Field(default=None, alias="monthSpot")
    cud1y: FloatOrNone = Field(default=None, alias="month1yCud")
    cud3y: FloatOrNone = Field(default=None, alias="month3yCud")
    # endregion


    # optional fields
    location: str | None = None
    region_location: str | None = Field(default=None, alias='regionLocation')
    region_location_long: str | None = Field(default=None, alias='regionLocationLong')
    region_location_country_code: str | None = Field(default=None, alias='regionLocationCountryCode')
    region_cfe: FloatOrNone = Field(default=None, alias='regionCfe')
    region_co2_kwh: FloatOrNone = Field(default=None, alias='regionCo2Kwh')
    region_low_co2: FloatOrNone = Field(default=None, alias='regionLowCo2')
    region_lat: FloatOrNone = Field(default=None, alias='regionLat')
    region_lng: FloatOrNone = Field(default=None, alias='regionLng')
    region_public_ipv4_addr: int | None = Field(default=None, alias='regionPublicIpv4Addr')
    zone_count: int | None = Field(default=None, alias='zoneCount')
    zones: str | None = None

    cpu_count: float = Field(alias='vCpus')
    shared_cpu: int | None = Field(default=None, alias="sharedCpu")
    intel: int | None = None
    amd: int | None = None
    arm: int | None = None

    cpu_platform_count: int | None = Field(default=None, alias="cpuPlatformCount")
    cpu_platform: str | None = Field(default=None, alias="cpuPlatform")

    cpu_base_clock: FloatOrNone = Field(default=None, alias="cpuBaseClock")
    cpu_turbo_clock: FloatOrNone = Field(default=None, alias="cpuTurboClock")
    cpu_single_max_turbo_clock: FloatOrNone = Field(default=None, alias="cpuSingleMaxTurboClock")

    available_cpu_platform_count: int | None = Field(default=None, alias="availableCpuPlatformCount")

    coremark_score: FloatOrNone = Field(default=None, alias="coremarkScore")
    standard_deviation: FloatOrNone = Field(default=None, alias="standardDeviation")
    sample_count: FloatOrNone = Field(default=None, alias="sampleCount")

    network_bandwidth: int = Field(alias='bandwidth')
    tier1_network_bandwidth: IntOrNone = Field(alias='tier1')

    @field_validator('ondemand', mode='after')
    @classmethod
    def normalize_ondemand(cls, v: float | None) -> float | None:
        if v is None:
            return None
        return v / AVG_HOURS_PER_MONTH

    @field_validator('spot', mode='after')
    @classmethod
    def normalize_spot(cls, v: float | None) -> float | None:
        if v is None:
            return None
        return v / AVG_HOURS_PER_MONTH

    @field_validator('cud1y', mode='after')
    @classmethod
    def normalize_cud1y(cls, v: float | None) -> float | None:
        if v is None:
            return None
        return v / AVG_HOURS_PER_MONTH

    @field_validator('cud3y', mode='after')
    @classmethod
    def normalize_cud3y(cls, v: float | None) -> float | None:
        if v is None:
            return None
        return v / AVG_HOURS_PER_MONTH


    @field_validator('sud', mode='after')
    @classmethod
    def normalize_sud(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if math.fabs(v) < 1e-5:
            return None
        return v / AVG_HOURS_PER_MONTH
