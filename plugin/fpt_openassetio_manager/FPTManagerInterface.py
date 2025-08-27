# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2025 The Foundry Visionmongers Ltd
"""
A single-class module, providing the FPTManagerInterface class.

This is the entry-point for the Flow Production Tracking OpenAssetIO
manager plugin.
"""
# pylint: disable=invalid-name,too-many-arguments
# pylint: disable=too-many-positional-arguments

import os
import pickle
from collections import namedtuple
from enum import Enum
from typing import Optional

try:
    from shotgun_api3 import Shotgun
except ImportError:
    from tank_vendor.shotgun_api3 import Shotgun

from openassetio.utils import FileUrlPathConverter
from openassetio import constants
from openassetio.trait import TraitsData
from openassetio.errors import BatchElementError
from openassetio.access import PolicyAccess, ResolveAccess, EntityTraitsAccess
from openassetio.managerApi import ManagerInterface
from openassetio_mediacreation.traits.content import LocatableContentTrait
from openassetio_mediacreation.traits.managementPolicy import ManagedTrait
from openassetio_mediacreation.traits.identity import DisplayNameTrait
from openassetio_mediacreation.traits.application import WorkTrait
from openassetio_mediacreation.traits.usage import EntityTrait
from openassetio_mediacreation.traits.timeDomain import FrameRangedTrait


