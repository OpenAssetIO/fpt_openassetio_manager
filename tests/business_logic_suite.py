# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2025 The Foundry Visionmongers Ltd

"""
A manager test harness test case suite that validates that
FPT Manager behaves with the correct business logic.
"""

# pylint: disable=invalid-name, missing-function-docstring, missing-class-docstring

from openassetio.access import ResolveAccess, EntityTraitsAccess
from openassetio.test.manager.harness import FixtureAugmentedTestCase
from openassetio_mediacreation.traits.content import LocatableContentTrait
from openassetio_mediacreation.traits.identity import DisplayNameTrait
from openassetio_mediacreation.traits.usage import EntityTrait


class Test_resolve(FixtureAugmentedTestCase):
    """
    Test suite for the Resolve business logic of FPT Manager.

    Tests the manager's ability to resolve FPT entities to their
    corresponding data.
    """

    def test_when_asset_resolved_then_returns_expected_traits(self):
        """
        Test resolving an asset returns all expected traits and
        properties.
        """
        entity_reference = self.requireEntityReferenceFixture("a_reference_to_a_readable_entity")
        trait_set = {
            LocatableContentTrait.kId,
            DisplayNameTrait.kId,
        }
        context = self.createTestContext()

        result = self._manager.resolve(entity_reference, trait_set, ResolveAccess.kRead, context)

        # Verify trait properties
        self.assertGreater(len(LocatableContentTrait(result).getLocation()), 0)
        self.assertGreater(len(DisplayNameTrait(result).getName()), 0)

    def test_when_workfile_resolved_then_returns_location(self):
        entity_reference = self.requireEntityReferenceFixture(
            "a_workfile_reference", skipTestIfMissing=True
        )
        trait_set = {
            LocatableContentTrait.kId,
        }
        context = self.createTestContext()

        result = self._manager.resolve(entity_reference, trait_set, ResolveAccess.kRead, context)

        self.assertTrue(LocatableContentTrait(result).getLocation().startswith("file://"))
        self.assertGreater(len(LocatableContentTrait(result).getLocation()), len("file://"))


class Test_entityTraits(FixtureAugmentedTestCase):
    """
    Test suite for the EntityTraits business logic of FPT Manager.

    Tests the manager's ability to identify traits associated with FPT
    entities.
    """

    def test_when_asset_queried_then_returns_expected_trait_set(self):
        """
        Test that an asset returns the expected set of traits.
        """
        entity_reference = self.requireEntityReferenceFixture("a_reference_to_an_existing_entity")
        context = self.createTestContext()

        result = self._manager.entityTraits(entity_reference, EntityTraitsAccess.kRead, context)

        expected_traits = {
            EntityTrait.kId,
            LocatableContentTrait.kId,
            DisplayNameTrait.kId,
        }
        self.assertSetEqual(result, expected_traits)
