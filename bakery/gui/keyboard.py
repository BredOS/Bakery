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
from gi.repository import Gtk, Adw, Gio, Gdk, GLib, Pango  # type: ignore


@Gtk.Template(resource_path="/org/bredos/bakery/ui/kb_screen.ui")
class kb_screen(Adw.Bin):
    __gtype_name__ = "kb_screen"

    event_controller = Gtk.EventControllerKey.new()
    langs_list = Gtk.Template.Child()  # GtkListBox
    models_list = Gtk.Template.Child()  # GtkDropDown

    variant_dialog = Gtk.Template.Child()
    variant_list = Gtk.Template.Child()  # GtkListBox
    select_variant_btn = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.kb_prettylayouts = {k: v for k, v in sorted(kb_layouts(True).items())}
        self.kb_prettymodels = kb_models(True)
        self.kb_layouts = kb_layouts()
        self.kb_models = kb_models()

        self.layout = {"model": "pc105", "layout": None, "variant": None}

        self.models_model = Gtk.StringList()
        self.models_list.set_model(self.models_model)
        for model in self.kb_models.keys():
            self.models_model.append(self.kb_models[model])

        # set pc105 as default
        self.models_list.set_selected(list(self.kb_models.keys()).index("pc105"))

        self.variant_dialog.set_transient_for(self.window)
        self.variant_dialog.set_modal(self.window)

        self.select_variant_btn.connect("clicked", self.confirm_selection)
        self.models_list.connect("notify::selected-item", self.on_model_changed)
        self.populate_layout_list()

    def on_model_changed(self, dropdown, *_):
        selected = dropdown.props.selected_item
        if selected is not None:
            self.layout["model"] = self.kb_prettymodels[selected.props.string]

    def populate_layout_list(self) -> None:
        for lang in self.kb_prettylayouts:
            row = Gtk.ListBoxRow()
            lang_label = Gtk.Label(label=lang)
            row.set_child(lang_label)

            self.langs_list.append(row)
            self.langs_list.connect("row-activated", self.selected_lang)
            self.last_selected_row = None

            # preselect the American English layout
            if lang == "American English":
                self.langs_list.select_row(row)
                self.last_selected_row = row
                self.layout["layout"] = "us"
                self.layout["variant"] = "normal"
                self.change_kb_layout("us", "pc105", "normal")

    def confirm_selection(self, *_) -> None:
        self.variant_dialog.hide()

    def show_dialog(self, *_) -> None:
        self.variant_dialog.present()

    def selected_lang(self, widget, row) -> None:
        if row != self.last_selected_row:
            self.last_selected_row = row
            lang = row.get_child().get_label()
            layouts = kb_variants(self.kb_prettylayouts[lang])
            self.layout["layout"] = self.kb_prettylayouts[lang]
            if not len(layouts):
                self.layout["variant"] = "normal"
                self.change_kb_layout(
                    self.layout["layout"], self.layout["model"], self.layout["variant"]
                )
            else:
                # clear the listbox
                self.variant_list.remove_all()
                # add normal layout
                newrow = Gtk.ListBoxRow()
                # Language - Layout
                layout_label = Gtk.Label(label=f"{lang} - normal")
                newrow.set_child(layout_label)

                self.variant_list.append(newrow)
                self.variant_list.connect("row-activated", self.selected_layout)

                self.last_selected_layout = None
                # preselect the normal layout
                self.variant_list.select_row(newrow)
                self.selected_layout(None, newrow)

                for layout_ in layouts:
                    newrow = Gtk.ListBoxRow()
                    # Language - Layout
                    layout_label = Gtk.Label(label=f"{lang} - {layout_}")
                    newrow.set_child(layout_label)

                    self.variant_list.append(newrow)
                    self.variant_list.connect("row-activated", self.selected_layout)

                self.show_dialog()

    def selected_layout(self, widget, row) -> None:
        if row != self.last_selected_layout:
            self.last_selected_layout = row
            self.layout["variant"] = row.get_child().get_label().split(" - ")[1]
            self.change_kb_layout(
                self.layout["layout"], self.layout["model"], self.layout["variant"]
            )

    def change_kb_layout(self, lang, model, layout) -> None:
        if layout == "normal":
            layout = ""
        lrun(["setxkbmap", "-model", model])
        lrun(["setxkbmap", "-layout", lang])
        # WARNING: Variant not set.
        # lrun(["setxkbmap", "-variant", layout])
