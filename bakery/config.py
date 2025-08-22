"Settings for the installer"
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

supported_languages = {"English": "en_US.UTF-8"}
timezone = {"region": "Europe", "zone": "London"}
installer_version = "1.3.2"
api_version = 1


def pages(_):
    return {
        "Keyboard": ["kb_screen", _("Keyboard")],
        "Locale": ["locale_screen", _("Locale")],
        "Timezone": ["timezone_screen", _("Timezone")],
        "User": ["user_screen", _("User")],
        "Desktops": ["de_screen", _("Desktops")],
        "Packages": ["packages_screen", _("Packages")],
        "Partitioning": ["partitioning_screen", _("Partitions")],
        "Summary": ["summary_screen", _("Summary")],
        "Install": ["install_screen", _("Install")],
        "Finish": ["finish_screen", _("Finish")],
    }


#    "Partitioning",

offline_pages_on_dev = [
    "Locale",
    "Keyboard",
    "Timezone",
    "User",
    "Summary",
    "Install",
    "Finish",
]
online_pages_on_dev = [
    "Locale",
    "Keyboard",
    "Timezone",
    "User",
    "Packages",
    "Desktops",
    "Summary",
    "Install",
    "Finish",
]
online_pages_from_iso = [
    "Locale",
    "Keyboard",
    "Timezone",
    "User",
    "Packages",
    "Desktops",
    "Partitioning",
    "Summary",
    "Install",
    "Finish",
]
offline_pages_from_iso = [
    "Locale",
    "Keyboard",
    "Timezone",
    "User",
    "Partitioning",
    "Summary",
    "Install",
    "Finish",
]

colors = [
    "color1",
    "color2",
    "color3",
    "color4",
    "color5",
    "color6",
    "color7",
    "color8",
    "color9",
    "color10",
    "color11",
    "color12",
    "color13",
    "color14",
    "color15",
]

