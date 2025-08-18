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
import tempfile
from time import sleep
from bredos.utilities import catch_exceptions
import psutil
from bakery import lrun, lp
import parted


def check_efi() -> bool:
    try:
        with open("/proc/mounts", "r") as mounts_file:
            mounts = mounts_file.read().split("\n")
            for mount in mounts:
                if "efivarfs" in mount:
                    lp("System is EFI", mode="debug")
                    return True
    except FileNotFoundError:
        lp("System is MBR/BIOS", mode="debug")
        return False


def check_partition_table(disk: str) -> str:
    try:
        device = parted.getDevice(disk)
        disk_instance = parted.newDisk(device)
        lp(f"Found a {disk_instance.type} partition table on {disk}", mode="debug")
        return disk_instance.type
    except Exception as e:
        lp(f"Error while processing disk {disk}: {str(e)}", mode="error")
        return None


@catch_exceptions
def get_block_devices():
    disks = subprocess.check_output(["lsblk", "-d", "-o", "NAME"]).decode("UTF-8")
    disk_list = disks.strip().split("\n")[1:]  # Skip header line
    disk_list = [
        disk
        for disk in disk_list
        if not disk.startswith("loop") and not disk.startswith("zram")
    ]
    disk_list = ["/dev/" + disk for disk in disk_list]
    lp("Found block devices: " + str(disk_list), mode="debug")
    return disk_list


def list_drives() -> dict:
    device_names = get_block_devices()
    pretty_names = {}

    for device_name in device_names:
        try:
            device = parted.getDevice(device_name)
            model = device.model.strip() if device.model else "Unknown"
            if len(model) > 20:
                model = model[:17] + "..."
            pretty_names[device_name] = model
        except Exception as e:
            lp(f"Error retrieving device info for {device_name}: {e}", mode="error")

    return pretty_names


@catch_exceptions
def get_partitions() -> list:
    # Get the partitions from get_block_devices
    disk_list = get_block_devices()
    partitions_dict = {}
    for disk in disk_list:
        try:
            device = parted.getDevice(disk)
            disk_instance = parted.newDisk(device)

            partitions_info = []
            for partition in disk_instance.partitions:
                # if partition is extended, skip it
                if partition.type == 2:
                    continue
                partition_info = {
                    partition.path: [
                        int(partition.getSize()),  # Size in MB
                        partition.geometry.start,  # Start sector
                        partition.geometry.end,  # End sector
                        (
                            partition.fileSystem.type if partition.fileSystem else None
                        ),  # Filesystem type
                    ]
                }
                partitions_info.append(partition_info)

            # Get the free space regions and add them to the partitions_info
            free_space_regions = disk_instance.getFreeSpaceRegions()
            for free_space_region in free_space_regions:
                if free_space_region.getSize() < 4:
                    continue
                free_space_info = {
                    "Free space": [
                        free_space_region.getSize(),  # Size in MB
                        free_space_region.start,  # Start sector
                        free_space_region.end,  # End sector
                        None,  # Filesystem type
                    ]
                }

                partitions_info.append(free_space_info)

            # Sort the partitions_info list by the start sector
            partitions_info.sort(key=lambda x: list(x.values())[0][1])
            partitions_dict[disk] = partitions_info

        except Exception as e:
            lp(f"Error while processing disk {disk}: {str(e)}", mode="error")
            # if str(e) contains "unrecognised disk label" then the disk is not partitioned and we have to return free_space for the whole disk
            try:
                if "unrecognised disk label" in str(e):
                    partitions_dict[disk] = [
                        {
                            "Free space": [
                                int(
                                    device.length * device.sectorSize / 1024 / 1024
                                ),  # Size in MB
                                0,  # Start sector
                                device.length,  # End sector
                                None,  # Filesystem type
                            ]
                        }
                    ]
            except:
                pass

    return partitions_dict  # {disk: [{part1: [size, start, end, fs]}, {part2: [size, start, end, fs]}, {"free_space": [size, start, end, None]}]}


