from gcp_compute_machines.providers.base import GCPMachinesProvider
from gcp_compute_machines.providers.scraper.models import ScrapedMachineInfoModel
from gcp_compute_machines.providers.scraper.scraper import InstanceScraper


class GCPMachinesScraper(GCPMachinesProvider):

    def __init__(
        self,
        gpc_project_name: str,
        gcp_sa_account_path: str,

    ):
        self._gcp_project_name = gpc_project_name
        self._gcp_sa_account_path = gcp_sa_account_path

        self._scraper = InstanceScraper(
            gcp_project=self._gcp_project_name,
            sa_path=self._gcp_sa_account_path
        )

    def fetch_gcp_machines(
        self,
        dump: bool,
        load: bool,
        *args,
        **kwargs
    ) -> list[ScrapedMachineInfoModel]:
        self._scraper.run(
            # dump=True means that app saves the scrapped SKUs data locally
            dump=True,
            # Set load=True if you want to use local SKUs data between sequential runs.
            load=False
        )
        return self._scraper.flat_pricing_data

    def dump_pricing_info(self, file_path: str):
        self._scraper.dump_flat_pricing_data(
            flat_pricing_data_file_path=file_path
        )
