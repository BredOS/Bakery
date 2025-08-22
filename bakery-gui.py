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

import faulthandler

faulthandler.enable()

from sys import argv
from os import path

from gi.repository import Gio

script_path: str = path.dirname(path.realpath(__file__))


def generate_gresource() -> None:
    """Generates the gresource file."""
    from subprocess import run

    run(
        ["glib-compile-resources", "org.bredos.bakery.gresource.xml"],
        cwd=path.join(script_path, "data"),
    )


def set_resources() -> None:
    """Sets the resource path for the UI files."""
    if not script_path.startswith("/usr/"):
        generate_gresource()
    resource: Gio.Resource = Gio.Resource.load(
        path.join(script_path, "data", "org.bredos.bakery.gresource")
    )
    Gio.Resource._register(resource)


if __name__ == "__main__":
    set_resources()
    from bakery.gui.main import BakeryApp

    app = BakeryApp(application_id="org.bredos.bakery")
    app.run(argv)
