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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib  # type: ignore


@time_fn
@Gtk.Template(resource_path="/org/bredos/bakery/ui/partitioning_screen.ui")
class partitioning_screen(Adw.Bin):
    __gtype_name__ = "partitioning_screen"

    sys_type: Gtk.Label = Gtk.Template.Child()
    part_table: Gtk.Label = Gtk.Template.Child()
    disk_list: Gtk.DropDown = Gtk.Template.Child()
    big_grid: Gtk.Grid = Gtk.Template.Child()
    after_label: Gtk.Label = Gtk.Template.Child()
    erase_all: Gtk.CheckButton = Gtk.Template.Child()
    manual_part: Gtk.CheckButton = Gtk.Template.Child()
    replace_part: Gtk.CheckButton = Gtk.Template.Child()
    encrypt: Gtk.CheckButton = Gtk.Template.Child()
    info_label: Gtk.Label = Gtk.Template.Child()
    guided_partitioning: Gtk.Button = Gtk.Template.Child()
    manual_partitioning: Gtk.Button = Gtk.Template.Child()
    term_button: Gtk.Button = Gtk.Template.Child()
    gparted_button: Gtk.Button = Gtk.Template.Child()
    stack: Gtk.Stack = Gtk.Template.Child()
    parts_group: Adw.PreferencesGroup = Gtk.Template.Child()
    refresh_parts: Gtk.Button = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.disk_list.connect("notify::selected-item", self.on_disk_selected)
        self.erase_all.connect("toggled", self.on_partitioning_type)
        self.manual_part.connect("toggled", self.on_partitioning_type)
        self.replace_part.connect("toggled", self.on_partitioning_type)
        self.selected_partition = None
        self.selectable = False
        self.selected_mode = None
        self.selected_mode_view = "guided"
        self.available_parts_box = None
        self.stack.set_visible_child_name("guided")
        self.guided_partitioning.set_visible(False)
        self.manual_partitioning.set_visible(True)

        self.manual_partitioning.connect("clicked", self.on_manual_partitioning_clicked)
        self.guided_partitioning.connect("clicked", self.on_guided_partitioning_clicked)

        self.term_button.connect("clicked", self.on_term_button_clicked)
        self.gparted_button.connect("clicked", self.on_gparted_button_clicked)
        self.refresh_parts.connect("clicked", self.refresh_parts_clicked)

        self.selection = {}

        self.is_efi = check_efi()
        self.device = detect_install_device()
        if self.is_efi:
            self.sys_type.set_label(
                _("System type: ") + "UEFI"
            )  # pyright: ignore[reportCallIssue]
        else:
            self.sys_type.set_label(
                _("System type: ") + "BIOS"
            )  # pyright: ignore[reportCallIssue]
        self.first_run = True
        self.new_first_run = True

        self.disk_model = Gtk.StringList()
        self.disk_list.set_model(self.disk_model)
        self.disks = list_drives()
        self.disk = list(self.disks.keys())[0]
        self.all_partitions = get_partitions()
        for disk in self.disks:
            self.disk_model.append(disk + ": " + self.disks[disk])
        partition_table = check_partition_table(self.disk)
        self.part_table.set_label(
            _("Partition table: ") + str(partition_table)
        )  # pyright: ignore[reportCallIssue]
        self.partitions = {}
        self.partitions[self.disk] = self.all_partitions[self.disk]
        self.populate_available_parts(self.partitions)
        self.populate_disk_preview(self.partitions)

    def validate_selection(self) -> bool:
        # Need atleast 1 / that is either ext4 or btrfs
        # If also Need atleast 1 /boot/efi that is either fat32
        # Else need atleast 1 /boot that is either fat32E
        root_found = False
        boot_found = False
        if self.selected_mode_view == "manual":
            for part, details in self.selection.items():
                fs = details["fs"]
                mp = details["mp"]

                # Check for root (/) partition with ext4 or btrfs
                if mp == "Use as root" and fs in ("ext4", "btrfs"):
                    root_found = True
                if mp == "Use as boot" and fs == "fat32":
                    boot_found = True

            if root_found and boot_found:
                return True
        elif self.selected_mode_view == "guided":
            if self.selected_mode == "erase_all":
                return True
        return False

    def refresh_parts_clicked(self, button) -> None:
        self.populate_available_parts(self.partitions)
        self.populate_disk_preview(self.partitions)

    def on_term_button_clicked(self, button) -> None:
        # List of common terminal applications to try
        terminals = [
            "gnome-terminal",
            "konsole",
            "xfce4-terminal",
            "mate-terminal",
            "terminator",
            "tilix",
            "alacritty",
            "kitty",
            "xterm",
            "kgx",  # GNOME Console
        ]

        # Try each terminal until one works
        for terminal in terminals:
            try:
                lrun([terminal], wait=False, force=True)
                return
            except:
                continue

    def on_gparted_button_clicked(self, button) -> None:
        lrun(["gparted"], wait=False, force=True)

    def on_guided_partitioning_clicked(self, button) -> None:
        self.selected_mode_view = "guided"
        self.stack.set_visible_child_name("guided")
        self.manual_partitioning.set_visible(True)
        self.guided_partitioning.set_visible(False)

    def on_manual_partitioning_clicked(self, button) -> None:
        self.selected_mode_view = "manual"
        self.stack.set_visible_child_name("manual")
        self.manual_partitioning.set_visible(False)
        self.guided_partitioning.set_visible(True)

    @time_fn
    def populate_available_parts(self, partitions) -> None:
        # For each partition, create a PartitionRow
        self.selection = {}
        if self.available_parts_box is not None:
            self.parts_group.remove(self.available_parts_box)
            self.available_parts_box = Adw.PreferencesGroup()
        else:
            self.available_parts_box = Adw.PreferencesGroup()
        for idx, partition in enumerate(partitions[list(partitions.keys())[0]]):
            for name, details in partition.items():
                size, _, _, fstype = details
                # get the number of the partition from the dicts keys number
                size_str = f"{size:.2f} MB" if size < 1024 else f"{size / 1024:.2f} GB"
                row = PartitionRow(
                    partition,
                    name,
                    size_str,
                    size,
                    self.selection,
                    self.available_parts_box,
                )
                self.available_parts_box.add(row)
        self.parts_group.add(self.available_parts_box)

    @time_fn
    def populate_disk_preview(self, partitions, new=False) -> None:
        if not new and self.first_run:
            self.first_run = False
            self.parts_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            self.legend_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            self.big_grid.attach(self.parts_box, 1, 0, 1, 1)
            self.big_grid.attach(self.legend_box, 1, 1, 1, 1)
            self.legend_box.set_halign(Gtk.Align.CENTER)
        elif not new and not self.first_run:
            self.big_grid.remove(self.parts_box)
            self.big_grid.remove(self.legend_box)
            self.legend_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            self.parts_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            self.big_grid.attach(self.parts_box, 1, 0, 1, 1)
            self.big_grid.attach(self.legend_box, 1, 1, 1, 1)
            self.legend_box.set_halign(Gtk.Align.CENTER)
        if new and self.new_first_run:
            self.after_label.set_visible(True)
            self.new_first_run = False
            self.new_legend_box = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=5
            )
            self.new_parts_box = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=0
            )
            self.big_grid.attach(self.new_parts_box, 1, 2, 1, 1)
            self.big_grid.attach(self.new_legend_box, 1, 3, 1, 1)
            self.new_legend_box.set_halign(Gtk.Align.CENTER)
        elif new and not self.new_first_run:
            self.big_grid.remove(self.new_parts_box)
            self.big_grid.remove(self.new_legend_box)
            self.new_parts_box = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=0
            )
            self.new_legend_box = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=5
            )
            self.big_grid.attach(self.new_parts_box, 1, 2, 1, 1)
            self.big_grid.attach(self.new_legend_box, 1, 3, 1, 1)
            self.new_legend_box.set_halign(Gtk.Align.CENTER)

        total_size = sum(
            partition[next(iter(partition))][0]
            for partition in partitions[list(partitions.keys())[0]]
        )

        sizes = []
        for partition in partitions[list(partitions.keys())[0]]:
            for name, details in partition.items():
                size, _, _, fstype = details
                literal_size = int((size / total_size) * 650)
                sizes.append(literal_size)

        min_size = 20
        total_allocated = sum(sizes)
        adjusted_sizes = []
        adjustment_needed = 650 - total_allocated

        for size in sizes:
            if size < min_size:
                adjustment_needed -= min_size - size
                adjusted_sizes.append(min_size)
            else:
                adjusted_sizes.append(size)

        if adjustment_needed != 0:
            proportion_total = sum(size for size in adjusted_sizes if size >= min_size)
            for i in range(len(adjusted_sizes)):
                if adjusted_sizes[i] >= min_size:
                    adjusted_sizes[i] += int(
                        adjustment_needed * (adjusted_sizes[i] / proportion_total)
                    )

        final_total = sum(adjusted_sizes)
        if final_total != 650:
            difference = 650 - final_total
            adjusted_sizes[-1] += difference

        for idx, partition in enumerate(partitions[list(partitions.keys())[0]]):
            for name, details in partition.items():
                size, _, _, fstype = details
                is_first = idx == 0
                is_last = idx == len(partitions[list(partitions.keys())[0]]) - 1
                literal_size = adjusted_sizes[idx]
                partition_box = self.make_part_box(
                    literal_size,
                    config.colors[idx % len(config.colors)],
                    idx,
                    is_first,
                    is_last,
                    selectable=(not new),
                )
                leg_box = self.make_legend_box(
                    name, size, fstype, config.colors[idx % len(config.colors)]
                )

                if not new:
                    self.parts_box.append(partition_box)
                    self.legend_box.append(leg_box)
                    self.parts_box.set_size_request(650, 35)
                else:
                    self.new_parts_box.append(partition_box)
                    self.new_legend_box.append(leg_box)
                    self.new_parts_box.set_size_request(650, 35)

    def make_part_box(
        self, size, color, part_num, first=False, last=False, selectable=True
    ) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_size_request(int(size), 35)

        box.add_css_class("partition-box")
        box.add_css_class(color)

        if first:
            box.add_css_class("first-partition")
        if last:
            box.add_css_class("last-partition")

        # Add click gesture for selection
        if selectable:
            gesture = Gtk.GestureClick.new()
            gesture.connect("pressed", self.on_partition_box_clicked, box)
            box.add_controller(gesture)

        box.part_num = part_num

        return box

    def make_legend_box(self, name, real_size, fstype, color) -> Gtk.Box:
        # size is in mb if size is less than 1024mb show in mb else in gb

        if real_size < 1024:
            size_str = f"{real_size:.2f} MB"
        else:
            size_str = f"{real_size / 1024:.2f} GB"

        size_label = Gtk.Label(
            label=f'<span foreground="white">{size_str}</span>'
        )  # Set color to 'white'
        size_label.set_xalign(0)
        size_label.set_use_markup(True)
        try:
            name = name.split("/dev/")[1]
        except:
            pass
        label = Gtk.Label(
            label=f'<span foreground="white">{name}</span>'
        )  # Set color to 'white'
        label.set_xalign(0)
        label.set_use_markup(True)

        fstype_label = Gtk.Label(
            label=f'<span foreground="white">{fstype if fstype else "Unknown"}</span>'
        )
        fstype_label.set_xalign(0)
        fstype_label.set_use_markup(True)

        color_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        color_box.set_size_request(16, 16)
        color_box.add_css_class(color)
        # center the color box
        color_box.set_halign(Gtk.Align.CENTER)
        # dont vertically expand the color box
        color_box.set_valign(Gtk.Align.CENTER)
        legend_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        legend_box.append(color_box)
        labels_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        labels_box.set_valign(Gtk.Align.CENTER)
        labels_box.append(label)
        labels_box.append(size_label)
        labels_box.append(fstype_label)
        legend_box.append(labels_box)
        return legend_box

    def on_disk_selected(self, dropdown, *_) -> None:
        selected = dropdown.props.selected_item
        if selected is not None:
            self.disk = selected.props.string.split(":")[0]
            self.part_table.set_label(
                "Partition table: " + str(check_partition_table(self.disk))
            )
            self.partitions = {}
            self.partitions[self.disk] = self.all_partitions[self.disk]
            self.populate_available_parts(self.partitions)
            self.populate_disk_preview(self.partitions)
            if self.selected_mode is not None:
                self.set_mode(self.selected_mode)

    def set_mode(self, mode):
        self.selected_mode = mode
        if self.selected_partition is not None:
            self.selected_partition.remove_css_class("selected")
        if mode == "erase_all":
            self.selectable = False
            self.info_label.set_label(
                "A new 256MB EFI partition will be created and the rest will be used for BredOS"
            )
            self.new_partitions = gen_new_partitions(self.partitions, "erase_all")
            self.populate_disk_preview(self.new_partitions, new=True)
        elif mode == "manual_part":
            self.info_label.set_label(
                "This will allow you to manually partition the disk"
            )
        elif mode == "replace_part":
            self.info_label.set_label(
                "This will replace the current partitions on the disk"
            )
            self.selectable = True
            self.populate_disk_preview(self.partitions, new=True)

    def on_partitioning_type(self, radio, *_) -> None:
        if radio is self.erase_all:
            self.set_mode("erase_all")
        elif radio is self.manual_part:
            self.set_mode("manual_part")
        elif radio is self.replace_part:
            self.set_mode("replace_part")

    def on_partition_box_clicked(self, gesture, n_press, x, y, box):
        if self.selected_partition is not None:
            # Remove the selection style from the previously selected partition
            self.selected_partition.remove_css_class("selected")

        if self.selectable:
            # Set the clicked box as the selected partition
            self.selected_partition = box
            # Add a selection style to the clicked box
            box.add_css_class("selected")
            print(self.partitions)
            self.new_partitions = gen_new_partitions(
                self.partitions, "replace", self.selected_partition.part_num
            )
            print(self.new_partitions)
            self.populate_disk_preview(self.new_partitions, new=True)

    def collect_data(self) -> dict:
        data = {}
        data["type"] = self.selected_mode_view
        data["efi"] = self.is_efi
        if self.selected_mode_view == "manual":
            data["disk"] = self.disk
            data["partitions"] = self.selection
        else:
            data["disk"] = self.disk
            data["mode"] = self.selected_mode
            try:
                data["partitions"] = self.new_partitions
            except AttributeError:
                data["partitions"] = None
        return data


