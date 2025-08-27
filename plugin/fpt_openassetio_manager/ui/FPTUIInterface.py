# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 The Foundry Visionmongers Ltd
"""
FPT OpenAssetIO UI delegate.
"""
# pylint: disable=invalid-name

from collections import defaultdict

try:
    from PySide6 import QtWidgets
except ImportError:
    from PyQt5 import QtWidgets


import openassetio
from openassetio import EntityReference
from openassetio.managerApi import HostSession
from openassetio.trait import TraitsData
from openassetio.ui import access
from openassetio.ui.managerApi import (
    UIDelegateInterface,
    UIDelegateRequest,
    UIDelegateStateInterface,
)
from openassetio_mediacreation.traits.application import WorkTrait
from openassetio_mediacreation.traits.identity import DisplayNameTrait
from openassetio_mediacreation.traits.threeDimensional import GeometryTrait
from openassetio_mediacreation.traits.twoDimensional import ImageTrait
from openassetio_mediacreation.traits.ui import (
    BrowserTrait,
    DetachedTrait,
    EntityInfoTrait,
    EntityProviderTrait,
    InlineTrait,
    InPlaceTrait,
    SingleUseTrait,
    TabbedTrait,
)
from openassetio_mediacreation.traits.uiPolicy import ManagedTrait

from ..FPTManagerInterface import FPTManagerInterface

# List of trait sets and the filters that should be applied by default
# to the loader (asset browser). Most-specific (i.e. largest) trait sets
# should be at the top to take precedence.
# TODO(DF): This is site-specific - should get this mapping from
#  settings passed to initialize() (i.e. from the config file).
trait_set_to_filter_names = [
    ({WorkTrait.kId}, {"Nuke Script", "Katana File", "Mari Archive", "Maya Scene"}),
    ({ImageTrait.kId}, {"Rendered Image", "Render Image", "UDIM Image", "Movie"}),
    ({GeometryTrait.kId}, {"Alembic Cache", "Vdb File"}),
]


class FPTUIState(UIDelegateStateInterface):
    """
    FPT UI state class.

    This class is used to store the state of a delegated UI element,
    such as the currently selected entity references.
    """

    def __init__(self):
        """
        Initialize the FPT UI state to empty.
        """
        UIDelegateStateInterface.__init__(self)
        self.__entity_references = []
        self.__native_data = None
        self.__updateRequestCallback = None

    def setEntityReferences(self, entity_references):
        """
        Set the currently selected entity references.
        """
        self.__entity_references = entity_references

    def entityReferences(self):
        """
        Get the currently selected entity references.
        """
        return self.__entity_references

    def entityTraitsDatas(self):
        """
        Get the currently selected traits.

        This is not used by the FPT UI delegate, so always returns an
        empty list.
        """
        return []

    def setNativeData(self, native_data):
        """
        Set the native data for the UI state.

        This is (potentially) used to store the native widget that is
        being displayed in the UI delegate.
        """
        self.__native_data = native_data

    def nativeData(self):
        """
        Get the native data for the UI state.

        This is (potentially) used to store the native widget that is
        being displayed in the UI delegate.
        """
        return self.__native_data

    def setUpdateRequestCallback(self, callback):
        """
        Set the update request callback.

        This is used to allow the host application to request updates
        to the UI delegate, e.g. to change the currently displayed
        entity.
        """
        self.__updateRequestCallback = callback

    def updateRequestCallback(self):
        """
        Get the update request callback.

        This is used to allow the host application to request updates
        to the UI delegate, e.g. to change the currently displayed
        entity.
        """
        return self.__updateRequestCallback


