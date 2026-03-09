"""Generic pagination wrapper schema."""

from __future__ import annotations

import math
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, computed_field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T] = Field(description="Daftar item pada halaman ini.")
    total_items: int = Field(
        description="Total jumlah item di semua halaman.",
        examples=[42],
    )
    page: int = Field(
        description="Nomor halaman saat ini (mulai dari 1).",
        examples=[1],
    )
    page_size: int = Field(
        description="Jumlah item per halaman (default=20, max=100).",
        examples=[20],
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_pages(self) -> int:
        """Total jumlah halaman berdasarkan total_items dan page_size."""
        if self.page_size == 0:
            return 0
        return math.ceil(self.total_items / self.page_size)
