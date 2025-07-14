# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2025 The Foundry Visionmongers Ltd

"""
Test cases for FPT Manager that make use of the OpenAssetIO manager test
harness.
"""

import os
import pytest

# pylint: disable=invalid-name,redefined-outer-name
# pylint: disable=missing-class-docstring,missing-function-docstring

from openassetio.test.manager import harness, apiComplianceSuite


class Test_FPTManager:
    def test_passes_apiComplianceSuite(self, harness_fixtures):
        assert harness.executeSuite(apiComplianceSuite, harness_fixtures)

    def test_passes_fpt_manager_business_logic_suite(
        self, fpt_manager_business_logic_suite, harness_fixtures
    ):
        assert harness.executeSuite(fpt_manager_business_logic_suite, harness_fixtures)


@pytest.fixture
def fpt_manager_business_logic_suite(base_dir):
    module_path = os.path.join(base_dir, "tests", "business_logic_suite.py")
    return harness.moduleFromFile(module_path)
