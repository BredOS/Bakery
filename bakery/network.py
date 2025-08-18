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

from . import config
from bredos.utilities import catch_exceptions
import socket, requests
from bakery import lrun, lp, _

import gi

gi.require_version("NM", "1.0")
from gi.repository import NM


@catch_exceptions
def test_up(hostport: tuple) -> bool:
    if not networking_up():
        return False
    try:
        socket.setdefaulttimeout(10)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(hostport)
        return True
    except:
        return False


@catch_exceptions
def networking_up() -> bool:
    # Tests if an interface is connected.
    client = NM.Client.new(None)
    devices = client.get_devices()
    for device in devices:
        if (
            device.get_type_description() in ["wifi", "ethernet"]
            and device.get_state().value_nick == "activated"
        ):
            return True
    return False


@catch_exceptions
def internet_up() -> bool:
    res = False
    for i in [
        ("8.8.8.8", 53),
        ("9.9.9.9", 53),
        ("1.1.1.1", 53),
        ("130.61.177.30", 443),
    ]:
        res = test_up(i)
        if res:
            break
    lp("Internet status: " + str(res))
    return res


@catch_exceptions
def geoip() -> dict:
    try:
        if not internet_up():
            raise OSError
        tz_data = requests.get("https://geoip.kde.org/v1/timezone").json()
        region, zone = tz_data["time_zone"].split("/")
        return {"region": region, "zone": zone}
    except:
        return config.timezone


@catch_exceptions
def ethernet_available() -> bool:
    client = NM.Client.new(None)
    devices = client.get_devices()
    for device in devices:
        if device.get_type_description() == "ethernet":
            return True
    return False


@catch_exceptions
def ethernet_connected() -> bool:
    client = NM.Client.new(None)
    devices = client.get_devices()
    for device in devices:
        if (
            device.get_type_description() == "ethernet"
            and device.get_state().value_nick == "activated"
        ):
            return True
    return False


@catch_exceptions
def wifi_available() -> bool:
    client = NM.Client.new(None)
    devices = client.get_devices()
    for device in devices:
        if device.get_type_description() == "wifi":
            return True
    return False


@catch_exceptions
def wifi_connected() -> bool:
    client = NM.Client.new(None)
    devices = client.get_devices()
    for device in devices:
        if (
            device.get_type_description() == "wifi"
            and device.get_state().value_nick == "activated"
        ):
            return True
    return False
