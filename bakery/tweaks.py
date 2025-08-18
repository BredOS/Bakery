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
import re
import yaml
from bredos.utilities import catch_exceptions


@catch_exceptions
def resolve_placeholders(config, context=None):
    """
    Recursively resolves placeholders in the configuration using the context.
    Re-evaluates until no placeholders remain.
    """
    if context is None:
        context = config  # Use the entire configuration as the context

    def resolve_value(value, context):
        """Resolve a single value with placeholders."""
        if isinstance(value, str):
            # Keep resolving placeholders until none are left
            while True:
                placeholders = re.findall(r"{{\s*([\w.]+)\s*}}", value)
                if not placeholders:
                    break  # Stop if no placeholders are left
                for placeholder in placeholders:
                    keys = placeholder.split(".")
                    resolved = context
                    for key in keys:
                        resolved = resolved.get(
                            key, f"{{{{ {placeholder} }}}}"
                        )  # Leave unresolved if missing
                    value = value.replace(f"{{{{ {placeholder} }}}}", resolved)
        return value

    if isinstance(config, dict):
        return {
            key: resolve_placeholders(value, context) for key, value in config.items()
        }
    elif isinstance(config, list):
        return [resolve_placeholders(item, context) for item in config]
    else:
        return resolve_value(config, context)


@catch_exceptions
def check_tweaks_config() -> bool:
    # curr dir + tweaks.yaml or /usr/share/bakery/tweaks.yaml prefer curr dir
    if os.path.isfile("tweaks.yaml"):
        return True
    elif os.path.isfile("/usr/share/bakery/tweaks.yaml"):
        return True
    return False


@catch_exceptions
def load_config() -> dict:
    # curr dir + tweaks.yaml or /usr/share/bakery/tweaks.yaml prefer curr dir
    if os.path.isfile("tweaks.yaml"):
        with open("tweaks.yaml", "r") as f:
            cfg = yaml.safe_load(f)
            return resolve_placeholders(cfg)
    elif os.path.isfile("/usr/share/bakery/tweaks.yaml"):
        with open("/usr/share/bakery/tweaks.yaml", "r") as f:
            cfg = yaml.safe_load(f)
            return resolve_placeholders(cfg)