class FPTUIInterface(UIDelegateInterface):
    """
    FPT UI delegate interface.

    This class will be called by the host application to request UI
    elements.
    """

    __browser_name = "FPT Asset Browser"

    def __init__(self):
        """
        Initialize the FPT UI delegate interface.
        """
        UIDelegateInterface.__init__(self)
        # Stash for widgets that need to be kept alive, and properly
        # disposed on host application exit.
        self.__sgtk_engine_lazy = None
        self.__widget_stash = None

    def displayName(self):
        """
        Retrieve the display name of the UI delegate.
        """
        return "FPT UI"

    def identifier(self):
        """
        Retrieve the unique identifier of the UI delegate.

        Must match the unique identifier of the corresponding manager
        plugin.
        """
        return "org.foundry.fpt"

    def initialize(self, _managerSettings, hostSession):
        """
        Initialize the UI delegate.
        """
        # Ensure we have an "off-screen" widget that can hold
        # dialogs when they're not in use, and clean them up when
        # the host exits
        if self.__widget_stash is None:
            self.__widget_stash = WidgetStash(hostSession.logger())

    def uiPolicy(self, _uiTraits, uiAccess, _context, _hostSession):
        """
        UI policy for the given traits and access level.
        """
        policy = TraitsData()
        # Read-only (no publishing support) for now.
        if uiAccess == access.UIAccess.kRead:
            ManagedTrait.imbueTo(policy)
            DisplayNameTrait(policy).setName(self.__browser_name)
        return policy

    def populateUI(self, uiTraits, uiAccess, uiDelegateRequest, context, hostSession):
        """
        Populate the UI for the given traits and access level.

        The Qt widget will either be provided in the returned state's
        nativeData() (for DetachedTrait), or added to the container
        provided in the request's nativeData() (for InPlaceTrait).
        """
        # pylint: disable=too-many-arguments,too-many-positional-arguments
        try:
            if self.__sgtk_engine is None:
                hostSession.logger().warning(
                    "OpenAssetIO FPT UI delegate requires an active SGTK engine"
                )
                return None

            if uiAccess != access.UIAccess.kRead:
                # We don't support publishing widgets, yet.
                return None

            initial_state = FPTUIState()

            widget = None

            if BrowserTrait.isImbuedTo(uiTraits) and EntityProviderTrait.isImbuedTo(uiTraits):
                widget = self.__create_read_asset_browser(
                    uiTraits,
                    uiDelegateRequest,
                    context,
                    hostSession,
                    initial_state,
                )
            elif InlineTrait.isImbuedTo(uiTraits) and EntityInfoTrait.isImbuedTo(uiTraits):
                widget = self.__create_inline_entity_info(
                    uiDelegateRequest, hostSession, initial_state
                )

            if widget is None:
                return None

            # Add a tab to the container.
            if InPlaceTrait.isImbuedTo(uiTraits):
                container = uiDelegateRequest.nativeData()
                if container is not None:
                    if TabbedTrait.isImbuedTo(uiTraits):
                        tab_idx = container.addTab(widget, self.__browser_name)
                        container.setCurrentIndex(tab_idx)
                    elif container.layout() is not None:
                        container.layout().addWidget(widget)
                    else:
                        widget.setParent(container)

            if DetachedTrait.isImbuedTo(uiTraits):
                initial_state.setNativeData(widget)

            return initial_state

        except Exception:  # pylint: disable=broad-exception-caught
            import traceback  # pylint: disable=import-outside-toplevel

            hostSession.logger().error(f"Failed to display FPT UI: {traceback.format_exc()}")
            return None

    def __create_read_asset_browser(
        self,
        ui_traits: TraitsData,
        request: UIDelegateRequest,
        context: openassetio.Context,
        host_session: HostSession,
        state: FPTUIState,
    ):
        # pylint: disable=too-many-arguments,too-many-positional-arguments
        entity_traits_datas = request.entityTraitsDatas()

        if entity_traits_datas is not None and all(
            WorkTrait.isImbuedTo(t) for t in entity_traits_datas
        ):
            # We're dealing (only) with work entities, so we'll use the
            # workfiles browser.
            return self.__create_workfiles_browser(
                ui_traits, request, context, host_session, state
            )

        return self.__create_loader_browser(ui_traits, request, context, host_session, state)

    def __create_workfiles_browser(
        self,
        ui_traits: TraitsData,
        request: UIDelegateRequest,
        context: openassetio.Context,
        host_session: HostSession,
        state: FPTUIState,
    ):
        """
        Create an FPT tk-multi-workfiles2 workfile browser for project
        files.

        This is special in that workfiles may not exist yet in the FPT
        database and are just globbed from disk, using defined path
        templates.
        """
        # pylint: disable=too-many-arguments,too-many-positional-arguments
        app = self.__sgtk_engine.apps.get("tk-multi-workfiles2")
        if app is None:
            host_session.logger().warning(
                "FPT browser requested but tk-multi-workfiles2 unavailable - have you set your FPT"
                " context appropriately? - attempting tk-multi-loader instead"
            )
            return self.__create_loader_browser(ui_traits, request, context, host_session, state)

        pkg = app.import_module("tk_multi_workfiles")

        class FileOpenForm(pkg.file_open_form.FileOpenForm):
            # pylint: disable=too-few-public-methods
            """
            Override base widget to customise actions.
            """

            def _perform_action(self, action):
                """
                Override base class method that executes the action
                chosen in the UI.

                Override base class so that the widget is not closed. It
                is up to the host application to decide when to close.

                Note that FPT will open the file in the host. Naively,
                we would like to block this and return an entity
                reference to the host, allowing the host to open the
                file. However, FPT can do non-trivial work culminating
                in opening the file e.g.
                  * Dialogs prompting the user (e.g. read-only state).
                  * Copying files if a user sandbox is active.
                  * Changing the global FPT context.
                  * Calling host application FPT-specific hooks.

                So we allow FPT to open the file in the host. We _also_
                return an entity reference to the host, and just hope
                that the host does the right thing.
                """
                if not action:
                    return

                close_dialog = action.execute(self)

                if not SingleUseTrait.isImbuedTo(ui_traits):
                    self._refresh_all_async()

                # Assume an item has been selected to open only if close
                # dialog is requested.
                if not close_dialog:
                    return
                # We only care about file-open actions.
                if not isinstance(action, pkg.actions.file_action.FileAction):
                    return

                if action.file.is_local:
                    tmplt = action.environment.work_template
                    fields = tmplt.get_fields(action.file.path)
                    fields_str = "/".join(str(fields[k.name]) for k in tmplt.ordered_keys)
                    ref = f"fpt://workfile/{tmplt.name}/{fields_str}"
                else:
                    # TODO(DF): is this branch ever taken?
                    ref = f"fpt://asset/PublishedFile/{action.file.published_file_id}"

                state.setEntityReferences([EntityReference(ref)])

                if callback := request.stateChangedCallback():
                    callback(state)

            def _on_cancel(self):
                state.setEntityReferences([])
                if callback := request.stateChangedCallback():
                    callback(state)

        class FileOpenFormContainer(QtWidgets.QWidget):
            """
            Container managing the state of the FPT workfiles browser.

            We must ensure the FPT FileOpenForm is properly closed in
            all cases. E.g. if the browser is hidden then destroyed,
            then `closeEvent()` is not called - this can happen with
            QDialog modal dialogs, which after `exec()` is done just
            hides, rather than closes.

            So here, we pull from a pool of widgets, constructing if not
            available. Luckily `showEvent` and `hideEvent` _are_
            triggered during the QDialog.exec_ process, so we put our
            construction/destruction logic (i.e. fetch from pool, return
            to pool) in there.
            """

            def __init__(self, widget_stash):
                QtWidgets.QWidget.__init__(self)
                self.__widget_stash = widget_stash
                self.__child = None

                self.setLayout(QtWidgets.QVBoxLayout())
                self.setSizePolicy(
                    QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
                )

            def showEvent(self, _event):
                """
                Override to retrieve cached widget from pool, or
                construct if none available.
                """
                if self.__child is not None:
                    return
                self.__child = self.__widget_stash.get_from_pool(
                    "tk-multi-workfiles2", self, FileOpenForm
                )
                self.layout().addWidget(self.__child)

            def hideEvent(self, _event):
                """
                Override to return widget to pool for later reuse.
                """
                if self.__child is None:
                    return
                self.__widget_stash.add_to_pool("tk-multi-workfiles2", self.__child)
                self.__child = None

        browser = QtWidgets.QWidget()
        browser.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        browser.setLayout(QtWidgets.QVBoxLayout())
        browser.layout().addWidget(FileOpenFormContainer(self.__widget_stash))
        return browser

    def __create_loader_browser(
        self,
        ui_traits: TraitsData,
        request: UIDelegateRequest,
        _context: openassetio.Context,
        host_session: HostSession,
        state: FPTUIState,
    ):
        """
        Create an FPT tk-multi-loader2 loader browser, for generic
        assets.
        """
        # pylint: disable=too-many-arguments,too-many-locals
        # pylint: disable=too-many-positional-arguments
        # pylint: disable=too-many-statements
        app = self.__sgtk_engine.apps.get("tk-multi-loader2")
        if app is None:
            host_session.logger().warning(
                "FPT browser requested but tk-multi-loader2 unavailable - have you set your FPT"
                " context appropriately?"
            )
            return None

        pkg = app.import_module("tk_multi_loader")

        class ActionManager(pkg.action_manager.ActionManager):
            """
            Action manager to define QActions for FPT assets to be
            shown in the loader.

            We don't define any actions, just use it for filtering
            available asset types from the view.
            """

            def __init__(self, request, *args, **kwargs):
                self.__enabled_filters = None
                self.update_filters_from_request(request)
                super().__init__(*args, **kwargs)

            def has_actions(self, code):
                """
                Check if the given FPT Published File Type is supported.

                This is called internally by the AppDialog. If there are
                no enabled actions for any type (`code`), the behaviour
                is to present an unfiltered browser.
                """
                return code in self.__enabled_filters

            def get_actions_for_publish(self, sg_data, ui_area):
                """
                Bug in base class - this method doesn't exist despite
                being used.
                """
                return self.get_actions_for_publishes([sg_data], ui_area)

            def update_filters_from_request(self, request):
                """
                Find a match in the global mapping of trait sets to FPT
                Published File Types, to use for filtering presented assets.
                """
                host_session.logger().debug(
                    f"Updating FPT loader filters using {request.entityTraitsDatas()}"
                )

                prev_enabled_filters = self.__enabled_filters
                self.__enabled_filters = set()

                if entity_traits_datas := request.entityTraitsDatas():
                    # TODO(DF): support multiple trait sets.
                    entity_traits = entity_traits_datas[0].traitSet()
                    for filter_trait_set, filter_names in trait_set_to_filter_names:
                        if filter_trait_set.issubset(entity_traits):
                            self.__enabled_filters = filter_names
                            break

                host_session.logger().debug(
                    f"Enabling FPT loader filters: {self.__enabled_filters}"
                )
                return prev_enabled_filters != self.__enabled_filters

        class AppDialog(pkg.dialog.AppDialog):
            """
            The FPT loader browser widget.

            Override base class to allow updatable filtering of FPT
            asset types.
            """

            def __init__(self, *args, **kwargs):
                self.__selected_entities = None
                super().__init__(*args, **kwargs)

            @property
            def selected_publishes_or_entities(self):
                """
                Get selected item.

                Prefer any PublishedFile that is selected, before
                falling back on other selected entity types.
                """
                return self.selected_publishes or self.__selected_entities or []

            def reload_filters_from_request(self, request: UIDelegateRequest):
                """
                Patch an issue in the base class.
                """
                # Patch bug in tk-multi-loader2 1.25.2 - if the
                # `SgHierarchyModel` is used then a reload will attempt
                # to call `_refresh_data()`, but that method doesn't
                # exist. There is a `reload_data` method, but that uses
                # a `_root_entity` member variable that doesn't exist
                # and calls the base class `load_data`  method with the
                # wrong signature.
                for entity_preset in self._entity_presets.values():
                    if isinstance(entity_preset.model, pkg.model_hierarchy.SgHierarchyModel):
                        if not hasattr(entity_preset.model, "_refresh_data"):
                            # pylint: disable=protected-access
                            entity_preset.model._refresh_data = lambda *a, **kw: None

                if self._action_manager.update_filters_from_request(request):
                    self._reload_action.trigger()

            def _on_treeview_item_selected(self):
                """
                Override base class to track selected items other than
                PublishedFiles.

                Selected items can include Project, Task, Shot or
                Sequence. Sadly, the tk-multi-loader2 widget does not
                show Versions.
                """
                super()._on_treeview_item_selected()

                prev_selected_publishes_or_entities = self.selected_publishes_or_entities

                selected_item = self._get_selected_entity()
                sg_data, field_value = pkg.model_item_data.get_item_data(selected_item)

                if sg_data is not None:
                    self.__selected_entities = [sg_data]
                elif (
                    isinstance(field_value, dict)
                    and "name" in field_value
                    and "type" in field_value
                ):
                    self.__selected_entities = [field_value]
                else:
                    self.__selected_entities = None

                if (
                    self.selected_publishes_or_entities
                    and self.selected_publishes_or_entities != prev_selected_publishes_or_entities
                ):
                    self.selection_changed.emit()

        class AppDialogContainer(QtWidgets.QWidget):
            """
            Container managing the state of the FPT loader browser.

            We must ensure the FPT AppDialog is properly closed in all
            cases. E.g. if the browser is hidden then destroyed, then
            `closeEvent()` is not called - this can happen with QDialog
            modal dialogs, which after `exec_()` is done just hides,
            rather than closes.

            So here, we pull from a pool of widgets, constructing if not
            available. Luckily `showEvent` and `hideEvent` _are_
            triggered during the QDialog.exec_ process, so we put our
            construction/destruction logic (i.e. fetch from pool, return
            to pool) in there.
            """

            def __init__(self, widget_stash):
                QtWidgets.QWidget.__init__(self)
                self.__widget_stash = widget_stash
                self.__child = None
                self.setLayout(QtWidgets.QVBoxLayout())
                self.setSizePolicy(
                    QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
                )

            def showEvent(self, _event):
                """
                Override to retrieve cached widget from pool, or
                construct if none available.
                """
                if self.__child is not None:
                    return

                self.__child = self.__widget_stash.get_from_pool(
                    "tk-multi-loader2", self, lambda: AppDialog(ActionManager(request))
                )
                self.__child.reload_filters_from_request(request)

                self.layout().addWidget(self.__child)

                if not SingleUseTrait.isImbuedTo(ui_traits):
                    self.__child.selection_changed.connect(self.on_selection_changed)

            def hideEvent(self, _event):
                """
                Override to return widget to pool for later reuse.
                """
                if self.__child is None:
                    return

                if not SingleUseTrait.isImbuedTo(ui_traits):
                    self.__child.selection_changed.disconnect(self.on_selection_changed)

                self.__widget_stash.add_to_pool("tk-multi-loader2", self.__child)
                self.__child = None

            def on_selection_changed(self):
                """
                Slot called when the selection in the browser changes.

                Call request callback with updated entity references.
                """
                entity_references = [
                    EntityReference(f"fpt://asset/{p['type']}/{p['id']}")
                    for p in self.__child.selected_publishes_or_entities
                ]
                state.setEntityReferences(entity_references)
                request.stateChangedCallback()(state)

        browser = QtWidgets.QWidget()
        browser.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        browser.setLayout(QtWidgets.QVBoxLayout())
        dialog_container = AppDialogContainer(self.__widget_stash)
        browser.layout().addWidget(dialog_container)

        if SingleUseTrait.isImbuedTo(ui_traits):
            # Add an OK and Cancel button to the bottom of the browser.
            buttons = QtWidgets.QWidget()
            browser.layout().addWidget(buttons)

            buttons.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            button_layout = QtWidgets.QHBoxLayout()
            buttons.setLayout(button_layout)
            button_layout.setContentsMargins(10, 0, 10, 10)
            button_layout.addStretch()

            ok_button = QtWidgets.QPushButton("OK")
            ok_button.clicked.connect(dialog_container.on_selection_changed)
            button_layout.addWidget(ok_button)

            cancel_button = QtWidgets.QPushButton("Cancel")

            def on_cancel():
                state.setEntityReferences([])
                request.stateChangedCallback()(state)

            cancel_button.clicked.connect(on_cancel)
            button_layout.addWidget(cancel_button)

        return browser

    def __create_inline_entity_info(
        self,
        initial_request: UIDelegateRequest,
        host_session: HostSession,
        initial_state: FPTUIState,
    ):
        """
        Create a tk-multi-shotgunpanel asset info panel.

        Initialises to info for the initial entity reference, if given.
        Otherwise will show a generic info panel about the current task.

        Adds an updateRequestCallback to allow the host to change the
        targeted entity.
        """
        app = self.__sgtk_engine.apps.get("tk-multi-shotgunpanel")
        if app is None:
            host_session.logger().warning(
                "FPT browser requested but tk-multi-shotgunpanel unavailable - have you set your"
                " FPT context appropriately?"
            )
            return None

        pkg = app.import_module("app")

        host_session.logger().debug(
            f"Adding inline entity info for {initial_request.entityReferences()}"
        )

        class AppDialogContainer(QtWidgets.QWidget):
            """
            Container managing the state of the FPT info panel.

            We must ensure the FPT AppDialog is properly closed in all
            cases. E.g. if the browser is hidden then destroyed, then
            `closeEvent()` is not called.

            So we maintain a pool of info widgets and reuse them when
            possible, or create a new one if none are available.
            """

            def __init__(self, widget_stash: "WidgetStash"):
                QtWidgets.QWidget.__init__(self)
                self.setLayout(QtWidgets.QVBoxLayout())
                self.setSizePolicy(
                    QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
                )
                self.__widget_stash = widget_stash
                self.__child = None
                self.__entity_type_and_id = None

            def showEvent(self, _event):
                """
                Override to retrieve cached widget from pool, or
                construct if none available, then navigate to the
                requested entity (if any).
                """
                if self.__child is not None:
                    return

                self.__child = self.__widget_stash.get_from_pool(
                    "tk-multi-shotgunpanel", self, pkg.dialog.AppDialog
                )
                self.layout().addWidget(self.__child)

                if self.__entity_type_and_id is not None:
                    self.__child.navigate_to_entity(*self.__entity_type_and_id)
                else:
                    self.__child._on_home_clicked()  # pylint: disable=protected-access

            def hideEvent(self, _event):
                """
                Override to return widget to pool for later reuse.
                """
                if self.__child is None:
                    return

                self.__widget_stash.add_to_pool("tk-multi-shotgunpanel", self.__child)
                self.__child = None

            def update_request(self, new_request: UIDelegateRequest):
                """
                Update the entity info panel to show the entity provided
                in the request.
                """
                if new_request is None:
                    self.hide()
                    self.close()
                    return

                host_session.logger().debug(
                    f"Updating inline entity info for {new_request.entityReferences()}"
                )
                try:
                    if refs := new_request.entityReferences():
                        ref_str = refs[0].toString()
                        ref_parts = ref_str[len(FPTManagerInterface.reference_prefix) :].split("/")
                        expected_num_parts = 3  # "asset", <type>, <id>
                        if len(ref_parts) != expected_num_parts:
                            host_session.logger().warning(
                                f"Unsupported reference for entity info panel: {ref_str}"
                            )
                            return

                        self.__entity_type_and_id = (ref_parts[1], int(ref_parts[2]))

                        # Dialog can be None if just created, in which
                        # case showEvent will handle navigation.
                        if self.__child is None:
                            return

                        self.__child.navigate_to_entity(*self.__entity_type_and_id)

                except Exception as exc:  # pylint: disable=broad-exception-caught
                    host_session.logger().error(
                        f"Failed to update inline entity info panel: {exc}"
                    )

            def closeEvent(self, event):
                """
                Override to ensure the child widget is closed.
                """
                host_session.logger().debug("Closing inline entity info")
                self.__child.close()
                super().closeEvent(event)

        dialog_container = AppDialogContainer(self.__widget_stash)
        dialog_container.update_request(initial_request)

        initial_state.setUpdateRequestCallback(dialog_container.update_request)

        return dialog_container

    @property
    def __sgtk_engine(self):
        """
        Load FPT currently active engine.

        Must do this lazily, since FPT initialization may augment
        sys.path with a custom location, messing up global variables.
        """
        if self.__sgtk_engine_lazy is not None:
            return self.__sgtk_engine_lazy

        import sgtk  # pylint: disable=import-outside-toplevel,import-error

        self.__sgtk_engine_lazy = sgtk.platform.current_engine()
        return self.__sgtk_engine_lazy


