# Orca
#
# Copyright 2005-2009 Sun Microsystems Inc.
# Copyright 2010-2013 The Orca Team.
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

"""Custom script for LibreOffice."""

__id__        = "$Id$"
__version__   = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2005-2009 Sun Microsystems Inc." \
                "Copyright (c) 2010-2013 The Orca Team."
__license__   = "LGPL"

import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi
from gi.repository import Gtk

import orca.cmdnames as cmdnames
import orca.debug as debug
import orca.focus_manager as focus_manager
import orca.scripts.default as default
import orca.guilabels as guilabels
import orca.keybindings as keybindings
import orca.input_event as input_event
import orca.messages as messages
import orca.orca_state as orca_state
import orca.settings_manager as settings_manager
import orca.structural_navigation as structural_navigation
from orca.ax_object import AXObject
from orca.ax_table import AXTable
from orca.ax_utilities import AXUtilities

from .braille_generator import BrailleGenerator
from .script_utilities import Utilities
from .spellcheck import SpellCheck
from .speech_generator import SpeechGenerator

_focusManager = focus_manager.getManager()
_settingsManager = settings_manager.getManager()

class Script(default.Script):

    def __init__(self, app):
        """Creates a new script for the given application.

        Arguments:
        - app: the application to create a script for.
        """

        default.Script.__init__(self, app)

        self.speakSpreadsheetCoordinatesCheckButton = None
        self.alwaysSpeakSelectedSpreadsheetRangeCheckButton = None
        self.skipBlankCellsCheckButton = None
        self.speakCellCoordinatesCheckButton = None
        self.speakCellHeadersCheckButton = None
        self.speakCellSpanCheckButton = None

    def getBrailleGenerator(self):
        """Returns the braille generator for this script.
        """
        return BrailleGenerator(self)

    def getSpeechGenerator(self):
        """Returns the speech generator for this script.
        """
        return SpeechGenerator(self)

    def getSpellCheck(self):
        """Returns the spellcheck for this script."""

        return SpellCheck(self)

    def getUtilities(self):
        """Returns the utilities for this script."""

        return Utilities(self)

    def getStructuralNavigation(self):
        """Returns the 'structural navigation' class for this script.
        """
        types = self.getEnabledStructuralNavigationTypes()
        return structural_navigation.StructuralNavigation(self, types, enabled=False)

    def getEnabledStructuralNavigationTypes(self):
        """Returns a list of the structural navigation object types
        enabled in this script.
        """

        enabledTypes = [structural_navigation.StructuralNavigation.TABLE_CELL]

        return enabledTypes

    def setupInputEventHandlers(self):
        """Defines InputEventHandler fields for this script that can be
        called by the key and braille bindings. In this particular case,
        we just want to be able to add a handler to return the contents of
        the input line.
        """

        default.Script.setupInputEventHandlers(self)
        self.inputEventHandlers.update(
            self.structuralNavigation.inputEventHandlers)

        self.inputEventHandlers["presentInputLineHandler"] = \
            input_event.InputEventHandler(
                Script.presentInputLine,
                cmdnames.PRESENT_INPUT_LINE)

        self.inputEventHandlers["setDynamicColumnHeadersHandler"] = \
            input_event.InputEventHandler(
                Script.setDynamicColumnHeaders,
                cmdnames.DYNAMIC_COLUMN_HEADER_SET)

        self.inputEventHandlers["clearDynamicColumnHeadersHandler"] = \
            input_event.InputEventHandler(
                Script.clearDynamicColumnHeaders,
                cmdnames.DYNAMIC_COLUMN_HEADER_CLEAR)

        self.inputEventHandlers["setDynamicRowHeadersHandler"] = \
            input_event.InputEventHandler(
                Script.setDynamicRowHeaders,
                cmdnames.DYNAMIC_ROW_HEADER_SET)

        self.inputEventHandlers["clearDynamicRowHeadersHandler"] = \
            input_event.InputEventHandler(
                Script.clearDynamicRowHeaders,
                cmdnames.DYNAMIC_ROW_HEADER_CLEAR)

        self.inputEventHandlers["panBrailleLeftHandler"] = \
            input_event.InputEventHandler(
                Script.panBrailleLeft,
                cmdnames.PAN_BRAILLE_LEFT,
                False) # Do not enable learn mode for this action

        self.inputEventHandlers["panBrailleRightHandler"] = \
            input_event.InputEventHandler(
                Script.panBrailleRight,
                cmdnames.PAN_BRAILLE_RIGHT,
                False) # Do not enable learn mode for this action

    def getAppKeyBindings(self):
        """Returns the application-specific keybindings for this script."""

        keyBindings = keybindings.KeyBindings()

        keyBindings.add(
            keybindings.KeyBinding(
                "a",
                keybindings.defaultModifierMask,
                keybindings.ORCA_MODIFIER_MASK,
                self.inputEventHandlers["presentInputLineHandler"]))

        keyBindings.add(
            keybindings.KeyBinding(
                "r",
                keybindings.defaultModifierMask,
                keybindings.ORCA_MODIFIER_MASK,
                self.inputEventHandlers["setDynamicColumnHeadersHandler"],
                1))

        keyBindings.add(
            keybindings.KeyBinding(
                "r",
                keybindings.defaultModifierMask,
                keybindings.ORCA_MODIFIER_MASK,
                self.inputEventHandlers["clearDynamicColumnHeadersHandler"],
                2))

        keyBindings.add(
            keybindings.KeyBinding(
                "c",
                keybindings.defaultModifierMask,
                keybindings.ORCA_MODIFIER_MASK,
                self.inputEventHandlers["setDynamicRowHeadersHandler"],
                1))

        keyBindings.add(
            keybindings.KeyBinding(
                "c",
                keybindings.defaultModifierMask,
                keybindings.ORCA_MODIFIER_MASK,
                self.inputEventHandlers["clearDynamicRowHeadersHandler"],
                2))

        bindings = self.structuralNavigation.keyBindings
        for keyBinding in bindings.keyBindings:
            keyBindings.add(keyBinding)

        return keyBindings

    def getAppPreferencesGUI(self):
        """Return a GtkGrid containing the application unique configuration
        GUI items for the current application."""

        grid = Gtk.Grid()
        grid.set_border_width(12)

        label = guilabels.SPREADSHEET_SPEAK_CELL_COORDINATES
        value = _settingsManager.getSetting('speakSpreadsheetCoordinates')
        self.speakSpreadsheetCoordinatesCheckButton = \
            Gtk.CheckButton.new_with_mnemonic(label)
        self.speakSpreadsheetCoordinatesCheckButton.set_active(value)
        grid.attach(self.speakSpreadsheetCoordinatesCheckButton, 0, 0, 1, 1)

        label = guilabels.SPREADSHEET_SPEAK_SELECTED_RANGE
        value = _settingsManager.getSetting('alwaysSpeakSelectedSpreadsheetRange')
        self.alwaysSpeakSelectedSpreadsheetRangeCheckButton = \
            Gtk.CheckButton.new_with_mnemonic(label)
        self.alwaysSpeakSelectedSpreadsheetRangeCheckButton.set_active(value)
        grid.attach(self.alwaysSpeakSelectedSpreadsheetRangeCheckButton, 0, 1, 1, 1)

        tableFrame = Gtk.Frame()
        grid.attach(tableFrame, 0, 2, 1, 1)

        label = Gtk.Label(label=f"<b>{guilabels.TABLE_NAVIGATION}</b>")
        label.set_use_markup(True)
        tableFrame.set_label_widget(label)

        tableAlignment = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        tableAlignment.set_padding(0, 0, 12, 0)
        tableFrame.add(tableAlignment)
        tableGrid = Gtk.Grid()
        tableAlignment.add(tableGrid)

        label = guilabels.TABLE_SPEAK_CELL_COORDINATES
        value = _settingsManager.getSetting('speakCellCoordinates')
        self.speakCellCoordinatesCheckButton = \
            Gtk.CheckButton.new_with_mnemonic(label)
        self.speakCellCoordinatesCheckButton.set_active(value)
        tableGrid.attach(self.speakCellCoordinatesCheckButton, 0, 0, 1, 1)

        label = guilabels.TABLE_SPEAK_CELL_SPANS
        value = _settingsManager.getSetting('speakCellSpan')
        self.speakCellSpanCheckButton = \
            Gtk.CheckButton.new_with_mnemonic(label)
        self.speakCellSpanCheckButton.set_active(value)
        tableGrid.attach(self.speakCellSpanCheckButton, 0, 1, 1, 1)

        label = guilabels.TABLE_ANNOUNCE_CELL_HEADER
        value = _settingsManager.getSetting('speakCellHeaders')
        self.speakCellHeadersCheckButton = \
            Gtk.CheckButton.new_with_mnemonic(label)
        self.speakCellHeadersCheckButton.set_active(value)
        tableGrid.attach(self.speakCellHeadersCheckButton, 0, 2, 1, 1)

        label = guilabels.TABLE_SKIP_BLANK_CELLS
        value = _settingsManager.getSetting('skipBlankCells')
        self.skipBlankCellsCheckButton = \
            Gtk.CheckButton.new_with_mnemonic(label)
        self.skipBlankCellsCheckButton.set_active(value)
        tableGrid.attach(self.skipBlankCellsCheckButton, 0, 3, 1, 1)

        spellcheck = self.spellcheck.getAppPreferencesGUI()
        grid.attach(spellcheck, 0, len(grid.get_children()), 1, 1)
        grid.show_all()

        return grid

    def getPreferencesFromGUI(self):
        """Returns a dictionary with the app-specific preferences."""

        prefs = {
            'speakCellSpan':
                self.speakCellSpanCheckButton.get_active(),
            'speakCellHeaders':
                self.speakCellHeadersCheckButton.get_active(),
            'skipBlankCells':
                self.skipBlankCellsCheckButton.get_active(),
            'speakCellCoordinates':
                self.speakCellCoordinatesCheckButton.get_active(),
            'speakSpreadsheetCoordinates':
                self.speakSpreadsheetCoordinatesCheckButton.get_active(),
            'alwaysSpeakSelectedSpreadsheetRange':
                self.alwaysSpeakSelectedSpreadsheetRangeCheckButton.get_active(),
        }

        prefs.update(self.spellcheck.getPreferencesFromGUI())
        return prefs

    def panBrailleLeft(self, inputEvent=None, panAmount=0):
        """In document content, we want to use the panning keys to browse the
        entire document.
        """

        focus = _focusManager.get_locus_of_focus()
        if self.flatReviewPresenter.is_active() \
           or not self.isBrailleBeginningShowing() \
           or self.utilities.isSpreadSheetCell(focus) \
           or not self.utilities.isTextArea(focus):
            return default.Script.panBrailleLeft(self, inputEvent, panAmount)

        text = focus.queryText()
        string, startOffset, endOffset = text.getTextAtOffset(
            text.caretOffset, Atspi.TextBoundaryType.LINE_START)
        if 0 < startOffset:
            text.setCaretOffset(startOffset-1)
            return True

        obj = self.utilities.findPreviousObject(focus)
        try:
            text = obj.queryText()
        except Exception:
            pass
        else:
            _focusManager.set_locus_of_focus(None, obj, notify_script=False)
            text.setCaretOffset(text.characterCount)
            return True

        return default.Script.panBrailleLeft(self, inputEvent, panAmount)

    def panBrailleRight(self, inputEvent=None, panAmount=0):
        """In document content, we want to use the panning keys to browse the
        entire document.
        """

        focus = _focusManager.get_locus_of_focus()
        if self.flatReviewPresenter.is_active() \
           or not self.isBrailleEndShowing() \
           or self.utilities.isSpreadSheetCell(focus) \
           or not self.utilities.isTextArea(focus):
            return default.Script.panBrailleRight(self, inputEvent, panAmount)

        text = focus.queryText()
        string, startOffset, endOffset = text.getTextAtOffset(
            text.caretOffset, Atspi.TextBoundaryType.LINE_START)
        if endOffset < text.characterCount:
            text.setCaretOffset(endOffset)
            return True

        obj = self.utilities.findNextObject(focus)
        try:
            text = obj.queryText()
        except Exception:
            pass
        else:
            _focusManager.set_locus_of_focus(None, obj, notify_script=False)
            text.setCaretOffset(0)
            return True

        return default.Script.panBrailleRight(self, inputEvent, panAmount)

    def presentInputLine(self, inputEvent):
        """Presents the contents of the input line for the current cell.

        Arguments:
        - inputEvent: if not None, the input event that caused this action.
        """

        focus = _focusManager.get_locus_of_focus()
        if not self.utilities.isSpreadSheetCell(focus):
            self.presentMessage(messages.SPREADSHEET_NOT_IN_A)
            return True

        text = AXTable.get_cell_formula(focus)
        if not text:
            text = self.utilities.displayedText(focus) or messages.EMPTY

        self.presentMessage(text)
        return True

    def setDynamicColumnHeaders(self, inputEvent):
        """Set the row for the dynamic header columns to use when speaking
        calc cell entries. In order to set the row, the user should first set
        focus to the row that they wish to define and then press Insert-r.

        Once the user has defined the row, it will be used to first speak
        this header when moving between columns.

        Arguments:
        - inputEvent: if not None, the input event that caused this action.
        """

        cell = _focusManager.get_locus_of_focus()
        parent = AXObject.get_parent(cell)
        if AXObject.get_role(parent) == Atspi.Role.TABLE_CELL:
            cell = parent

        table = AXTable.get_table(cell)
        if table:
            row = AXTable.get_cell_coordinates(cell)[0]
            AXTable.set_dynamic_column_headers_row(table, row)
            self.presentMessage(messages.DYNAMIC_COLUMN_HEADER_SET % (row + 1))

        return True

    def clearDynamicColumnHeaders(self, inputEvent):
        """Clear the dynamic header column.

        Arguments:
        - inputEvent: if not None, the input event that caused this action.
        """

        table = AXTable.get_table(_focusManager.get_locus_of_focus())
        if table:
            AXTable.clear_dynamic_column_headers_row(table)
            msg = messages.DYNAMIC_COLUMN_HEADER_CLEARED
        else:
            msg = messages.TABLE_NOT_IN_A

        self.presentationInterrupt()
        self.presentMessage(msg)
        return True

    def setDynamicRowHeaders(self, inputEvent):
        """Set the column for the dynamic header rows to use when speaking
        calc cell entries. In order to set the column, the user should first
        set focus to the column that they wish to define and then press
        Insert-c.

        Once the user has defined the column, it will be used to first speak
        this header when moving between rows.

        Arguments:
        - inputEvent: if not None, the input event that caused this action.
        """

        cell = _focusManager.get_locus_of_focus()
        parent = AXObject.get_parent(cell)
        if AXObject.get_role(parent) == Atspi.Role.TABLE_CELL:
            cell = parent

        table = AXTable.get_table(cell)
        if table:
            column = AXTable.get_cell_coordinates(cell)[1]
            AXTable.set_dynamic_row_headers_column(table, column)
            self.presentMessage(
                messages.DYNAMIC_ROW_HEADER_SET % self.utilities.columnConvert(column + 1))

        return True

    def clearDynamicRowHeaders(self, inputEvent):
        """Clear the dynamic row headers.

        Arguments:
        - inputEvent: if not None, the input event that caused this action.
        """

        table = AXTable.get_table(_focusManager.get_locus_of_focus())
        if table:
            AXTable.clear_dynamic_row_headers_column(table)
            msg = messages.DYNAMIC_ROW_HEADER_CLEARED
        else:
            msg = messages.TABLE_NOT_IN_A

        self.presentationInterrupt()
        self.presentMessage(msg)
        return True

    def locusOfFocusChanged(self, event, oldLocusOfFocus, newLocusOfFocus):
        """Called when the visual object with focus changes.

        Arguments:
        - event: if not None, the Event that caused the change
        - oldLocusOfFocus: Accessible that is the old locus of focus
        - newLocusOfFocus: Accessible that is the new locus of focus
        """

        # Check to see if this is this is for the find command. See
        # comment #18 of bug #354463.
        #
        if self.findCommandRun and \
           event.type.startswith("object:state-changed:focused"):
            self.findCommandRun = False
            self.find()
            return

        if self.flatReviewPresenter.is_active():
            self.flatReviewPresenter.quit()

        if self.spellcheck.isSuggestionsItem(newLocusOfFocus) \
           and not self.spellcheck.isSuggestionsItem(oldLocusOfFocus):
            self.updateBraille(newLocusOfFocus)
            self.spellcheck.presentSuggestionListItem(includeLabel=True)
            return

        # TODO - JD: Sad hack that wouldn't be needed if LO were fixed.
        # If we are in the slide presentation scroll pane, also announce
        # the current page tab. See bug #538056 for more details.
        #
        rolesList = [Atspi.Role.SCROLL_PANE,
                     Atspi.Role.PANEL,
                     Atspi.Role.PANEL,
                     Atspi.Role.ROOT_PANE,
                     Atspi.Role.FRAME,
                     Atspi.Role.APPLICATION]
        if self.utilities.hasMatchingHierarchy(newLocusOfFocus, rolesList):
            parent = AXObject.get_parent(newLocusOfFocus)
            for child in AXObject.iter_children(parent, AXUtilities.is_page_tab_list):
                for tab in AXObject.iter_children(child, AXUtilities.is_selected):
                    self.presentObject(tab)

        # TODO - JD: This is a hack that needs to be done better. For now it
        # fixes the broken echo previous word on Return.
        elif newLocusOfFocus and oldLocusOfFocus \
           and AXObject.get_role(newLocusOfFocus) == Atspi.Role.PARAGRAPH \
           and AXObject.get_role(oldLocusOfFocus) == Atspi.Role.PARAGRAPH \
           and newLocusOfFocus != oldLocusOfFocus:
            lastKey, mods = self.utilities.lastKeyAndModifiers()
            if lastKey == "Return" and _settingsManager.getSetting('enableEchoByWord'):
                self.echoPreviousWord(oldLocusOfFocus)
                return

            # TODO - JD: And this hack is another one that needs to be done better.
            # But this will get us to speak the entire paragraph when navigation by
            # paragraph has occurred.
            event_string, mods = self.utilities.lastKeyAndModifiers()
            isControlKey = mods & keybindings.CTRL_MODIFIER_MASK
            isShiftKey = mods & keybindings.SHIFT_MODIFIER_MASK
            if event_string in ["Up", "Down"] and isControlKey and not isShiftKey:
                string = self.utilities.displayedText(newLocusOfFocus)
                if string:
                    voice = self.speechGenerator.voice(obj=newLocusOfFocus, string=string)
                    self.speakMessage(string, voice=voice)
                    self.updateBraille(newLocusOfFocus)
                    try:
                        text = newLocusOfFocus.queryText()
                    except Exception:
                        pass
                    else:
                        self._saveLastCursorPosition(newLocusOfFocus, text.caretOffset)
                    return

        # Pass the event onto the parent class to be handled in the default way.
        default.Script.locusOfFocusChanged(self, event,
                                           oldLocusOfFocus, newLocusOfFocus)

    def onNameChanged(self, event):
        """Called whenever a property on an object changes.

        Arguments:
        - event: the Event
        """

        if self.spellcheck.isCheckWindow(event.source):
            return

        # Impress slide navigation.
        #
        if self.utilities.isInImpress(event.source) \
           and self.utilities.isDrawingView(event.source):
            title, position, count = \
                self.utilities.slideTitleAndPosition(event.source)
            if title:
                title += "."

            msg = messages.PRESENTATION_SLIDE_POSITION % \
                    {"position" : position, "count" : count}
            msg = self.utilities.appendString(title, msg)
            self.presentMessage(msg)

        default.Script.onNameChanged(self, event)

    def onActiveChanged(self, event):
        """Callback for object:state-changed:active accessibility events."""

        if not AXObject.get_parent(event.source):
            msg = "SOFFICE: Event source lacks parent"
            debug.printMessage(debug.LEVEL_INFO, msg, True)
            return

        # Prevent this events from activating the find operation.
        # See comment #18 of bug #354463.
        if self.findCommandRun:
            return

        default.Script.onActiveChanged(self, event)

    def onActiveDescendantChanged(self, event):
        """Called when an object who manages its own descendants detects a
        change in one of its children.

        Arguments:
        - event: the Event
        """

        focus = _focusManager.get_locus_of_focus()
        if self.utilities.isSameObject(event.any_data, focus):
            return

        if event.source == self.spellcheck.getSuggestionsList():
            if AXUtilities.is_focused(event.source):
                _focusManager.set_locus_of_focus(event, event.any_data, False)
                self.updateBraille(focus)
                self.spellcheck.presentSuggestionListItem()
            else:
                self.spellcheck.presentErrorDetails()
            return

        if self.utilities.isSpreadSheetCell(event.any_data) \
           and not AXUtilities.is_focused(event.any_data) \
           and not AXUtilities.is_focused(event.source) :
            msg = "SOFFICE: Neither source nor child have focused state. Clearing cache on table."
            debug.printMessage(debug.LEVEL_INFO, msg, True)
            AXObject.clear_cache(event.source)

        default.Script.onActiveDescendantChanged(self, event)

    def onChildrenAdded(self, event):
        """Callback for object:children-changed:add accessibility events."""

        if self.utilities.isSpreadSheetCell(event.any_data):
            _focusManager.set_locus_of_focus(event, event.any_data)
            return

        if AXUtilities.is_table_related(event.source):
            AXTable.clear_cache_now("children-changed event.")

        if AXTable.is_last_cell(event.any_data):
            activeRow = self.pointOfReference.get('lastRow', -1)
            activeCol = self.pointOfReference.get('lastColumn', -1)
            if activeRow < 0 or activeCol < 0:
                return

            if _focusManager.focus_is_dead():
                _focusManager.set_locus_of_focus(event, event.source, False)

            self.utilities.handleUndoTextEvent(event)
            rowCount = AXTable.get_row_count(event.source)
            if activeRow == rowCount:
                full = messages.TABLE_ROW_DELETED_FROM_END
                brief = messages.TABLE_ROW_DELETED
            else:
                full = messages.TABLE_ROW_INSERTED_AT_END
                brief = messages.TABLE_ROW_INSERTED
            self.presentMessage(full, brief)
            return

        default.Script.onChildrenAdded(self, event)

    def onFocus(self, event):
        """Callback for focus: accessibility events."""

        # NOTE: This event type is deprecated and Orca should no longer use it.
        # This callback remains just to handle bugs in applications and toolkits
        # during the remainder of the unstable (3.11) development cycle.

        focus = _focusManager.get_locus_of_focus()
        if self.utilities.isSameObject(focus, event.source):
            return

        if self.utilities.isFocusableLabel(event.source):
            _focusManager.set_locus_of_focus(event, event.source)
            return

        role = AXObject.get_role(event.source)

        if self.utilities.isZombie(event.source) \
           or role in [Atspi.Role.TEXT, Atspi.Role.LIST]:
            comboBox = self.utilities.containingComboBox(event.source)
            if comboBox:
                _focusManager.set_locus_of_focus(event, comboBox, True)
                return

        # This seems to be something we inherit from Gtk+
        if role in [Atspi.Role.TEXT, Atspi.Role.PASSWORD_TEXT]:
            _focusManager.set_locus_of_focus(event, event.source)
            return

        # Ditto.
        if role == Atspi.Role.PUSH_BUTTON:
            _focusManager.set_locus_of_focus(event, event.source)
            return

        # Ditto.
        if role == Atspi.Role.TOGGLE_BUTTON:
            _focusManager.set_locus_of_focus(event, event.source)
            return

        # Ditto.
        if role == Atspi.Role.COMBO_BOX:
            _focusManager.set_locus_of_focus(event, event.source)
            return

        # Ditto.
        if role == Atspi.Role.PANEL and AXObject.get_name(event.source):
            _focusManager.set_locus_of_focus(event, event.source)
            return

    def onFocusedChanged(self, event):
        """Callback for object:state-changed:focused accessibility events."""

        if self._inSayAll:
            return

        if self._lastCommandWasStructNav:
            return

        if not event.detail1:
            return

        role = AXObject.get_role(event.source)
        if role in [Atspi.Role.TEXT, Atspi.Role.LIST]:
            comboBox = self.utilities.containingComboBox(event.source)
            if comboBox:
                _focusManager.set_locus_of_focus(event, comboBox, True)
                return

        parent = AXObject.get_parent(event.source)
        if parent and AXObject.get_role(parent) == Atspi.Role.TOOL_BAR:
            default.Script.onFocusedChanged(self, event)
            return

        # TODO - JD: Verify this is still needed
        ignoreRoles = [Atspi.Role.FILLER, Atspi.Role.PANEL]
        if role in ignoreRoles:
            return

        # We will present this when the selection changes.
        if role == Atspi.Role.MENU:
            return

        if self.utilities._flowsFromOrToSelection(event.source):
            return

        if role == Atspi.Role.PARAGRAPH:
            obj, offset = self.pointOfReference.get("lastCursorPosition", (None, -1))
            start, end, string = self.utilities.getCachedTextSelection(obj)
            if start != end:
                return

            keyString, mods = self.utilities.lastKeyAndModifiers()
            if keyString in ["Left", "Right"]:
                _focusManager.set_locus_of_focus(event, event.source, False)
                return

        if self.utilities.isSpreadSheetTable(event.source):
            if _focusManager.focus_is_dead():
                msg = "SOFFICE: Event believed to be post-editing focus claim."
                debug.printMessage(debug.LEVEL_INFO, msg, True)
                _focusManager.set_locus_of_focus(event, event.source, False)
                return

            focus = _focusManager.get_locus_of_focus()
            if AXUtilities.is_paragraph(focus) or AXUtilities.is_table_cell(focus):
                msg = "SOFFICE: Event believed to be post-editing focus claim based on role."
                debug.printMessage(debug.LEVEL_INFO, msg, True)
                _focusManager.set_locus_of_focus(event, event.source, False)
                return

        default.Script.onFocusedChanged(self, event)

    def onCaretMoved(self, event):
        """Callback for object:text-caret-moved accessibility events."""

        if event.detail1 == -1:
            return

        if AXObject.get_role(event.source) == Atspi.Role.PARAGRAPH \
           and not AXUtilities.is_focused(event.source):
            AXObject.clear_cache(event.source)
            if AXUtilities.is_focused(event.source):
                msg = "SOFFICE: Clearing cache was needed due to missing state-changed event."
                debug.printMessage(debug.LEVEL_INFO, msg, True)

        if self.utilities._flowsFromOrToSelection(event.source):
           return

        if self._lastCommandWasStructNav:
            return

        if self.utilities.isSpreadSheetCell(_focusManager.get_locus_of_focus()):
            if not self.utilities.isCellBeingEdited(event.source):
                msg = "SOFFICE: Event ignored: Source is not cell being edited."
                debug.printMessage(debug.LEVEL_INFO, msg, True)
                return

        super().onCaretMoved(event)

    def onCheckedChanged(self, event):
        """Callback for object:state-changed:checked accessibility events."""

        obj = event.source
        role = AXObject.get_role(obj)
        parentRole = AXObject.get_role(AXObject.get_parent(obj))
        if role not in [Atspi.Role.TOGGLE_BUTTON, Atspi.Role.PUSH_BUTTON] \
           or not parentRole == Atspi.Role.TOOL_BAR:
            default.Script.onCheckedChanged(self, event)
            return

        sourceWindow = self.utilities.topLevelObject(obj)
        focusWindow = self.utilities.topLevelObject(_focusManager.get_locus_of_focus())
        if sourceWindow != focusWindow:
            return

        # Announce when the toolbar buttons are toggled if we just toggled
        # them; not if we navigated to some text.
        weToggledIt = False
        if isinstance(orca_state.lastInputEvent, input_event.MouseButtonEvent):
            x = orca_state.lastInputEvent.x
            y = orca_state.lastInputEvent.y
            weToggledIt = obj.queryComponent().contains(x, y, 0)
        elif AXUtilities.is_focused(obj):
            weToggledIt = True
        else:
            keyString, mods = self.utilities.lastKeyAndModifiers()
            navKeys = ["Up", "Down", "Left", "Right", "Page_Up", "Page_Down",
                       "Home", "End", "N"]
            wasCommand = mods & keybindings.COMMAND_MODIFIER_MASK
            weToggledIt = wasCommand and keyString not in navKeys
        if weToggledIt:
            self.presentObject(obj, alreadyFocused=True, interrupt=True)

    def onSelectedChanged(self, event):
        """Callback for object:state-changed:selected accessibility events."""

        full, brief = "", ""
        if self.utilities.isSelectedTextDeletionEvent(event):
            msg = "SOFFICE: Change is believed to be due to deleting selected text"
            debug.printMessage(debug.LEVEL_INFO, msg, True)
            full = messages.SELECTION_DELETED
        elif self.utilities.isSelectedTextRestoredEvent(event):
            msg = "SOFFICE: Selection is believed to be due to restoring selected text"
            debug.printMessage(debug.LEVEL_INFO, msg, True)
            if self.utilities.handleUndoTextEvent(event):
                full = messages.SELECTION_RESTORED

        if full or brief:
            self.presentMessage(full, brief)
            self.utilities.updateCachedTextSelection(event.source)
            return

        super().onSelectedChanged(event)

    def onSelectionChanged(self, event):
        """Callback for object:selection-changed accessibility events."""

        if self.utilities.isSpreadSheetTable(event.source):
            if _settingsManager.getSetting('onlySpeakDisplayedText'):
                return
            if _settingsManager.getSetting('alwaysSpeakSelectedSpreadsheetRange'):
                self.utilities.speakSelectedCellRange(event.source)
                return
            if self.utilities.handleRowAndColumnSelectionChange(event.source):
                return
            self.utilities.handleCellSelectionChange(event.source)
            return

        if event.source == self.spellcheck.getSuggestionsList():
            if _focusManager.focus_is_active_window():
                msg = "SOFFICE: Not presenting because locusOfFocus is window"
                debug.printMessage(debug.LEVEL_INFO, msg, True)
            elif AXUtilities.is_focused(event.source):
                _focusManager.set_locus_of_focus(event, event.any_data, False)
                self.updateBraille(event.any_data)
                self.spellcheck.presentSuggestionListItem()
            else:
                self.spellcheck.presentErrorDetails()
            return

        if not self.utilities.isComboBoxSelectionChange(event):
            super().onSelectionChanged(event)
            return

        selectedChildren = self.utilities.selectedChildren(event.source)
        if len(selectedChildren) == 1 \
           and self.utilities.containingComboBox(event.source) == \
               self.utilities.containingComboBox(_focusManager.get_locus_of_focus()):
            _focusManager.set_locus_of_focus(event, selectedChildren[0], True)

    def onTextSelectionChanged(self, event):
        """Callback for object:text-selection-changed accessibility events."""

        if self.utilities.isComboBoxNoise(event):
            msg = "SOFFICE: Event is believed to be combo box noise"
            debug.printMessage(debug.LEVEL_INFO, msg, True)
            return

        if AXObject.is_dead(event.source):
            msg = "SOFFICE: Ignoring event from dead source."
            debug.printMessage(debug.LEVEL_INFO, msg, True)
            return

        super().onTextSelectionChanged(event)

    def getTextLineAtCaret(self, obj, offset=None, startOffset=None, endOffset=None):
        """To-be-removed. Returns the string, caretOffset, startOffset."""

        if AXObject.get_role(AXObject.get_parent(obj)) == Atspi.Role.COMBO_BOX:
            try:
                text = obj.queryText()
            except NotImplementedError:
                return ["", 0, 0]

            if text.caretOffset < 0:
                [lineString, startOffset, endOffset] = text.getTextAtOffset(
                    0, Atspi.TextBoundaryType.LINE_START)

                # Sometimes we get the trailing line-feed -- remove it
                #
                if lineString[-1:] == "\n":
                    lineString = lineString[:-1]

                return [lineString, 0, startOffset]

        textLine = super().getTextLineAtCaret(obj, offset, startOffset, endOffset)
        if not AXUtilities.is_focused(obj):
            textLine[0] = self.utilities.displayedText(obj)

        return textLine

    def onWindowActivated(self, event):
        """Callback for window:activate accessibility events."""

        super().onWindowActivated(event)
        if not self.spellcheck.isCheckWindow(event.source):
            return

        child = AXObject.get_child(event.source, 0)
        if AXObject.get_role(child) == Atspi.Role.DIALOG:
            _focusManager.set_locus_of_focus(event, child, False)

        self.spellcheck.presentErrorDetails()

    def onWindowDeactivated(self, event):
        """Callback for window:deactivate accessibility events."""

        self._lastCommandWasStructNav = False

        super().onWindowDeactivated(event)
        self.spellcheck.deactivate()
