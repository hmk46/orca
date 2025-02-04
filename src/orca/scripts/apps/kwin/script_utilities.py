# Orca
#
# Copyright 2019 Igalia, S.L.
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

"""Custom script utilities for kwin."""

__id__        = "$Id$"
__version__   = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2019 Igalia, S.L."
__license__   = "LGPL"

from orca.ax_object import AXObject
from orca.ax_utilities import AXUtilities
from orca.scripts import switcher


class Utilities(switcher.Utilities):
    """Custom script utilities for kwin."""

    def isSwitcherContainer(self, obj):
        """Returns True if obj is the switcher container."""

        return AXUtilities.is_filler(obj) and AXUtilities.is_focused(obj)

    def isSwitcherSelectionChangeEventType(self, event):
        """Returns True if this event is the one we use to present changes."""

        if event.type.startswith("object:state-changed:focused"):
            return event.detail1

        return False

    def getSelectionName(self, container):
        """Returns the name of the currently-selected item."""

        if self.isSwitcherContainer(container):
            return AXObject.get_name(container)

        return ""
