# Timer functions
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
import subprocess
import tempfile
from time import monotonic, sleep

from bakery import lrun, lp, dryrun, _
from . import config
from .iso import (
    copy_kern_from_iso,
    generate_fstab,
    grub_cfg,
    grub_install,
    regenerate_initramfs,
    run_chroot_cmd,
    unpack_sqfs,
)
from .keyboard import kb_set
from .locale import enable_locales, set_locale
from .misc import is_sbc, copy_logs, populate_messages, st
from .packages import remove_packages
from .partitioning import mount_all_partitions, partition_disk, unmount_all
from .timezone import tz_ntp, tz_set
from .tweaks import load_config
from .validate import gidc, shells, uidc


_stimer = monotonic()


def reset_timer() -> None:
    global _stimer
    _stimer = monotonic()


def get_timer() -> float:
    return monotonic() - _stimer


def enable_services(services: list, chroot: bool = False, mnt_dir: str = None) -> None:
    try:
        for i in services:
            cmd = ["systemctl", "enable", i]
            if chroot:
                run_chroot_cmd(mnt_dir, cmd)
            else:
                lrun(cmd)
    except:
        pass


def final_setup(settings, mnt_dir: str = None) -> None:
    if settings["install_type"]["source"] == "on_device":
        lrun(["systemctl", "disable", "resizefs.service"], silent=True)
        enable_services(
            ["bluetooth.service", "fstrim.timer", "oemcleanup.service", "cups.socket"],
        )
        if (
            settings["session_configuration"]["dm"] == "gdm"
            and settings["user"]["autologin"] == True
        ):
            # rm /etc/gdm/custom.conf
            lrun(["rm", "/etc/gdm/custom.conf"], silent=True)
        lrun(
            [
                "rm",
                "-f",
                "/etc/sudoers.d/g_wheel",
                "/etc/polkit-1/rules.d/49-nopasswd_global.rules",
            ]
        )
    elif settings["install_type"]["source"] == "from_iso":
        cfg = load_config()
        if is_sbc(settings["install_type"]["device"]):
            tweaks = cfg["devices"][settings["install_type"]["device"]].get("dt")
            if tweaks:
                grub_cfg(
                    cmdline=tweaks.get("cmdline", None),
                    dtb=tweaks.get("dtb", None),
                    timeout=tweaks.get("timeout", 5),
                    update=True,
                    chroot=True,
                    mnt_dir=mnt_dir,
                )
            pythontweaks = tweaks.get("tweaks", None)
            if pythontweaks:
                exec(pythontweaks["python"])
        else:
            arch = platform.machine()
            tweaks = cfg.get(f"arch_{arch}")
            if tweaks:
                grub_cfg(
                    cmdline=tweaks.get("cmdline", None),
                    dtb=tweaks.get("dtb", None),
                    timeout=tweaks.get("timeout", 5),
                    update=True,
                    chroot=True,
                    mnt_dir=mnt_dir,
                )
                pythontweaks = tweaks.get("tweaks", None)
                if pythontweaks:
                    exec(pythontweaks["python"])

        if settings["install_type"]["type"] == "offline":
            enable_services(
                [
                    "bluetooth.service",
                    "fstrim.timer",
                    "oemcleanup.service",
                    "cups.socket",
                ],
                chroot=True,
                mnt_dir=mnt_dir,
            )
            if (
                settings["session_configuration"]["dm"] == "gdm"
                and settings["user"]["autologin"] == True
            ):
                # rm /etc/gdm/custom.conf
                lrun(["rm", mnt_dir + "/etc/gdm/custom.conf"], silent=True)
            lrun(
                [
                    "rm",
                    "-f",
                    mnt_dir + "/etc/sudoers.d/g_wheel",
                    mnt_dir + "/etc/polkit-1/rules.d/49-nopasswd_global.rules",
                ]
            )