sbcs = [
    "ArmSoM AIM7 ",
    "ArmSoM Sige7",
    "ArmSoM W3",
    "Banana Pi M7",
    "Embedfire LubanCat-4",
    "Firefly AIO-3588L MIPI101(Linux)",
    "Firefly ITX-3588J HDMI(Linux)",
    "FriendlyElec CM3588",
    "FriendlyElec NanoPC-T6",
    "FriendlyElec NanoPC-T6 LTS",
    "FriendlyElec NanoPi R6C",
    "FriendlyElec NanoPi R6S",
    "Fxblox RK1",
    "Fydetab Duo",
    "HINLINK H88K",
    "Indiedroid Nova",
    "Khadas Edge2",
    "Khadas VIM4",
    "Khadas VIM 4",
    "Mekotronics R58 MiniPC (RK3588 MINIPC LP4x V1.0 BlueBerry Board)",
    "Mekotronics R58X (RK3588 EDGE LP4x V1.0 BlueBerry Board)",
    "Mekotronics R58X-4G (RK3588 EDGE LP4x V1.2 BlueBerry Board)",
    "Mixtile Blade 3",
    "Mixtile Blade 3 v1.0.1",
    "Mixtile Core 3588E",
    "Milk-V Mars",
    "Orange Pi 5",
    "Orange Pi 5 Plus",
    "Orange Pi 5 Pro",
    "Orange Pi 5 Max",
    "Orange Pi 5 Ultra",
    "Orange Pi 5B",
    "Orange Pi CM5",
    "Orange Pi R2S",
    "Orange Pi RV",
    "Orange Pi RV2",
    "RK3588 CoolPi CM5 EVB Board",
    "RK3588 CoolPi CM5 NoteBook Board",
    "RK3588 EDGE LP4x V1.2 MeiZhuo BlueBerry Board",
    "RK3588 EDGE LP4x V1.4 BlueBerry Board",
    "RK3588 MINIPC-MIZHUO LP4x V1.0 BlueBerry Board",
    "RK3588S CoolPi 4B Board",
    "ROC-RK3588S-PC V12(Linux)",
    "Radxa Orion O6",
    "Radxa CM5 IO",
    "Radxa CM5 RPI CM4 IO",
    "Radxa NX5 IO",
    "Radxa NX5 Module",
    "Radxa ROCK 5 ITX",
    "Radxa ROCK 5A",
    "Radxa ROCK 5B",
    "Radxa ROCK 5B Plus",
    "Radxa ROCK 5C",
    "Radxa ROCK 5D",
    "Rockchip RK3588",
    "Rockchip RK3588 EVB1 LP4 V10 Board",
    "Rockchip RK3588 EVB1 LP4 V10 Board + DSI DSC PANEL MV2100UZ1 DISPLAY Ext Board",
    "Rockchip RK3588 EVB1 LP4 V10 Board + RK Ext HDMImale to eDP V10",
    "Rockchip RK3588 EVB1 LP4 V10 Board + RK HDMI to DP Ext Board",
    "Rockchip RK3588 EVB1 LP4 V10 Board + RK3588 EDP 8LANES V10 Ext Board",
    "Rockchip RK3588 EVB1 LP4 V10 Board + Rockchip RK3588 EVB V10 Extboard",
    "Rockchip RK3588 EVB1 LP4 V10 Board + Rockchip RK628 HDMI to MIPI Extboard",
    "Rockchip RK3588 EVB2 LP4 V10 Board",
    "Rockchip RK3588 EVB2 LP4 V10 eDP Board",
    "Rockchip RK3588 EVB2 LP4 V10 eDP to DP Board",
    "Rockchip RK3588 EVB3 LP5 V10 Board",
    "Rockchip RK3588 EVB3 LP5 V10 EDP Board",
    "Rockchip RK3588 EVB4 LP4 V10 Board",
    "Rockchip RK3588 EVB6 LP4 V10 Board",
    "Rockchip RK3588 EVB7 LP4 V10 Board",
    "Rockchip RK3588 EVB7 LP4 V11 Board",
    "Rockchip RK3588 EVB7 V11 Board",
    "Rockchip RK3588 EVB7 V11 Board + Rockchip RK628 HDMI to MIPI Extboard",
    "Rockchip RK3588 NVR DEMO LP4 SPI NAND Board",
    "Rockchip RK3588 NVR DEMO LP4 V10 Android Board",
    "Rockchip RK3588 NVR DEMO LP4 V10 Board",
    "Rockchip RK3588 NVR DEMO1 LP4 V21 Android Board",
    "Rockchip RK3588 NVR DEMO1 LP4 V21 Board",
    "Rockchip RK3588 NVR DEMO3 LP4 V10 Android Board",
    "Rockchip RK3588 NVR DEMO3 LP4 V10 Board",
    "Rockchip RK3588 PCIE EP Demo V11 Board",
    "Rockchip RK3588 TOYBRICK LP4 X10 Board",
    "Rockchip RK3588 TOYBRICK X10 Board",
    "Rockchip RK3588 VEHICLE EVB V10 Board",
    "Rockchip RK3588 VEHICLE EVB V20 Board",
    "Rockchip RK3588 VEHICLE EVB V21 Board",
    "Rockchip RK3588 VEHICLE EVB V22 Board",
    "Rockchip RK3588 VEHICLE S66 Board V10",
    "Rockchip RK3588-RK1608 EVB7 LP4 V10 Board",
    "Rockchip RK3588J",
    "Rockchip RK3588M",
    "Rockchip RK3588S",
    "Rockchip RK3588S EVB1 LP4X V10 Board",
    "Rockchip RK3588S EVB2 LP5 V10 Board",
    "Rockchip RK3588S EVB3 LP4 V10 Board + Rockchip RK3588S EVB V10 Extboard",
    "Rockchip RK3588S EVB3 LP4 V10 Board + Rockchip RK3588S EVB V10 Extboard1",
    "Rockchip RK3588S EVB3 LP4 V10 Board + Rockchip RK3588S EVB V10 Extboard2",
    "Rockchip RK3588S EVB3 LP4X V10 Board",
    "Rockchip RK3588S EVB4 LP4X V10 Board",
    "Rockchip RK3588S EVB8 LP4X V10 Board",
    "Rockchip RK3588S TABLET RK806 SINGLE Board",
    "Rockchip RK3588S TABLET V10 Board",
    "Rockchip RK3588S TABLET V11 Board",
    "Turing Machines RK1",
]

iso_packages_to_remove = [
    "bakery-device-tweaks",
    "bakery-gui",
    "bakery-tui",
    "bakery",
    "mkinitcpio-archiso",
    "mkinitcpio-nfs-utils",
]

dms = {
    "sddm": "sddm.service",
    "lightdm": "lightdm.service",
    "gdm": "gdm.service",
    "lxdm": "lxdm.service",
    "tdm": "tdm.service",
    "kdm": "kdm.service",
    "mdm": "mdm.service",
    "slim": "slim.service",
    "entrance": "entrance.service",
}
