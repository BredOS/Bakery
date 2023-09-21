#
# Copyright 2023 BredOS
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import gi
import os
import gettext

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

# Gettext
gettext.bindtextdomain("bakery", "./po")
gettext.textdomain("bakery")
gettext.install("bakery", "./po")
# py file path
script_dir = os.path.dirname(os.path.realpath(__file__))


class BakeryApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        # Create a Builder
        builder = Gtk.Builder()
        builder.add_from_file(script_dir + "/data/window.ui")

        self.create_action("about", self.on_about_action)

        # Obtain and show the main window
        self.win = builder.get_object("main_window")
        self.win.set_application(
            self
        )  # Application will close once it no longer has active windows attached to it
        self.win.present()

    def on_preferences_action(self, widget, _):
        """Callback for the app.preferences action."""
        # Implement your preferences logic here
        pass

    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name="BredOS Installer",
            application_icon="org.bredos.bakery",
            developer_name="BredOS",
            version="0.1.0",
            developers=["Panda", "bill88t"],
            copyright="© 2023 BredOS",
            comments="BredOS Installer is a simple installer for BredOS.",
            license_type=Gtk.License.GPL_3_0,
            website="https://BredOS.org",
        )
        about.present()

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.
        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


app = BakeryApp(application_id="org.bredos.bakery")
app.run(sys.argv)
