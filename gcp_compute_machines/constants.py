from typing import Literal

# 365 * 24 / 12 - GCP uses the same value
AVG_HOURS_PER_MONTH = 730

OnDemandUsage = 'ondemand'
SpotUsage = 'spot'
CommitmentOneYearUsage = 'cud1y'
CommitmentThreeYearsUsage = 'cud3y'

UsageType = Literal['ondemand', 'spot', 'cud1y', 'cud3y']


__all__ = [
    "AVG_HOURS_PER_MONTH",
    'UsageType',
    'OnDemandUsage',
    'SpotUsage',
    'CommitmentOneYearUsage',
    'CommitmentThreeYearsUsage'
]
