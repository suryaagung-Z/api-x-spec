"""Generic pagination wrapper schema."""

from __future__ import annotations

import math
from typing import Generic, TypeVar

from pydantic import BaseModel, computed_field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total_items: int
    page: int
    page_size: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return math.ceil(self.total_items / self.page_size)
