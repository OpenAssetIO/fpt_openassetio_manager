# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 The Foundry Visionmongers Ltd
"""
Entry point for the FPT OpenAssetIO UI delegate plugin.
"""
from openassetio.ui.pluginSystem import PythonPluginSystemUIDelegatePlugin


class FPTUIPlugin(PythonPluginSystemUIDelegatePlugin):
    """
    The PythonPluginSystemUIDelegatePlugin is responsible for
    constructing instances of the UI delegate's implementation of the
    OpenAssetIO interfaces and returning them to the host.
    """

    @classmethod
    def identifier(cls):
        """
        Retrieve the unique identifier for this plugin.

        This should match the identifier used in the corresponding
        manager plugin to ensure proper association between the UI
        delegate and the manager.
        """
        return "org.foundry.fpt"

    @classmethod
    def interface(cls):
        """
        Construct and return an instance of the UI delegate interface.
        """
        # pylint: disable=import-outside-toplevel
        from .FPTUIInterface import FPTUIInterface

        return FPTUIInterface()


# The plugin's public entrypoint
# pylint: disable=invalid-name
openassetioUIPlugin = FPTUIPlugin
