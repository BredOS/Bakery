#!/usr/bin/env python
#
# Copyright 2025 BredOS
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

from bakery.keyboard import kb_layouts, kb_models

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib  # type: ignore


@Gtk.Template(resource_path="/org/bredos/bakery/ui/summary_screen.ui")
class summary_screen(Adw.Bin):
    __gtype_name__ = "summary_screen"

    locale_preview = Gtk.Template.Child()
    kb_lang = Gtk.Template.Child()
    kb_variant = Gtk.Template.Child()
    kb_model = Gtk.Template.Child()
    tz_preview = Gtk.Template.Child()

    name_preview = Gtk.Template.Child()
    username_preview = Gtk.Template.Child()
    hostname_preview = Gtk.Template.Child()

    autologin = Gtk.Template.Child()  # switch
    nopasswd = Gtk.Template.Child()  # switch

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window

    def page_shown(self) -> None:
        self.data = self.window.collect_data()
        self.locale_preview.set_label(self.data["locale"])
        self.kb_lang.set_label(kb_layouts()[self.data["layout"]["layout"]])
        self.kb_variant.set_label(self.data["layout"]["variant"])
        self.kb_model.set_label(kb_models()[self.data["layout"]["model"]])
        self.tz_preview.set_label(
            self.data["timezone"]["region"] + "/" + self.data["timezone"]["zone"]
        )
        self.name_preview.set_label(self.data["user"]["fullname"])
        self.username_preview.set_label(self.data["user"]["username"])
        self.hostname_preview.set_label(self.data["hostname"])
        self.autologin.set_active(self.data["user"]["autologin"])
        self.nopasswd.set_active(self.data["user"]["sudo_nopasswd"])
