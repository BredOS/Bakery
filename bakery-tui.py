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

import os, sys, time, curses, bakery
import argparse, signal, config

from pytz import timezone
from datetime import datetime
from babel import dates, numbers
from bredos import curseapp as c
from babel import Locale as bLocale
from pyrunning import LoggingHandler
from time import sleep
from bakery import lp


c.APP_NAME = "Bakery"
DRYRUN = bakery.dryrun
SIDEBAR = {
    "Welcome": False,
    "Locale": False,
    "Keyboard": False,
    "Timezone": False,
    "User": False,
    "Summary": False,
    "Install": False,
    "Finish": False,
}

data = {}
LOGS = []

# ------------ Irrelevant --------------


def check_root() -> None:
    if os.geteuid():
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
    install_data = {
        "type": "offline",
        "source": bakery.detect_install_source(),
        "device": bakery.detect_install_device(),
    }
    data["install_type"] = install_data
    data["session_configuration"] = bakery.detect_session_configuration()
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


def handle_stupid(signum=None, frame=None) -> None:
    pass


signal.signal(signal.SIGQUIT, handle_stupid)
signal.signal(signal.SIGTSTP, handle_stupid)


def dump_logs() -> None:
    lp("test")
    c.message(LOGS, "logs dump")


# -------------- Main Manu --------------


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
                    preselect=variants.index("en_US.UTF-8 UTF-8")
                    if lang == "English"
                    else -1,
                    sidebar=sidebar,
                )

                if isinstance(variant, int):
                    return (lang, variant)
            else:
                return
        except KeyboardInterrupt:
            break
    return


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
    return


def timezone_menu() -> dict | None:
    pass


def main_menu():
    c.init()
    stage = 0
    locale = None
    keyboard = None
    timezone = None
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
                locale = None
                _, locale = locale_menu()
                stage = 0 if locale is None else 2
            elif stage == 2:
                keyboard = None
                keyboard = keyboard_menu()
                stage = 1 if keyboard is None else 3
            elif stage == 3:
                timezone = None
                timezone = timezone_menu()
                stage = 2 if timezone is None else 4
            elif stage == 4:
                user = user_menu()
            elif stage == 5:
                summary = summary_confirm()
            elif stage == 6:
                installation = install()
            elif stage == 7:
                pass  # Do finish menu here
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
