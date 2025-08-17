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


@Gtk.Template(resource_path="/org/bredos/bakery/ui/packages_screen.ui")
class packages_screen(Gtk.Box):
    __gtype_name__ = "packages_screen"
    packages_box = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window

        # Get current architecture
        self.current_arch = platform.machine()

        # Load packages data
        self.packages = get_packages_list()

        # State tracking
        self.selection_state = {}  # key -> bool (selected state)
        self.checkboxes = {}  # key -> Gtk.CheckButton
        self.group_hierarchy = (
            {}
        )  # group_key -> {"packages": [pkg_keys], "subgroups": [grp_keys]}
        self.parent_map = {}  # child_key -> parent_key
        self._updating = False  # prevent signal loops during programmatic updates

        # Package tracking
        self.package_metadata = {}  # pkg_key -> {"name": str, "post_install": str}
        self.group_metadata = {}  # grp_key -> {"post_install": str}

        # UI state
        self.current_category = None
        self.filtered_packages = []

        # Select all default packages before building UI
        self.select_all_default_packages()
        # Build and show UI
        self.build_ui()
        GLib.idle_add(appstream_initialize)

    def escape_html(self, s, quote=True):
        """
        Replace special characters "&", "<" and ">" to HTML-safe sequences.
        If the optional flag quote is true (the default), the quotation mark
        characters, both double quote (") and single quote (') characters are also
        translated.
        """
        s = s.replace("&", "&amp;")  # Must be done first!
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
        if quote:
            s = s.replace('"', "&quot;")
            s = s.replace("'", "&#x27;")
        return s

    def build_categories_panel(self):
        """Build and return the left panel with categories and search"""
        # Create left panel container
        left_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, spacing=12)
        set_margins(left_box, 12, 6, 12, 6)
        left_box.set_size_request(280, -1)

        # Categories header row (label + button)
        header_row = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing=8)
        categories_label = Gtk.Label.new("Categories")
        categories_label.set_halign(Gtk.Align.START)
        categories_label.add_css_class("title-2")
        header_row.append(categories_label)

        reset_btn = Gtk.Button.new_with_label("Reset selection")
        reset_btn.add_css_class("suggested-action")
        reset_btn.set_halign(Gtk.Align.END)
        reset_btn.set_valign(Gtk.Align.CENTER)
        reset_btn.set_tooltip_text("Reset all selections to default")
        reset_btn.set_hexpand(True)
        reset_btn.connect("clicked", self.on_default_selections)
        header_row.append(reset_btn)

        left_box.append(header_row)

        # Search entry
        self.search_entry = Gtk.SearchEntry.new()
        self.search_entry.set_placeholder_text("Search applications and categories...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        left_box.append(self.search_entry)

        # Categories list in scrolled window
        categories_scrolled = Gtk.ScrolledWindow()
        categories_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        categories_scrolled.set_vexpand(True)
        left_box.append(categories_scrolled)

        # Categories list box
        self.categories_list = Gtk.ListBox.new()
        self.categories_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.categories_list.add_css_class("navigation-sidebar")
        self.categories_list.connect("row-selected", self.on_category_selected)
        categories_scrolled.set_child(self.categories_list)

        # Populate categories
        self.populate_categories()

        return left_box

    def build_applications_panel(self):
        """Build and return the right panel for application selection"""
        # Create right panel container
        right_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, spacing=12)
        set_margins(right_box, 12, 6, 12, 6)
        right_box.set_hexpand(True)
        right_box.set_vexpand(True)

        # Applications header
        self.applications_label = Gtk.Label.new("Select Applications")
        self.applications_label.set_halign(Gtk.Align.START)
        self.applications_label.add_css_class("title-2")
        right_box.append(self.applications_label)

        # Applications description (dimmed)
        self.category_desc_label = None  # Initialize here
        # Applications list in scrolled window
        apps_scrolled = Gtk.ScrolledWindow()
        apps_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        apps_scrolled.set_vexpand(True)
        right_box.append(apps_scrolled)

        # Applications list box
        self.applications_list = Gtk.ListBox.new()
        self.applications_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.applications_list.add_css_class("boxed-list")
        self.applications_list.set_valign(Gtk.Align.START)
        apps_scrolled.set_child(self.applications_list)

        return right_box

    def populate_categories(self):
        """Populate the categories list"""
        self.show_selected_applications_category()
        groups = self.packages if isinstance(self.packages, list) else [self.packages]
        for grp_data in groups:
            if self.is_valid_group(grp_data) and self.is_arch_compatible(grp_data):
                self.add_category_row(grp_data, [])

    def add_category_row(self, group_data, parent_path, depth=0):
        """Add a category row to the categories list"""
        name = group_data.get("name", "Unnamed")
        current_path = parent_path + [name]
        group_key = self.make_group_key(current_path)

        row = Gtk.ListBoxRow.new()
        row.group_data = group_data
        row.group_key = group_key
        row.depth = depth

        row_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing=8)
        set_margins(row_box, 8 + (depth * 16), 8, 8, 8)

        icon_name = group_data.get("icon")
        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_icon_size(Gtk.IconSize.NORMAL)
            row_box.append(icon)

        title_label = Gtk.Label.new(name)
        title_label.set_wrap(True)
        title_label.set_max_width_chars(24)
        title_label.set_ellipsize(Pango.EllipsizeMode.NONE)
        row_box.append(title_label)

        # Show expand arrow as a flat button if this group/subgroup has subgroups
        subgroups = group_data.get("subgroups", [])
        has_subgroups = any(
            self.is_valid_group(sg) and self.is_arch_compatible(sg) for sg in subgroups
        )
        if has_subgroups:
            arrow_icon = Gtk.Image.new_from_icon_name("go-next-symbolic")
            arrow_icon.set_icon_size(Gtk.IconSize.NORMAL)
            arrow_btn = Gtk.Button.new()
            arrow_btn.set_child(arrow_icon)
            arrow_btn.add_css_class("flat")
            arrow_btn.set_focusable(False)
            row_box.append(arrow_btn)
            row.has_subgroups = True
            row.expanded = False

            def on_arrow_clicked(
                btn, row=row, group_data=group_data, depth=depth, arrow_icon=arrow_icon
            ):
                if getattr(row, "expanded", False):
                    self.collapse_category(row)
                    arrow_icon.set_from_icon_name("go-next-symbolic")
                else:
                    self.expand_category(row, group_data, depth)
                    arrow_icon.set_from_icon_name("go-down-symbolic")

            arrow_btn.connect("clicked", on_arrow_clicked)

        row.set_child(row_box)
        self.categories_list.append(row)

        self.group_hierarchy[group_key] = {"packages": [], "subgroups": []}

        packages = group_data.get("packages", [])
        for pkg_data in packages:
            if self.is_valid_package(pkg_data) and self.is_arch_compatible(pkg_data):
                self.create_package_key(pkg_data, current_path, group_key)

    def create_package_key(self, pkg_data, parent_path, group_key):
        """Create package key and store metadata"""
        if isinstance(pkg_data, str):
            name = pkg_data
            post_install = None
        else:
            name = pkg_data.get("name", "")
            post_install = pkg_data.get("post-install")

        pkg_key = self.make_package_key(parent_path, name)

        # Store package metadata
        self.package_metadata[pkg_key] = {
            "name": name,
            "post_install": post_install,
            "data": pkg_data,
        }

        # Add to group hierarchy
        self.group_hierarchy[group_key]["packages"].append(pkg_key)
        self.parent_map[pkg_key] = group_key

        return pkg_key

    def on_category_selected(self, list_box, row):
        """Handle category selection and expansion logic"""
        if not row:
            return

        group_data = getattr(row, "group_data", None)
        group_key = getattr(row, "group_key", None)
        has_subgroups = getattr(row, "has_subgroups", False)
        depth = getattr(row, "depth", 0)

        # Check if category is empty (no packages and no valid subgroups after arch filtering)
        packages = (
            group_data.get("packages", []) if isinstance(group_data, dict) else []
        )
        has_packages = any(
            self.is_valid_package(pkg) and self.is_arch_compatible(pkg)
            for pkg in packages
        )
        subgroups = (
            group_data.get("subgroups", []) if isinstance(group_data, dict) else []
        )
        has_valid_subgroups = any(
            self.is_valid_group(sg) and self.is_arch_compatible(sg) for sg in subgroups
        )
        if not has_packages and not has_valid_subgroups:
            return  # Do nothing if category is truly empty

        # Pre-select children if group/subgroup is selected
        if isinstance(group_data, dict) and group_data.get("selected", False):
            self.select_group_and_children(group_data, group_key)

        # If it has subgroups, expand always
        if has_subgroups:
            if not getattr(row, "expanded", False):
                self.expand_category(row, group_data, depth)
            # Only select and show packages if there are packages
            if has_packages:
                self.categories_list.select_row(row)
                self.show_category_packages(group_data, group_key)
        else:
            self.categories_list.select_row(row)
            self.show_category_packages(group_data, group_key)

    def select_group_and_children(self, group_data, group_key):
        """Recursively select group/subgroup and its children packages/subgroups"""
        selected = group_data.get("selected")
        if selected is False:
            return  #

        self.selection_state[group_key] = True
        packages = group_data.get("packages", [])
        for pkg_data in packages:
            if self.is_valid_package(pkg_data) and self.is_arch_compatible(pkg_data):
                if isinstance(pkg_data, dict):
                    pkg_name = pkg_data.get("name", "")
                else:
                    pkg_name = pkg_data
                pkg_key = f"pkg:{group_key}/{pkg_name}"
                self.selection_state[pkg_key] = True
                checkbox = self.checkboxes.get(pkg_key)
                if checkbox:
                    checkbox.set_active(True)

        # Recurse into subgroups
        subgroups = group_data.get("subgroups", [])
        for sg in subgroups:
            if self.is_valid_group(sg) and self.is_arch_compatible(sg):
                sg_name = sg.get("name", "Unnamed")
                sg_key = f"grp:{'/'.join(group_key.split('/')[1:] + [sg_name])}"
                self.select_group_and_children(sg, sg_key)

    def expand_category(self, row, group_data, depth):
        """Expand category to show subgroups (arrow down)"""
        row.expanded = True
        row_box = row.get_child()
        children = []
        child = row_box.get_first_child()
        while child:
            children.append(child)
            child = child.get_next_sibling()
        if children and isinstance(children[-1], Gtk.Image):
            children[-1].set_from_icon_name("go-down-symbolic")
        row_index = self.get_row_index(row)
        subgroups = group_data.get("subgroups", [])
        parent_path = group_data.get("name", "").split("/")
        for i, sub_data in enumerate(subgroups):
            if self.is_valid_group(sub_data) and self.is_arch_compatible(sub_data):
                self.insert_category_row(
                    sub_data, parent_path, depth + 1, row_index + i + 1
                )

    def collapse_category(self, row):
        """Collapse category to hide subgroups (arrow right)"""
        row.expanded = False
        row_box = row.get_child()
        children = []
        child = row_box.get_first_child()
        while child:
            children.append(child)
            child = child.get_next_sibling()
        if children and isinstance(children[-1], Gtk.Image):
            children[-1].set_from_icon_name("go-next-symbolic")
        self.remove_subgroup_rows(row)

    def insert_category_row(self, group_data, parent_path, depth, index):
        """Insert a category row at specific index"""
        name = group_data.get("name", "Unnamed")
        current_path = parent_path + [name]
        group_key = self.make_group_key(current_path)
        row = Gtk.ListBoxRow.new()
        row.group_data = group_data
        row.group_key = group_key
        row.depth = depth
        row.is_subgroup = True
        row_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing=8)
        set_margins(row_box, 8 + (depth * 16), 8, 8, 8)
        icon_name = group_data.get("icon")
        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_icon_size(Gtk.IconSize.NORMAL)
            row_box.append(icon)
        label = Gtk.Label.new(name)
        label.set_wrap(True)  # <-- Use set_wrap for GTK4
        label.set_max_width_chars(24)
        label.set_ellipsize(Pango.EllipsizeMode.NONE)
        row_box.append(label)
        # Show expand arrow as a flat button if this subgroup has subgroups
        subgroups = group_data.get("subgroups", [])
        has_subgroups = any(
            self.is_valid_group(sg) and self.is_arch_compatible(sg) for sg in subgroups
        )
        if has_subgroups:
            arrow_icon = Gtk.Image.new_from_icon_name("go-next-symbolic")
            arrow_icon.set_icon_size(Gtk.IconSize.NORMAL)
            arrow_btn = Gtk.Button.new()
            arrow_btn.set_child(arrow_icon)
            arrow_btn.add_css_class("flat")
            arrow_btn.set_focusable(False)
            row_box.append(arrow_btn)
            row.has_subgroups = True
            row.expanded = False

            def on_arrow_clicked(
                btn, row=row, group_data=group_data, depth=depth, arrow_icon=arrow_icon
            ):
                if getattr(row, "expanded", False):
                    self.collapse_category(row)
                    arrow_icon.set_from_icon_name("go-next-symbolic")
                else:
                    self.expand_category(row, group_data, depth)
                    arrow_icon.set_from_icon_name("go-down-symbolic")

            arrow_btn.connect("clicked", on_arrow_clicked)
        row.set_child(row_box)
        self.categories_list.insert(row, index)

    def get_row_index(self, target_row):
        """Get the index of a row in the list"""
        index = 0
        row = self.categories_list.get_row_at_index(0)
        while row:
            if row == target_row:
                return index
            index += 1
            row = self.categories_list.get_row_at_index(index)
        return -1

    def remove_subgroup_rows(self, parent_row):
        """Remove all subgroup rows after the parent"""
        parent_index = self.get_row_index(parent_row)
        if parent_index == -1:
            return

        rows_to_remove = []
        index = parent_index + 1
        row = self.categories_list.get_row_at_index(index)

        # Use Python attribute instead of get_data
        while row and getattr(row, "is_subgroup", False):
            rows_to_remove.append(row)
            index += 1
            row = self.categories_list.get_row_at_index(index)

        for row in rows_to_remove:
            self.categories_list.remove(row)

    def show_category_packages(self, group_data, group_key):
        """Show only packages for the selected group/subgroup"""
        self.current_category = group_key
        category_name = group_data.get("name", "Category")
        self.applications_label.set_text(f"Select Applications - {category_name}")

        # Remove any previous description label if present
        if hasattr(self, "category_desc_label") and self.category_desc_label:
            parent = self.category_desc_label.get_parent()
            if parent:
                parent.remove(self.category_desc_label)
            self.category_desc_label = None

        # Add category description label under header, dimmed
        description = group_data.get("description", "")
        if description:
            desc_label = Gtk.Label.new(description)
            set_margins(desc_label, 0, 0, 0, 8)
            desc_label.set_halign(Gtk.Align.START)
            desc_label.set_wrap(True)
            desc_label.set_wrap_mode(Pango.WrapMode.WORD)
            desc_label.set_ellipsize(Pango.EllipsizeMode.NONE)
            desc_label.add_css_class("dim-label")
            right_panel = self.applications_label.get_parent()
            if right_panel:
                right_panel.insert_child_after(desc_label, self.applications_label)
            self.category_desc_label = desc_label

        # Clear current applications list
        child = self.applications_list.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.applications_list.remove(child)
            child = next_child

        # Show only packages for this group/subgroup
        packages = group_data.get("packages", [])
        for pkg_data in packages:
            # --- For Selected Applications category, always tick selected ---
            if group_key == "grp:selected":
                # Find the key for this package
                if isinstance(pkg_data, dict):
                    pkg_name = pkg_data.get("name", pkg_data.get("pkgname", ""))
                    # Try both normal and appstream keys
                    pkg_key = f"pkg:{pkg_name}"
                    # Find the actual key in selection_state
                    found_key = None
                    for k in self.selection_state:
                        if k.endswith(f"/{pkg_name}") or k.endswith(
                            f"/{pkg_data.get('pkgname', '')}"
                        ):
                            found_key = k
                            break
                    if found_key:
                        self.selection_state[found_key] = True
                elif isinstance(pkg_data, str):
                    pkg_key = None
                    for k in self.selection_state:
                        if k.endswith(f"/{pkg_data}"):
                            pkg_key = k
                            break
                    if pkg_key:
                        self.selection_state[pkg_key] = True
            # ...existing code...
            if self.is_valid_package(pkg_data) and self.is_arch_compatible(pkg_data):
                pkg_row = self.create_application_row(pkg_data, group_key)
                if pkg_row:
                    # Attach metadata for AppStream/Flatpak rows
                    if isinstance(pkg_data, dict) and pkg_data.get("appstream"):
                        pkg_key = f"pkg:appstream/{pkg_data.get('pkgname', pkg_data.get('name', ''))}"
                        self.package_metadata[pkg_key] = pkg_data
                        # Attach metadata to checkbox for reliable retrieval
                        checkbox = pkg_row.get_last_child()
                        if checkbox:
                            checkbox.row_data = pkg_data
                    self.applications_list.append(pkg_row)

    def build_ui(self):
        lp("Building two-panel package selection UI", "info")

        # Create main horizontal box container
        main_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing=5)
        main_box.set_hexpand(True)
        main_box.set_vexpand(True)
        self.packages_box.append(main_box)

        # Left panel - Categories
        left_box = self.build_categories_panel()
        left_box.set_hexpand(False)
        left_box.set_size_request(280, -1)  # Fixed width for categories panel
        main_box.append(left_box)

        # Separator
        separator = Gtk.Separator.new(Gtk.Orientation.VERTICAL)
        separator.set_vexpand(True)
        main_box.append(separator)

        # Right panel - Applications
        right_box = self.build_applications_panel()
        main_box.append(right_box)

        # Remove self._select_first_category()
        # Instead, show instructions in applications panel
        instruction_label = Gtk.Label.new(
            "Select a category on the left to view and choose applications.\n"
            "You can also search for packages or categories using the search box."
        )
        instruction_label.set_halign(Gtk.Align.CENTER)
        instruction_label.set_valign(Gtk.Align.CENTER)
        instruction_label.set_margin_top(24)
        instruction_label.set_margin_bottom(24)
        instruction_label.add_css_class("dim-label")
        self.applications_list.append(instruction_label)

    def init_all_package_checkboxes(self):
        """Create checkboxes for all packages in all groups/subgroups so their state can be set"""

        def recurse(groups, parent_path):
            for grp_data in groups:
                if not (
                    self.is_valid_group(grp_data) and self.is_arch_compatible(grp_data)
                ):
                    continue
                name = grp_data.get("name", "Unnamed")
                current_path = parent_path + [name]
                group_key = self.make_group_key(current_path)
                packages = grp_data.get("packages", [])
                for pkg_data in packages:
                    if self.is_valid_package(pkg_data) and self.is_arch_compatible(
                        pkg_data
                    ):
                        pkg_key = self.create_package_key(
                            pkg_data, current_path, group_key
                        )
                        # Create a dummy checkbox for each package so apply_default_selections can set its state
                        if pkg_key not in self.checkboxes:
                            checkbox = Gtk.CheckButton.new()
                            self.checkboxes[pkg_key] = checkbox
                subgroups = grp_data.get("subgroups", [])
                if subgroups:
                    recurse(subgroups, current_path)

        groups = self.packages if isinstance(self.packages, list) else [self.packages]
        recurse(groups, [])

    def create_application_row(self, pkg_data, group_key):
        """Create an application row for the right panel"""
        # Normalize package data
        if isinstance(pkg_data, str):
            name = pkg_data
            description = ""
            selected = False
            immutable = False
            icon_name = None
            is_appstream = False
            pkg_key = f"pkg:{group_key}/{name}"
            origin = None
        else:
            name = pkg_data.get("name", "")
            description = pkg_data.get("description", "")
            selected = pkg_data.get("selected", False)
            immutable = pkg_data.get("immutable", False) or pkg_data.get(
                "critical", False
            )
            icon_name = pkg_data.get("icon")
            is_appstream = pkg_data.get("appstream", False)
            origin = pkg_data.get("origin")
            # For AppStream results, use pkgname for key uniqueness
            if is_appstream:
                pkg_key = f"pkg:appstream/{pkg_data.get('pkgname', name)}"
            else:
                pkg_key = f"pkg:{group_key}/{name}"

        if not name:
            return None

        if pkg_key not in self.selection_state:
            self.selection_state[pkg_key] = selected

        action_row = Adw.ActionRow.new()
        # --- Show Flatpak or ArchLinux origin in title ---
        display_name = name
        if is_appstream and origin == "flatpak":
            display_name = f"{name} - Flatpak"
        elif origin and str(origin).startswith("archlinux-arch-"):
            display_name = f"{name} - ArchLinux Repositories"
        action_row.set_title(display_name)
        if description:
            safe_description = self.escape_html(description)
            action_row.set_subtitle(safe_description)
        # Show icon if available
        if icon_name:
            # Fix: handle tuple icons from AppStream
            if isinstance(icon_name, tuple):
                icon_name = icon_name[0] if icon_name else None
            if isinstance(icon_name, str) and icon_name and path.isfile(icon_name):
                icon_widget = Gtk.Image.new_from_file(icon_name)
                icon_widget.set_icon_size(Gtk.IconSize.NORMAL)
                action_row.add_prefix(icon_widget)

        checkbox = Gtk.CheckButton.new()
        checkbox.set_active(
            True
            if pkg_key.startswith("pkg:grp:selected/")
            else self.selection_state.get(pkg_key, selected)
        )
        checkbox.set_sensitive(not immutable)
        self.checkboxes[pkg_key] = checkbox
        checkbox.connect("toggled", self.on_application_toggled, pkg_key)
        action_row.add_suffix(checkbox)
        action_row.set_activatable_widget(checkbox)
        return action_row

    def on_application_toggled(self, checkbox, pkg_key, first=False):
        """Handle application checkbox toggle"""
        if self._updating:
            return

        active = checkbox.get_active()
        self.selection_state[pkg_key] = active

        # If toggled in Selected Applications category, untick everywhere
        child = self.categories_list.get_first_child()
        if child:
            group_data = getattr(child, "group_data", None)
            if isinstance(group_data, dict) and group_data.get("_is_selected_category"):
                # If unticked, untick everywhere for all keys matching the package name
                if not active:
                    # Extract package name from key
                    pkg_name = None
                    if pkg_key.startswith("pkg:appstream/"):
                        # AppStream key
                        pkg_name = pkg_key.split("/", 1)[1]
                    else:
                        # Normal key
                        pkg_name = pkg_key.split("/")[-1]
                    # Untick all keys that end with this package name
                    for key, cb in self.checkboxes.items():
                        cb.set_active(False)
                        self.selection_state.pop(key, None)
                        for i in self.selection_state:
                            if pkg_name in i:
                                self.selection_state[i] = False

        self.update_selected_applications_category()
        pkg_name = pkg_key.split("/")[-1]
        lp(f"Application '{pkg_name}' toggled to: {active}", "debug")

    def on_search_changed(self, search_entry):
        """Handle search in categories and packages, including AppStream results"""
        search_text = search_entry.get_text().lower().strip()
        lp(f"Search input: '{search_text}'", "info")

        # Remove previous search category if present
        def remove_search_category():
            child = self.categories_list.get_first_child()
            while child:
                group_data = getattr(child, "group_data", None)
                if isinstance(group_data, dict) and group_data.get(
                    "_is_search_category"
                ):
                    self.categories_list.remove(child)
                    break
                child = child.get_next_sibling()

        remove_search_category()

        # Step 1: Expand all groups and subgroups
        def expand_all_rows():
            child = self.categories_list.get_first_child()
            while child:
                if getattr(child, "has_subgroups", False) and not getattr(
                    child, "expanded", False
                ):
                    self.expand_category(child, child.group_data, child.depth)
                child = child.get_next_sibling()
            # Recursively expand subgroups
            expanded = True
            while expanded:
                expanded = False
                child = self.categories_list.get_first_child()
                while child:
                    if getattr(child, "has_subgroups", False) and not getattr(
                        child, "expanded", False
                    ):
                        self.expand_category(child, child.group_data, child.depth)
                        expanded = True
                    child = child.get_next_sibling()

        expand_all_rows()

        # Step 2: Filter rows according to search
        if not search_text:
            # Show all rows if search is empty
            child = self.categories_list.get_first_child()
            while child:
                child.set_visible(True)
                # Collapse all expanded categories
                if getattr(child, "has_subgroups", False) and getattr(
                    child, "expanded", False
                ):
                    self.collapse_category(child)
                child = child.get_next_sibling()
            # Show applications for selected category only
            selected_row = self.categories_list.get_selected_row()
            if selected_row:
                self.show_category_packages(
                    selected_row.group_data, selected_row.group_key
                )
            return

        def subgroup_matches(subgroups):
            for sg in subgroups:
                if not isinstance(sg, dict):
                    continue
                sg_name = sg.get("name") or ""
                sg_desc = sg.get("description") or ""
                if search_text in sg_name.lower() or search_text in sg_desc.lower():
                    return True
                for pkg in sg.get("packages", []):
                    if isinstance(pkg, dict):
                        pkg_name = pkg.get("name") or ""
                        pkg_desc = pkg.get("description") or ""
                        if (
                            search_text in pkg_name.lower()
                            or search_text in pkg_desc.lower()
                        ):
                            return True
                    elif isinstance(pkg, str):
                        if search_text in pkg.lower():
                            return True
                # Recurse further
                if subgroup_matches(sg.get("subgroups", [])):
                    return True
            return False

        # Step 3: Filter categories/subgroups
        child = self.categories_list.get_first_child()
        while child:
            group_data = getattr(child, "group_data", None)
            show_row = False

            if isinstance(group_data, dict):
                name = group_data.get("name") or ""
                description = group_data.get("description") or ""
                if search_text in name.lower() or search_text in description.lower():
                    show_row = True
                for pkg in group_data.get("packages", []):
                    if isinstance(pkg, dict):
                        pkg_name = pkg.get("name") or ""
                        pkg_desc = pkg.get("description") or ""
                        if (
                            search_text in pkg_name.lower()
                            or search_text in pkg_desc.lower()
                        ):
                            show_row = True
                            break
                    elif isinstance(pkg, str):
                        if search_text in pkg.lower():
                            show_row = True
                            break
                if not show_row and subgroup_matches(group_data.get("subgroups", [])):
                    show_row = True

            child.set_visible(show_row)
            child = child.get_next_sibling()

        # Step 4: Collect all matching packages for the search category
        def collect_matching_packages(groups):
            matches = []
            seen_names = set()

            def recurse(grp, group_key):
                packages = grp.get("packages", [])
                for pkg in packages:
                    if self.is_valid_package(pkg) and self.is_arch_compatible(pkg):
                        if isinstance(pkg, dict):
                            pkg_name = pkg.get("name", "")
                            pkg_desc = pkg.get("description", "")
                            if (
                                search_text in pkg_name.lower()
                                or search_text in pkg_desc.lower()
                            ):
                                if pkg_name and pkg_name not in seen_names:
                                    matches.append(pkg)
                                    seen_names.add(pkg_name)
                        elif isinstance(pkg, str):
                            if search_text in pkg.lower():
                                if pkg not in seen_names:
                                    matches.append(pkg)
                                    seen_names.add(pkg)
                for sg in grp.get("subgroups", []):
                    if self.is_valid_group(sg) and self.is_arch_compatible(sg):
                        recurse(sg, group_key)

            groups_list = groups if isinstance(groups, list) else [groups]
            for grp in groups_list:
                if self.is_valid_group(grp) and self.is_arch_compatible(grp):
                    recurse(grp, grp.get("name", ""))
            return matches

        matches = collect_matching_packages(self.packages)

        # Limit local matches to 15
        matches = matches[:15]

        # --- AppStream search integration ---
        appstream_matches = []
        seen_pkgnames = set()
        try:
            appstream_results = search_appstream(search_text)
            for component in appstream_results:
                info = get_appstream_app_info(component)
                pkgname = info.get("package")
                # If origin is flatpak and package is None, use id as package name
                if info.get("origin") == "flatpak" and not pkgname:
                    pkgname = info.get("id")
                    info["package"] = pkgname
                if not pkgname or pkgname in seen_pkgnames:
                    continue
                seen_pkgnames.add(pkgname)
                # Only add if not already present in matches (by pkgname)
                if not any(
                    (isinstance(pkg, dict) and pkg.get("name") == pkgname)
                    or (isinstance(pkg, str) and pkg == pkgname)
                    for pkg in matches
                ):
                    appstream_dict = {
                        "name": info.get("name", pkgname),
                        "description": info.get("description", ""),
                        "icon": info.get("icon"),
                        "pkgname": pkgname,
                        "origin": info.get("origin"),
                        "id": info.get("id"),
                        "keywords": info.get("keywords"),
                        "selected": False,
                        "appstream": True,
                    }
                    appstream_matches.append(appstream_dict)
                # Limit AppStream matches to 15
                if len(appstream_matches) >= 15:
                    break
        except Exception as e:
            lp(f"AppStream search error: {e}", "warn")

        # Add AppStream results to matches
        matches.extend(appstream_matches)

        search_category_data = {
            "name": "Search Results",
            "description": "All matching applications",
            "icon": "system-search-symbolic",
            "packages": matches,
            "_is_search_category": True,
            "hidden": True,
        }
        search_row = Gtk.ListBoxRow.new()
        search_row.group_data = search_category_data
        search_row.group_key = "grp:search"
        search_row.depth = 0
        search_row.is_search_category = True
        row_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing=8)
        row_box.set_margin_top(8)
        row_box.set_margin_bottom(8)
        row_box.set_margin_start(8)
        row_box.set_margin_end(8)
        icon = Gtk.Image.new_from_icon_name("system-search-symbolic")
        icon.set_icon_size(Gtk.IconSize.NORMAL)
        row_box.append(icon)
        label = Gtk.Label.new("Search Results")
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        row_box.append(label)
        search_row.set_child(row_box)
        self.categories_list.insert(search_row, 0)
        self.categories_list.select_row(search_row)
        self.show_category_packages(search_category_data, "grp:search")

    def on_default_selections(self, button):
        """Handle default package selections button"""

        # Reset all selections
        for key in self.selection_state:
            self.selection_state[key] = False
            checkbox = self.checkboxes.get(key)
            if checkbox:
                checkbox.set_active(False)

        # Apply default selections from package data
        groups = self.packages if isinstance(self.packages, list) else [self.packages]
        self.apply_default_selections(groups, [])

    def apply_default_selections(self, groups, parent_path):
        """Recursively apply default selections"""
        for grp_data in groups:
            if not (
                self.is_valid_group(grp_data) and self.is_arch_compatible(grp_data)
            ):
                continue

            name = grp_data.get("name", "Unnamed")
            current_path = parent_path + [name]

            # Apply defaults to packages in this group
            packages = grp_data.get("packages", [])
            for pkg_data in packages:
                if self.is_valid_package(pkg_data) and self.is_arch_compatible(
                    pkg_data
                ):
                    if isinstance(pkg_data, dict) and pkg_data.get("selected", False):
                        pkg_name = pkg_data.get("name", "")
                        pkg_key = f"pkg:{self.make_group_key(current_path)}/{pkg_name}"
                        # Ensure package_metadata is set for collect_data and selection
                        self.package_metadata[pkg_key] = {
                            "name": pkg_name,
                            "post_install": pkg_data.get("post-install"),
                            "data": pkg_data,
                        }
                        self.selection_state[pkg_key] = True
                        checkbox = self.checkboxes.get(pkg_key)
                        if checkbox:
                            checkbox.set_active(True)

            # Recurse into subgroups
            subgroups = grp_data.get("subgroups", [])
            if subgroups:
                self.apply_default_selections(subgroups, current_path)

    def is_valid_group(self, data):
        """Check if group data is valid"""
        return isinstance(data, dict) and data.get("name")

    def make_group_key(self, path):
        """Create unique key for group"""
        return "grp:" + "/".join(path)

    def make_package_key(self, path, name):
        """Create unique key for package"""
        return "pkg:" + "/".join(path + [name])

    def is_valid_package(self, data):
        """Check if package data is valid"""
        if isinstance(data, str):
            return True
        return isinstance(data, dict) and data.get("name")

    def collect_data(self):
        """Get selected packages, post-install scripts, and flatpaks"""
        selected_packages = []
        post_install_scripts = []
        selected_flatpaks = []

        # Collect selected packages
        for key, is_selected in self.selection_state.items():
            if key.startswith("pkg:appstream/") and is_selected:
                # AppStream/Flatpak selection
                metadata = None
                # Try to find the dict in checkboxes (row data)
                checkbox = self.checkboxes.get(key)
                if checkbox and hasattr(checkbox, "row_data"):
                    metadata = checkbox.row_data
                # Fallback: try to get from package_metadata
                if not metadata:
                    metadata = self.package_metadata.get(key, {})
                pkgname = None
                origin = None
                if isinstance(metadata, dict):
                    pkgname = metadata.get("pkgname") or metadata.get("name")
                    origin = metadata.get("origin")
                else:
                    # fallback for str
                    pkgname = key.split("/")[-1]
                if origin == "flatpak":
                    selected_flatpaks.append(pkgname)
                else:
                    selected_packages.append(pkgname)
            elif key.startswith("pkg:") and is_selected:
                metadata = self.package_metadata.get(key, {})
                pkg_name = metadata.get("name", key.split("/")[-1])
                selected_packages.append(pkg_name)
                post_install = metadata.get("post_install")
                if post_install:
                    post_install_scripts.append(post_install)
        # Collect post-install scripts from selected groups
        for key, is_selected in self.selection_state.items():
            if key.startswith("grp:") and is_selected:
                metadata = self.group_metadata.get(key, {})
                post_install = metadata.get("post_install")
                if post_install:
                    post_install_scripts.append(post_install)

        # Remove duplicates while preserving order
        unique_packages = [
            pkg for pkg in dict.fromkeys(selected_packages) if pkg
        ]  # filter out None/empty
        unique_scripts = [
            script for script in dict.fromkeys(post_install_scripts) if script
        ]
        unique_flatpaks = [fp for fp in dict.fromkeys(selected_flatpaks) if fp]

        lp(
            f"Selected {len(unique_packages)} packages, {len(unique_flatpaks)} flatpaks, with {len(unique_scripts)} post-install scripts",
            "info",
        )

        return {
            "packages": sorted(unique_packages),
            "post_install_scripts": unique_scripts,
            "flatpaks": sorted(unique_flatpaks),
        }

    def is_arch_compatible(self, item_data):
        """Check if package/group is compatible with current architecture"""
        if not isinstance(item_data, dict):
            return True  # String packages have no arch restrictions

        required_arch = item_data.get("arch")
        if not required_arch:
            return True  # No arch restriction means compatible with all

        # Handle both single arch and list of arches
        if isinstance(required_arch, str):
            required_archs = [required_arch]
        else:
            required_archs = required_arch

        return self.current_arch in required_archs

    def select_all_default_packages(self):
        """Recursively select all packages in groups/subgroups with selected=True, unless overridden."""

        def recurse(groups, parent_path, parent_selected=False):
            for grp_data in groups:
                if not (
                    self.is_valid_group(grp_data) and self.is_arch_compatible(grp_data)
                ):
                    lp(
                        f"Skipping group: {grp_data.get('name', 'Unnamed')} (invalid or not arch compatible)",
                        "debug",
                    )
                    continue
                name = grp_data.get("name", "Unnamed")
                current_path = parent_path + [name]
                group_key = self.make_group_key(current_path)
                # Determine if this group is selected by default
                group_selected = grp_data.get("selected", parent_selected)
                packages = grp_data.get("packages", [])
                for pkg_data in packages:
                    if self.is_valid_package(pkg_data) and self.is_arch_compatible(
                        pkg_data
                    ):
                        # If parent group is selected, select package unless package.selected is False
                        pkg_selected = group_selected
                        if isinstance(pkg_data, dict) and "selected" in pkg_data:
                            pkg_selected = pkg_data["selected"]
                        if pkg_selected:
                            pkg_name = (
                                pkg_data.get("name", "")
                                if isinstance(pkg_data, dict)
                                else pkg_data
                            )
                            pkg_key = f"pkg:{group_key}/{pkg_name}"
                            self.selection_state[pkg_key] = True
                subgroups = grp_data.get("subgroups", [])
                if subgroups:
                    recurse(subgroups, current_path, group_selected)

        groups = self.packages if isinstance(self.packages, list) else [self.packages]
        recurse(groups, [], False)

    def show_selected_applications_category(self):
        """Show the Selected Applications category with all currently selected packages and add to groups"""
        selected_pkgs = []
        seen_names = set()
        for key, is_selected in self.selection_state.items():
            if key.startswith("pkg:") and is_selected:
                pkg_data = self.package_metadata.get(key, {}).get(
                    "data", key.split("/")[-1]
                )
                # Get name for deduplication
                pkg_name = None
                if isinstance(pkg_data, dict):
                    pkg_name = (
                        pkg_data.get("name") or pkg_data.get("pkgname") or str(pkg_data)
                    )
                else:
                    pkg_name = str(pkg_data)
                if pkg_name and pkg_name not in seen_names:
                    selected_pkgs.append(pkg_data)
                    seen_names.add(pkg_name)
            elif key.startswith("pkg:appstream/") and is_selected:
                pkg_data = self.package_metadata.get(key, {})
                if not pkg_data:
                    checkbox = self.checkboxes.get(key)
                    if checkbox and hasattr(checkbox, "row_data"):
                        pkg_data = checkbox.row_data
                pkg_name = None
                if isinstance(pkg_data, dict):
                    pkg_name = (
                        pkg_data.get("name") or pkg_data.get("pkgname") or str(pkg_data)
                    )
                else:
                    pkg_name = str(pkg_data)
                if pkg_name and pkg_name not in seen_names:
                    selected_pkgs.append(pkg_data if pkg_data else key.split("/")[-1])
                    seen_names.add(pkg_name)

        # Sort selected_pkgs alphabetically by name (dict or str)
        def get_pkg_name(pkg):
            if isinstance(pkg, dict):
                return pkg.get("name") or pkg.get("pkgname") or ""
            return str(pkg)

        selected_pkgs = sorted(selected_pkgs, key=get_pkg_name)

        selected_category_data = {
            "name": "Selected Applications",
            "description": "All applications you have selected so far.",
            "icon": "emblem-ok-symbolic",
            "packages": selected_pkgs,
            "_is_selected_category": True,
            "hidden": False,
        }

        # --- Add to self.groups for consistency ---
        if not hasattr(self, "groups"):
            self.groups = (
                self.packages if isinstance(self.packages, list) else [self.packages]
            )
        # Remove previous selected category from groups if present
        self.groups = [
            g
            for g in self.groups
            if not (isinstance(g, dict) and g.get("_is_selected_category"))
        ]
        self.groups.insert(0, selected_category_data)

        # --- Add to UI ---
        self.remove_selected_applications_category()
        selected_row = Gtk.ListBoxRow.new()
        selected_row.group_data = selected_category_data
        selected_row.group_key = "grp:selected"
        selected_row.depth = 0
        selected_row.is_selected_category = True
        row_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing=8)
        row_box.set_margin_top(8)
        row_box.set_margin_bottom(8)
        row_box.set_margin_start(8)
        row_box.set_margin_end(8)
        icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        icon.set_icon_size(Gtk.IconSize.NORMAL)
        row_box.append(icon)
        label = Gtk.Label.new("Selected Applications")
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        row_box.append(label)
        selected_row.set_child(row_box)
        self.categories_list.insert(selected_row, 0)
        # Do not select by default, just add to the list

    def remove_selected_applications_category(self):
        """Remove the Selected Applications category from the categories list if present"""
        child = self.categories_list.get_first_child()
        while child:
            group_data = getattr(child, "group_data", None)
            if isinstance(group_data, dict) and group_data.get("_is_selected_category"):
                self.categories_list.remove(child)
                break
            child = child.get_next_sibling()

    def update_selected_applications_category(self):
        """Update the Selected Applications category if it exists, otherwise do nothing"""
        child = self.categories_list.get_first_child()
        while child:
            group_data = getattr(child, "group_data", None)
            if isinstance(group_data, dict) and group_data.get("_is_selected_category"):
                self.show_selected_applications_category()
                break
            child = child.get_next_sibling()
