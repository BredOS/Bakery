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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw  # type: ignore


@Gtk.Template(resource_path="/org/bredos/bakery/ui/user_screen.ui")
class user_screen(Adw.Bin):
    __gtype_name__ = "user_screen"

    fullname_entry = Gtk.Template.Child()
    user_entry = Gtk.Template.Child()
    hostname_entry = Gtk.Template.Child()
    pass_entry = Gtk.Template.Child()
    confirm_pass_entry = Gtk.Template.Child()
    user_info = Gtk.Template.Child()

    uid_row = Gtk.Template.Child()
    nopasswd = Gtk.Template.Child()
    autologin = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window

        self.pass_entry.connect("changed", self.on_confirm_pass_changed)
        self.confirm_pass_entry.connect("changed", self.on_confirm_pass_changed)
        self.user_entry.connect("changed", self.on_username_changed)
        self.hostname_entry.connect("changed", self.on_hostname_changed)
        self.fullname_entry.connect("changed", self.on_fullname_changed)
        self.uid_row.connect("changed", self.validate_uid)
        self.validate_uid(self.uid_row)
        self.user_info_is_visible = False

    def on_fullname_changed(self, entry):
        fullname = entry.get_text()
        a = validate_fullname(fullname)
        if a == "":
            self.user_info.set_visible(False)
            self.user_info_is_visible = False
            self.fullname_entry.remove_css_class("error")
        else:
            self.user_info.set_label(a)
            self.fullname_entry.add_css_class("error")
            if not self.user_info_is_visible:
                self.user_info.set_visible(True)
                self.user_info_is_visible = True

    def validate_uid(self, spin_entry):
        uid = int(spin_entry.get_value())
        if not uidc(uid) and not gidc(uid):
            spin_entry.remove_css_class("error")
            return uid
        else:
            spin_entry.add_css_class("error")
            return None

    def on_hostname_changed(self, entry):
        hostname = entry.get_text()
        a = validate_hostname(hostname)
        if a == "":
            self.user_info.set_visible(False)
            self.user_info_is_visible = False
            self.hostname_entry.remove_css_class("error")
        else:
            self.user_info.set_label(a)
            self.hostname_entry.add_css_class("error")
            if not self.user_info_is_visible:
                self.user_info.set_visible(True)
                self.user_info_is_visible = True

    def on_username_changed(self, entry):
        username = entry.get_text()
        a = validate_username(username)
        if a == "":
            self.user_info.set_visible(False)
            self.user_info_is_visible = False
            self.user_entry.remove_css_class("error")
        else:
            self.user_info.set_label(a)
            self.user_entry.add_css_class("error")
            if not self.user_info_is_visible:
                self.user_info.set_visible(True)
                self.user_info_is_visible = True

    def on_confirm_pass_changed(self, entry):
        pass_text = self.pass_entry.get_text()
        confirm_pass_text = entry.get_text()

        if not pass_text == confirm_pass_text:
            self.confirm_pass_entry.add_css_class("error")
        elif (
            pass_text == confirm_pass_text
            or not len(pass_text)
            or not len(confirm_pass_text)
        ):
            self.confirm_pass_entry.remove_css_class("error")

    def get_fullname(self) -> str:
        if self.fullname_entry.get_text() == "":
            return None
        else:
            if validate_fullname(self.fullname_entry.get_text()) == "":
                return self.fullname_entry.get_text()
            else:
                return None

    def get_username(self) -> str:
        if self.user_entry.get_text() == "":
            return None
        else:
            if validate_username(self.user_entry.get_text()) == "":
                return self.user_entry.get_text()
            else:
                return None

    def get_hostname(self) -> str:
        if self.hostname_entry.get_text() == "":
            return None
        else:
            if validate_hostname(self.hostname_entry.get_text()) == "":
                return self.hostname_entry.get_text()
            else:
                return None

    def get_password(self) -> str:
        if self.pass_entry.get_text() == "":
            return None
        else:
            pass_text = self.pass_entry.get_text()
            confirm_pass_text = self.confirm_pass_entry.get_text()
            if pass_text == confirm_pass_text:
                return pass_text
            else:
                return None

    def collect_data(self) -> dict:
        data = {}
        data["fullname"] = self.get_fullname()
        data["username"] = self.get_username()
        data["password"] = self.get_password()
        data["uid"] = self.validate_uid(self.uid_row)
        data["gid"] = self.validate_uid(self.uid_row)
        data["sudo_nopasswd"] = self.nopasswd.get_active()
        data["autologin"] = self.autologin.get_active()
        data["shell"] = "/bin/bash"
        data["groups"] = ["wheel", "network", "video", "audio", "storage"]
        return data
