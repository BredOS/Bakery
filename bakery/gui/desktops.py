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

from bakery import lp, lrun, _
from bakery.gui.helper import set_margins
from bakery.packages import get_desktops_list
from bredos.utilities import time_fn

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject, GLib  # type: ignore


class DesktopItem(GObject.GObject):
    name = GObject.Property(type=str, default="")
    icon = GObject.Property(type=str, default="")
    description = GObject.Property(type=str, default="")
    screenshot = GObject.Property(type=str, default="")
    id = GObject.Property(type=str, default="")


@time_fn
@Gtk.Template(resource_path="/org/bredos/bakery/ui/de_screen.ui")
class de_screen(Adw.Bin):
    __gtype_name__ = "de_screen"

    de_list: Gtk.ListBox = Gtk.Template.Child()
    screenshot: Gtk.Picture = Gtk.Template.Child()
    description: Gtk.Label = Gtk.Template.Child()
    main: Adw.StatusPage = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window

        desktops = get_desktops_list()
        self._store = Gio.ListStore(item_type=DesktopItem)
        selected_index = 0
        items = desktops.get("items", [])
        # Use enumerate and zip for faster property assignment
        for idx, desktop in enumerate(items):
            item = DesktopItem()
            item.props.id = desktop.get("id", "")
            item.props.name = desktop.get("name", "")
            item.props.icon = desktop.get("icon", "")
            item.props.description = desktop.get("description", "")
            item.props.screenshot = desktop.get("screenshot", "")
            self._store.append(item)
            if desktop.get("selected", False) and selected_index == 0:
                selected_index = idx

        factory = Gtk.SignalListItemFactory()

        def on_setup(_factory, list_item):
            box = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=6,
                halign=Gtk.Align.START,
                valign=Gtk.Align.CENTER,
            )
            image = Gtk.Image(pixel_size=32)
            label = Gtk.Label(xalign=0.5)
            label.set_wrap(True)
            box.append(image)
            box.append(label)
            box._image = image
            box._label = label
            list_item.set_child(box)

        def on_bind(_factory, list_item):
            item = list_item.get_item()
            child = list_item.get_child()
            child._label.set_text(item.props.name or "")
            # Only catch exception for set_from_resource
            try:
                child._image.set_from_resource(item.props.icon)
            except Exception:
                child._image.set_from_icon_name("image-missing")

        factory.connect("setup", on_setup)
        factory.connect("bind", on_bind)

        self.de_list.set_factory(factory)
        self._selection = Gtk.SingleSelection(model=self._store)
        self.de_list.set_model(self._selection)

        def on_selection_changed(selection, position, n_items):
            item = selection.get_selected_item()
            if not item:
                return
            try:
                self.screenshot.set_resource(item.props.screenshot)
                self.screenshot.set_size_request(320, 180)
            except Exception:
                pass
            self.description.set_text(item.props.description or "")

        self._selection.connect("selection-changed", on_selection_changed)

        # Only call on_selection_changed if selection is valid
        if self._store.get_n_items() > 0:
            self._selection.set_selected(selected_index)
            if self._selection.get_selected_item():
                on_selection_changed(self._selection, 0, 0)

    def collect_data(self):
        desktops = get_desktops_list()
        selected_idx = self._selection.get_selected()
        if selected_idx is None or selected_idx < 0:
            return {}
        items = desktops.get("items", [])
        if selected_idx >= len(items):
            return {}
        de = items[selected_idx]

        def collect_packages(group):
            pkgs = []
            for pkg in group.get("packages", []):
                if isinstance(pkg, dict):
                    name = pkg.get("name")
                    if name:
                        pkgs.append(name)
                elif isinstance(pkg, str):
                    pkgs.append(pkg)
            for subgroup in group.get("subgroups", []):
                pkgs.extend(collect_packages(subgroup))
            return pkgs

        all_packages = collect_packages(de.get("packages", {}))

        return {
            "id": de.get("id"),
            "dm": de.get("dm"),
            "de": de.get("de"),
            "session": de.get("session"),
            "packages": all_packages,
        }
