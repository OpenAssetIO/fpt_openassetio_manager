# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2025 The Foundry Visionmongers Ltd

"""
Manager test harness test case fixtures for Flow Production Tracking
Manager.
"""
import os

from openassetio import constants
from openassetio_mediacreation.traits.content import LocatableContentTrait
from openassetio_mediacreation.traits.identity import DisplayNameTrait
from openassetio_mediacreation.traits.usage import EntityTrait


##
# Authentication

SERVER_URL = os.environ["OPENASSETIO_TEST_SERVER_URL"]
API_KEY = os.environ.get("OPENASSETIO_TEST_API_KEY")
SCRIPT_NAME = os.environ.get("OPENASSETIO_TEST_SCRIPT_NAME")
LEGACY_USER = os.environ.get("OPENASSETIO_TEST_LEGACY_USER")
LEGACY_PASSWORD = os.environ.get("OPENASSETIO_TEST_LEGACY_PASSWORD")

##
# PublishedFile support

EXISTING_PUBLISHEDFILE_ID = os.environ["OPENASSETIO_TEST_EXISTING_PUBLISHEDFILE_ID"]
MISSING_PUBLISHEDFILE_ID = os.environ["OPENASSETIO_TEST_MISSING_PUBLISHEDFILE_ID"]

##
# Workfile support

# ID of project to use to retrieve pipeline config.
PROJECT_ID = os.environ.get("OPENASSETIO_TEST_PROJECT_ID")
# Name of an FPT file path template.
WORKFILE_TEMPLATE_NAME = os.environ.get("OPENASSETIO_TEST_WORKFILE_TEMPLATE_NAME")
# Fields for the above FPT file path template, in order, separated by
# `/`.
WORKFILE_TEMPLATE_FIELDS = os.environ.get("OPENASSETIO_TEST_WORKFILE_TEMPLATE_FIELDS")


IDENTIFIER = "org.foundry.fpt"

# Entity References
VALID_REF = f"fpt://asset/PublishedFile/{EXISTING_PUBLISHEDFILE_ID}"
NON_REF = "not a reference"
MALFORMED_REF = (
    f"fpt://asset/PublishedFile/{EXISTING_PUBLISHEDFILE_ID}/unsupported_extra_path_component"
)
EXISTING_REF = VALID_REF
MISSING_ENTITY_REF = f"fpt://asset/PublishedFile/{MISSING_PUBLISHEDFILE_ID}"

# Error Messages
ERROR_MSG_MALFORMED_REF = "Entity identifier is malformed"
ERROR_MSG_MISSING_ENTITY = f"Entity '{MISSING_ENTITY_REF}' not found"
ERROR_MSG_AUTH_ERROR = "Authentication failed"
ERROR_MSG_CONN_ERROR = "Connection failed"
ERROR_READ_ONLY_ACCESS = "Entities are read-only"

fixtures = {
    "identifier": IDENTIFIER,
    "settings": {
        "server_url": SERVER_URL,
        # Script auth.
        "script_name": SCRIPT_NAME,
        "api_key": API_KEY,
        # Legacy login auth.
        "login": LEGACY_USER,
        "password": LEGACY_PASSWORD,
        "project_id": int(PROJECT_ID) if PROJECT_ID else None,
    },
    "shared": {
        "a_valid_reference": VALID_REF,
        "an_invalid_reference": NON_REF,
    },
    "Test_identifier": {"test_matches_fixture": {"identifier": IDENTIFIER}},
    "Test_displayName": {"test_matches_fixture": {"display_name": "Flow Production Tracking"}},
    "Test_info": {
        "test_matches_fixture": {
            "info": {constants.kInfoKey_EntityReferencesMatchPrefix: "fpt://"}
        }
    },
    "Test_resolve": {
        "shared": {
            "a_reference_to_a_readable_entity": EXISTING_REF,
            "a_set_of_valid_traits": {LocatableContentTrait.kId, DisplayNameTrait.kId},
            "a_reference_to_a_readonly_entity": EXISTING_REF,
            "the_error_string_for_a_reference_to_a_readonly_entity": ERROR_READ_ONLY_ACCESS,
            "a_reference_to_a_missing_entity": MISSING_ENTITY_REF,
            "the_error_string_for_a_reference_to_a_missing_entity": ERROR_MSG_MISSING_ENTITY,
            "a_malformed_reference": MALFORMED_REF,
            "the_error_string_for_a_malformed_reference": ERROR_MSG_MALFORMED_REF,
        }
    },
    "Test_entityTraits": {
        "shared": {
            "a_reference_to_an_existing_entity": EXISTING_REF,
            "the_traits_for_an_existing_entity": {
                EntityTrait.kId,
                LocatableContentTrait.kId,
                DisplayNameTrait.kId,
            },
        },
        "test_when_querying_malformed_reference_then_malformed_reference_error_is_returned": {
            "a_malformed_reference": MALFORMED_REF,
            "expected_error_message": ERROR_MSG_MALFORMED_REF,
        },
        "test_when_querying_missing_reference_for_read_then_resolution_error_is_returned": {
            "a_reference_to_a_missing_entity": MISSING_ENTITY_REF,
            "expected_error_message": ERROR_MSG_MISSING_ENTITY,
        },
    },
}

# business_logic_suite.py specific
if WORKFILE_TEMPLATE_NAME:
    fixtures["Test_resolve"]["test_when_workfile_resolved_then_returns_location"] = {
        "a_workfile_reference": (
            f"fpt://workfile/{WORKFILE_TEMPLATE_NAME}/{WORKFILE_TEMPLATE_FIELDS}"
        )
    }