@catch_exceptions
def gen_new_partitions(old_partitions: dict, action: str, part_to_replace=None) -> dict:
    # get the drives physical sector size, sector size, length
    disk = list(old_partitions.keys())[0]
    device = parted.getDevice(disk)
    sector_size = device.sectorSize
    physical_sector_size = device.physicalSectorSize
    length = device.length
    drive_size = length * sector_size / 1024 / 1024  # in MB
    if action == "erase_all":
        # efi 256M, root rest
        new_partitions = {}
        for disk, partitions in old_partitions.items():
            new_partitions[disk] = [
                {"EFI": [float(256), 2048, 256 * 1024 * 1024 // sector_size, "fat32"]},
                {
                    "BredOS": [
                        int(drive_size) - 257,
                        257 * 1024 * 1024 // sector_size,
                        length - sector_size,
                        "btrfs",
                    ]
                },
            ]
        return new_partitions
    elif action == "replace":
        # check there is a fat32 that can be used for efi if not create one before the partition to be replaced
        # check for fat32 partition
        for disk, partitions in old_partitions.items():
            for partition in partitions:
                if partition[list(partition.keys())[0]][3] == "fat32":
                    fat32 = partition
                    break
                else:
                    fat32 = None
        new_partitions = {}
        for disk, partitions in old_partitions.items():
            # Get the partition to be replaced using the  number
            part = partitions[part_to_replace]

            # Initialize the new partitions list for the disk
            new_partitions[disk] = []

            # Add all the partitions except the one to be replaced
            for partition in partitions:
                if partition != part:
                    new_partitions[disk].append(partition)

            # Get the start and end of the partition to be replaced
            start = part[list(part.keys())[0]][1]
            end = part[list(part.keys())[0]][2]
            size = part[list(part.keys())[0]][0]
            sector_size = 512  # Assume a default sector size

            if fat32:
                new_partitions[disk].append(
                    {
                        "fat32": [
                            256,
                            start,
                            start + (256 * 1024 * 1024 // sector_size),
                            "fat32",
                        ]
                    }
                )

                # Add the root partition
                new_partitions[disk].append(
                    {
                        "BredOS": [
                            size - 257,
                            start + (257 * 1024 * 1024 // sector_size),
                            end,
                            "btrfs",
                        ]
                    }
                )
            else:
                new_partitions[disk].append({"BredOS": [size, start, end, "btrfs"]})
        # sort the partitions by the start sector
        for disk, partitions in new_partitions.items():
            partitions.sort(key=lambda x: list(x.values())[0][1])
        return new_partitions


@catch_exceptions
def format_partition(
    partition: str, fs: str, subvols: bool = False, home_subvol: bool = False
) -> None:
    if fs == "fat32":
        lp("Formatting partition: " + partition + " as fat32")
        lrun(["mkfs.fat", "-F32", partition])
    elif fs == "ext4":
        lp("Formatting partition: " + partition + " as ext4")
        lrun(["mkfs.ext4", partition])
    elif fs == "btrfs":
        lp("Formatting partition: " + partition + " as btrfs")
        lrun(["mkfs.btrfs", "-f", partition])
        if subvols:
            temp_dir = tempfile.mkdtemp()
            lp("Mounting partition: " + partition + " to " + temp_dir)
            lp("Creating subvolumes")
            try:
                lrun(["mount", partition, temp_dir])
                subvolumes = ["@", "@cache", "@log", "@pkg", "@.snapshots"]
                if home_subvol:
                    subvolumes.append("@home")
                for subvol in subvolumes:
                    lp("Creating subvolume: " + subvol)
                    lrun(
                        [
                            "btrfs",
                            "subvolume",
                            "create",
                            os.path.join(temp_dir, subvol),
                        ]
                    )
            finally:
                lp("Done creating subvolumes")
                lp("Unmounting partition: " + partition)
                lrun(["umount", temp_dir])
                os.rmdir(temp_dir)


@catch_exceptions
def get_fs(partition: str) -> str:
    cmd = ["lsblk", "-no", "FSTYPE", partition]
    return subprocess.check_output(cmd).decode("utf-8").strip()


@catch_exceptions
def get_uuid(partition: str) -> str:
    cmd = ["blkid", "-s", "UUID", "-o", "value", partition]
    return subprocess.check_output(cmd).decode("utf-8").strip()


@catch_exceptions
def get_disk_size(disk: str) -> int:
    device = parted.getDevice(disk)
    return int(device.length * device.sectorSize / 1024 / 1024)


@catch_exceptions
def mount_partition(
    partition: str,
    mount_point: str,
    opts: str = None,
    btrfs: bool = False,
    home_subvol: bool = False,
) -> None:
    if not btrfs:
        lp("Mounting partition: " + partition + " to " + mount_point)
        if opts:
            lrun(["mount", "-o", opts, partition, mount_point])
        else:
            lrun(["mount", partition, mount_point])
    else:
        lp("Mounting btrfs partition: " + partition + " to " + mount_point)
        if opts:
            lrun(["mount", "-o", "subvol=@", opts, partition, mount_point])
        else:
            lrun(["mount", "-o", "subvol=@", partition, mount_point])
        lp("Mounting btrfs subvolumes")
        subvolumes = {
            "log": "/var/log",
            "cache": "/var/cache",
            "pkg": "/var/cache/pacman/pkg",
        }
        if home_subvol:
            subvolumes["home"] = "/home"
        for subvol, path in subvolumes.items():
            os.makedirs(mount_point + path, exist_ok=True)
            lp("Mounting subvolume: " + subvol + " to " + path)
            lrun(
                [
                    "mount",
                    "-o",
                    "subvol=@" + subvol,
                    partition,
                    mount_point + path,
                ]
            )


@catch_exceptions
def unmount_all(mnt_dir: str) -> None:
    lp("Unmounting all partitions")
    lrun(["umount", "-R", mnt_dir])


@catch_exceptions
def mount_all_partitions(partitions: dict, mnt_dir: str) -> None:
    if partitions["type"] == "guided":
        if partitions["mode"] == "erase_all":
            disk = partitions["disk"]
            if "nvme" in disk or "mmcblk" in disk:
                part_prefix = "p"
            else:
                part_prefix = ""
            mount_partition(
                disk + part_prefix + "2", mnt_dir, "", btrfs=True, home_subvol=True
            )
            if partitions["efi"]:
                os.makedirs(os.path.join(mnt_dir, "boot", "efi"), exist_ok=True)
                mount_partition(
                    disk + part_prefix + "1",
                    os.path.join(mnt_dir, "boot/efi"),
                    "",
                    btrfs=False,
                )
            else:
                os.makedirs(os.path.join(mnt_dir, "boot"), exist_ok=True)
                mount_partition(
                    disk + part_prefix + "1",
                    os.path.join(mnt_dir, "boot"),
                    "",
                    btrfs=False,
                )
            lp("Mounted partitions")
    elif partitions["type"] == "manual":
        # Check if user wants seperate home partition
        home_subvol = True
        for part, options in partitions["partitions"].items():
            if options["mp"] == "Use as home":
                home_subvol = False
                break
        # First find and mount the "Use as root" partition
        for part, options in partitions["partitions"].items():
            fs_type = options["fs"]
            mount_point = options["mp"]
            if mount_point == "Use as root":
                mount_partition(part, mnt_dir, "", btrfs=True, home_subvol=home_subvol)
                break
        # Then find and mount the "Use as boot" partition
        for part, options in partitions["partitions"].items():
            fs_type = options["fs"]
            mount_point = options["mp"]
            if mount_point == "Use as boot":
                os.makedirs(os.path.join(mnt_dir, "boot", "efi"), exist_ok=True)
                mount_partition(
                    part, os.path.join(mnt_dir, "boot", "efi"), "", btrfs=False
                )
                break
        # Then find and mount the "Use as home" partition
        for part, options in partitions["partitions"].items():
            fs_type = options["fs"]
            mount_point = options["mp"]
            if mount_point == "Use as home":
                os.makedirs(os.path.join(mnt_dir, "home"), exist_ok=True)
                mount_partition(part, os.path.join(mnt_dir, "home"))


@catch_exceptions
def rescan_partitions() -> None:
    lp("Rescanning partitions")
    lrun(["partprobe"])


@catch_exceptions
def partition_disk(partitions: dict) -> None:
    # {'type': 'guided', 'efi': True, 'disk': '/dev/nvme1n1', 'mode': 'erase_all', 'partitions': {'/dev/nvme1n1': [{'EFI': [256.0, 2048, 524288, 'fat32']}, {'swap': [2048.0, 526336, 4196352, 'swap']}, {'BredOS': [241891, 4198400, 500117680, 'btrfs']}]}}
    # OR
    # {'type': 'manual', 'efi': True, 'disk': '/dev/nvme1n1', 'partitions': {'/dev/nvme1n1p1': {'fs': 'fat32', 'mp': 'Use as boot'}, '/dev/nvme1n1p2': {'fs': 'btrfs', 'mp': 'Use as root'}, '/dev/nvme1n1p3': {'fs': None, 'mp': 'Use as home'}}}
    disk = partitions["disk"]
    # make sure the disk doesn't have any mounted partitions
    parts = psutil.disk_partitions()

    # Find partitions on the specified disk
    for partition in parts:
        if partition.device.startswith(disk):
            lp("Unmounting partition: " + partition.device)
            lrun(["umount", partition.device])
    if partitions["type"] == "guided":
        if partitions["mode"] == "erase_all":
            if "nvme" in disk or "mmcblk" in disk:
                part_prefix = "p"
            else:
                part_prefix = ""
            # size = get_disk_size(disk)
            parted_cmd = [
                "parted",
                "--script",
                disk,
                "--align",
                "optimal",
            ]
            parted_cmd.extend(["mklabel", "gpt"])
            parted_cmd.extend(["mkpart", "primary", "fat32", "2048s", "256M"])
            parted_cmd.extend(["set", "1", "esp", "on"])
            # parted_cmd.extend(["set", "1", "boot", "on"])
            parted_cmd.extend(["mkpart", "primary", "btrfs", "256M", "100%"])
            lp("Partitioning disk: " + disk)
            lp("Creating new GPT partition table")
            lp("Creating EFI partition")
            lp("Creating BredOS root partition")
            lp("Running parted command: " + " ".join(parted_cmd))
            lrun(parted_cmd)
            sleep(1)
            format_partition(disk + part_prefix + "1", "fat32")
            format_partition(
                disk + part_prefix + "2", "btrfs", subvols=True, home_subvol=True
            )
    elif partitions["type"] == "manual":
        # Check if user wants seperate home partition
        home_subvol = True
        for part, options in partitions["partitions"].items():
            if options["mp"] == "Use as home":
                home_subvol = False
                break
        # Iterate through the partitions in the manual scheme
        for part, options in partitions["partitions"].items():
            fs_type = options["fs"]
            mp = options["mp"]
            # Format partitions based on filesystem type
            if mp == "Use as boot":
                format_partition(part, fs_type)
            elif mp == "Use as root":
                if fs_type == "btrfs":
                    format_partition(
                        part, fs_type, subvols=True, home_subvol=home_subvol
                    )
                else:
                    format_partition(part, fs_type, home_subvol=home_subvol)
            elif mp == "Use as home":
                fs = get_fs(part)
                # if fs_type is None or "Don't format" is selected and the actual fs is either btrfs or ext4 dont do anything
                if (fs_type == None or fs_type == "Don't format") and (
                    fs != "btrfs" or fs != "ext4"
                ):
                    format_partition(part, fs)
