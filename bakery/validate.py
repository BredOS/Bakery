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


def validate_username(username) -> str:
    if len(username) > 30:
        return "Cannot be longer than 30 characters"
    elif not len(username):
        return "Cannot be empty"
    if len(username) and username[0] in ["-", "_", "."]:
        return "Cannot start with special characters"
    for i in range(len(username)):
        if not (
            (
                username[i].isdigit()
                or username[i].islower()
                or username[i] in ["-", "_", "."]
            )
            and username[i].isascii()
        ):
            return "Invalid characters (Use lowercase latin characters, numbers and '-' '_' '.')"
    return ""


def validate_fullname(fullname) -> str:
    if len(fullname) > 30:
        return "Cannot be longer than 30 characters"
    elif not len(fullname):
        return "Cannot be empty"
    for i in range(len(fullname)):
        if not (
            fullname[i].isdigit()
            or fullname[i].islower()
            or fullname[i].isupper()
            or fullname[i].isspace()
            or fullname[i] in ["'", "-"]
        ):
            return 'Invalid characters (Use characters, numbers and "\'")'
    return ""


def validate_hostname(hostname) -> str:
    if len(hostname) > 63:
        return "Cannot be longer than 30 characters"
    elif not len(hostname):
        return "Cannot be empty"
    if len(hostname) and hostname[0] == "_":
        return "Cannot start with '_'"
    for i in range(len(hostname)):
        if not (
            (
                hostname[i].isdigit()
                or hostname[i].islower()
                or hostname[i].isupper()
                or hostname[i] in ["-"]
            )
            and hostname[i].isascii()
        ):
            return 'Invalid characters (Use characters, numbers and "\'")'
    return ""


# User configuration functions.


def gidc(gid) -> bool:
    if gid is False:
        return True
    elif isinstance(gid, int):
        gid = str(gid)
    elif not gid.isdigit():
        raise TypeError("GID not a number!")
    with open("/etc/group") as gr:
        data = gr.read().split("\n")
        for i in data:
            try:
                if i.split(":")[-2] == gid:
                    return True
            except IndexError:
                pass
    return False


def uidc(uid: str) -> bool:
    if uid is False:
        return True
    if isinstance(uid, int):
        uid = str(uid)
    elif not uid.isdigit():
        raise TypeError("UID not a number!")
    with open("/etc/passwd") as pw:
        data = pw.read().split("\n")
        for i in data:
            try:
                if i.split(":")[2] == uid:
                    return True
            except IndexError:
                pass
    return False


def shells() -> set:
    res = set()
    with open("/etc/shells") as sh:
        data = sh.read().split("\n")
        for i in data:
            if i.startswith("/"):
                res.add(i)
    return res
