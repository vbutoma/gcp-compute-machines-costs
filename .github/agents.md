# Agent Reference: gcp-compute-machines-costs

This document is the authoritative technical reference for AI coding agents working in this repository. Read it before writing, editing, or reviewing any code.

---

## Purpose

Scrapes and normalizes GCP Compute Engine machine metadata and pricing into a unified format. Supports two scraping strategies (GCP API and gcloud-compute.com web scraper) and outputs flat YAML data ready for downstream consumption by CloudPlanner's placement API.

---

## Architecture Overview

```
Public API (gcp_compute_machines/__init__.py)
    │
    ├── GCPMachinesScraper           → Wraps InstanceScraper (GCP Compute + Billing APIs)
    └── GCloudComputeMachinesProvider → Web-scrapes gcloud-compute.com CSV
    │
    Both implement: GCPMachinesProvider (abstract base)
    Both return:    list[GCPMachineType subclass]
```

### Provider Hierarchy

```
GCPMachinesProvider (abstract)
├── GCPMachinesScraper          — delegates to InstanceScraper
└── GCloudComputeMachinesProvider — standalone, HTTP CSV download
```

### Model Hierarchy

```
GCPMachineType (base Pydantic model)
├── ScrapedMachineInfoModel     — used by GCPMachinesScraper / InstanceScraper
└── GcloudComputeMachineInfoModel — used by GCloudComputeMachinesProvider
```

---

## File Map

| Path | Role |
|------|------|
| `gcp_compute_machines/__init__.py` | Public API exports |
| `gcp_compute_machines/constants.py` | `AVG_HOURS_PER_MONTH=730`, `UsageType` literals |
| `gcp_compute_machines/exceptions.py` | `ZeroSKURegexMatch`, `MultipleSKURegexMatch` |
| `providers/base/base_machines_provider.py` | Abstract `GCPMachinesProvider` |
| `providers/base/models/base_machine_info_model.py` | `GCPMachineType` — the shared output model |
| `providers/base/models/helper_types.py` | `FloatOrNone`, `IntOrNone` validators |
| `providers/scraper/scraper.py` | `InstanceScraper` — core GCP API orchestration |
| `providers/scraper/scraped_machines_provider.py` | `GCPMachinesScraper` adapter |
| `providers/scraper/models/machine_info_model.py` | `ScrapedMachineInfoModel` |
| `providers/scraper/models/skus/` | SKU Pydantic models (regex mappings, GPU, storage) |
| `providers/scraper/mappings/` | Static CSV + YAML reference data per machine family |
| `providers/gcloud_compute/gcloud_compute_provider.py` | `GCloudComputeMachinesProvider` |
| `providers/gcloud_compute/models/gcloud_compute_machine_info_model.py` | `GcloudComputeMachineInfoModel` |

---

## Key Data Model: `GCPMachineType`

All providers return lists of objects inheriting from this model.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Machine type name (e.g. `n2-standard-4`) |
| `series` | `str` | Hardware series (e.g. `n2`) |
| `family` | `str` | Category (e.g. `General purpose`) |
| `cpu_count` | `float` | vCPU count (alias: `VCPUs`) |
| `ram` | `float` | RAM in GB |
| `region` | `str \| None` | GCP region (e.g. `us-central1`) |
| `ondemand` | `float \| None` | On-demand hourly price (USD) |
| `spot` | `float \| None` | Spot hourly price (USD) |
| `sud` | `float \| None` | Sustained Use Discount hourly price |
| `cud1y` | `float \| None` | 1-year committed use hourly price |
| `cud3y` | `float \| None` | 3-year committed use hourly price |
| `cpu_platforms` | `str \| None` | CPU platform (e.g. `Cascadelake`) |
| `default_network_bandwidth` | `int` | Mbps |
| `tier1_network_bandwidth` | `int \| None` | Tier-1 Mbps |
| `gpu_support` | `bool \| None` | Whether GPUs can be attached |
| `gpu_count_by_default` | `int \| None` | Default GPU count |
| `default_gpu` | `str \| None` | Default GPU type |

`ScrapedMachineInfoModel` adds: `local_ssd_support`, `local_ssd_enabled_by_default`, `local_ssd_default_size`, `nested_virtualization`.

`GcloudComputeMachineInfoModel` adds: carbon metrics, region lat/lng, CPU type flags (intel/amd/arm), performance benchmarks.

---

## Pricing Constant

```python
AVG_HOURS_PER_MONTH = 730  # 365 * 24 / 12
```

**All prices are normalized to hourly USD.** GCP billing SKUs quote some resources (RAM, LocalSSD) monthly — divide by 730 to get hourly.

---

## InstanceScraper: End-to-End Scraping Flow

`InstanceScraper` (`providers/scraper/scraper.py`) is the core engine. Called indirectly via `GCPMachinesScraper`.

