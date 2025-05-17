from abc import abstractmethod
from gcp_compute_machines.providers.base.models.base_machine_info_model import GCPMachineType


class GCPMachinesProvider:


    @abstractmethod
    def fetch_gcp_machines(self, *args, **kwargs) -> list[GCPMachineType]:
        """
        An abstract method to fetch GCP machines data.

        :return: a list of GCP machines
        """
        pass

    @abstractmethod
    def dump_pricing_info(self, *args, **kwargs):
        pass


__all__ = [
    'GCPMachinesProvider'
]