class WidgetStash(QtWidgets.QWidget):
    """
    Pool of widgets to keep alive and clean up properly.

    The most important thing this class does is call `close()` on the
    widgets in the pool when the "aboutToQuit" signal is detected. This
    is important because otherwise QThreads may be left running, which
    causes a fatal exception on program exit. I.e. we cannot trust the
    host application to call `close()` on all its child widgets.

    A secondary benefit of this class is when singleton widgets are
    reused, we keep their state (e.g. selected asset group) between
    views by the user, making for slightly better UX.

    The FPT widgets are also rather leaky, leaving open sockets and
    other things, despite being closed/destroyed. So reusing these
    widgets means less ResourceWarning spam (until the host application
    exits, at least).

    In general, there is no Qt notification to a widget that its about
    to be destroyed. So any widget outside the pool may not get the
    necessary `close()` call when the host exits. However, in all cases
    we return widgets to the pool on `hideEvent`, which does seem to be
    consistently called when a Qt application exits, and is called
    before "aboutToQuit" is triggered. This means even "active" widgets
    end up being cleaned up properly.
    """

    def __init__(self, logger):
        """
        Initialize the widget stash.
        """
        super().__init__()
        self.hide()
        self.__logger = logger
        self.__widget_pool = defaultdict(list)

        QtWidgets.QApplication.instance().aboutToQuit.connect(self.__aboutToQuit)

    def get_from_pool(self, key, parent, factory):
        """
        Get a widget from the pool identified by `key`, or create a new
        one if none available.
        """
        if widgets := self.__widget_pool.get(key):
            self.__logger.debug(f"WidgetStash: found available {key}")
            widget = widgets.pop()
        else:
            self.__logger.debug(f"WidgetStash: creating new {key}")
            widget = factory()

        widget.setParent(parent)
        return widget

    def add_to_pool(self, key, widget):
        """
        Return a widget to the pool identified by `key`.
        """
        self.__logger.debug(f"WidgetStash: returning a {key} to the pool")
        widget.setParent(self)
        self.__widget_pool[key].append(widget)

    def __aboutToQuit(self, *_args):
        """
        Event handler for "aboutToQuit" signal.

        Clean up all widgets in pools by calling `close()` on them.
        """
        self.__logger.debug("WidgetStash: aboutToQuit - cleaning up")

        for widgets in self.__widget_pool.values():
            for widget in widgets:
                widget.close()
