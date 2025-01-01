# GCP Compute Machines Costs

This repository provides python module for scraping and exporting GCP Compute Machines metadata and costs information.

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

```python
from gcp_compute_machines import InstanceScraper

gcp_project_name = 'CHANGE_ME'
gcp_sa_account_path = 'CHANGE_ME'


scraper = InstanceScraper(
    gcp_project=gcp_project_name,
    sa_path=gcp_sa_account_path
)
scraper.run(
    # dump=True means that app saves the scrapped SKUs data locally for future reuses.
    dump=True,
    # Set load=True if you want to use local SKUs data between sequential runs.
    load=True
)
scraper.dump_pricing_info(
    raw_pricing_data_file_path='./data/raw_gcp_machines_pricing.yaml',
    flat_pricing_data_file_path='./data/flat_gcp_machines_pricing.yaml'
)
```

# License 

This project is under the [Apache License, Version 2.0](./LICENSE) unless noted otherwise.

# Important info

Please note this project is not an official Google product. 

That means no warranty in costs data integrity. Use scraped data wisely. 