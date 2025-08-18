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
from time import sleep

from bredos.utilities import catch_exceptions
from bakery import lrun, lp, log_file, dryrun, _
from bakery import config
from pyrunning import LoggingLevel

st_msgs = []


@catch_exceptions
def detect_install_source() -> str:
    with open("/proc/cmdline", "r") as cmdline_file:
        cmdline = cmdline_file.read()
        if "archisobasedir" in cmdline or "archisolabel" in cmdline:
            lp("Installation source: from_iso", mode="debug")
            return "from_iso"
        else:
            lp("Installation source: on_device", mode="debug")
            return "on_device"


def is_sbc(device: str) -> bool:
    if device in config.sbcs:
        return True
    return False


def copy_logs(new_usern: str, chroot: bool = False, mnt_dir: str = None) -> None:
    if dryrun:
        lp("Would have synced and copied logs.")
        return
    subprocess.run("sync")
    if chroot:
        subprocess.run(
            [
                "cp",
                "-v",
                log_file,
                mnt_dir + "/home/" + new_usern + "/.bredos/bakery/logs",
            ]
        )
    else:
        subprocess.run(
            [
                "cp",
                "-vr",
                "/root/.bredos",
                "/home/" + new_usern + "/.bredos",
            ]
        )
        subprocess.run(
            [
                "chown",
                "-R",
                new_usern + ":" + new_usern,
                "/home/" + new_usern + "/.bredos",
            ]
        )


def upload_log() -> str:
    command = f"cat {log_file} | nc termbin.com 9999"
    lp("Uploading log to termbin.com")
    try:
        result = subprocess.run(
            command, shell=True, check=True, text=True, capture_output=True
        )
        lp("Log uploaded to " + result.stdout.strip().split("\n")[0])
        return result.stdout.strip().split("\n")[0]
    except subprocess.CalledProcessError:
        lp("Error uploading log to termbin.com", mode="error")
        return "error"


def reboot(time: int = 5) -> None:
    if time < 0:
        raise ValueError("Time cannot be lower than 0")
    if not dryrun:
        subprocess.run(["sh", "-c", f"sleep {time} && shutdown -r now &"])
    else:
        print("Skipping reboot during dryrun.")


def populate_messages(
    lang=None,
    type: str = "on_device_offline",
) -> None:
    global st_msgs
    st_msgs.clear()
    if type == "on_device_offline":
        st_msgs += [
            [_("Preparing for installation"), 0],  # 0
            [_("Applying Locale Settings"), 10],  # 1
            [_("Applying Keyboard Settings"), 20],  # 2
            [_("Applying Timezone Settings"), 30],  # 3
            [_("Creating User account"), 40],  # 4
            [_("Setting Hostname"), 50],  # 5
            [_("Finalizing installation"), 90],  # 6
            [_("Cleaning up installation"), 100],  # 7
        ]
    elif type == "from_iso_offline":
        st_msgs += [
            [_("Preparing for installation"), 0],  # 0
            [_("Partitioning Disk"), 0],  # 1
            [_("Mounting Disk"), 15],  # 2
            [_("Copying Files from iso"), 20],  # 3
            [_("Regenerating initramfs"), 24],  # 4
            [_("Generating fstab"), 28],  # 5
            [_("Setting up bootloader"), 32],  # 6
            [_("Removing packages"), 40],  # 7
            [_("Applying Locale Settings"), 50],  # 8
            [_("Applying Keyboard Settings"), 60],  # 9
            [_("Applying Timezone Settings"), 70],  # 10
            [_("Creating User account"), 80],  # 11
            [_("Setting Hostname"), 85],  # 12
            [_("Finalizing installation"), 90],  # 13
            [_("Cleaning up installation"), 100],  # 14
        ]


def console_logging(
    logging_level: int,
    message: str,
    *args,
    loginfo_filename="",
    loginfo_line_number=-1,
    loginfo_function_name="",
    loginfo_stack_info=None,
    **kwargs,
) -> None:
    logging_level_name = LoggingLevel(logging_level).name
    pos = message.find("%ST")
    if pos != -1:
        prs = message.rfind("%")
        stm = st_msgs[int(message[pos + 3 : prs])]
        lp("STATUS  : " + stm[0])
        lp("PROGRESS: " + str(stm[1]) + "%")


def st(msg_id: int) -> None:
    sleep(0.2)
    lp("%ST" + str(msg_id) + "%")
    sleep(0.2)


populate_messages()
