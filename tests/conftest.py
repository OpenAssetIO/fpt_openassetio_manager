# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2025 The Foundry Visionmongers Ltd

"""
Shared fixtures for FPT Manager pytest coverage.
"""

# pylint: disable=invalid-name,redefined-outer-name
# pylint: disable=missing-class-docstring,missing-function-docstring

import os
import pytest

from openassetio.test.manager import harness

@pytest.fixture
def harness_fixtures(base_dir):
    """
    Provides the fixtures dict for FPT Manager when used with
    the openassetio.test.manager.apiComplianceSuite.
    """
    fixtures_path = os.path.join(base_dir, "tests", "fixtures.py")
    return harness.fixturesFromPyFile(fixtures_path)


@pytest.fixture
def base_dir():
    """
    Provides the path to the base directory for the FPT Manager
    codebase.
    """
    return os.path.dirname(os.path.dirname(__file__))
