from gcp_compute_machines.providers.base_machines_provider import GCPMachinesProvider
import requests
import csv


class GcloudComputeMachinesProvider(GCPMachinesProvider):
    """
    This provider is done on top of the https://gcloud-compute.com/ website.

    Link to original repository: https://github.com/Cyclenerd/google-cloud-compute-machine-types
    """

    def __init__(self):
        pass


    def fetch_gcp_machines(self):
        # todo:
        pass