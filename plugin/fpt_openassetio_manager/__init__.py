# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2025 The Foundry Visionmongers Ltd

"""
Module Documentation for FPT OpenAssetIO Manager.

This module provides an OpenAssetIO manager plugin for Flow Production
Tracking (formerly Shotgrid).
"""
from openassetio.pluginSystem import PythonPluginSystemManagerPlugin


class FPTManagerPlugin(PythonPluginSystemManagerPlugin):
    """
    The PythonPluginSystemManagerPlugin is responsible for constructing
    instances of the manager's implementation of the OpenAssetIO
    interfaces and returning them to the host.
    """

    @staticmethod
    def identifier():
        return "org.foundry.fpt"

    @classmethod
    def interface(cls):
        # pylint: disable=import-outside-toplevel
        from .FPTManagerInterface import FPTManagerInterface

        return FPTManagerInterface()


# The plugin's public entrypoint
# pylint: disable=invalid-name
openassetioPlugin = FPTManagerPlugin
