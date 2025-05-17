# GCP Compute Machines Costs

This project is a python package for scraping and exporting GCP Compute Machines metadata and costs information.

# Requirements

* python >= 3.12
* GCP service account with the next assigned permissions:
  * compute.machineTypes.list 
  * compute.regions.list 
  * compute.zones.list

# Installation

```bash
pip install gcp-compute-machines
```

# Usage

Create new file scrape.py with the next content and change `gcp_project_name` and `gcp_sa_account_path` variables.

## API Scraper

```python
from gcp_compute_machines import GCPMachinesScraper

gcp_project_name = 'CHANGE_ME'
gcp_sa_account_path = 'CHANGE_ME'

scraper = GCPMachinesScraper(
    gpc_project_name=gcp_project_name,
    gcp_sa_account_path=gcp_sa_account_path
)
machines = scraper.fetch_gcp_machines(
    # dump=True means that app saves the scrapped SKUs data locally
    dump=True,
    # Set load=True if you want to use local SKUs data between sequential runs.
    load=False
)

scraper.dump_pricing_info(
    file_path='./data/flat_gcp_machines_pricing.yaml'
)
```

## Loader for https://gcloud-compute.com/

This code downloads data from the website above and loads it into pydantic model.

```python
from gcp_compute_machines import GCloudComputeMachinesProvider

scraper = GCloudComputeMachinesProvider()
machines = scraper.fetch_gcp_machines()
scraper.dump_pricing_info("./data/flat_gcloud_compute_machines_pricing.yaml")
```

Keep in mind that:
* All pricing fields are normalized to hourly cost
* Some fields were renamed or dropped

# License 

This project is under the [Apache License, Version 2.0](./LICENSE) unless noted otherwise.

# Important info

Please note this project is not an official Google product. 

That means no warranty in costs data integrity. Use scraped data wisely.
