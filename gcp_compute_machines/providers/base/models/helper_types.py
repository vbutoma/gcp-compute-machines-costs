from pydantic import BeforeValidator
from typing import Annotated


def float_or_none_validator(v: float | None) -> float | None:
    if v is None:
        return v
    if isinstance(v, str) and len(v) == 0:
        return None
    return v


def int_or_none_validator(v: int | None) -> int | None:
    if v is None:
        return v
    if isinstance(v, str) and len(v) == 0:
        return None
    return v


FloatOrNone = Annotated[float | None, BeforeValidator(float_or_none_validator)]
IntOrNone = Annotated[int | None, BeforeValidator(int_or_none_validator)]


__all__ = [
    "FloatOrNone",
    "IntOrNone"
]
