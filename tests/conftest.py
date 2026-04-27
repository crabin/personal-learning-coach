"""Shared pytest fixtures."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect all data_store I/O to a temporary directory."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # Reload _data_dir cache by resetting the env var before each test
    return tmp_path
