from typing import Literal

OnDemandUsage = 'ondemand'
SpotUsage = 'spot'
CommitmentOneYearUsage = 'cud1y'
CommitmentThreeYearsUsage = 'cud3y'

UsageType = Literal['ondemand', 'spot', 'cud1y', 'cud3y']


__all__ = [
    'UsageType',
    'OnDemandUsage',
    'SpotUsage',
    'CommitmentOneYearUsage',
    'CommitmentThreeYearsUsage'
]
