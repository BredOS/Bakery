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

from datetime import datetime
import os
import locale
from bredos.translations import setup_translations
from bredos.logging import (
    setup_logging,
    setup_handler,
    lp,
    lrun,
    dryrun,
    expected_to_fail,
    get_handler,
    get_logger,
)

if dryrun:
    # ./DRYRUN.log
    log_path = "."
    log_filename = "DRYRUN.log"
else:
    log_path = os.path.join(os.path.expanduser("~"), ".bredos", "bakery", "logs")
    log_filename = datetime.now().strftime("BAKERY-%Y-%m-%d-%H-%M-%S.log")

setup_logging("bredos-bakery", log_path, log_filename)
setup_handler()
lp("Logger started.")
lp("Dry run = " + str(dryrun))
lp("Setting up translations..")
_, _p = setup_translations(
    "bakery", locale.getdefaultlocale()[0]
)  # pyright: ignore[reportGeneralTypeIssues]
lp("Translations setup.")

dryrun = dryrun
log_file = os.path.join(log_path, log_filename)
lp = lp
lrun = lrun
_p = _p
_ = _
expected_to_fail = expected_to_fail

from bakery import misc

st_msgs = misc.st_msgs