class PartitionRow(Adw.ActionRow):
    def __init__(
        self,
        part: dict,
        part_name: str,
        size_str: str,
        size: int,
        selection: dict,
        available_parts_box,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.partition_info = part
        self.part_name = part_name
        self.size = size_str
        self.available_parts_box = available_parts_box
        self.selection = selection
        self.set_title(part_name)
        self.set_subtitle(size_str)
        self.set_icon_name("drive-harddisk")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        fs_dropdown = Gtk.DropDown()
        fs_dropdown.set_valign(Gtk.Align.CENTER)
        fs_model = Gtk.StringList()
        fs_dropdown.set_model(fs_model)

        mp_dropdown = Gtk.DropDown()
        mp_dropdown.set_valign(Gtk.Align.CENTER)
        mp_model = Gtk.StringList()
        mp_dropdown.set_model(mp_model)

        mp_model.append("Do not use")
        fs_model.append("Don't format")

        if size < 50:
            # Can't use this partition due to size
            sleep(0.01)
        elif size < 4000:
            mp_model.append("Use as boot")
            fs_model.append("fat32")
        else:
            mp_model.append("Use as root")
            mp_model.append("Use as home")
            fs_model.append("ext4")
            fs_model.append("btrfs")

        box.append(fs_dropdown)
        box.append(mp_dropdown)
        self.add_suffix(box)

        mp_dropdown.connect("notify::selected-item", self.on_mp_changed)
        fs_dropdown.connect("notify::selected-item", self.on_fs_changed)

    def change_selection(self, key: Any, value: Any):
        if not self.part_name in self.selection:
            self.selection[self.part_name] = {"fs": None, "mp": None}
        self.selection[self.part_name][key] = value

    def on_fs_changed(self, dropdown, *_):
        selected = dropdown.props.selected_item
        if selected is not None:
            self.fs = selected.props.string
            self.change_selection("fs", self.fs)

    def on_mp_changed(self, dropdown, *_):
        selected = dropdown.props.selected_item
        if selected is not None:
            mountpoint = selected.props.string

            # Check if another partition is already using this mountpoint
            for part, sel in self.selection.items():
                if (
                    part != self.part_name
                    and sel["mp"] == mountpoint
                    and mountpoint != "Do not use"
                ):
                    # If mountpoint is already used, show an error or reset dropdown
                    self.available_parts_box.set_title(
                        f"Error: Mountpoint '{mountpoint}' is already used by '{part}'"
                    )
                    dropdown.set_selected(0)  # Reset to "Do not use"
                    return

            # Otherwise, apply the mountpoint selection
            self.mp = mountpoint
            self.change_selection("mp", self.mp)
