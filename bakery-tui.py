#!/usr/bin/env python
#
# Copyright 2023 BredOS
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

import os, sys, time, curses, bakery, pwd
import argparse, signal, config, re, json
import subprocess
from bakery import lp
from time import sleep
from pytz import timezone
from datetime import datetime
from babel import dates, numbers
from bredos import curseapp as c
from babel import Locale as bLocale
from pyrunning import LoggingHandler


c.APP_NAME = "Bakery"
DRYRUN = bakery.dryrun
LOGS = []
SIDEBAR = {
    "Welcome": False,
    "Locale": False,
    "Keyboard": False,
    "Timezone": False,
    "Partitioning": False,
    "User": False,
    "Summary": False,
    "Install": False,
    "Finish": False,
}
INSTALL_TYPE = bakery.detect_install_source()

# ------------ Irrelevant --------------


def check_root() -> None:
    if (not DRYRUN) and os.geteuid():
        print("Bakery must be run as root!", file=sys.stderr)
        exit(1)


colors = {
    "CRITICAL": "\033[38;2;164;0;0m",  # #a40000 - dark red
    "ERROR": "\033[38;2;255;0;0m",  # #ff0000 - bright red
    "EXCEPTION": "\033[38;2;255;0;0m",  # #ff0000 - bright red
    "WARNING": "\033[38;2;255;165;0m",  # #ffa500 - orange
    "INFO": "\033[38;2;53;132;228m",  # #3584e4 - blue
    "DEBUG": "\033[38;2;128;128;128m",  # #808080 - gray
    "NOTSET": "\033[38;2;128;128;128m",  # #808080 - gray
    "": "\033[38;2;128;128;128m",  # #808080 - gray
    None: "\033[38;2;128;128;128m",  # #808080 - gray
}

# Reset code to return to default color
RESET = "\033[0m"


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
    LOGS.append(colors[logging_level_name] + message + RESET)


def prepare() -> None:
    logging_handler = LoggingHandler(
        logger=bakery.logger,
        logging_functions=[console_logging],
    )


def handle_stupid(signum=None, frame=None) -> None:
    pass


signal.signal(signal.SIGQUIT, handle_stupid)
signal.signal(signal.SIGTSTP, handle_stupid)


def dump_logs() -> None:
    lp("test")
    c.message(LOGS, "logs dump")


