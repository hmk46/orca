# Orca
#
# Copyright 2011 The Orca Team.
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

"""Custom script for xfwm4."""

__id__        = "$Id$"
__version__   = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2011 The Orca Team."
__license__   = "LGPL"

from orca.scripts import default
from orca.ax_object import AXObject
from orca.ax_utilities import AXUtilities

class Script(default.Script):
    """Custom script for xfwm4."""

    def on_text_inserted(self, event):
        """Callback for object:text-changed:insert accessibility events."""

        if not AXUtilities.is_label(event.source):
            default.Script.on_text_inserted(self, event)
            return

        self.presentMessage(AXObject.get_name(event.source))

    def on_text_deleted(self, event):
        """Callback for object:text-changed:delete accessibility events."""

        if not AXUtilities.is_label(event.source):
            default.Script.on_text_deleted(self, event)
