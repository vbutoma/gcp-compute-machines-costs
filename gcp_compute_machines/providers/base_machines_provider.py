from abc import ABC, abstractmethod
from typing import List
from gcp_compute_machines.models.base_machine_info_model import BaseGCPMachine


class GCPMachinesProvider:

    def __init__(self):
        pass

    @abstractmethod
    def fetch_gcp_machines(self) -> List[BaseGCPMachine]:
        """
        An abstract method to fetch GCP machines data.

        :return: a list of GCP machines
        """
        pass


__all__ = [
    'GCPMachinesProvider'
]