def device_size(dev_path: str) -> int:
    result = subprocess.run(
        ["lsblk", "--json", "--bytes", dev_path],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    return int(data["blockdevices"][0]["size"])


def valid_install_medium(dev_path) -> bool:
    try:
        size = device_size(dev_path)
        return size > 8 * 1024**3  # 8 GiB
    except:
        return False


# -------------- Installation steps --------------


def locale_menu() -> tuple | None:
    langs = sorted(bakery.langs().keys())

    sidebar = SIDEBAR.copy()
    sidebar["Locale"] = True
    while True:
        try:
            lang = c.selector(
                langs,
                False,
                "Locale: Select System Language",
                preselect=langs.index("English"),
                sidebar=sidebar,
            )

            if isinstance(lang, int):
                lang = langs[lang]

                variants = sorted(bakery.langs()[lang])
                variant = c.selector(
                    variants,
                    False,
                    "Locale: Select Variant",
                    preselect=(
                        variants.index("en_US.UTF-8 UTF-8") if lang == "English" else -1
                    ),
                    sidebar=sidebar,
                )

                if isinstance(variant, int):
                    return (lang, variants[variant])
            else:
                return
        except KeyboardInterrupt:
            break


def keyboard_menu() -> dict | None:
    c.suspend()
    print("Please wait, loading layouts..")
    kb_prettylayouts = {k: v for k, v in sorted(bakery.kb_layouts(True).items())}
    kb_prettylayouts_keys = list(kb_prettylayouts.keys())
    kb_prettymodels = bakery.kb_models(True).keys()
    kb_models = bakery.kb_models()
    kb_models_keys = list(kb_models.keys())
    sleep(0.4)
    c.resume()

    sidebar = SIDEBAR.copy()
    sidebar["Keyboard"] = True
    while True:
        try:
            layout = c.selector(
                kb_prettylayouts_keys,
                False,
                "Keyboard: Choose Layout",
                preselect=kb_prettylayouts_keys.index("American English"),
                sidebar=sidebar,
            )

            if isinstance(layout, int):
                while True:
                    try:
                        pretty_chosen = kb_prettylayouts_keys[layout]
                        layout = kb_prettylayouts[pretty_chosen]

                        variants = [f"{pretty_chosen} - Normal"]
                        ll = ["normal"]
                        c.suspend()
                        print("Loading variants..")
                        for i in bakery.kb_variants(layout):
                            variants.append(f"{pretty_chosen} - {i}")
                            ll.append(i)
                        time.sleep(0.4)
                        c.resume()

                        variant = c.selector(
                            variants,
                            False,
                            "Keyboard: Select Variant",
                            sidebar=sidebar,
                        )

                        if isinstance(variant, int):
                            variant = ll[variant]

                            while True:
                                try:
                                    model = c.selector(
                                        kb_models.values(),
                                        False,
                                        "Keyboard: Model Selection",
                                        preselect=kb_models_keys.index("pc105"),
                                        sidebar=sidebar,
                                    )

                                    if isinstance(model, int):
                                        model = kb_models_keys[model]

                                        return {
                                            "model": model,
                                            "layout": layout,
                                            "variant": variant,
                                        }
                                    else:
                                        break
                                except KeyboardInterrupt:
                                    break
                        else:
                            break
                    except KeyboardInterrupt:
                        break
            else:
                return
        except KeyboardInterrupt:
            break


def timezone_menu() -> dict | None:
    c.suspend()
    tz_list = bakery.tz_list()
    current_timezone = bakery.geoip()
    regions = sorted(list(tz_list.keys()))
    sleep(0.4)
    c.resume()

    sidebar = SIDEBAR.copy()
    sidebar["Timezone"] = True
    while True:
        try:
            region = c.selector(
                regions,
                False,
                "Timezone: Choose Region",
                preselect=regions.index(current_timezone["region"]),
                sidebar=sidebar,
            )

            if isinstance(region, int):
                region = regions[region]
                zones = sorted(list(tz_list[region]))

                zone = c.selector(
                    zones,
                    False,
                    "Timezone: Select zone",
                    preselect=zones.index(current_timezone["zone"]),
                    sidebar=sidebar,
                )

                if isinstance(zone, int):
                    zone = zones[zone]
                    return {
                        "region": region,
                        "zone": zone,
                        "ntp": True,
                    }
                else:
                    break
            else:
                return
        except KeyboardInterrupt:
            break


def partitioning_menu() -> dict | None:
    sidebar = SIDEBAR.copy()
    sidebar["Partitioning"] = True

    while True:
        try:
            mode_choice = c.selector(
                ["Simple (Automatic)", "Advanced (Manual)"],
                False,
                "Partitioning: Choose Mode",
                sidebar=sidebar,
            )

            if isinstance(mode_choice, int):
                if not mode_choice:
                    return simple_partitioning_mode(sidebar)
                else:
                    return advanced_partitioning_mode(sidebar)
            else:
                break
        except KeyboardInterrupt:
            break


def simple_partitioning_mode(sidebar: dict) -> dict | None:
    c.suspend()
    print("Loading available drives...")
    drives = bakery.list_drives()
    invalid = []
    for i in drives.keys():
        print(f"{i}: ", end="")
        if not valid_install_medium(i):
            invalid.append(i)
            print("invalid")
        else:
            print("valid")
    for i in invalid:
        del drives[i]

    sleep(0.4)
    c.resume()

    if not drives:
        c.message(["No installable drives found!"], "Error")
        return None

    drive_list = []
    drive_keys = list(drives.keys())

    for device, model in drives.items():
        try:
            device_obj = parted.getDevice(device)
            size_gb = round(device_obj.length * device_obj.sectorSize / (1024**3), 1)
            drive_list.append(f"{device}: {model} ({size_gb} GB)")
        except:
            drive_list.append(f"{device}: {model}")

    while True:
        try:
            selected = c.selector(
                drive_list,
                False,
                "Partitioning: Select Drive for Automatic Installation",
                sidebar=sidebar,
            )

            if isinstance(selected, int):
                selected_device = drive_keys[selected]

                if c.confirm(
                    [
                        f"Selected drive: {drives[selected_device]}",
                        f"Device: {selected_device}",
                        "",
                        "WARNING: This will ERASE ALL DATA on the selected drive!",
                        "A 256MB EFI partition and BredOS root partition will be created.",
                        "",
                        "Do you want to continue?",
                    ],
                    "Partitioning: Confirm Drive Selection",
                    sidebar=sidebar,
                ):
                    return {
                        "type": "guided",
                        "mode": "erase_all",
                        "disk": selected_device,
                        "efi": bakery.check_efi(),
                    }
            else:
                break
        except KeyboardInterrupt:
            break


def advanced_partitioning_mode(sidebar: dict) -> dict | None:
    instructions = [
        "Usage of `parted` and/or `fdisk` recommended.",
        "",
        "Requirements:",
        "  - EFI Partition: FAT32/FAT16/FAT12, minimum 16MB in size, bootable.",
        "  - ROOT Filesystem: BTRFS/EXT4, minimum 5GB in size.",
        "Optional, accepted secondary partitions:",
        "  - BOOT Partition: FAT32/EXT4, minimum 512MB in size, bootable.",
        "  - HOME Partition: BTRFS/EXT4, no size requirement.",
        "",
        "Make sure to keep note of the created partitions.",
    ]

    if c.confirm(
        [
            "Advanced Partitioning Mode",
            "",
            "You will now access a ROOT shell to manually partition your drives.",
            "You are free to create the partitions however you like.",
            "",
        ]
        + instructions
        + [
            "",
            "Press Y and Enter confirm and open the shell, or N and Enter to go back.",
        ],
        "Advanced Partitioning",
        sidebar=sidebar,
    ):
        while True:
            c.suspend()
            print(
                "\x1b[2J\x1b[3J\x1b[H"
                + ("=" * 69)
                + "\n-!!- ADVANCED PARTITIONING SHELL -!!-\n\n"
                + "\n".join(instructions)
                + "\n\nBe careful and good luck.\n"
                + "Type 'exit' to return to Bakery.\n"
                + ("=" * 69)
                + "\n"
            )

            try:
                subprocess.run(["/bin/bash"], check=False)
            except Exception as e:
                print(f"Error opening shell: {e}")

            print("\nReturning to installer...")
            sleep(0.4)
            c.resume()

            try:
                partitioning_done = c.confirm(
                    [
                        "Have you finished setting up your partitions?",
                        "",
                        "Press Y to continue or N to re-enter the shell.",
                        "(If you wish to go back in setup, continue.)",
                    ]
                    + instructions,
                    "Advanced Partitioning: Confirmation",
                    sidebar=sidebar,
                )

                if isinstance(partitioning_done, bool):
                    if partitioning_done:
                        return manual_partition_assignment(sidebar)
                else:  # Go back through install
                    break
            except KeyboardInterrupt:
                break


def manual_partition_assignment(sidebar: dict) -> dict | None:
    c.suspend()
    print("Scanning for partitions...")
    all_partitions = bakery.get_partitions()
    sleep(0.4)
    c.resume()

    if not all_partitions:
        c.message(["No partitions found! Please create partitions first."], "Error")
        return None

    # Build list of actual partitions (not free space)
    available_partitions = []
    partition_details = {}

    for disk, partitions in all_partitions.items():
        for partition_info in partitions:
            for part_name, details in partition_info.items():
                if part_name != "Free space":
                    size_mb, start, end, fs_type = details
                    size_gb = round(size_mb / 1024, 1)
                    fs_display = fs_type if fs_type else "Unknown"
                    display_name = f"{part_name} ({size_gb}GB, {fs_display})"
                    available_partitions.append(display_name)
                    partition_details[part_name] = {
                        "size": size_mb,
                        "fs": fs_type,
                        "display": display_name,
                    }

    if not available_partitions:
        c.message(["No usable partitions found!"], "Error")
        return None

    # Assignment logic would continue here...
    # This is a simplified version - you'd need to implement the full
    # partition assignment interface similar to the GUI version

    selected_disk = list(all_partitions.keys())[0]  # Simplified
    return {
        "type": "manual",
        "disk": selected_disk,
        "efi": bakery.check_efi(),
        "partitions": {},  # Would be populated by assignment interface
    }


def user_menu() -> None:
    sidebar = SIDEBAR.copy()
    sidebar["User"] = True

    state = 0

    def FullNameConstraint(inp: str) -> bool:
        return (
            bool(re.fullmatch(r"[A-Za-z\s']+", inp)) if isinstance(inp, str) else False
        )

    def ValidAvailableUsername(inp: str) -> bool:
        if (
            (not isinstance(inp, str))
            or inp.endswith("-")
            or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", inp)
        ):
            return False
        try:
            pwd.getpwnam(inp)
            return False
        except KeyError:
            return True

    def HostnameConstraint(inp: str) -> bool:
        return isinstance(inp, str) and bool(
            re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9\-]{0,62}", inp)
        )

    def PasswordConstraint(inp: str) -> bool:
        return isinstance(inp, str) and len(inp) >= 4

    def UIDConstraint(inp: str) -> bool:
        if (not inp) and not isinstance(inp, str) or not inp.isdigit():
            return False
        uid = int(inp)
        if uid < 1000:
            return False
        try:
            pwd.getpwuid(uid)
            return False
        except KeyError:
            return True

    fullname = None
    username = None
    hostname = None
    password = None
    uidsussy = None
    sudo_nopasswd = False
    autologin = False

    while True:
        try:
            if not state:
                fullname = c.text_input(
                    [
                        "Please input your full name.",
                        "Allowed characters: Letters, spaces, apostrophes",
                        "",
                        "Full Name:",
                    ],
                    "User: Input Full Name",
                    constraint=FullNameConstraint,
                    sidebar=sidebar,
                )
                if isinstance(fullname, str):
                    state = 1
                else:
                    break
            elif state == 1:
                username = c.text_input(
                    [
                        "Please input your desired username.",
                        "It must match Linux username rules and be available.",
                        "",
                        "Username:",
                    ],
                    "User: Input Username",
                    constraint=ValidAvailableUsername,
                    sidebar=sidebar,
                )
                state = 2 if isinstance(username, str) else 0
            elif state == 2:
                hostname = c.text_input(
                    [
                        "Please input the system hostname.",
                        "Must be alphanumeric and optionally contain dashes.",
                        "",
                        "Hostname:",
                    ],
                    "User: Input Hostname",
                    constraint=HostnameConstraint,
                    sidebar=sidebar,
                )
                state = 3 if isinstance(hostname, str) else 1
            elif state == 3:
                password = c.text_input(
                    [
                        "Please input your password.",
                        "Minimum 4 characters.",
                        "",
                        "Password:",
                    ],
                    "User: Input Password",
                    mask=True,
                    constraint=PasswordConstraint,
                    sidebar=sidebar,
                )
                state = 4 if isinstance(password, str) else 2
            elif state == 4:
                confirm = c.text_input(
                    [
                        "Please confirm your password.",
                        "",
                        "Confirm Password:",
                    ],
                    "User: Confirm Password",
                    mask=True,
                    constraint=lambda x: x == password,
                    sidebar=sidebar,
                )
                state = 5 if (isinstance(confirm, str) and confirm == password) else 3
            elif state == 5:
                uid_input = c.text_input(
                    [
                        "Please input a UID.",
                        "Must be a number >= 1000 and not in use.",
                        "",
                        "UID:",
                    ],
                    "User: Input UID",
                    constraint=lambda x: UIDConstraint(x) or x == "",
                    prefill="1000",
                    sidebar=sidebar,
                )
                if isinstance(uid_input, str):
                    uidsussy = int(uid_input)
                    state = 6
                else:
                    state = 4
            elif state == 6:
                npwd = c.confirm(
                    [
                        "Would you like sudo to not require password confirmations?",
                        "",
                        "Press Y/N and Enter to confirm.",
                    ],
                    "User: Sudo nopasswd",
                    sidebar=sidebar,
                )
                if isinstance(npwd, bool):
                    state = 7
                    sudo_nopasswd = npwd
                else:
                    state = 5
            elif state == 7:
                autol = c.confirm(
                    [
                        "Would you login automatically upon boot?",
                        "",
                        "Press Y/N and Enter to confirm.",
                    ],
                    "User: Autologin",
                    sidebar=sidebar,
                )
                if isinstance(autol, bool):
                    state = 420
                    autologin = autol
                else:
                    state = 6
            else:
                return hostname, {
                    "fullname": fullname,
                    "username": username,
                    "password": password,
                    "uid": uidsussy,
                    "gid": uidsussy,
                    "sudo_nopasswd": sudo_nopasswd,
                    "autologin": autologin,
                    "shell": "/bin/bash",
                    "groups": ["wheel", "network", "video", "audio", "storage"],
                }
        except KeyboardInterrupt:
            if state:
                state -= 1
            else:
                break


