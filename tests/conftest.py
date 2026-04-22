"""Shared fixtures."""

from __future__ import annotations

import pytest

from src import Cache


@pytest.fixture()
def cache() -> Cache:
    return Cache(max_items=4)


@pytest.fixture()
def big_cache() -> Cache:
    return Cache(max_items=1024)
