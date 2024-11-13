# Utilities for obtaining event-related information.
#
# Copyright 2024 Igalia, S.L.
# Copyright 2024 GNOME Foundation Inc.
# Author: Joanmarie Diggs <jdiggs@igalia.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., Franklin Street, Fifth Floor,
# Boston MA  02110-1301 USA.

# pylint: disable=too-many-return-statements
# pylint: disable=duplicate-code
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements

"""Utilities for obtaining event-related information."""

__id__        = "$Id$"
__version__   = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2024 Igalia, S.L." \
                "Copyright (c) 2024 GNOME Foundation Inc."
__license__   = "LGPL"

import enum
import threading
import time

from . import debug
from . import focus_manager
from . import input_event_manager

from .ax_object import AXObject
from .ax_text import AXText
from .ax_utilities_role import AXUtilitiesRole
from .ax_utilities_state import AXUtilitiesState

class TextEventReason(enum.Enum):
    """Enum representing the reason for an object:text- event."""

    UNKNOWN = 0
    AUTO_DELETION = 1
    AUTO_INSERTION = 2
    BACKSPACE = 3
    CHILDREN_CHANGE = 4
    CUT = 5
    DELETE = 6
    MOUSE_MIDDLE_BUTTON = 7
    MOUSE_PRIMARY_BUTTON = 8
    NAVIGATION_BY_CHARACTER = 9
    NAVIGATION_BY_LINE = 10
    NAVIGATION_BY_PARAGRAPH = 11
    NAVIGATION_BY_PAGE = 12
    NAVIGATION_BY_WORD = 13
    NAVIGATION_TO_FILE_BOUNDARY = 14
    NAVIGATION_TO_LINE_BOUNDARY = 15
    PAGE_SWITCH = 16
    PASTE = 17
    SELECT_ALL = 18
    SELECTED_TEXT_DELETION = 19
    SELECTED_TEXT_INSERTION = 20
    SELECTED_TEXT_RESTORATION = 21
    SELECTION_BY_CHARACTER = 22
    SELECTION_BY_LINE = 23
    SELECTION_BY_PARAGRAPH = 24
    SELECTION_BY_PAGE = 25
    SELECTION_BY_WORD = 26
    SELECTION_TO_FILE_BOUNDARY = 27
    SELECTION_TO_LINE_BOUNDARY = 28
    SPIN_BUTTON_VALUE_CHANGE = 29
    TYPING = 30
    REDO = 31
    UI_UPDATE = 32
    UNDO = 33
    UNSPECIFIED_COMMAND = 34
    UNSPECIFIED_NAVIGATION = 35
    UNSPECIFIED_SELECTION = 36