def summary_confirm(manifest: dict) -> bool:
    sidebar = SIDEBAR.copy()
    sidebar["Summary"] = True
    data = [
        "Ready to install. Please and confirm:",
        "",
        "Install Type:",
        " - Type   : " + manifest["install_type"]["type"],
        " - Source : " + manifest["install_type"]["source"],
        " - Device : " + manifest["install_type"]["device"],
        "",
        "Session Configuration:",
        " - Display Manager     : " + manifest["session_configuration"]["dm"],
        " - Desktop Environment : " + manifest["session_configuration"]["de"],
        " - Wayland             : "
        + str(manifest["session_configuration"]["is_wayland"]),
        "",
        "Root Password: REDACTED",
        "",
        "Keyboard Layout: ",
        " - Type   : " + manifest["layout"]["model"],
        " - Source : " + manifest["layout"]["layout"],
        " - Device : " + manifest["layout"]["variant"],
        "",
        "Locale: ",
        " - Region : " + manifest["locale"]["region"],
        " - Zone   : " + manifest["locale"]["zone"],
        " - NTP    : " + str(manifest["locale"]["ntp"]),
        "",
        "Hostname: " + manifest["hostname"],
        "",
        "User data:",
        " - Full name     : " + manifest["user"]["fullname"],
        " - Username      : " + manifest["user"]["username"],
        " - Password      : REDACTED",
        " - UID/GID       : " + str(manifest["user"]["uid"]),
        " - Sudo nopasswd : " + str(manifest["user"]["sudo_nopasswd"]),
        " - Autologin     : " + str(manifest["user"]["autologin"]),
    ]

    if manifest["partitions"]:
        data += [
            "",
            "Partitioning:",
            " - Type : " + manifest["partitions"]["type"],
            " - Mode : " + manifest["partitions"]["mode"],
            " - Disk : " + manifest["partitions"]["disk"],
            " - EFI  : " + ("YES" if manifest["partitions"]["efi"] else "NO"),
        ]

    return c.confirm(
        data,
        "Summary: Confirm",
        sidebar=sidebar,
    )


