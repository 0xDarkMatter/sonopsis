"""
Pytest configuration and shared fixtures.
"""

import sys
from pathlib import Path

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def prose_dir(project_root):
    """Return the prose directory."""
    return project_root / "prose"


@pytest.fixture
def config_file(project_root):
    """Return the config.yaml path."""
    return project_root / "config.yaml"
