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

from pytz import timezone
from datetime import datetime
from bakery import lp, lrun, _
from bakery.network import geoip
from bakery.timezone import tz_list

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib  # type: ignore


@Gtk.Template(resource_path="/org/bredos/bakery/ui/timezone_screen.ui")
class timezone_screen(Adw.Bin):
    __gtype_name__ = "timezone_screen"

    regions_list = Gtk.Template.Child()
    zones_list = Gtk.Template.Child()
    curr_time = Gtk.Template.Child()
    preview_row = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.tz_list = tz_list()
        current_timezone = geoip()
        self.timezone = {}
        self.timezone["region"] = current_timezone["region"]
        self.timezone["zone"] = current_timezone["zone"]
        self.timezone["ntp"] = True

        self.zones_list.connect("notify::selected-item", self.on_zone_changed)
        self.zone_model = Gtk.StringList()
        self.zones_list.set_model(self.zone_model)

        self.regions_list.connect("notify::selected-item", self.on_region_changed)
        self.region_model = Gtk.StringList()
        self.regions_list.set_model(self.region_model)
        for item in list(self.tz_list.keys()):
            self.region_model.append(item)

        self.change_regions_list(current_timezone["region"])
        self.regions_list.set_selected(
            list(self.tz_list.keys()).index(current_timezone["region"])
        )
        self.select_zone(current_timezone["region"], current_timezone["zone"])

    def on_region_changed(self, dropdown, *_):
        selected = dropdown.props.selected_item
        if selected is not None:
            self.timezone["region"] = selected.props.string
            self.change_regions_list(selected.props.string)

    def on_zone_changed(self, dropdown, *_):
        selected = dropdown.props.selected_item
        if selected is not None:
            self.timezone["zone"] = selected.props.string
            self.preview_timezone(self.timezone["region"], selected.props.string)

    def change_regions_list(self, region) -> None:
        self.zone_model = Gtk.StringList()
        self.zones_list.set_model(self.zone_model)
        for zone in self.tz_list[region]:
            self.zone_model.append(zone)

    def select_zone(self, region, zone) -> None:
        # get the index of the zone in the list
        index = self.tz_list[region].index(zone)
        self.zones_list.set_selected(index)

    def preview_timezone(self, region, zone) -> None:
        # timezone expects region/zone
        try:
            tz = timezone(str(region + "/" + zone))
        except:
            tz = None
        if tz is not None:
            time = datetime.now(tz)
            self.curr_time.set_label(time.strftime("%Y-%m-%d %H:%M:%S"))
            self.preview_row.set_subtitle(
                _("Previewing time in ") + str(tz)
            )  # pyright: ignore[reportCallIssue]
