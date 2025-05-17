from gcp_compute_machines.providers.base.base_machines_provider import GCPMachinesProvider
from gcp_compute_machines.providers.gcloud_compute.models import GcloudComputeMachineInfoModel
from datetime import datetime
import yaml
import csv
import requests
import loguru
import sys


class GCloudComputeMachinesProvider(GCPMachinesProvider):
    """
    This provider is done on top of the https://gcloud-compute.com/ website.

    Link to original repository: https://github.com/Cyclenerd/google-cloud-compute-machine-types
    """

    def __init__(
        self,
        logger = None,
        log_level: str = 'DEBUG',  # used only if logger is None
    ):
        if logger is None:
            self.logger = loguru.logger
            self.logger.remove()
            self.logger.add(sys.stdout, level=log_level)
        else:
            self.logger = logger
        self.__url = "https://gcloud-compute.com/machine-types-regions.csv"
        self.__data: list[GcloudComputeMachineInfoModel] = []

    def fetch_gcp_machines(self) -> list[GcloudComputeMachineInfoModel]:
        self.logger.info(f"Loading data from {self.__url}")
        # Download the CSV data
        response = requests.get(self.__url)
        self.logger.debug(f'Got {response.status_code} for GET: {self.__url}')
        response.raise_for_status()
        # Decode bytes to string (assuming UTF-8 encoding)
        csv_data = response.text
        # Parse CSV rows
        reader = csv.reader(csv_data.splitlines())
        # Skip header
        header = next(reader)
        # Instantiate model for each row
        result = []
        for row in reader:
            # Map header to row to create a dict
            data = dict(zip(header, row))
            # Create Pydantic model instance
            item = GcloudComputeMachineInfoModel(**data)
            result.append(item)
        self.__data = result[:]
        self.logger.info(f"Loaded {len(self.__data)} GCP machines from {self.__url}")
        return result

    def dump_pricing_info(self, file_path: str):
        metadata = {
            'last_time_updated': int(datetime.now().timestamp()),
            "origin": self.__url
        }
        with open(file_path, 'w') as file:
            yaml.dump({
                'metadata': metadata,
                'machines': [x.model_dump() for x in self.__data]
            }, file)


__all__ = [
    'GCloudComputeMachinesProvider'
]