### Initialization
1. Load GCP credentials from service account JSON
2. Initialize `RegionsClient`, `ZonesClient`, `MachineTypesClient`
3. Load static mapping files from `providers/scraper/mappings/`

### `run(dump=False, load=False)`
1. `get_zones()` / `get_regions()`
2. `get_machine_types(load, dump)` — per-zone specs
3. `init_skus(load, dump)` — billing catalog → `on_demand_skus`, `spot_skus`, `cud1_skus`, `cud3_skus`
4. `calculate_ondemand_pricing()`
5. `calculate_sud_pricing()` — GCP SUD tier math, not a billing SKU
6. `calculate_spot_pricing()` / `calculate_cud1y_pricing()` / `calculate_cud3y_pricing()`
7. `_make_flat_pricing_data()` → `list[ScrapedMachineInfoModel]`

### Caching
- `load=True` → use cached `gcp_instances.yaml` + `gcp_sku.yaml`; **always use in tests**
- `dump=True` → save intermediate files for reuse

### SKU Matching
GCP billing SKU descriptions are unstable. Regex patterns in `mappings/*.yaml` match by description:
```yaml
n2:
  cpu:
    ondemand: 'N2 Instance Core.*'
    spot: 'Spot Preemptible N2 Instance Core.*'
```
- `ZeroSKURegexMatch` → no match, warns and skips
- `MultipleSKURegexMatch` → picks lowest price

### Pricing Calculation Per (machine, region)
- CPU cost = `cpu_count × price_per_cpu_unit`
- RAM cost = `ram_gb × price_per_gb`
- GPU cost = `gpu_count × price_per_gpu`
- LocalSSD cost = monthly ÷ 730
- f1-micro / g1-small = instance-level SKU pricing
- SUD = GCP 4-tier sliding scale discount on on-demand

---

## GCloudComputeMachinesProvider

Downloads `https://gcloud-compute.com/machine-types-regions.csv`. Monthly pricing normalized to hourly in field validators. Use when GCP credentials are unavailable.

---

## Static Reference Data (`mappings/`)

| File pattern | Content |
|---|---|
| `{family}-machines.csv` | vCPUs, RAM, network, GPU, LocalSSD metadata |
| `{family}-machines-sku.yaml` | SKU regex per pricing model |
| `gpu-skus-mapping.yaml` | GPU type → SKU regex |
| `storage-skus-mapping.yaml` | LocalSSD SKU regex |

Families: `general-purpose`, `compute-optimized`, `memory-optimized`, `storage-optimized`, `accelerator-optimized`

**Never edit regex patterns without validating against live GCP billing SKU descriptions.**

---

## Public API

```python
from gcp_compute_machines import (
    GCPMachinesScraper, GCloudComputeMachinesProvider, GCPMachinesProvider,
    GCPMachineType, ScrapedMachineInfoModel, GcloudComputeMachineInfoModel,
    AVG_HOURS_PER_MONTH, UsageType, OnDemandUsage, SpotUsage,
    CommitmentOneYearUsage, CommitmentThreeYearsUsage,
    ZeroSKURegexMatch, MultipleSKURegexMatch,
)
```

### Typical Usage
```python
# GCP API scraper
scraper = GCPMachinesScraper(gpc_project_name='my-project', gcp_sa_account_path='/path/to/sa.json')
machines = scraper.fetch_gcp_machines(dump=True, load=False)
scraper.dump_pricing_info('machines_pricing.yaml')

# Web scraper (no credentials)
provider = GCloudComputeMachinesProvider()
machines = provider.fetch_gcp_machines()
provider.dump_pricing_info('machines.yaml')
```

---

## Output YAML Format

```yaml
metadata:
  last_time_updated: 1704067200
machines:
  - name: n2-standard-4
    series: n2
    region: us-central1
    cpu_count: 4
    ram: 16.0
    ondemand: 0.19776
    spot: 0.05933
    sud: 0.13850
    cud1y: 0.14328
    cud3y: 0.10658
```

One row per (machine, region) pair.

---

## GCP Credentials Requirements

SA needs: `compute.machineTypes.list`, `compute.regions.list`, `compute.zones.list`, `billing.cloudCatalog.get`

---

## Agent Invariants

1. **All prices are hourly** — always normalize by `AVG_HOURS_PER_MONTH = 730`.
2. **Regex patterns are fragile** — validate any `mappings/*.yaml` change against live SKU descriptions.
3. **`load=True` in tests** — never call GCP APIs in tests.
4. **One row per (machine, region)** — do not collapse regions.
5. **Abstract base is stable** — implement `fetch_gcp_machines` + `dump_pricing_info`; do not change the interface.
6. **`GCPMachineType` is the contract** — field names are consumed by placement-api; do not rename or remove.
