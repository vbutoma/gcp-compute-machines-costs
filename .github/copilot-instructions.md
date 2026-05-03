# Copilot instructions (repo-wide)

These instructions apply to all Copilot Chat/code suggestions in this repository.

## Product context

This repository is a Python package that provides GCP instances data:
- name
- Machine Series
- Machine Family
- vCPU count
- Memory (GB)
- GPU count (if applicable)
- GPU type (if applicable)
- Region availability
- Pricing information: ondemand, spot, committed use discounts (if applicable)
- Network performance (if available)

The package is designed to help users make informed decisions about which GCP instance types to use for their workloads, based on their specific requirements and budget.

## How it works

The package retrieves data from GCP's Compute Engine API:
- Regions API
- Compute Engine API
- SKUs API

Some of the data is not possible to achieve through the API, so it is scraped manually from the GCP pricing page: https://docs.cloud.google.com/compute/docs/machine-resource
In future it should be replaced with auto-scraping if possible. 

## Agent Reference

For the full technical reference including architecture, data models, scraping flows, SKU matching, and agent invariants, see [agents.md](agents.md).