class FPTManagerInterface(ManagerInterface):
    """
    Implement the OpenAssetIO ManagerInterface for Flow Production
    Tracking.

    https://openassetio.github.io/OpenAssetIO/classopenassetio_1_1v1_1_1manager_api_1_1_manager_interface.html
    """

    # Entity references provided to this asset manager should be
    # prefixed with this string to be considered valid.
    # e.g. "fpt://asset/PublishedFile/123"
    reference_prefix = "fpt://"

    def __init__(self):
        super().__init__()
        # Client for queries to an FPT service. Required for
        # PublishedFile objects and other database types.
        self.__sgclient = None
        # FPT Toolkit Core API instance. Required for workfiles. Lazily
        # constructed - use self.__sgtk instead.
        self.__sgtk_lazy = None
        # Project ID to use as a fallback when `current_engine()` is
        # unavailable, i.e. when the host is not launched via FPT
        # Desktop. Required for FPT Toolkit Core API instance.
        self.__project_id = None

        self.__settings = {}
        # Utility for converting `file://` URLs to/from paths.
        # Construction deferred until `initialize` since construction of
        # this is not cheap.
        self.__file_url_path_converter = None

    def identifier(self):
        """
        Retrieve the unique identifier of this manager plugin.
        """
        return "org.foundry.fpt"

    def initialize(self, managerSettings, hostSession):
        """
        Initialize the Flow Production Tracking connection using SGTK's
        authentication.
        """
        self.__settings.update(managerSettings)

        self.__file_url_path_converter = FileUrlPathConverter()

        # Load settings from config.toml
        server_url = self.__settings.get("server_url")
        # Due to Python->C++->Python translation, explicit None becomes
        # False, so we must convert back to None.
        script_name = self.__settings.get("script_name") or None
        api_key = self.__settings.get("api_key") or None
        login = self.__settings.get("login") or None
        password = self.__settings.get("password") or None
        session_token = None
        http_proxy = None

        self.__project_id = self.__settings.get("project_id") or None
        self.__sgtk_lazy = None  # Reset to None in case project ID is updated.

        # Extract user from environment (e.g. we're in an app launched
        # by FPT Desktop).
        if serialized_user := os.getenvb("SHOTGUN_DESKTOP_CURRENT_USER".encode("latin-1")):
            hostSession.logger().debug(
                "Initialising OpenAssetIO FPT plugin using SHOTGUN_DESKTOP_CURRENT_USER"
            )
            user_details = pickle.loads(serialized_user)
            server_url = user_details["data"]["host"]
            http_proxy = user_details["data"]["http_proxy"]
            session_token = user_details["data"]["session_token"]

        # Authenticate with FPT.
        try:
            self.__sgclient = Shotgun(
                server_url,
                script_name=script_name,
                api_key=api_key,
                login=login,
                password=password,
                session_token=session_token,
                http_proxy=http_proxy,
            )
            self.__sgclient.connect()
        except Exception as e:
            raise RuntimeError("Failed to authenticate with FPT") from e

    def displayName(self):
        """
        Human-readable display name of this plugin
        """
        return "Flow Production Tracking"

    def hasCapability(self, capability):
        """
        Advertise supported capabilities of this plugin.
        """
        # For the first iteration, we'll support basic capabilities
        if capability in (
            ManagerInterface.Capability.kEntityReferenceIdentification,
            ManagerInterface.Capability.kManagementPolicyQueries,
            ManagerInterface.Capability.kResolution,
            ManagerInterface.Capability.kEntityTraitIntrospection,
        ):
            return True
        return False

    def info(self):
        """
        Arbitrary metadata about this plugin.
        """
        return {constants.kInfoKey_EntityReferencesMatchPrefix: self.reference_prefix}

    def managementPolicy(self, traitSets, policyAccess, _context, _hostSession):
        """
        The policy of this plugin with respect to each given trait set,
        and the access mode, context and host.
        """
        policies = [TraitsData() for _ in traitSets]

        # For now, we'll only support read access.
        if policyAccess != PolicyAccess.kRead:
            # Return empty policies i.e. all unsupported.
            return policies

        for trait_set, policy in zip(traitSets, policies):
            # TODO(DF): we should also check against "family traits"
            # e.g. "ImageTrait", to signal our support for particular
            # kinds of asset. At the moment we're saying e.g. _any_
            # asset with a location is managed, which is almost
            # definitely not true.

            if LocatableContentTrait.kId in trait_set:
                ManagedTrait.imbueTo(policy)
                LocatableContentTrait.imbueTo(policy)

            # Only support DisplayName if not a workfile (since they're
            # just a file on disk).
            if WorkTrait not in trait_set and DisplayNameTrait.kId in trait_set:
                ManagedTrait.imbueTo(policy)
                DisplayNameTrait.imbueTo(policy)

            if FrameRangedTrait.kId in trait_set:
                ManagedTrait.imbueTo(policy)
                FrameRangedTrait.imbueTo(policy)

        return policies

    def isEntityReferenceString(self, someString, _hostSession):
        """
        Check if a string looks like it could be an entity reference.

        Note that since we set
        `constants.kInfoKey_EntityReferencesMatchPrefix` in `info()`,
        then the OpenAssetIO middleware will skip this function in
        favour of an optimised prefix check. So in practice, this
        function will rarely, if ever, be called.
        """
        # Check if the string starts with our prefix.
        return someString.startswith(self.reference_prefix)

    def entityTraits(
        self,
        entityReferences,
        entityTraitsAccess,
        _context,
        _hostSession,
        successCallback,
        errorCallback,
    ):
        """
        Query the traits associated with each of the given entities.
        """
        # For now, we'll only support read access
        if entityTraitsAccess != EntityTraitsAccess.kRead:
            result = BatchElementError(
                BatchElementError.ErrorCode.kEntityAccessError, "Entities are read-only"
            )
            for idx in range(len(entityReferences)):
                errorCallback(idx, result)
            return

        # Process each reference
        for idx, ref in enumerate(entityReferences):
            ref_str = ref.toString()

            parsed_ref = self.__parse_reference(ref_str)

            if parsed_ref is None:
                error_result = BatchElementError(
                    BatchElementError.ErrorCode.kMalformedEntityReference,
                    "Entity identifier is malformed",
                )
                errorCallback(idx, error_result)
                continue

            if parsed_ref.type == _ReferenceType.ASSET:

                ref_filter = self.__parsed_asset_reference_to_query_filter(parsed_ref)

                asset = self.__sgclient.find_one(*ref_filter)

                if not asset:
                    error_result = BatchElementError(
                        BatchElementError.ErrorCode.kEntityResolutionError,
                        f"Entity '{ref_str}' not found",
                    )
                    errorCallback(idx, error_result)
                    continue

                traits = {EntityTrait.kId, LocatableContentTrait.kId, DisplayNameTrait.kId}
                successCallback(idx, traits)

            elif parsed_ref.type == _ReferenceType.WORKFILE:
                # We only support resolving path for workfiles. Assumes
                # the "entity" exists - i.e. the "entity" is the path,
                # whether it's a valid path is a separate concern.
                traits = {EntityTrait.kId, LocatableContentTrait.kId}
                successCallback(idx, traits)

    def resolve(
        self,
        entityReferences,
        traitSet,
        resolveAccess,
        _context,
        _hostSession,
        successCallback,
        errorCallback,
    ):
        """
        Query trait properties for each of the given entities.
        """
        # For now, we'll only support read access
        if resolveAccess != ResolveAccess.kRead:
            result = BatchElementError(
                BatchElementError.ErrorCode.kEntityAccessError, "Entities are read-only"
            )
            for idx in range(len(entityReferences)):
                errorCallback(idx, result)
            return

        fields = []
        if LocatableContentTrait.kId in traitSet:
            # TODO(DF): Will eventually have to construct fields based
            #  on asset type (trait set).
            # PublishedFile objects
            fields.append("path")
            # Version objects
            fields.append("sg_path_to_movie")
            fields.append("sg_path_to_geometry")
            fields.append("sg_path_to_frames")
            fields.append("sg_uploaded_movie")
        if DisplayNameTrait.kId in traitSet:
            fields.append("name")
        if FrameRangedTrait.kId in traitSet:
            fields.append("entity.Shot.sg_cut_in")
            fields.append("entity.Shot.sg_cut_out")
            fields.append("entity.Shot.sg_head_in")
            fields.append("entity.Shot.sg_tail_out")

        # Process each reference
        for idx, ref in enumerate(entityReferences):
            ref_str = ref.toString()
            parsed_ref = self.__parse_reference(ref_str)

            if parsed_ref is None:
                error_result = BatchElementError(
                    BatchElementError.ErrorCode.kMalformedEntityReference,
                    "Entity identifier is malformed",
                )
                errorCallback(idx, error_result)
                continue

            if parsed_ref.type == _ReferenceType.ASSET:
                self.__resolve_asset(idx, parsed_ref, fields, successCallback, errorCallback)

            elif parsed_ref.type == _ReferenceType.WORKFILE:
                success_result = TraitsData()

                if LocatableContentTrait.kId in traitSet:

                    LocatableContentTrait(success_result).setLocation(
                        self.__file_url_path_converter.pathToUrl(
                            parsed_ref.template.apply_fields(parsed_ref.fields)
                        )
                    )

                successCallback(idx, success_result)

    def __resolve_asset(
        self,
        idx,
        parsed_ref: "_ParsedReference",
        fields,
        successCallback,
        errorCallback,
    ):
        """
        Resolve the traits of an entity by querying the SGTK server.
        """
        asset_data = self.__sgclient.find_one(
            *self.__parsed_asset_reference_to_query_filter(parsed_ref), fields
        )

        if not asset_data:
            error_result = BatchElementError(
                BatchElementError.ErrorCode.kEntityResolutionError,
                f"Entity '{parsed_ref.ref_str}' not found",
            )
            errorCallback(idx, error_result)
            return

        success_result = TraitsData()

        if paths := asset_data.get("path"):
            # Note: "url" is not encoded properly, so must get path and
            # encode ourselves.
            if path := paths.get("local_path"):
                url = self.__file_url_path_converter.pathToUrl(path)
                LocatableContentTrait(success_result).setLocation(url)
            elif path := paths.get("url"):
                # If project/platform root path is not configured,
                # only available path may be a URL, so may as well try
                # that.
                LocatableContentTrait(success_result).setLocation(path)
            else:
                # Has the location trait, but the location isn't
                # valid for the local system.
                LocatableContentTrait.imbueTo(success_result)

        elif path := (
            asset_data.get("sg_path_to_frames")
            or asset_data.get("sg_path_to_geometry")
            or asset_data.get("sg_path_to_movie")
        ):
            url = self.__file_url_path_converter.pathToUrl(path)
            LocatableContentTrait(success_result).setLocation(url)

        elif url_data := asset_data.get("sg_uploaded_movie"):
            LocatableContentTrait(success_result).setLocation(url_data["url"])

        if name := asset_data.get("name"):
            DisplayNameTrait(success_result).setName(name)

        if frame := asset_data.get("entity.Shot.sg_head_in"):
            FrameRangedTrait(success_result).setStartFrame(frame)
        if frame := asset_data.get("entity.Shot.sg_tail_out"):
            FrameRangedTrait(success_result).setEndFrame(frame)
        if frame := asset_data.get("entity.Shot.sg_cut_in"):
            FrameRangedTrait(success_result).setInFrame(frame)
        if frame := asset_data.get("entity.Shot.sg_cut_out"):
            FrameRangedTrait(success_result).setOutFrame(frame)

        successCallback(idx, success_result)

    @property
    def __sgtk(self):
        """
        FPT Toolkit Core API instance.

        Must do this lazily, since FPT initialization may augment
        sys.path with a custom location, overriding any previously
        loaded sgtk package, including its global variables.
        """
        if self.__sgtk_lazy is not None:
            return self.__sgtk_lazy

        # pylint: disable=import-outside-toplevel,import-error
        import sgtk

        # pylint: disable=no-member
        engine = sgtk.platform.current_engine()
        if engine:
            self.__sgtk_lazy = engine.sgtk
        elif self.__project_id:
            self.__sgtk_lazy = sgtk.sgtk_from_entity("Project", self.__project_id)

        return self.__sgtk_lazy

    @classmethod
    def __parsed_asset_reference_to_query_filter(
        cls, ref: "_ParsedReference"
    ) -> Optional[tuple[str, list]]:
        """
        Convert a parsed reference to arguments suitable for a `find`
        query via the SGTK Python SDK.
        """
        return ref.fields["type"], [["id", "is", ref.fields["id"]]]

    def __parse_reference(self, ref_str: str) -> Optional["_ParsedReference"]:
        """
        Parse an entity reference string into its components.

        Formats:
          - fpt://asset/{asset_type}/{asset_id}
          - fpt://workfile/{template_name}/{field1}/{field2}...
        """
        if not ref_str.startswith(self.reference_prefix):
            return None

        # Remove prefix and split path
        ref_type, *parts = ref_str[len(self.reference_prefix):].split("/")

        min_num_parts = 2

        if len(parts) < min_num_parts:
            return None

        if ref_type == "asset":
            # Normal assets are database entries. They are uniquely
            # identified by a composite key of type and id.
            return self.__parse_asset_reference(ref_str, parts)

        if ref_type == "workfile":
            return self.__parse_workfile_reference(ref_str, parts)

        return None

    def __parse_asset_reference(
        self, ref_str: str, parts: list[str]
    ) -> Optional["_ParsedReference"]:
        """
        Parse an exploded asset reference.

        I.e. fpt://asset/{asset_type}/{asset_id}
        """
        expected_num_parts = 2

        if len(parts) != expected_num_parts:
            return None

        obj_type, ident_str = parts

        try:
            ident = int(ident_str)
        except ValueError:
            return None

        return _ParsedReference(
            ref_str=ref_str, type=_ReferenceType.ASSET, fields={"type": obj_type, "id": ident}
        )

    def __parse_workfile_reference(
        self, ref_str: str, parts: list[str]
    ) -> Optional["_ParsedReference"]:
        """
        Parse an exploded workfile reference.

        I.e. fpt://workfile/{template_name}/{field1}/{field2}...
        """
        # We require an FPT Toolkit Core API instance, which is separate
        # from the FPT client API SDK.
        if self.__sgtk is None:
            return None

        # Workfiles are stored on disk and not in the database. So
        # we require the entity reference to contain the file path
        # template name and the fields for the template, in the
        # correct order.
        tmplt_key, *field_values = parts

        tmplt = self.__sgtk.templates[tmplt_key]
        try:
            # Cannot use k.value_from_str() since version numbers
            # won't have any zero-padding, so validation may fail.
            # So we skip validation by using k._as_value() and just
            # catch any exception.
            # pylint: disable=protected-access
            fields = {k.name: k._as_value(f) for k, f in zip(tmplt.ordered_keys, field_values)}
        except Exception:  # pylint: disable=broad-exception-caught
            return None

        return _ParsedReference(
            ref_str=ref_str, type=_ReferenceType.WORKFILE, fields=fields, template=tmplt
        )


class _ReferenceType(Enum):
    """
    Enum to differentiate different kinds of entity reference.
    """

    ASSET = 1
    WORKFILE = 2


_ParsedReference = namedtuple(
    "ParsedReference", ("ref_str", "type", "fields", "template"), defaults=(None,)
)