def install(manifest: dict) -> bool:
    c.suspend()
    bakery.install(manifest)
    c.resume()
    return True


def main_menu() -> None:
    c.init()
    stage = 0
    locale = None
    keyboard = None
    timezone = None
    parts = None
    user = None
    while True:
        try:
            if not stage:
                sidebar = SIDEBAR.copy()
                sidebar["Welcome"] = True
                if c.confirm(
                    [
                        "Welcome to BredOS!",
                        "",
                        "Let the Bakery installer whip up the perfect BredOS recipe for your machine!",
                        "",
                        "Press Y and Enter to advance with the installation.",
                    ],
                    sidebar=sidebar,
                ):
                    stage = 1  # Locale
                elif DRYRUN:
                    return
            elif stage == 1:
                locale = locale_menu()
                if locale is None:
                    stage = 0
                else:
                    stage = 2
                    locale = locale[1]
            elif stage == 2:
                keyboard = keyboard_menu()
                stage = 1 if keyboard is None else 3
            elif stage == 3:
                timezone = timezone_menu()
                stage = 2 if timezone is None else 4
            elif stage == 4:
                if INSTALL_TYPE == "from_iso" or True:
                    parts = partitioning_menu()
                    stage = 3 if parts is None else 5
                else:
                    stage = 5
            elif stage == 5:
                user = user_menu()
                stage = (4 if INSTALL_TYPE == "from_iso" else 3) if user is None else 6
            elif stage == 6:
                manifest = {
                    "install_type": {
                        "type": "offline",
                        "source": INSTALL_TYPE,
                        "device": bakery.detect_install_device(),
                    },
                    "session_configuration": bakery.detect_session_configuration(),
                    "root_password": False,
                    "layout": keyboard,
                    "locale": timezone,
                    "hostname": user[0],
                    "user": user[1],
                    "installer": {
                        "installer_version": config.installer_version,
                        "ui": "tui",
                    },
                    "packages": {},
                    "partitions": parts if parts is not None else [],
                }

                if INSTALL_TYPE == "from_iso":
                    manifest["packages"]["to_remove"] = config.iso_packages_to_remove
                    manifest["packages"]["de_packages"] = []

                if summary_confirm(manifest):
                    stage = 7 if install(manifest) else 8
                else:
                    stage = 5
            else:
                success = stage == 7
                c.message(
                    [
                        "Installation finished!",
                        "",
                        "Press Enter to reboot into your new installation.",
                    ]
                )
                if not DRYRUN:
                    bakery.reboot()
        except KeyboardInterrupt:
            if DRYRUN:
                return


# -------------- ENTRY POINT --------------


def main() -> None:
    global DRYRUN
    c.DRYRUN = DRYRUN

    try:
        main_menu()
    finally:
        c.suspend()


if __name__ == "__main__":
    check_root()
    prepare()
    main()
