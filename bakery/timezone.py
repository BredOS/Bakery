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

import subprocess
from bredos.utilities import catch_exceptions
from bakery import lrun, lp
from .iso import run_chroot_cmd


@catch_exceptions
def tz_list() -> dict:
    res = {}
    data = (
        subprocess.check_output(["timedatectl", "list-timezones"])
        .decode("UTF-8")
        .split()
    )
    for i in data:
        if "/" in i:
            cont = i[: i.find("/")]
            if cont not in res.keys():
                res[cont] = []
            res[cont].append(i[i.find("/") + 1 :])
    return res


@catch_exceptions
def tz_set(region: str, zone: str, chroot: bool = False, mnt_dir: str = None) -> None:
    tzs = tz_list()
    if region in tzs.keys() and zone in tzs[region]:
        if chroot:
            # in chroot use symlink
            lrun(
                [
                    "ln",
                    "-sfv",
                    "/usr/share/zoneinfo/" + region + "/" + zone,
                    mnt_dir + "/etc/localtime",
                ]
            )
        else:
            lrun(["timedatectl", "set-timezone", region + "/" + zone])
    else:
        lp("Timezone " + region + "/" + zone + " not a valid timezone!")
        raise TypeError("Timezone " + region + "/" + zone + " not a valid timezone!")


@catch_exceptions
def tz_ntp(ntp: bool, chroot: bool = False, mnt_dir: str = None) -> None:
    lp("Setting ntp to " + str(ntp))
    if chroot:
        run_chroot_cmd(mnt_dir, ["systemctl", "enable", "systemd-timesyncd"])
    else:
        lrun(["timedatectl", "set-ntp", str(int(ntp))])
