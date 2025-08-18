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

import os
import gi

gi.require_version("AppStream", "1.0")

from gi.repository import AppStream

box = None


def appstream_initialize() -> None:
    global box
    pool = AppStream.Pool()
    pool.load()
    box = pool.get_components()
    pool.clear()


def search_appstream(query: str, limit: int = 25) -> list:
    """
    Search AppStream database for applications matching the query.

    Args:
        query (str): Search query string
        limit (int): Maximum number of results to return

    Returns:
        list: List of dictionaries containing app information
    """
    results = []
    for component in box.as_array():
        name = component.get_name() or ""
        description = component.get_summary() or ""
        origin = component.get_origin() or ""
        if (
            query.lower() in name.lower() or query.lower() in description.lower()
        ) and origin != "":
            results.append(component)
            if len(results) >= limit:
                break
    return results


def appstream_get_icon(component):
    icons = component.get_icons()
    icon_path = None
    icon_name = "N/A"
    # Prefer CACHED icons, fallback to LOCAL
    for icon in icons:
        if (
            icon.get_kind() == AppStream.IconKind.CACHED
            or icon.get_kind() == AppStream.IconKind.LOCAL
        ):
            icon_path_candidate = icon.get_filename()
            if icon_path_candidate and os.path.isfile(icon_path_candidate):
                icon_path = icon_path_candidate
                icon_name = icon.get_name() or os.path.basename(icon_path_candidate)

    return icon_path if icon_path else "N/A", icon_name


def get_appstream_app_info(component) -> dict:
    """
    Get application information from AppStream component.
    """
    return {
        "name": component.get_name(),
        "id": component.get_id(),
        "package": component.get_pkgname(),
        "origin": component.get_origin(),
        "icon": appstream_get_icon(component),
        "description": component.get_summary(),
        "keywords": component.get_keywords(),
    }
