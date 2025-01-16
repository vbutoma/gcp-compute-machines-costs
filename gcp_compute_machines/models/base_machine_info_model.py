from typing import Optional

from pydantic import BaseModel, field_validator, Field


class BaseGCPMachine(BaseModel):

    name: str
    series: str
    family: str

    description: str = ''