def adduser(
    username: str,
    password: str,
    uid,
    gid,
    shell: str,
    groups: list,
    chroot: bool = False,
    mnt_dir: str = None,
) -> None:
    if isinstance(uid, int):
        uid = str(uid)
    elif not uid.isdigit():
        raise TypeError("UID not a number!")
    if gid is False:
        gid = uid
    elif isinstance(gid, int):
        gid = str(gid)
    elif not gid.isdigit():
        raise TypeError("GID not a number!")
    if shell not in shells():
        raise OSError("Invalid shell")
    if uidc(uid):
        raise OSError("Used UID")
    if gidc(gid):
        raise OSError("Used GID")
    lp("Making group " + username + " on gid " + gid)
    if chroot:
        run_chroot_cmd(mnt_dir, ["groupadd", username, "-g", gid])
    else:
        lrun(["groupadd", username, "-g", gid])  # May silently fail, which is fine.
    lp("Adding user " + username + " on " + uid + ":" + gid + " with shell " + shell)
    if chroot:
        run_chroot_cmd(
            mnt_dir,
            [
                "useradd",
                "-N",
                username,
                "-u",
                uid,
                "-g",
                gid,
                "-m",
                "-s",
                shell,
            ],
        )
    else:
        lrun(["useradd", "-N", username, "-u", uid, "-g", gid, "-m", "-s", shell])
    for i in groups:
        groupadd(username, i, chroot, mnt_dir)
    passwd(username, password, chroot, mnt_dir)


def groupadd(
    username: str, group: str, chroot: bool = False, mnt_dir: str = None
) -> None:
    lp("Adding " + username + " to group " + group)
    cmd = ["usermod", "-aG", group, username]
    if chroot:
        run_chroot_cmd(mnt_dir, cmd)
    else:
        lrun(cmd)


def passwd(
    username: str, password: str, chroot: bool = False, mnt_dir: str = None
) -> None:
    lp("Setting user " + username + " password")
    cmd = ["passwd", username]
    if dryrun:
        lp("Would have run: " + str(cmd) + ", with the password via stdin.")
    elif dryrun and chroot:
        lp("Would have run: " + str(cmd) + ", with the password via stdin in chroot")
    elif chroot:
        subprocess.run(
            ["arch-chroot", mnt_dir] + cmd, input=f"{password}\n{password}", text=True
        )
    else:
        subprocess.run(cmd, input=f"{password}\n{password}", text=True)


def sudo_nopasswd(no_passwd: bool, chroot: bool = False, mnt_dir: str = None) -> None:
    if dryrun:
        lp("Would have set sudoers to " + str(not no_passwd))
    else:
        if chroot:
            path = mnt_dir + "/etc/sudoers"
        else:
            path = "/etc/sudoers"
        if no_passwd:
            content = "%wheel ALL=(ALL:ALL) NOPASSWD: ALL"
        else:
            content = "%wheel ALL=(ALL:ALL) ALL"
        lp(f"Setting {path} to {content}")
        with open(path, "a") as f:
            f.write(content)


def enable_autologin(
    username: str,
    session_configuration: dict,
    install_type: dict,
    chroot: bool = False,
    mnt_dir: str = None,
) -> None:
    dm = session_configuration["dm"]
    de = session_configuration["de"]
    is_wayland = session_configuration["is_wayland"]
    if dm == "lightdm":
        lp("Enabling autologin for " + username + " in " + dm)
        if (install_type["source"] == "on_device") or (
            install_type["source"] == "from_iso" and install_type["type"] == "offline"
        ):
            cmd = [
                "cp",
                "/etc/lightdm/lightdm.conf.bak",
                "/etc/lightdm/lightdm.conf",
            ]
            if chroot and mnt_dir:
                run_chroot_cmd(mnt_dir, cmd)
            else:
                lrun(cmd)
        new_content = (
            "autologin-user=" + username + "\n"
            "user-session=" + de + "\n"
            "greeter-session=lightdm-slick-greeter\n"
            "autologin-user-timeout=0\n"
            "autologin-guest=false"
        )
        if dryrun:
            lp("Would have replaced [Seat:*] section in lightdm.conf with:")
            lp(new_content)
        else:
            if chroot and mnt_dir:
                with open(mnt_dir + "/etc/lightdm/lightdm.conf", "r") as f:
                    content = f.read()
            else:
                with open("/etc/lightdm/lightdm.conf", "r") as f:
                    content = f.read()

            modified_content = content.replace(
                "\n[Seat:*]", "\n[Seat:*]\n" + new_content
            )

            if chroot and mnt_dir:
                with open(mnt_dir + "/etc/lightdm/lightdm.conf", "w") as f:
                    f.write(modified_content)
            else:
                with open("/etc/lightdm/lightdm.conf", "w") as f:
                    f.write(modified_content)
    elif dm == "gdm":
        lp("Enabling autologin for " + username + " in " + dm)

        config = f"""# GDM configuration storage

[daemon]
# Uncomment the line below to force the login screen to use Xorg
#WaylandEnable=false
AutomaticLogin={username}
AutomaticLoginEnable=True
# TimedLoginEnable=true
# TimedLogin={username}
# TimedLoginDelay=5
DefaultSession={de}

[security]

[xdmcp]

[chooser]

[debug]
# Uncomment the line below to turn on debugging
#Enable=true
"""
        cmd = f'echo "{config}" > /etc/gdm/custom.conf'
        if chroot and mnt_dir:
            run_chroot_cmd(mnt_dir, ["sh", "-c", cmd])
        else:
            lrun(["sh", "-c", cmd])
    groupadd(username, "autologin", chroot, mnt_dir)


