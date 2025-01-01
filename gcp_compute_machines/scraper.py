import csv
import json
import loguru
import yaml
import os
import re
import sys

from datetime import datetime
from gcp_compute_machines.models import *
from gcp_compute_machines.exceptions import ZeroSKURegexMatch, MultipleSKURegexMatch
from gcp_compute_machines.constants import *

from google.cloud import \
    billing_v1, \
    compute_v1
from google.oauth2 import service_account
from typing import Optional, List, Dict, Any, Literal


def nice(number: float, digits=5) -> float:
    return round(number, digits)


class InstanceScraper:
    # 365 * 24 / 12 - GCP uses the same value
    AVG_HOURS_PER_MONTH = 730

    DEFAULT_REGION = 'us-east1'
    DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), 'mappings')
    SUPPORTED_MACHINE_TYPES: List[str] = [
        'accelerator-optimized',
        'compute-optimized',
        'general-purpose',
        'storage-optimized',
        'memory-optimized'
    ]

    GCP_INSTANCES_DATA = 'gcp_instances.yaml'
    GCP_SKU_DATA = 'gcp_sku.yaml'
    GCP_SKU_DATA_JSON = 'gcp_sku.json'
    GCP_COMPUTE_ENGINE_SERVICE_NAME = 'services/6F81-5844-456A'

    def __init__(
        self,
        gcp_project: str,
        sa_path: str,
        logger: Optional[Any] = None,
        log_level: str = 'DEBUG',  # used only if logger is None
        data_dir: Optional[str] = None,
        machine_families: Optional[List[str]] = None,
    ):
        if logger is None:
            self.logger = loguru.logger
            self.logger.remove()
            self.logger.add(sys.stdout, level=log_level)
        else:
            self.logger = logger
        self.gcp_project = gcp_project

        self.credentials = service_account.Credentials.from_service_account_file(sa_path)
        self.regions_client = compute_v1.RegionsClient(credentials=self.credentials)
        self.zones_client = compute_v1.ZonesClient(credentials=self.credentials)
        self.machines_client = compute_v1.MachineTypesClient(credentials=self.credentials)

        if machine_families is None:
            self.machine_families = self.SUPPORTED_MACHINE_TYPES
        else:
            self.machine_families = machine_families
        self.data_dir = self.DEFAULT_DATA_DIR if data_dir is None else data_dir

        # Load GPU skus mapping
        self.gpus: Dict[str, GPUInfoModel] = {}
        self.__load_gpu_info()

        # Load families and machines data
        self.machine_family_sku: Dict[str, ComputeFamilySKUModel] = dict()
        self.general_machines_info: Dict[str, MachineInfoModel] = dict()
        self.__load_machine_families_info()

        self.pricing_data = {}
        self.flat_pricing_data: List[MachineInfoModel] = []
        self.regions = []
        self.zones = []
        self.machines = {}
        self.on_demand_skus = []
        self.spot_skus = []
        self.cud1_skus = []
        self.cud3_skus = []
        self.skus = {
            OnDemandUsage: [],
            SpotUsage: [],
            CommitmentOneYearUsage: [],
            CommitmentThreeYearsUsage: [],
        }

    def __load_gpu_info(self):
        with open(os.path.join(self.data_dir, 'gpu-skus-mapping.yaml'), 'r') as file:
            self.logger.debug('Loading GPU mapping data')
            gpu_skus_mapping_data = yaml.safe_load(file)
            for k, v in gpu_skus_mapping_data.items():
                self.gpus[k] = GPUInfoModel(**v)
                self.logger.debug(
                    f'Loaded {k} GPU sku data: {self.gpus[k]}'
                )

    def __load_machine_families_info(self):
        for machine_family in self.machine_families:
            family_costs_mapping_filepath = os.path.join(self.data_dir, f'{machine_family}-machines-sku.yaml')
            family_general_info_mapping_filepath = os.path.join(self.data_dir, f'{machine_family}-machines.csv')

            with open(family_costs_mapping_filepath, 'r') as file:
                skus_mapping_data = yaml.safe_load(file)
                for k, v in skus_mapping_data.items():
                    self.machine_family_sku[k] = ComputeFamilySKUModel(**v)
                    self.logger.debug(
                        f'Loaded {k} family CPU/RAM SKU data: {self.machine_family_sku[k]}'
                    )

            with open(family_general_info_mapping_filepath, 'r') as csv_file:
                reader = csv.reader(csv_file, delimiter=',')
                headers = next(reader)
                data = [MachineInfoModel(**{h:x for (h, x) in zip(headers, row)}) for row in reader]
                self.logger.debug(data)
                for machine_data in data:
                    self.general_machines_info[machine_data.machine] = machine_data
        self.logger.info(f'Loaded {len(self.general_machines_info)} machines')

    def get_regions(self) -> List[str]:
        self.logger.debug('[GetRegions] Started')
        regions_request = compute_v1.ListRegionsRequest(
            project=self.gcp_project
        )
        page_result = self.regions_client.list(request=regions_request)
        self.regions = []
        for response in page_result:
            self.regions.append(response.name)
        self.logger.info(f'[GetRegions] Loaded {len(self.regions)} regions: {self.regions}')
        return self.regions

    def get_zones(self):
        self.logger.debug('[GetZones] Started.')
        zone_types_request = compute_v1.ListZonesRequest(
            project=self.gcp_project
        )
        page_result = self.zones_client.list(request=zone_types_request)
        self.zones = []
        for response in page_result:
            self.zones.append(response.name)
        self.logger.info(f'[GetZones] Loaded {len(self.zones)} zones: {self.zones}')
        return self.zones

    def get_machine_types(
        self,
        load=False,
        dump=False
    ):
        self.logger.info('[GetMachineTypes] Started')
        self.machines = {}

        if load and os.path.exists(self.GCP_INSTANCES_DATA):
            self.logger.info(f'[GetMachineTypes] Loading from file {self.GCP_INSTANCES_DATA}')
            with open(self.GCP_INSTANCES_DATA, 'r') as file:
                self.machines = yaml.safe_load(file)
                self.logger.info('[GetMachineTypes] Loaded from file. Done')
                return self.machines

        for zone in self.zones:
            self.logger.debug(f'Processing machines from zone: {zone}')
            request = compute_v1.ListMachineTypesRequest(
                project=self.gcp_project,
                zone=zone,
            )
            page_result = self.machines_client.list(request=request)
            for response in page_result:
                if response.name not in self.machines:
                    self.machines[response.name] = {
                        'cpu': response.guest_cpus,
                        'ram': response.memory_mb / 1024,
                        'zones': [zone]
                    }
                else:
                    self.machines[response.name]['zones'].append(zone)

        for machine in self.machines:
            self.machines[machine]['regions'] = list(set(['-'.join(x.split('-')[:2]) for x in self.machines[machine]['zones']]))

        self.logger.info(f'[GetMachineTypes] Machines: {self.machines.keys()}')
        if dump:
            self.logger.info(f'[GetMachineTypes] Saving instances into {self.GCP_INSTANCES_DATA}')
            with open(self.GCP_INSTANCES_DATA, 'w') as file:
                yaml.dump(self.machines, file)
        self.logger.info('[GetMachineTypes] Done')
        return self.machines


    def init_skus(self, load=False, dump=False):
        skus_data = self.get_skus_data(load, dump)

        def _get_usage_type_skus(usage_type: str):
            return list(skus_data['CPU'].get(usage_type, {}).values()) + \
                   list(skus_data['RAM'].get(usage_type, {}).values()) + \
                   list(skus_data['GPU'].get(usage_type, {}).values()) + \
                   list(skus_data['N1Standard'].get(usage_type, {}).values()) + \
                   list(skus_data['F1Micro'].get(usage_type, {}).values()) + \
                   list(skus_data['G1Small'].get(usage_type, {}).values())

        self.on_demand_skus = _get_usage_type_skus('OnDemand')
        self.spot_skus = _get_usage_type_skus('Preemptible')
        self.cud1_skus = _get_usage_type_skus('Commit1Yr')
        self.cud3_skus = _get_usage_type_skus('Commit3Yr')
        self.skus[OnDemandUsage] = self.on_demand_skus
        self.skus[SpotUsage] = self.spot_skus
        self.skus[CommitmentOneYearUsage] = self.cud1_skus
        self.skus[CommitmentThreeYearsUsage] = self.cud3_skus

    def get_skus_data(self, load=False, dump=False):
        self.logger.info('[GetSkusData] Started')
        unique_sku_groups = set()
        if load and os.path.exists(self.GCP_SKU_DATA_JSON):
            self.logger.info(f'[GetSkusData] Loading from {self.GCP_SKU_DATA_JSON}')
            with open(self.GCP_SKU_DATA_JSON, 'r') as file:
                return json.load(file)

        client = billing_v1.CloudCatalogClient(credentials=self.credentials)

        compute_engine_service_name = self.GCP_COMPUTE_ENGINE_SERVICE_NAME
        # Initialize request argument(s)
        skus = {
            'CPU': {},
            'GPU': {},
            'RAM': {},
            'N1Standard': {},
            'F1Micro': {},
            'G1Small': {}
        }

        request = billing_v1.ListSkusRequest(
            parent=compute_engine_service_name
        )
        page_result = client.list_skus(request=request)

        # Handle the response
        for response in page_result:
            unique_sku_groups.add(response.category.resource_group)
            if response.category.resource_group not in skus:
                continue
            sku_pricing_info = response.pricing_info[0]
            # We should not see the warnings below for CPU and RAM
            if len(sku_pricing_info.pricing_expression.tiered_rates) > 1:
                self.logger.warning(f'[GetSkusData] {response.description}')
            if len(sku_pricing_info.pricing_expression.tiered_rates) == 0:
                self.logger.warning(f'[GetSkusData] {response.description}')
                continue
            if response.category.usage_type not in skus[response.category.resource_group]:
                skus[response.category.resource_group][response.category.usage_type] = {}
            skus[response.category.resource_group][response.category.usage_type][response.name] = {
                'name': response.name,
                'sku_id': response.sku_id,
                'description': response.description,
                'usage_unit': sku_pricing_info.pricing_expression.usage_unit,
                'usage_unit_description': sku_pricing_info.pricing_expression.usage_unit_description,
                'base_unit': sku_pricing_info.pricing_expression.base_unit,
                'base_unit_description': sku_pricing_info.pricing_expression.base_unit_description,
                'base_unit_conversion_factor': sku_pricing_info.pricing_expression.base_unit_conversion_factor,
                'display_quantity': sku_pricing_info.pricing_expression.display_quantity,
                'pricing': {
                    'start_usage_amount': sku_pricing_info.pricing_expression.tiered_rates[0].start_usage_amount,
                    'unit_price_currency_code': sku_pricing_info.pricing_expression.tiered_rates[0].unit_price.currency_code,
                    'unit_price_units': sku_pricing_info.pricing_expression.tiered_rates[0].unit_price.units,
                    'unit_price_nanos': sku_pricing_info.pricing_expression.tiered_rates[0].unit_price.nanos,
                },
                'regions': list(response.service_regions)
            }
        self.logger.debug(unique_sku_groups)
        if dump:
            self.logger.info(f'[GetSkusData] Saving skus data into file {self.GCP_SKU_DATA}')
            with open(self.GCP_SKU_DATA, 'w') as file:
                yaml.dump(skus, file)
            with open(self.GCP_SKU_DATA_JSON, 'w') as file:
                json.dump(skus, file)
        self.logger.info('[GetSkusData] Done')
        return skus

    def get_machine_cost(self, machine_family: str, machine_name: str, usage_type: UsageType):
        if machine_name not in self.pricing_data[machine_family]:
            self.pricing_data[machine_family][machine_name] = {
                'regions': {},
            }
        machine = self.machines[machine_name]

        instance_price_regex = self.machine_family_sku[machine_family].instance.get_usage_type(usage_type)
        if instance_price_regex is None:
            self.logger.debug(
                f"[GetPricing({usage_type})] {usage_type} pricing is not supported for machine family {machine_family}")
            return
        machine_skus = list(
            filter(lambda x: re.search(instance_price_regex, x['description']), self.skus[usage_type]))
        for region in machine['regions']:
            instance_region_sku = list(filter(lambda x: region in x['regions'], machine_skus))
            if len(instance_region_sku) == 0:
                continue
            price = self.calculate_regional_instance_price(
                machine_name,
                region,
                machine_skus
            )

            if region not in self.pricing_data[machine_family][machine_name]['regions']:
                self.pricing_data[machine_family][machine_name]['regions'][region] = {}
            self.pricing_data[machine_family][machine_name]['regions'][region][usage_type] = nice(price)

    def calculate_regional_sku_price(
        self,
        region: str,
        available_skus: list
    ) -> float:
        regional_skus = list(filter(lambda x: region in x['regions'], available_skus))
        if len(regional_skus) == 0:
            raise ZeroSKURegexMatch()
        if len(regional_skus) != 1:
            self.logger.error(f'Multiple regional SKU match: {regional_skus}')
            if len(regional_skus) == 2:
                # todo: implement conflict resolving strategy and get it from settings.
                #  For now, I decided that selecting SKU with the lowest price is the best strategy.
                self.logger.warning(f'Using the SKU with the lowest price in order to resolve SKU conflict.')
                return min(
                    [x['pricing']['unit_price_units'] + x['pricing']['unit_price_nanos'] * 10 ** (-9) for x in regional_skus]
                )
            raise MultipleSKURegexMatch()
        regional_sku = regional_skus[0]
        return regional_sku['pricing']['unit_price_units'] + regional_sku['pricing']['unit_price_nanos'] * 10 ** (-9)


    def calculate_regional_cpu_price(
        self,
        machine_name: str,
        cpu: float,
        region: str,
        available_skus: list
    ) -> Optional[float]:
        try:
            return cpu * self.calculate_regional_sku_price(region, available_skus)
        except ZeroSKURegexMatch:
            self.logger.warning(
                f'Zero CPU SKUs are found for machine {machine_name} in region {region}'
            )
            return None
        except MultipleSKURegexMatch:
            self.logger.error(
                f'Multiple CPU SKUs are found for machine {machine_name} in region {region}'
            )
            return None

    def calculate_regional_ram_price(
        self,
        machine_name: str,
        ram: float,
        region: str,
        available_skus: list
    ) -> Optional[float]:
        try:
            return ram * self.calculate_regional_sku_price(region, available_skus)
        except ZeroSKURegexMatch:
            self.logger.warning(
                f'Zero RAM SKUs are found for machine {machine_name} in region {region}'
            )
            return None
        except MultipleSKURegexMatch:
            self.logger.error(
                f'Multiple RAM SKUs are found for machine {machine_name} in region {region}'
            )
            return None

    def calculate_regional_instance_price(
        self,
        machine_name: str,
        region: str,
        available_skus: list
    ) -> Optional[float]:
        try:
            return self.calculate_regional_sku_price(region, available_skus)
        except ZeroSKURegexMatch:
            self.logger.warning(
                f'Zero instance SKUs are found for machine {machine_name} in region {region}'
            )
            return None
        except MultipleSKURegexMatch:
            self.logger.error(
                f'Multiple instance SKUs are found for machine {machine_name} in region {region}'
            )
            return None

    def calculate_regional_gpu_price(
        self,
        machine_name: str,
        gpus: float,
        region: str,
        available_skus: list
    ) -> Optional[float]:
        try:
            return gpus * self.calculate_regional_sku_price(region, available_skus)
        except ZeroSKURegexMatch:
            self.logger.warning(
                f'Zero GPU SKUs are found for machine {machine_name} in region {region}'
            )
            return None
        except MultipleSKURegexMatch:
            self.logger.error(
                f'Multiple GPU SKUs are found for machine {machine_name} in region {region}'
            )
            return None

    def _calculate_pricing(self, usage_type: UsageType):
        """
        Calculates prices for GCP Compute instances for provided usage type.

        :return:
            family:
                machine_type:
                    regions:
                        region_name:
                            usage_type: cost
        """
        self.logger.info(f'[GetPricing({usage_type})] Started')
        machines = self.machines
        for machine_family in self.machine_family_sku:
            if machine_family not in self.pricing_data:
                self.pricing_data[machine_family] = {}

            if machine_family == 'f1':
                self.get_machine_cost('f1', 'f1-micro', usage_type)
                continue
            if machine_family == 'g1':
                self.get_machine_cost('g1', 'g1-small', usage_type)
                continue

            family_machines = [x for x in machines if x.split('-')[0] == machine_family]

            cpu_price_regex = self.machine_family_sku[machine_family].cpu.get_usage_type(usage_type)
            ram_price_regex = self.machine_family_sku[machine_family].ram.get_usage_type(usage_type)

            if cpu_price_regex is None or ram_price_regex is None:
                self.logger.debug(f"[GetPricing({usage_type})] {usage_type} pricing is not supported for machine family {machine_family}")
                continue
            self.logger.debug(cpu_price_regex)
            self.logger.debug(ram_price_regex)

            # CPU and RAM skus are common for the whole family
            machine_cpu_skus = list(
                filter(lambda x: re.search(cpu_price_regex, x['description']), self.skus[usage_type]))
            machine_ram_skus = list(
                filter(lambda x: re.search(ram_price_regex, x['description']), self.skus[usage_type]))

            for machine_name in family_machines:
                self.logger.debug(f'[GetPricing({usage_type})] Processing {machine_name}...')

                if machine_name not in self.general_machines_info:
                    self.logger.error(f'[GetPricing({usage_type})] {machine_name} is missing in mapping data.')
                    # todo: implement safe execution handler
                    continue
                if machine_name not in self.pricing_data[machine_family]:
                    self.pricing_data[machine_family][machine_name] = {
                        'regions': {},
                    }
                machine = machines[machine_name]

                _machine_general_info = self.general_machines_info[machine_name].model_dump(by_alias=True)

                if self.general_machines_info[machine_name].gpu_support and self.general_machines_info[machine_name].gpu_count_by_default:
                    gpu_name = self.general_machines_info[machine_name].default_gpu
                    gpu_price_regex = self.gpus[gpu_name].skus.get_usage_type(usage_type)
                    machine_gpu_skus = list(
                        filter(lambda x: re.search(gpu_price_regex, x['description']), self.skus[usage_type])
                    )
                else:
                    machine_gpu_skus = None

                for region in machine['regions']:
                    price = 0

                    cpu_price = self.calculate_regional_cpu_price(
                        machine_name=machine_name,
                        cpu=machine['cpu'],
                        region=region,
                        available_skus=machine_cpu_skus
                    )
                    if cpu_price is None:
                        continue
                    price += cpu_price

                    ram_price = self.calculate_regional_ram_price(
                        machine_name=machine_name,
                        ram=machine['ram'],
                        region=region,
                        available_skus=machine_ram_skus
                    )
                    if ram_price is None:
                        continue
                    price += ram_price

                    if (self.general_machines_info[machine_name].gpu_support and
                            self.general_machines_info[machine_name].gpu_count_by_default):
                        gpu_price = self.calculate_regional_gpu_price(
                            machine_name=machine_name,
                            gpus=self.general_machines_info[machine_name].gpu_count_by_default,
                            region=region,
                            available_skus=machine_gpu_skus
                        )
                        if gpu_price:
                            price += gpu_price

                    # todo: add local SSD price. Some machines have local SSD enabled by default

                    if region not in self.pricing_data[machine_family][machine_name]['regions']:
                        self.pricing_data[machine_family][machine_name]['regions'][region] = {}
                    self.pricing_data[machine_family][machine_name]['regions'][region][usage_type] = nice(price)

        self.logger.info(f'[GetPricing({usage_type})] Done')
        return self.flat_pricing_data

    def calculate_ondemand_pricing(self):
        self._calculate_pricing(OnDemandUsage)

    def calculate_sud_pricing(self):
        """
        Calculates SUD prices for GCP Compute instances.

        Discounts are taken from https://cloud.google.com/compute/docs/sustained-use-discounts
        """
        base_costs = [1, 1, 1, 1]
        sud_discounts_30 = [1, 0.8, 0.6, 0.4]
        sud_discounts_20 = [1, 0.8678, 0.733, 0.6]
        sud_mappings = {
            'f1': sud_discounts_30,
            'g1': sud_discounts_30,
            'n1': sud_discounts_30,
            'n1-custom': sud_discounts_30,
            'm1': sud_discounts_30,
            'm2': sud_discounts_30,
            #
            'n2': sud_discounts_20,
            'n2-custom': sud_discounts_20,
            'n2d': sud_discounts_20,
            'n2d-custom': sud_discounts_20,
            'c2': sud_discounts_20
        }
        # todo: add support for GPU devices
        for family in self.pricing_data:
            costs_per_usage = sud_mappings.get(family, base_costs)
            for family_machine in self.pricing_data[family]:
                for region in self.pricing_data[family][family_machine]['regions']:
                    hours_discount = self.AVG_HOURS_PER_MONTH / len(costs_per_usage)
                    base_price = self.pricing_data[family][family_machine]['regions'][region]['ondemand']
                    machine_cost = 0
                    if family in sud_mappings:
                        for multiplier in costs_per_usage:
                            machine_cost += base_price * hours_discount * multiplier
                        machine_cost /= self.AVG_HOURS_PER_MONTH
                        self.pricing_data[family][family_machine]['regions'][region]['sud'] = machine_cost

    def calculate_spot_pricing(self):
        self._calculate_pricing(SpotUsage)

    def calculate_cud1y_pricing(self):
        self._calculate_pricing(CommitmentOneYearUsage)

    def calculate_cud3y_pricing(self):
        self._calculate_pricing(CommitmentThreeYearsUsage)

    def dump_pricing_info(
        self,
        raw_pricing_data_file_path: str = 'raw_gcp_machines_pricing.yaml',
        flat_pricing_data_file_path: str = 'flat_gcp_machines_pricing.yaml'
    ):
        metadata = {
            'last_time_updated': int(datetime.now().timestamp())
        }
        with open(raw_pricing_data_file_path, 'w') as file:
            yaml.dump(
                {
                    'metadata': metadata,
                    'machines': self.pricing_data
                },
                file
            )
        with open(flat_pricing_data_file_path, 'w') as file:
            yaml.dump({
                'metadata': metadata,
                'machines': [x.model_dump() for x in self.flat_pricing_data]
            }, file)


    def _make_flat_pricing_data(self):
        self.flat_pricing_data = []
        for machine_family in self.pricing_data:
            for machine_name in self.pricing_data[machine_family]:
                _machine_general_info = self.general_machines_info[machine_name].model_dump(by_alias=True)
                for region in self.pricing_data[machine_family][machine_name]['regions']:
                    _machine_general_info['region'] = region
                    for usage_type, price in self.pricing_data[machine_family][machine_name]['regions'][region].items():
                        _machine_general_info[usage_type] = price

                    self.flat_pricing_data.append(
                        MachineInfoModel(
                            **_machine_general_info,
                        )
                    )

    def run(
        self,
        dump=False,
        load=False
    ):
        self.get_zones()
        self.get_regions()
        self.get_machine_types(load=load, dump=dump)
        self.init_skus(load=load, dump=dump)
        self.calculate_ondemand_pricing()
        self.calculate_sud_pricing()
        self.calculate_spot_pricing()
        self.calculate_cud1y_pricing()
        self.calculate_cud3y_pricing()
        self._make_flat_pricing_data()






