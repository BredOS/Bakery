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
import platform
import re
import tempfile

from bakery import lrun, lp, _, expected_to_fail
from bredos.utilities import catch_exceptions
from .partitioning import mount_partition


def run_chroot_cmd(work_dir: str, cmd: list, *args, **kwargs) -> None:
    lrun(["arch-chroot", work_dir] + cmd, *args, **kwargs)


@catch_exceptions
def grub_install(mnt_dir: str, arch: str = "arm64-efi") -> None:
    lp("Installing GRUB for the " + arch + " platform")
    run_chroot_cmd(
        mnt_dir,
        [
            "grub-install",
            f"--target={arch}",
            "--efi-directory=/boot/efi",
            "--removable",
            "--bootloader-id=BredOS",
        ],
    )
    lp("GRUB installation complete")
    lp("Generating GRUB configuration")
    run_chroot_cmd(mnt_dir, ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"])
    lp("GRUB configuration generated")


def file_update(file_path: str, comment_keys: list = [], updates: dict = {}):
    """
    Validates a file exists and updates specific lines' values, while retaining the order and optionally commenting/uncommenting lines.

    Args:
        file_path (str): The path to the file to validate and update.
        updates (dict, optional): A dictionary where keys are line keys and values are the new values to set.
        comment_keys (list, optional): A list of keys to comment out.

    Returns:
        bool: If the operation was successful or not.
    """
    # Check if the file exists
    if not os.path.isfile(file_path):
        return False

    # Read the file
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()
    except Exception as e:
        lp(f"Error reading {file_path}: {e}")
        return False

    # Pattern to match lines (supports whitespace variations)
    pattern = re.compile(r"^\s*#?\s*(\w+)\s*=\s*(.*)$")
    updated_lines = []
    modified = False

    for line in lines:
        match = pattern.match(line)
        if match:
            key = match.group(1)
            value = match.group(2)

            # Handle updates
            if key in updates:
                updated_value = updates[key]
                updated_lines.append(f"{key}={updated_value}\n")
                modified = True
            # Handle commenting out lines
            elif key in comment_keys:
                updated_lines.append(f"# {key}={value}\n")
                modified = True
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    # Write back the updated file if changes were made
    if modified:
        try:
            with open(file_path, "w") as file:
                file.writelines(updated_lines)
        except Exception as e:
            lp(f"Error writing to the file: {e}")
            return False
    return True


@catch_exceptions
def grub_cfg(
    cmdline: str = None,
    dtb: str = None,
    distribution: str = "BredOS",
    timeout: int = 5,
    update: bool = True,
    chroot: bool = False,
    mnt_dir: str = None,
) -> None:
    grubpath = (mnt_dir if chroot else "") + "/etc/default/grub"
    lp("Configuring GRUB..")
    updates = {}
    comment_keys = []

    if cmdline is not None:
        lp(f'Setting cmdline to "{cmdline}"')
        updates["GRUB_CMDLINE_LINUX_DEFAULT"] = f'"{cmdline}"'

    if dtb is not None:
        if dtb:
            lp('Setting Device Tree to "{dtb}"')
            updates["GRUB_DTB"] = f'"{dtb}"'
        else:
            lp("Disabling Device Tree")
            comment_keys.append("GRUB_DTB")

    if distribution:
        lp("Configuring distribution name..")
        updates["GRUB_DISTRIBUTOR"] = f'"{distribution}"'

    if timeout > 0:
        lp("Setting timeout..")
        updates["GRUB_TIMEOUT"] = str(timeout)
    else:
        lp("Disabling timeout..")
        comment_keys.append("GRUB_TIMEOUT")

    if file_update(grubpath, comment_keys, updates):
        lp("Reconfiguration complete.")
    else:
        lp("Failed to update GRUB configuration!")
        raise RuntimeError("Failed to update GRUB configuration!")

    if not update:
        lp("Skipping GRUB regeneration..")
        return

    cmd = ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"]
    if chroot and mnt_dir is not None:
        run_chroot_cmd(mnt_dir, cmd)
    else:
        lrun(cmd)
    lp("GRUB update complete")


@catch_exceptions
def unpack_sqfs(sqfs_file: str, mnt_dir: str) -> None:
    squashfs_mnt = tempfile.mkdtemp()
    lp("Mounting squashfs file: " + sqfs_file + " to " + squashfs_mnt)
    mount_partition(sqfs_file, squashfs_mnt, "loop")
    lp("Copying files from squashfs to " + mnt_dir)
    lrun(["cp", "-apr", squashfs_mnt + "/*", mnt_dir], shell=True)
    lp("Done copying files! Unmounting squashfs")
    lrun(["umount", squashfs_mnt])
    os.rmdir(squashfs_mnt)


@catch_exceptions
def copy_kern_from_iso(mnt_dir: str) -> None:
    lp("Copying kernel and initramfs from ISO to " + mnt_dir)
    arch = platform.machine()
    lrun(
        [
            "cp",
            "-avr",
            "/run/archiso/bootmnt/arch/boot/" + arch + "/*",
            mnt_dir + "/boot",
        ],
        shell=True,
    )
    if arch == "x86_64":
        lrun(
            [
                "cp",
                "-avr",
                "/run/archiso/bootmnt/arch/boot/intel-ucode.img",
                mnt_dir + "/boot",
            ]
        )
        lrun(
            [
                "cp",
                "-avr",
                "/run/archiso/bootmnt/arch/boot/amd-ucode.img",
                mnt_dir + "/boot",
            ]
        )
    lp("Done copying kernel and initramfs")


@catch_exceptions
def regenerate_initramfs(mnt_dir: str) -> None:
    # mnt_dir/etc/mkinitcpio.conf.bak -> mnt_dir/etc/mkinitcpio.conf
    lrun(
        [
            "mv",
            mnt_dir + "/etc/mkinitcpio.conf.bak",
            mnt_dir + "/etc/mkinitcpio.conf",
        ]
    )
    lp("Regenerating initramfs")
    run_chroot_cmd(mnt_dir, ["mkinitcpio", "-P"], postrunfn=expected_to_fail)
    lp("Initramfs regeneration complete")


@catch_exceptions
def generate_fstab(mnt_dir: str) -> None:
    lp("Generating fstab")
    fstab_path = os.path.join(mnt_dir, "etc", "fstab")

    # Generate the fstab file
    lrun(["genfstab", "-U", mnt_dir, ">", fstab_path], shell=True)

    # Process the generated fstab
    with open(fstab_path, "r") as f:
        lines = f.readlines()

    updated_lines = []
    skip_next = False

    for line in lines:
        if skip_next:
            skip_next = False
            continue
        if line.startswith("# /dev/zram0"):
            updated_lines.append(line)
            skip_next = True
        else:
            updated_lines.append(line)

    with open(fstab_path, "w") as f:
        f.writelines(updated_lines)

    lp("Fstab generated")
