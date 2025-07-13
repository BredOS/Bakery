#!/usr/bin/env python

import os, sys, time, curses
import argparse, signal, config

from bredos import curseapp as c
from pytz import timezone
from datetime import datetime
from babel import dates, numbers
from babel import Locale as bLocale
from bakery import (
    dryrun,
    kb_models,
    kb_layouts,
    kb_variants,
    langs,
    tz_list,
    geoip,
    validate_username,
    validate_fullname,
    validate_hostname,
    check_efi,
    check_partition_table,
    list_drives,
    get_partitions,
    gen_new_partitions,
    lp,
    setup_translations,
    debounce,
    _,
    uidc,
    gidc,
    lrun,
    detect_install_device,
    detect_install_source,
    detect_session_configuration,
    reboot,
    upload_log,
    log_path,
    time_fn,
)


c.APP_NAME = "Bakery"
DRYRUN = dryrun
SIDE_BAR = {}

data = {}

# ------------ Irrelevant --------------


def check_root() -> bool:
    if os.geteuid():
        print("Bakery must be run as root!", file=sys.stderr)
        return False
    return True


def prepare() -> None:
    install_data = {
        "type": "offline",
        "source": detect_install_source(),
        "device": detect_install_device(),
    }
    data["install_type"] = install_data
    data["session_configuration"] = detect_session_configuration()
    data["root_password"] = False
    installer = {}
    installer["installer_version"] = config.installer_version
    installer["ui"] = "tui"
    data["installer"] = installer
    data["packages"] = {}
    if install_data["source"] == "from_iso":
        data["packages"]["to_remove"] = config.iso_packages_to_remove
        data["packages"]["de_packages"] = []
    data["partitions"] = []


# --------------- RUNNER ----------------


def handle_stupid(signum=None, frame=None) -> None:
    pass


signal.signal(signal.SIGQUIT, handle_stupid)
signal.signal(signal.SIGTSTP, handle_stupid)


# -------------- Main Manu --------------


def main_menu():
    c.init()
    c.menu(
        "Bakery",
        {"test": print},
        "Exit Bakery",
    )


# -------------- ENTRY POINT --------------


def main() -> None:
    global DRYRUN
    parser = argparse.ArgumentParser(prog="bakery-tui", description=c.APP_NAME)
    parser.add_argument(
        "--dryrun", action="store_true", help="Simulate running commands (SAFE)."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate running commands (SAFE)."
    )
    subparsers = parser.add_subparsers(dest="command")

    args = parser.parse_args()

    if args.dryrun or args.dry_run:
        DRYRUN = True
        c.DRYRUN = True

    if args.command is None:
        try:
            main_menu()
        finally:
            c.suspend()
    else:
        raise NotImplementedError("Sh!+ not done yet.")


if __name__ == "__main__":
    if check_root():
        prepare()
        main()