def enable_autologin_tty(
    username: str, chroot: bool = False, mnt_dir: str = None
) -> None:
    cmd_mkdir = ["mkdir", "-p", "/etc/systemd/system/getty@tty1.service.d/"]
    if chroot and mnt_dir:
        run_chroot_cmd(mnt_dir, cmd_mkdir)
    else:
        lrun(cmd_mkdir)

    overrideconf = f"""[Service]
ExecStart=
ExecStart=-/usr/bin/agetty --autologin {username} --noclear %I $TERM
"""
    cmd_override = f'echo "{overrideconf}" |  tee /etc/systemd/system/getty@tty1.service.d/override.conf'
    if chroot and mnt_dir:
        run_chroot_cmd(mnt_dir, ["sh", "-c", cmd_override])
    else:
        lrun(["sh", "-c", cmd_override])


def set_hostname(hostname: str, chroot: bool = False, mnt_dir: str = None) -> None:
    cmd = ["bash", "-c", f"echo {hostname} > /etc/hostname"]
    if chroot and mnt_dir:
        run_chroot_cmd(mnt_dir, cmd)
    else:
        lrun(cmd)


def install(settings=None) -> int:
    """
    The main install function.

    Returns 0 on success,
            1 on general error,
            2 on invalid settings,
            3 on implementation missing.
    """
    start_time = monotonic()
    if settings is None:
        if dryrun:
            settings = {
                "install_type": {
                    "type": "offline",
                    "source": "on_device",
                    "device": "rpi4",
                },
                "session_configuration": {
                    "dm": "lightdm",
                    "de": "XFCE",
                    "is_wayland": False,
                },
                "layout": {"model": "pc105", "layout": "us", "variant": "alt-intl"},
                "locale": "en_US.UTF-8 UTF-8",
                "timezone": {"region": "Europe", "zone": "Sofia", "ntp": True},
                "hostname": "breborb",
                "user": {
                    "fullname": "Bred guy",
                    "username": "Panda",
                    "password": "123",
                    "uid": 1005,
                    "gid": False,
                    "shell": "/bin/bash",
                    "groups": ["wheel", "network", "video", "audio", "storage", "uucp"],
                    "sudo_nopasswd": False,
                    "autologin": True,
                },
                "root_password": False,
                "installer": {
                    "shown_pages": ["Keyboard", "Timezone", "User", "Locale"],
                    "installer_version": "0.1.0",
                    "ui": "tui",
                },
                "packages": {},
            }
        else:
            raise ValueError("No data passed with dryrun disabled.")

    if settings["install_type"]["type"] == "online":
        lp("Online mode not yet implemented!", mode="error")
        return 3
    elif settings["install_type"]["type"] == "offline":
        lp("%ST0%")  # Preparing
        sleep(0.15)
        # Parse settings
        reset_timer()

        lp("Validating manifest")
        if "installer" in settings.keys():
            if "installer_version" in settings["installer"].keys():
                if (
                    settings["installer"]["installer_version"]
                    < config.installer_version
                ):
                    lp("Toml installer version lower than current.", mode="warn")
                else:
                    lp("Toml installer version matches.")
            else:
                lp("Did not find version specification, cannot continue.", mode="error")
                return 2
        else:
            lp("Not a bakery manifest", mode="error")
            return 2
        for i in [
            "install_type",
            "session_configuration",
            "layout",
            "locale",
            "timezone",
            "hostname",
            "user",
            "root_password",
            "packages",
        ]:
            if i not in settings.keys():
                lp("Invalid manifest, does not contain " + i, mode="error")
                return 2
        for i in ["type", "source", "device"]:
            if i not in settings["install_type"].keys():
                lp("Invalid install_type manifest, does not contain " + i, mode="error")
                return 2
        for i in ["dm", "de", "is_wayland"]:
            if i not in settings["session_configuration"].keys():
                lp(
                    "Invalid session_configuration manifest, does not contain " + i,
                    mode="error",
                )
                return 2
        for i in ["model", "layout", "variant"]:
            if i not in settings["layout"].keys():
                lp("Invalid layout manifest, does not contain " + i, mode="error")
                return 2
            if (not isinstance(settings["layout"][i], str)) and (
                settings["layout"][i] != False
            ):
                lp(i + " must be a string or False", mode="error")
                return 2
        for i in ["region", "zone", "ntp"]:
            if i not in settings["timezone"].keys():
                lp("Invalid timezone manifest, does not contain " + i, mode="error")
                return 2
        for i in [
            settings["timezone"]["region"],
            settings["timezone"]["zone"],
            settings["locale"],
        ]:
            if not isinstance(i, str):
                lp(i + " must be a string", mode="error")
                return 2
        if not isinstance(settings["timezone"]["ntp"], bool):
            lp("ntp must be a bool", mode="error")
            return 2
        for i in ["root_password"]:
            if (not isinstance(settings[i], str)) and (settings[i] != False):
                lp(i + " must be a string or False", mode="error")
                return 2
        for i in [
            "fullname",
            "username",
            "password",
            "uid",
            "gid",
            "shell",
            "groups",
            "sudo_nopasswd",
            "autologin",
        ]:
            if i not in settings["user"].keys():
                lp("Invalid user manifest, does not contain " + i, mode="error")
                return 2
        for i in ["shown_pages", "ui"]:
            if i not in settings["installer"].keys():
                lp("Invalid installer manifest, does not contain " + i, mode="error")
                return 2
        lp("Manifest validated")
        populate_messages(
            type=settings["install_type"]["source"]
            + "_"
            + settings["install_type"]["type"]
        )
        lp("Took {:.5f}".format(get_timer()))
        st(1)  # Locales
        reset_timer()

        if settings["install_type"]["source"] == "on_device":
            enable_locales([settings["locale"]])
            set_locale(settings["locale"])

            lp("Took {:.5f}".format(get_timer()))
            st(2)  # keyboard
            reset_timer()

            kb_set(
                settings["layout"]["model"],
                settings["layout"]["layout"],
                settings["layout"]["variant"],
            )

            lp("Took {:.5f}".format(get_timer()))
            st(3)  # TZ
            reset_timer()

            tz_set(settings["timezone"]["region"], settings["timezone"]["zone"])
            tz_ntp(settings["timezone"]["ntp"])

            lp("Took {:.5f}".format(get_timer()))
            st(4)  # Configure users
            reset_timer()

            adduser(
                settings["user"]["username"],
                settings["user"]["password"],
                settings["user"]["uid"],
                settings["user"]["gid"],
                settings["user"]["shell"],
                settings["user"]["groups"],
            )
            sudo_nopasswd(settings["user"]["sudo_nopasswd"])
            passwd("root", settings["user"]["password"])
            # ideally, we should have a way to check which DM/DE is installed
            if settings["user"]["autologin"]:
                enable_autologin(
                    settings["user"]["username"],
                    settings["session_configuration"],
                    settings["install_type"],
                )

                enable_autologin_tty(settings["user"]["username"])

            lp("Took {:.5f}".format(get_timer()))
            st(5)  # Configure hostname
            reset_timer()

            set_hostname(settings["hostname"])

            lp("Took {:.5f}".format(get_timer()))
            st(6)  # finishing up
            reset_timer()

            final_setup(settings)

            lp("Took {:.5f}".format(get_timer()))
            st(7)  # Cleanup
            reset_timer()

            # Done
            lp(
                "Installation finished. Total time: {:.5f}".format(
                    monotonic() - start_time
                )
            )
            copy_logs(settings["user"]["username"])
            return 0
        elif settings["install_type"]["source"] == "from_iso":
            try:
                lp("Took {:.5f}".format(get_timer()))
                st(1)  # Partitioning
                reset_timer()
                # Partition disk
                partition_disk(settings["partitions"])

                arch = platform.machine()
                if arch == "aarch64":
                    grub_arch = "arm64-efi"
                    sqfs_file = "/run/archiso/bootmnt/arch/aarch64/airootfs.sfs"
                else:
                    grub_arch = "x86_64-efi"
                    sqfs_file = "/run/archiso/bootmnt/arch/x86_64/airootfs.sfs"

                if not os.path.isfile(sqfs_file):
                    lp("Using fallback RAM squashfs")
                    sqfs_file = "/run/archiso/copytoram/airootfs.sfs"

                lp("Took {:.5f}".format(get_timer()))
                st(2)  # Mounting
                reset_timer()

                mnt_dir = tempfile.mkdtemp()
                # Mount partitions
                mount_all_partitions(settings["partitions"], mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(3)  # Unsquash
                reset_timer()
                # unpack squashfs
                unpack_sqfs(sqfs_file, mnt_dir)

                # Copy kernel and initramfs
                copy_kern_from_iso(mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(4)  # initramfs
                reset_timer()
                # Regenerate initramfs
                regenerate_initramfs(mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(5)  # fstab
                reset_timer()
                # Generate fstab
                generate_fstab(mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(6)  # Grub
                reset_timer()
                # Install grub
                grub_install(mnt_dir, arch=grub_arch)

                lp("Took {:.5f}".format(get_timer()))
                st(7)  # Removing packages
                reset_timer()
                # Remove packages
                remove_packages(
                    settings["packages"]["to_remove"], chroot=True, mnt_dir=mnt_dir
                )

                lp("Took {:.5f}".format(get_timer()))
                st(8)  # Locale
                reset_timer()
                enable_locales([settings["locale"]], chroot=True, mnt_dir=mnt_dir)
                set_locale(settings["locale"], chroot=True, mnt_dir=mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(9)  # keyboard
                reset_timer()

                kb_set(
                    settings["layout"]["model"],
                    settings["layout"]["layout"],
                    settings["layout"]["variant"],
                    chroot=True,
                    mnt_dir=mnt_dir,
                )

                lp("Took {:.5f}".format(get_timer()))
                st(10)  # TZ
                reset_timer()

                tz_set(
                    settings["timezone"]["region"],
                    settings["timezone"]["zone"],
                    chroot=True,
                    mnt_dir=mnt_dir,
                )
                tz_ntp(settings["timezone"]["ntp"], chroot=True, mnt_dir=mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(11)  # Configure users
                reset_timer()

                adduser(
                    settings["user"]["username"],
                    settings["user"]["password"],
                    settings["user"]["uid"],
                    settings["user"]["gid"],
                    settings["user"]["shell"],
                    settings["user"]["groups"],
                    chroot=True,
                    mnt_dir=mnt_dir,
                )
                lp("sudo_nopasswd")
                sudo_nopasswd(
                    settings["user"]["sudo_nopasswd"], chroot=True, mnt_dir=mnt_dir
                )
                passwd(
                    "root", settings["user"]["password"], chroot=True, mnt_dir=mnt_dir
                )
                # ideally, we should have a way to check which DM/DE is installed
                if settings["user"]["autologin"]:
                    enable_autologin(
                        settings["user"]["username"],
                        settings["session_configuration"],
                        settings["install_type"],
                        chroot=True,
                        mnt_dir=mnt_dir,
                    )

                    enable_autologin_tty(
                        settings["user"]["username"], chroot=True, mnt_dir=mnt_dir
                    )

                lp("Took {:.5f}".format(get_timer()))
                st(12)  # Configure hostname
                reset_timer()

                set_hostname(settings["hostname"], chroot=True, mnt_dir=mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(13)  # finishing up
                reset_timer()

                final_setup(settings, mnt_dir)

                unmount_all(mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(14)  # Cleanup
                reset_timer()

                # Done
                lp(
                    "Installation finished. Total time: {:.5f}".format(
                        monotonic() - start_time
                    )
                )
                copy_logs(settings["user"]["username"], chroot=True, mnt_dir=mnt_dir)
                return 0
            except:
                return 1
    elif settings["install_type"]["type"] == "custom":
        lp("Custom mode not yet implemented!", mode="error")
        return 3
