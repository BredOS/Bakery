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
import subprocess
from bredos.utilities import catch_exceptions
import yaml
from bakery import lrun, lp, expected_to_fail
from bakery.network import internet_up
from .iso import run_chroot_cmd
import gi
from gi.repository import Gio


@catch_exceptions
def pacstrap(mnt_dir: str, packages: list) -> None:
    lp("Pacstrapping packages: " + " ".join(packages))
    lrun(["pacstrap", mnt_dir] + packages)
    lp("Pacstrap complete")


@catch_exceptions
def install_packages(packages: list, chroot: bool = False, mnt_dir: str = None) -> None:
    cmd = ["pacman", "-Sy", "--noconfirm"] + packages
    lp("Installing packages: " + " ".join(packages))
    if chroot and mnt_dir is not None:
        run_chroot_cmd(mnt_dir, cmd)
    else:
        lrun(cmd)
    lp("Package installation complete")


@catch_exceptions
def remove_packages(packages: list, chroot: bool = False, mnt_dir: str = None) -> None:
    # Remove each package in the list separately
    for package in packages:
        cmd = ["pacman", "-R", "--noconfirm", package]
        lp("Removing package: " + package)
        if chroot and mnt_dir is not None:
            run_chroot_cmd(mnt_dir, cmd, postrunfn=expected_to_fail)
        else:
            lrun(cmd, postrunfn=expected_to_fail)


@catch_exceptions
def ensure_localdb(retries: int = 3) -> None:
    if not internet_up():
        raise OSError("Internet Unavailable.")
    tried = 0
    while tried < retries:
        lrun(["pacman", "-Sy"], force=True)
        if len(os.listdir("/var/lib/pacman/sync/")):
            break
        tried += 1
    if not len(os.listdir("/var/lib/pacman/sync/")):
        raise OSError("Could not update databases.")


@catch_exceptions
def get_packages_list() -> dict:
    """
    Returns netinstall list of packages.
    """

    data_bytes = Gio.resources_lookup_data("/org/bredos/bakery/packages.yaml", 0)

    return yaml.safe_load(data_bytes.get_data().decode("utf-8"))


@catch_exceptions
def get_desktops_list() -> dict:
    """
    Returns desktop list of packages.
    """

    data_bytes = Gio.resources_lookup_data("/org/bredos/bakery/desktops.yaml", 0)

    return yaml.safe_load(data_bytes.get_data().decode("utf-8"))


@catch_exceptions
def package_desc(packages: list) -> dict:
    ensure_localdb()
    res = {}
    if len(packages):
        outp = (
            subprocess.check_output(["pacman", "-Si"] + packages)
            .decode("UTF-8")
            .split()
        )
        cindex = 0
        cur_desc = ""
        cur_pkg = None
        in_desc = False
        while cindex < len(outp):
            if (not in_desc) and outp[cindex] == "Name" and outp[cindex + 1] == ":":
                cur_pkg = outp[cindex + 2]
                cindex += 3
            if (
                (not in_desc)
                and outp[cindex] == "Description"
                and outp[cindex + 1] == ":"
            ):
                cindex += 1
                in_desc = True
            elif in_desc:
                if outp[cindex] == "Architecture" and outp[cindex + 1] == ":":
                    if cur_pkg in packages:
                        res[cur_pkg] = cur_desc
                    in_desc = False
                    cur_desc = ""
                else:
                    cur_desc += (" " if len(cur_desc) else "") + outp[cindex]
            cindex += 1
    return res