class AXUtilitiesEvent:
    """Utilities for obtaining event-related information."""

    LAST_KNOWN_DESCRIPTION: dict[int, str] = {}
    LAST_KNOWN_NAME: dict[int, str] = {}

    LAST_KNOWN_CHECKED: dict[int, bool] = {}
    LAST_KNOWN_EXPANDED: dict[int, bool] = {}
    LAST_KNOWN_INDETERMINATE: dict[int, bool] = {}
    LAST_KNOWN_PRESSED: dict[int, bool] = {}
    LAST_KNOWN_SELECTED: dict[int, bool] = {}

    TEXT_EVENT_REASON: dict[int, TextEventReason] = {}

    _lock = threading.Lock()

    @staticmethod
    def _clear_stored_data():
        """Clears any data we have cached for objects"""

        while True:
            time.sleep(60)
            AXUtilitiesEvent._clear_all_dictionaries()

    @staticmethod
    def _clear_all_dictionaries(reason=""):
        msg = "AXUtilitiesEvent: Clearing local cache."
        if reason:
            msg += f" Reason: {reason}"
        debug.print_message(debug.LEVEL_INFO, msg, True)
        AXUtilitiesEvent.LAST_KNOWN_DESCRIPTION.clear()
        AXUtilitiesEvent.LAST_KNOWN_NAME.clear()
        AXUtilitiesEvent.LAST_KNOWN_CHECKED.clear()
        AXUtilitiesEvent.LAST_KNOWN_EXPANDED.clear()
        AXUtilitiesEvent.LAST_KNOWN_INDETERMINATE.clear()
        AXUtilitiesEvent.LAST_KNOWN_PRESSED.clear()
        AXUtilitiesEvent.LAST_KNOWN_SELECTED.clear()
        AXUtilitiesEvent.TEXT_EVENT_REASON.clear()

    @staticmethod
    def clear_cache_now(reason=""):
        """Clears all cached information immediately."""

        AXUtilitiesEvent._clear_all_dictionaries(reason)

    @staticmethod
    def save_object_info_for_events(obj):
        """Saves properties, states, etc. of obj for later use in event processing."""

        if obj is None:
            return

        AXUtilitiesEvent.LAST_KNOWN_DESCRIPTION[hash(obj)] = AXObject.get_description(obj)
        AXUtilitiesEvent.LAST_KNOWN_NAME[hash(obj)] = AXObject.get_name(obj)
        AXUtilitiesEvent.LAST_KNOWN_CHECKED[hash(obj)] = AXUtilitiesState.is_checked(obj)
        AXUtilitiesEvent.LAST_KNOWN_EXPANDED[hash(obj)] = AXUtilitiesState.is_expanded(obj)
        AXUtilitiesEvent.LAST_KNOWN_INDETERMINATE[hash(obj)] = \
            AXUtilitiesState.is_indeterminate(obj)
        AXUtilitiesEvent.LAST_KNOWN_PRESSED[hash(obj)] = AXUtilitiesState.is_pressed(obj)
        AXUtilitiesEvent.LAST_KNOWN_SELECTED[hash(obj)] = AXUtilitiesState.is_selected(obj)

        window = focus_manager.get_manager().get_active_window()
        AXUtilitiesEvent.LAST_KNOWN_NAME[hash(window)] = AXObject.get_name(window)
        AXUtilitiesEvent.LAST_KNOWN_DESCRIPTION[hash(window)] = AXObject.get_description(window)

    @staticmethod
    def start_cache_clearing_thread():
        """Starts thread to periodically clear cached details."""

        thread = threading.Thread(target=AXUtilitiesEvent._clear_stored_data)
        thread.daemon = True
        thread.start()

    @staticmethod
    def get_last_known_name(obj):
        """Returns the last known name of obj."""

        return AXUtilitiesEvent.LAST_KNOWN_NAME.get(hash(obj), "")

    @staticmethod
    def get_text_event_reason(event):
        """Returns the TextEventReason for the given event."""

        if event.type.startswith("object:text-changed:insert"):
            return AXUtilitiesEvent._get_text_insertion_event_reason(event)
        if event.type.startswith("object:text-caret-moved"):
            return AXUtilitiesEvent._get_caret_moved_event_reason(event)
        if event.type.startswith("object:text-changed:delete"):
            return AXUtilitiesEvent._get_text_deletion_event_reason(event)
        raise ValueError(f"Unexpected event type: {event.type}")

    @staticmethod
    def _get_caret_moved_event_reason(event):
        """Returns the TextEventReason for the given event."""

        reason = AXUtilitiesEvent.TEXT_EVENT_REASON.get(hash(event))
        if reason is not None:
            return reason

        reason = TextEventReason.UNKNOWN
        mgr = input_event_manager.get_manager()
        obj = event.source
        if mgr.last_event_was_caret_selection():
            if mgr.last_event_was_line_navigation():
                reason = TextEventReason.SELECTION_BY_LINE
            elif mgr.last_event_was_word_navigation():
                reason = TextEventReason.SELECTION_BY_WORD
            elif mgr.last_event_was_character_navigation():
                reason = TextEventReason.SELECTION_BY_CHARACTER
            elif mgr.last_event_was_page_navigation():
                reason = TextEventReason.SELECTION_BY_PAGE
            elif mgr.last_event_was_line_boundary_navigation():
                reason = TextEventReason.SELECTION_TO_LINE_BOUNDARY
            elif mgr.last_event_was_file_boundary_navigation():
                reason = TextEventReason.SELECTION_TO_FILE_BOUNDARY
            else:
                reason = TextEventReason.UNSPECIFIED_SELECTION
        elif mgr.last_event_was_caret_navigation():
            if mgr.last_event_was_line_navigation():
                reason = TextEventReason.NAVIGATION_BY_LINE
            elif mgr.last_event_was_word_navigation():
                reason = TextEventReason.NAVIGATION_BY_WORD
            elif mgr.last_event_was_character_navigation():
                reason = TextEventReason.NAVIGATION_BY_CHARACTER
            elif mgr.last_event_was_page_navigation():
                reason = TextEventReason.NAVIGATION_BY_PAGE
            elif mgr.last_event_was_line_boundary_navigation():
                reason = TextEventReason.NAVIGATION_TO_LINE_BOUNDARY
            elif mgr.last_event_was_file_boundary_navigation():
                reason = TextEventReason.NAVIGATION_TO_FILE_BOUNDARY
            else:
                reason = TextEventReason.UNSPECIFIED_NAVIGATION
        elif mgr.last_event_was_select_all():
            reason = TextEventReason.SELECT_ALL
        elif mgr.last_event_was_primary_click_or_release():
            reason = TextEventReason.MOUSE_PRIMARY_BUTTON
        elif AXUtilitiesState.is_editable(obj) or AXUtilitiesRole.is_terminal(obj):
            if mgr.last_event_was_backspace():
                reason = TextEventReason.BACKSPACE
            elif mgr.last_event_was_delete():
                reason = TextEventReason.DELETE
            elif mgr.last_event_was_cut():
                reason = TextEventReason.CUT
            elif mgr.last_event_was_paste():
                reason = TextEventReason.PASTE
            elif mgr.last_event_was_undo():
                reason = TextEventReason.UNDO
            elif mgr.last_event_was_redo():
                reason = TextEventReason.REDO
            elif mgr.last_event_was_page_switch():
                reason = TextEventReason.PAGE_SWITCH
            elif mgr.last_event_was_command():
                reason = TextEventReason.UNSPECIFIED_COMMAND
            elif mgr.last_event_was_printable_key():
                reason = TextEventReason.TYPING

        AXUtilitiesEvent.TEXT_EVENT_REASON[hash(event)] = reason
        msg = f"AXUtilitiesEvent: Reason for event: {reason}"
        debug.print_message(debug.LEVEL_INFO, msg, True)
        return reason

    @staticmethod
    def _get_text_deletion_event_reason(event):
        """Returns the TextEventReason for the given event."""

        reason = AXUtilitiesEvent.TEXT_EVENT_REASON.get(hash(event))
        if reason is not None:
            return reason

        reason = TextEventReason.UNKNOWN
        mgr = input_event_manager.get_manager()
        obj = event.source
        if AXObject.get_role(obj) in AXUtilitiesRole.get_text_ui_roles():
            reason = TextEventReason.UI_UPDATE
        elif mgr.last_event_was_page_switch():
            reason = TextEventReason.PAGE_SWITCH
        elif AXUtilitiesState.is_editable(obj) or AXUtilitiesRole.is_terminal(obj):
            if mgr.last_event_was_backspace():
                reason = TextEventReason.BACKSPACE
            elif mgr.last_event_was_delete():
                reason = TextEventReason.DELETE
            elif mgr.last_event_was_cut():
                reason = TextEventReason.CUT
            elif mgr.last_event_was_paste():
                reason = TextEventReason.PASTE
            elif mgr.last_event_was_undo():
                reason = TextEventReason.UNDO
            elif mgr.last_event_was_redo():
                reason = TextEventReason.REDO
            elif mgr.last_event_was_command():
                reason = TextEventReason.UNSPECIFIED_COMMAND
            elif mgr.last_event_was_printable_key():
                reason = TextEventReason.TYPING
            elif mgr.last_event_was_up_or_down() or mgr.last_event_was_page_up_or_page_down():
                if AXUtilitiesRole.is_spin_button(obj) \
                   or AXObject.find_ancestor(obj, AXUtilitiesRole.is_spin_button):
                    reason = TextEventReason.SPIN_BUTTON_VALUE_CHANGE
                else:
                    reason = TextEventReason.AUTO_DELETION
            if reason == TextEventReason.UNKNOWN:
                selected_text, _start, _end = AXText.get_cached_selected_text(obj)
                if selected_text and event.any_data.strip() == selected_text.strip():
                    reason = TextEventReason.SELECTED_TEXT_DELETION
        elif mgr.last_event_was_command():
            reason = TextEventReason.UNSPECIFIED_COMMAND
        elif "\ufffc" in event.any_data and not event.any_data.replace("\ufffc", ""):
            reason = TextEventReason.CHILDREN_CHANGE

        AXUtilitiesEvent.TEXT_EVENT_REASON[hash(event)] = reason
        msg = f"AXUtilitiesEvent: Reason for event: {reason}"
        debug.print_message(debug.LEVEL_INFO, msg, True)
        return reason

    @staticmethod
    def _get_text_insertion_event_reason(event):
        """Returns the TextEventReason for the given event."""

        reason = AXUtilitiesEvent.TEXT_EVENT_REASON.get(hash(event))
        if reason is not None:
            return reason

        reason = TextEventReason.UNKNOWN
        mgr = input_event_manager.get_manager()
        obj = event.source
        if AXObject.get_role(obj) in AXUtilitiesRole.get_text_ui_roles():
            reason = TextEventReason.UI_UPDATE
        elif mgr.last_event_was_page_switch():
            reason = TextEventReason.PAGE_SWITCH
        elif AXUtilitiesState.is_editable(obj) \
                or AXUtilitiesRole.is_terminal(obj):
            selected_text, _start, _end = AXText.get_selected_text(obj)
            if selected_text and event.any_data == selected_text:
                reason = TextEventReason.SELECTED_TEXT_INSERTION
            if mgr.last_event_was_backspace():
                reason = TextEventReason.BACKSPACE
            elif mgr.last_event_was_delete():
                reason = TextEventReason.DELETE
            elif mgr.last_event_was_cut():
                reason = TextEventReason.CUT
            elif mgr.last_event_was_paste():
                reason = TextEventReason.PASTE
            elif mgr.last_event_was_undo():
                if reason == TextEventReason.SELECTED_TEXT_INSERTION:
                    reason = TextEventReason.SELECTED_TEXT_RESTORATION
                else:
                    reason = TextEventReason.UNDO
            elif mgr.last_event_was_redo():
                if reason == TextEventReason.SELECTED_TEXT_INSERTION:
                    reason = TextEventReason.SELECTED_TEXT_RESTORATION
                else:
                    reason = TextEventReason.REDO
            elif mgr.last_event_was_command():
                reason = TextEventReason.UNSPECIFIED_COMMAND
            elif mgr.last_event_was_printable_key():
                if reason == TextEventReason.SELECTED_TEXT_INSERTION:
                    reason = TextEventReason.AUTO_INSERTION
                else:
                    reason = TextEventReason.TYPING
            elif mgr.last_event_was_middle_click() or mgr.last_event_was_middle_release():
                reason = TextEventReason.MOUSE_MIDDLE_BUTTON
            elif mgr.last_event_was_up_or_down() or mgr.last_event_was_page_up_or_page_down():
                if AXUtilitiesRole.is_spin_button(obj) \
                   or AXObject.find_ancestor(obj, AXUtilitiesRole.is_spin_button):
                    reason = TextEventReason.SPIN_BUTTON_VALUE_CHANGE
                else:
                    reason = TextEventReason.AUTO_INSERTION
            if reason == TextEventReason.UNKNOWN:
                if len(event.any_data) == 1:
                    pass
                elif mgr.last_event_was_tab() and event.any_data != "\t":
                    reason = TextEventReason.AUTO_INSERTION
                elif mgr.last_event_was_return() and event.any_data != "\n":
                    reason = TextEventReason.AUTO_INSERTION
        elif mgr.last_event_was_command():
            reason = TextEventReason.UNSPECIFIED_COMMAND
        elif "\ufffc" in event.any_data and not event.any_data.replace("\ufffc", ""):
            reason = TextEventReason.CHILDREN_CHANGE

        AXUtilitiesEvent.TEXT_EVENT_REASON[hash(event)] = reason
        msg = f"AXUtilitiesEvent: Reason for event: {reason}"
        debug.print_message(debug.LEVEL_INFO, msg, True)
        return reason

    @staticmethod
    def is_presentable_active_descendant_change(event):
        """Returns True if this event should be presented as an active-descendant change."""

        if not event.any_data:
            msg = "AXUtilitiesEvent: No any_data."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        if not (AXUtilitiesState.is_focused(event.source) \
           or AXUtilitiesState.is_focused(event.any_data)):
            msg = "AXUtilitiesEvent: Neither source nor child have focused state."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        focus = focus_manager.get_manager().get_locus_of_focus()
        if AXUtilitiesRole.is_table_cell(focus):
            table = AXObject.find_ancestor(focus, AXUtilitiesRole.is_tree_or_tree_table)
            if table is not None and table != event.source:
                msg = "AXUtilitiesEvent: Event is from a different tree or tree table."
                debug.print_message(debug.LEVEL_INFO, msg, True)
                return False

        msg = "AXUtilitiesEvent: Event is presentable."
        debug.print_message(debug.LEVEL_INFO, msg, True)
        return True

    @staticmethod
    def is_presentable_checked_change(event):
        """Returns True if this event should be presented as a checked-state change."""

        old_state = AXUtilitiesEvent.LAST_KNOWN_CHECKED.get(hash(event.source))
        new_state = AXUtilitiesState.is_checked(event.source)
        if old_state == new_state:
            msg = "AXUtilitiesEvent: The new state matches the old state."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        AXUtilitiesEvent.LAST_KNOWN_CHECKED[hash(event.source)] = new_state
        if event.source != focus_manager.get_manager().get_locus_of_focus():
            msg = "AXUtilitiesEvent: The event is not from the locus of focus."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        # Radio buttons normally change their state when you arrow to them, so we handle the
        # announcement of their state changes in the focus handling code.
        if AXUtilitiesRole.is_radio_button(event.source) \
           and not input_event_manager.get_manager().last_event_was_space():
            msg = "AXUtilitiesEvent: Only presentable for this role if toggled by user."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        msg = "AXUtilitiesEvent: Event is presentable."
        debug.print_message(debug.LEVEL_INFO, msg, True)
        return True

    @staticmethod
    def is_presentable_description_change(event):
        """Returns True if this event should be presented as a description change."""

        old_description = AXUtilitiesEvent.LAST_KNOWN_DESCRIPTION.get(hash(event.source))
        new_description = event.any_data
        if old_description == new_description:
            msg = "AXUtilitiesEvent: The new description matches the old description."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        AXUtilitiesEvent.LAST_KNOWN_DESCRIPTION[hash(event.source)] = new_description
        if not new_description:
            msg = "AXUtilitiesEvent: The description is empty."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        if not AXUtilitiesState.is_showing(event.source):
            msg = "AXUtilitiesEvent: The event source is not showing."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        focus = focus_manager.get_manager().get_locus_of_focus()
        if event.source != focus and not AXObject.is_ancestor(focus, event.source):
            msg = "AXUtilitiesEvent: The event is not from the locus of focus or ancestor."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        msg = "AXUtilitiesEvent: Event is presentable."
        debug.print_message(debug.LEVEL_INFO, msg, True)
        return True

    @staticmethod
    def is_presentable_expanded_change(event):
        """Returns True if this event should be presented as an expanded-state change."""

        old_state = AXUtilitiesEvent.LAST_KNOWN_EXPANDED.get(hash(event.source))
        new_state = AXUtilitiesState.is_expanded(event.source)
        if old_state == new_state:
            msg = "AXUtilitiesEvent: The new state matches the old state."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        AXUtilitiesEvent.LAST_KNOWN_EXPANDED[hash(event.source)] = new_state
        if event.source == focus_manager.get_manager().get_locus_of_focus():
            msg = "AXUtilitiesEvent: Event is presentable, from the locus of focus."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return True

        if AXUtilitiesRole.is_table_row(event.source) or AXUtilitiesRole.is_list_box(event.source):
            msg = "AXUtilitiesEvent: Event is presentable based on role."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return True

        if AXUtilitiesRole.is_combo_box(event.source) or AXUtilitiesRole.is_button(event.source):
            if not AXUtilitiesState.is_focused(event.source):
                msg = "AXUtilitiesEvent: Only presentable for this role if focused."
                debug.print_message(debug.LEVEL_INFO, msg, True)
                return False

        msg = "AXUtilitiesEvent: Event is presentable."
        debug.print_message(debug.LEVEL_INFO, msg, True)
        return True

    @staticmethod
    def is_presentable_indeterminate_change(event):
        """Returns True if this event should be presented as an indeterminate-state change."""

        old_state = AXUtilitiesEvent.LAST_KNOWN_INDETERMINATE.get(hash(event.source))
        new_state = AXUtilitiesState.is_indeterminate(event.source)
        if old_state == new_state:
            msg = "AXUtilitiesEvent: The new state matches the old state."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        AXUtilitiesEvent.LAST_KNOWN_INDETERMINATE[hash(event.source)] = new_state

        # If this state is cleared, the new state will become checked or unchecked
        # and we should get object:state-changed:checked events for those cases.
        if not new_state:
            msg = "AXUtilitiesEvent: The new state should be presented as a checked-change."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        if event.source != focus_manager.get_manager().get_locus_of_focus():
            msg = "AXUtilitiesEvent: The event is not from the locus of focus."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        msg = "AXUtilitiesEvent: Event is presentable."
        debug.print_message(debug.LEVEL_INFO, msg, True)
        return True

    @staticmethod
    def is_presentable_name_change(event):
        """Returns True if this event should be presented as a name change."""

        old_name = AXUtilitiesEvent.LAST_KNOWN_NAME.get(hash(event.source))
        new_name = event.any_data
        if old_name == new_name:
            msg = "AXUtilitiesEvent: The new name matches the old name."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        AXUtilitiesEvent.LAST_KNOWN_NAME[hash(event.source)] = new_name
        if not new_name:
            msg = "AXUtilitiesEvent: The name is empty."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        if not AXUtilitiesState.is_showing(event.source):
            msg = "AXUtilitiesEvent: The event source is not showing."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        if AXUtilitiesRole.is_frame(event.source):
            if event.source != focus_manager.get_manager().get_active_window():
                msg = "AXUtilitiesEvent: Event is for frame other than the active window."
                debug.print_message(debug.LEVEL_INFO, msg, True)
                return False

            # Example: Typing the subject in an email client causing the window name to change.
            focus = focus_manager.get_manager().get_locus_of_focus()
            if AXUtilitiesState.is_editable(focus) and AXText.get_character_count(focus) \
               and AXText.get_all_text(focus) in event.any_data:
                msg = "AXUtilitiesEvent: Event is redundant notification for the locus of focus."
                debug.print_message(debug.LEVEL_INFO, msg, True)
                return False

            msg = "AXUtilitiesEvent: Event is presentable."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return True

        if event.source != focus_manager.get_manager().get_locus_of_focus():
            msg = "AXUtilitiesEvent: The event is not from the locus of focus."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        msg = "AXUtilitiesEvent: Event is presentable."
        debug.print_message(debug.LEVEL_INFO, msg, True)
        return True

    @staticmethod
    def is_presentable_pressed_change(event):
        """Returns True if this event should be presented as a pressed-state change."""

        old_state = AXUtilitiesEvent.LAST_KNOWN_PRESSED.get(hash(event.source))
        new_state = AXUtilitiesState.is_pressed(event.source)
        if old_state == new_state:
            msg = "AXUtilitiesEvent: The new state matches the old state."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        AXUtilitiesEvent.LAST_KNOWN_PRESSED[hash(event.source)] = new_state
        if event.source != focus_manager.get_manager().get_locus_of_focus():
            msg = "AXUtilitiesEvent: The event is not from the locus of focus."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        msg = "AXUtilitiesEvent: Event is presentable."
        debug.print_message(debug.LEVEL_INFO, msg, True)
        return True

    @staticmethod
    def is_presentable_selected_change(event):
        """Returns True if this event should be presented as a selected-state change."""

        old_state = AXUtilitiesEvent.LAST_KNOWN_SELECTED.get(hash(event.source))
        new_state = AXUtilitiesState.is_selected(event.source)
        if old_state == new_state:
            msg = "AXUtilitiesEvent: The new state matches the old state."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        AXUtilitiesEvent.LAST_KNOWN_SELECTED[hash(event.source)] = new_state
        if event.source != focus_manager.get_manager().get_locus_of_focus():
            msg = "AXUtilitiesEvent: The event is not from the locus of focus."
            debug.print_message(debug.LEVEL_INFO, msg, True)
            return False

        msg = "AXUtilitiesEvent: Event is presentable."
        debug.print_message(debug.LEVEL_INFO, msg, True)
        return True


AXUtilitiesEvent.start_cache_clearing_thread()
