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

import faulthandler
from typing import Any

faulthandler.enable()
from sys import argv
import gi
from os import path
import threading
import locale
import gettext
import platform
import bakery
from bakery import (
    dryrun,
    kb_models,
    kb_layouts,
    kb_variants,
    langs,
    tz_list,
    geoip,
    validate_username,
    validate_fullname,
    validate_hostname,
    check_efi,
    check_partition_table,
    list_drives,
    get_partitions,
    gen_new_partitions,
    lp,
    setup_translations,
    debounce,
    _,
    uidc,
    gidc,
    lrun,
    detect_install_device,
    detect_install_source,
    detect_session_configuration,
    reboot,
    upload_log,
    log_path,
    time_fn,
    get_packages_list,
)
from time import sleep
from datetime import datetime
from babel import dates, numbers
from babel import Locale as bLocale
from pyrunning import (
    LoggingHandler,
    LogMessage,
    Command,
    LoggingLevel,
    BatchJob,
    Function,
)
from pytz import timezone
import config

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib  # type: ignore

# py file path
script_dir = path.dirname(path.realpath(__file__))


class BakeryApp(Adw.Application):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)
        # Force dark mode
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        self.css_provider = self.load_css(script_dir + "/data/main.css")

    def on_activate(self, app) -> None:
        self.create_action("about", self.on_about_action)

    def do_activate(self) -> None:
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        global win
        win = self.props.active_window
        if not win:
            win = BakeryWindow(application=self)
            self.win = win
            self.add_custom_styling(self.win)
        win.present()

    def on_preferences_action(self, widget, _) -> None:
        """Callback for the app.preferences action."""
        # Implement your preferences logic here
        pass

    def on_about_action(self, widget, py) -> None:
        """Callback for the app.about action."""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name=_("BredOS Installer"), # pyright: ignore[reportCallIssue]
            application_icon="org.bredos.bakery",
            developer_name="BredOS",
            debug_info=self.win.collect_data(show_pass=False),
            version=config.installer_version,
            developers=["Panda <panda@bredos.org>", "bill88t <bill88t@bredos.org>"],
            designers=["Panda <panda@bredos.org>", "DustyDaimler"],
            documenters=["Panda <panda@bredos.org>", "DroidMaster"],
            translator_credits=_("translator-credits"),  # pyright: ignore[reportCallIssue]
            copyright=_("Copyright The BredOS developers"),  # pyright: ignore[reportCallIssue]
            comments=_("Bakery is a simple installer for BredOS"),  # pyright: ignore[reportCallIssue]
            license_type=Gtk.License.GPL_3_0,
            website="https://BredOS.org",
            issue_url="https://github.com/BredOS/Bakery/issues",
            support_url="https://discord.gg/jwhxuyKXaa",
        )
        translators = ["Bill88t  <bill88t@bredos.org>", "Panda <panda@bredos.org>"]
        about.add_credit_section(_("Translated by"), translators)  # pyright: ignore[reportCallIssue]
        about.add_acknowledgement_section(_("Special thanks to"), ["Shivanandvp"])  # pyright: ignore[reportCallIssue]
        about.present()

    def create_action(self, name, callback, shortcuts=None) -> None:
        """Add an application action.
        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    def load_css(self, css_fn):
        """create a provider for custom styling"""
        global css_provider
        css_provider = None
        if css_fn and path.exists(css_fn):
            css_provider = Gtk.CssProvider()
            try:
                css_provider.load_from_path(css_fn)
            except GLib.Error as e:
                lp(f"Error loading CSS : {e} ", mode="error")
                return None
            lp(f"loading custom styling : {css_fn}", mode="debug")
        return css_provider

    def _add_widget_styling(self, widget):
        if css_provider:
            context = widget.get_style_context()
            context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def add_custom_styling(self, widget):
        self._add_widget_styling(widget)
        # Recursively apply styling to all descendants
        if hasattr(widget, "get_first_child"):
            child = widget.get_first_child()
            while child:
                self.add_custom_styling(child)
                child = child.get_next_sibling()
        elif hasattr(widget, "__iter__"):
            for child in widget:
                self.add_custom_styling(child)

@Gtk.Template.from_file(script_dir + "/data/window.ui")
class BakeryWindow(Adw.ApplicationWindow):
    __gtype_name__ = "BakeryWindow"

    stack1 = Gtk.Template.Child()
    steps_box = Gtk.Template.Child()
    button_box = Gtk.Template.Child()
    back_btn = Gtk.Template.Child()
    next_btn = Gtk.Template.Child()

    main_stk = Gtk.Template.Child()
    main_page = Gtk.Template.Child()
    install_page = Gtk.Template.Child()
    offline_install = Gtk.Template.Child()
    online_install = Gtk.Template.Child()
    custom_install = Gtk.Template.Child()
    install_cancel = Gtk.Template.Child()
    install_confirm = Gtk.Template.Child()
    err_dialog = Gtk.Template.Child()
    log_dialog = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_deletable(False)
        # go to the first page of main stack
        self.main_stk.set_visible_child(self.main_page.get_child())
        self.cancel_dialog = self.install_cancel
        self.cancel_dialog.set_property("hide-on-close", True)
        self.install_type = None
        self.install_source = detect_install_source()
        self.install_device = detect_install_device()
        self.session_configuration = detect_session_configuration()
        self.online_install.connect("clicked", self.main_button_clicked)
        self.offline_install.connect("clicked", self.main_button_clicked)
        self.custom_install.connect("clicked", self.main_button_clicked)
        self.cancel_dialog.connect("response", self.on_cancel_dialog_response)

        self.next_btn.connect("clicked", self.on_next_clicked)
        self.back_btn.connect("clicked", self.on_back_clicked)
        self.err_dialog.connect("response", self.on_err_dialog_response)
        self.log_dialog.connect("response", self.on_log_dialog_response)

        # Initialize step indicators
        self.step_indicators = []
        self.step_separators = []

    def on_err_dialog_response(self, dialog, resp) -> None:
        if resp == "yes":
            self.err_dialog.hide()
            logurl = upload_log()
            if logurl == "error":
                self.log_dialog.set_heading(_("Log upload failed"))  # pyright: ignore[reportCallIssue]
                self.log_dialog.set_body(
                    _("The log file could not be uploaded it can still be found at")  # pyright: ignore[reportCallIssue]
                    + '<br><a href="file://'
                    + log_path
                    + '">'
                    + log_path
                    + "</a>"
                )
            else:
                self.log_dialog.set_heading(_("Log uploaded"))  # pyright: ignore[reportCallIssue]
                self.log_dialog.set_body(
                    _("The log file has been uploaded, you can find it at")  # pyright: ignore[reportCallIssue]
                    + '\n<a href="'
                    + logurl
                    + '">'
                    + logurl
                    + "</a>"
                    + '\n<a href="file://'
                    + log_path
                    + '">'
                    + log_path
                    + "</a>"
                )
            self.log_dialog.present()
        if resp == "no":
            self.err_dialog.hide()
            exit(1)

    def on_log_dialog_response(self, dialog, resp) -> None:
        if resp == "ok":
            self.log_dialog.hide()
            exit(1)

    @time_fn
    @debounce(2)
    def main_button_clicked(self, button) -> None:
        if button == self.offline_install:
            self.init_screens("offline")
        elif button == self.online_install:
            self.init_screens("online")
        elif button == self.custom_install:
            self.init_screens("custom")

    def on_install_btn_clicked(self, button) -> None:
        # connect the yes button to the install function
        self.install_confirm.connect("response", self.on_install_dialog_response)
        self.install_confirm.set_property("hide-on-close", True)
        self.install_confirm.show()

    @debounce(0.3)
    def start_install(self) -> None:
        self.current_page = self.pages.index("Install")
        page_name = self.pages[self.current_page]
        page_id = self.get_page_id(page_name)
        self.stack1.set_visible_child_name(page_id)
        self.button_box.set_visible(False)
        self.install_thread = InstallThread(self, all_pages["Install"])
        self.install_thread.start()

    def on_install_dialog_response(self, dialog, resp) -> None:
        if resp == "yes":
            self.install_confirm.hide()
            self.start_install()
        else:
            self.install_confirm.hide()

    def on_done_clicked(self, button) -> None:
        # quit the app
        self.close()
        reboot()

    @debounce(0.3)
    def on_next_clicked(self, button) -> None:
        num_pages = len(self.pages)
        if self.current_page < num_pages - 1:
            self.current_page += 1
            if self.current_page == self.pages.index("Summary"):
                self.next_btn.disconnect_by_func(self.on_next_clicked)
                self.next_btn.connect("clicked", self.on_install_btn_clicked)
                self.update_buttons()
                page_name = self.pages[self.current_page]
                page_id = self.get_page_id(page_name)
                self.stack1.set_visible_child_name(page_id)
            else:
                page_name = self.pages[self.current_page]
                page_id = self.get_page_id(page_name)
                self.stack1.set_visible_child_name(page_id)
                self.update_buttons()
            
            # Update step indicators after page change
            self.update_step_indicators()

    def on_back_clicked(self, button) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            page_name = self.pages[self.current_page]
            page_id = self.get_page_id(page_name)
            self.stack1.set_visible_child_name(page_id)
            try:
                self.next_btn.disconnect_by_func(self.on_install_btn_clicked)
                self.next_btn.connect("clicked", self.on_next_clicked)
            except:
                pass
            self.update_buttons()
            
            # Update step indicators after page change
            self.update_step_indicators()

    def update_buttons(self) -> None:
        num_pages = len(self.pages)
        # if page is user page make it so user cant go forward
        global user_event
        global part_event
        user_event = threading.Event()
        part_event = threading.Event()
        self.check_thread = CheckThread(all_pages["User"])

        if self.install_source == "from_iso":
            self.check_part_thread = CheckPartitioningThread(all_pages["Partitioning"])

            if self.current_page == self.pages.index("User"):
                self.next_btn.set_sensitive(False)
                # start the thread to check when all fields are filled
                self.next_btn.set_label(_("Next"))  # pyright: ignore[reportCallIssue]
                self.check_thread.start()
            elif self.current_page == self.pages.index("Partitioning"):
                user_event.set()
                self.next_btn.set_sensitive(False)
                # start the thread to check when all fields are filled
                self.next_btn.set_label(_("Next"))  # pyright: ignore[reportCallIssue]
                self.check_part_thread.start()
            elif self.current_page == self.pages.index("Summary"):
                user_event.set()
                all_pages["Summary"].page_shown()
                # change the next button to install
                self.next_btn.set_label(_("Install"))  # pyright: ignore[reportCallIssue]
                self.next_btn.set_sensitive(self.current_page < num_pages - 1)
                self.back_btn.set_sensitive(self.current_page > 0)
            elif self.current_page == self.pages.index("Install"):
                self.back_btn.set_sensitive(False)
                self.next_btn.set_sensitive(False)
            else:
                self.next_btn.set_label(_("Next"))  # pyright: ignore[reportCallIssue]
                user_event.set()
                part_event.set()
                self.next_btn.set_sensitive(self.current_page < num_pages - 1)
                self.back_btn.set_sensitive(self.current_page > 0)
        else:
            if self.current_page == self.pages.index("User"):
                self.next_btn.set_sensitive(False)
                # start the thread to check when all fields are filled
                self.next_btn.set_label(_("Next"))  # pyright: ignore[reportCallIssue]
                self.check_thread.start()
            elif self.current_page == self.pages.index("Summary"):
                user_event.set()
                all_pages["Summary"].page_shown()
                # change the next button to install
                self.next_btn.set_label(_("Install"))  # pyright: ignore[reportCallIssue]
                self.next_btn.set_sensitive(self.current_page < num_pages - 1)
                self.back_btn.set_sensitive(self.current_page > 0)
            elif self.current_page == self.pages.index("Install"):
                self.back_btn.set_sensitive(False)
                self.next_btn.set_sensitive(False)
            else:
                self.next_btn.set_label(_("Next"))  # pyright: ignore[reportCallIssue]
                user_event.set()
                part_event.set()
                self.next_btn.set_sensitive(self.current_page < num_pages - 1)
                self.back_btn.set_sensitive(self.current_page > 0)

    def on_cancel_clicked(self, button) -> None:
        # connect the yes button to the delete_pages function
        self.cancel_dialog.present()

    def on_close_clicked(self, button) -> None:
        # connect the yes button to the delete_pages function
        self.cancel_dialog.present()

    def on_cancel_dialog_response(self, dialog, resp) -> None:
        if resp == "yes":
            self.cancel_dialog.hide()
            self.close()
        else:
            self.cancel_dialog.hide()

    def delete_pages(self, dialog, resp) -> None:
        if resp == "yes":
            self.main_stk.set_visible_child(self.main_page.get_child())
            # remove all pages from stack1

            pages = [self.get_page_id(x) for x in self.pages]
            for page_id in pages:
                w = self.stack1.get_child_by_name(page_id)
                self.stack1.remove(w)
        self.cancel_dialog.hide()

    def get_page_id(self, page_name) -> str:
        return page_name

    def collect_data(self, show_pass=False, *_) -> dict:
        data = {}
        if not self.install_type == None:
            install_data = {}
            install_data["type"] = self.install_type
            install_data["source"] = self.install_source
            install_data["device"] = self.install_device
            data["install_type"] = install_data
            data["session_configuration"] = self.session_configuration
            data["root_password"] = False
            data["layout"] = all_pages["Keyboard"].layout
            data["locale"] = all_pages["Locale"].locale
            data["timezone"] = all_pages["Timezone"].timezone
            data["hostname"] = all_pages["User"].get_hostname()
            data["user"] = all_pages["User"].collect_data()
            if not show_pass:
                data["user"]["password"] = "REDACTED"
            installer = {}
            installer["installer_version"] = config.installer_version
            installer["ui"] = "gui"
            installer["shown_pages"] = self.pages
            data["installer"] = installer
            data["packages"] = {}
            if self.install_source == "from_iso":
                data["packages"]["to_remove"] = config.iso_packages_to_remove
                data["packages"]["de_packages"] = []
            try:
                data["partitions"] = all_pages["Partitioning"].collect_data()
            except:
                data["partitions"] = []
            if self.install_type == "online":
                data["packages"]["extra_to_install"] = all_pages["Packages"].collect_data()
                data["packages"]["de_packages"] = []

            return data
        else:
            return {"install_type": "None"}

    def set_list_text(list, string) -> None:
        n = list.get_n_items()
        if n > 0:
            list.splice(0, n, [string])
        else:
            list.append(string)

    def add_pages(self, stack, pages) -> None:
        global all_pages, pages_dict
        all_pages = {}
        pages_dict = config.pages(_)
        for page in pages:
            page_ = globals()[pages_dict[page][0]](window=self)
            all_pages[page] = page_
            stack.add_titled(page_, page, pages_dict[page][1])

    def create_step_indicators(self):
        """Create circular step indicators with page names above and horizontal lines between circles using overlays"""
        for indicator in self.step_indicators:
            self.steps_box.remove(indicator)
        self.step_indicators.clear()
        if hasattr(self, "step_separators"):
            for sep in self.step_separators:
                self.steps_box.remove(sep)
        self.step_separators = []
        self.step_circles = []  # Store circle buttons
        self.step_names = []    # Store name labels

        pages_dict = config.pages(_)
        num_pages = len(self.pages)
        for i, page_name in enumerate(self.pages):
            overlay = Gtk.Overlay()
            overlay.set_halign(Gtk.Align.CENTER)
            overlay.set_valign(Gtk.Align.START)
            overlay.set_size_request(75, -1)

            # Separator (only if not first step)
            if i > 0:
                separator = Gtk.Separator.new(orientation=Gtk.Orientation.HORIZONTAL)
                separator.set_size_request(50, 4)
                separator.set_margin_top(35)
                separator.set_margin_end(75)
                separator.set_halign(Gtk.Align.CENTER)
                separator.set_valign(Gtk.Align.START)
                separator.get_style_context().add_class("step-separator")
                if i - 1 < self.current_page:
                    separator.get_style_context().add_class("separator-completed")
                elif i - 1 == self.current_page - 1:
                    separator.get_style_context().add_class("separator-current")
                else:
                    separator.get_style_context().add_class("separator-inactive")
                overlay.add_overlay(separator)
                self.step_separators.append(separator)
                self.get_application().add_custom_styling(separator)

            # Step container (name label on top, circle below)
            step_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            step_container.set_size_request(75, -1)
            step_container.get_style_context().add_class("step-indicator-container")

            page_display_name = pages_dict[page_name][1] if page_name in pages_dict else page_name
            name_label = Gtk.Label(label=page_display_name)
            name_label.get_style_context().add_class("step-name")
            name_label.set_halign(Gtk.Align.CENTER)
            name_label.set_valign(Gtk.Align.CENTER)
            step_container.append(name_label)
            self.step_names.append(name_label)  # Store reference

            circle_button = Gtk.Button(label="")
            circle_button.set_can_target(False)
            circle_button.set_size_request(24, 24)
            circle_button.set_halign(Gtk.Align.CENTER)
            circle_button.set_valign(Gtk.Align.CENTER)
            circle_button.get_style_context().add_class("circular")
            if i == self.current_page:
                circle_button.get_style_context().add_class("current-step")
            elif i < self.current_page:
                circle_button.get_style_context().add_class("completed-step")
            else:
                circle_button.get_style_context().add_class("inactive-step")
            step_container.append(circle_button)
            self.step_circles.append(circle_button)  # Store reference

            overlay.set_child(step_container)
            self.steps_box.append(overlay)
            self.step_indicators.append(overlay)
            self.get_application().add_custom_styling(step_container)

    def update_step_indicators(self):
        """Update step indicators to show current progress and separator colors"""
        if not self.step_indicators:
            return
        for i, overlay in enumerate(self.step_indicators):
            # Use stored circle_button reference
            circle_button = self.step_circles[i]
            context = circle_button.get_style_context()
            context.remove_class("current-step")
            context.remove_class("completed-step")
            context.remove_class("inactive-step")
            if i == self.current_page:
                context.add_class("current-step")
            elif i < self.current_page:
                context.add_class("completed-step")
            else:
                context.add_class("inactive-step")
            # Update separator color if present
            if i > 0:
                separator = self.step_separators[i - 1]
                sep_ctx = separator.get_style_context()
                sep_ctx.remove_class("separator-completed")
                sep_ctx.remove_class("separator-current")
                sep_ctx.remove_class("separator-inactive")
                if i - 1 < self.current_page:
                    sep_ctx.add_class("separator-completed")
                elif i - 1 == self.current_page - 1:
                    sep_ctx.add_class("separator-current")
                else:
                    sep_ctx.add_class("separator-inactive")
            # Update name label style for current step
            name_label = self.step_names[i]
            name_ctx = name_label.get_style_context()
            name_ctx.remove_class("current-step-name")
            if i == self.current_page:
                name_ctx.add_class("current-step-name")

    def init_screens(self, install_type) -> None:
        if install_type == "online":
            if self.install_source == "from_iso":
                self.pages = config.online_pages_from_iso
            else:
                self.pages = config.online_pages_on_dev
            self.add_pages(self.stack1, self.pages)
        elif install_type == "offline":
            if self.install_source == "from_iso":
                self.pages = config.offline_pages_from_iso
            else:
                self.pages = config.offline_pages_on_dev
            self.add_pages(self.stack1, self.pages)

        bakery.logging_handler = LoggingHandler(
            logger=bakery.logger,
            logging_functions=[all_pages["Install"].console_logging],
        )
        self.install_type = install_type
        self.current_page = 0

        # Create step indicators after pages are determined
        self.create_step_indicators()

        self.update_buttons()
        self.main_stk.set_visible_child(self.install_page.get_child())


@Gtk.Template.from_file(script_dir + "/data/kb_screen.ui")
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


@Gtk.Template.from_file(script_dir + "/data/locale_screen.ui")
class locale_screen(Adw.Bin):
    __gtype_name__ = "locale_screen"

    langs_list = Gtk.Template.Child()
    date_preview = Gtk.Template.Child()
    currency_preview = Gtk.Template.Child()

    locale_dialog = Gtk.Template.Child()
    locales_list = Gtk.Template.Child()
    select_locale_btn = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.lang_data = {k: v for k, v in sorted(langs().items())}

        self.locale_dialog.set_transient_for(self.window)
        self.locale_dialog.set_modal(self.window)

        self.populate_locales_list()
        self.select_locale_btn.connect("clicked", self.hide_dialog)

    def populate_locales_list(self) -> None:
        for lang in self.lang_data:
            row = Gtk.ListBoxRow()
            lang_label = Gtk.Label(label=lang)
            row.set_child(lang_label)

            self.langs_list.append(row)
            self.langs_list.connect("row-activated", self.selected_lang)
            self.last_selected_row = None

            if lang == "English":
                self.langs_list.select_row(row)
                self.last_selected_row = row
                self.update_previews("en_US.UTF-8 UTF-8")

    def selected_lang(self, widget, row) -> None:
        if row != self.last_selected_row:
            self.last_selected_row = row
            lang = row.get_child().get_label()
            if len(self.lang_data[lang]) == 1:
                self.update_previews(self.lang_data[lang][0])
            else:
                # clear the listbox
                self.locales_list.remove_all()
                sr = langs()[lang]
                sr.sort()
                for locale in sr:
                    newrow = Gtk.ListBoxRow()
                    # Language - Layout
                    locale_label = Gtk.Label(label=locale)
                    newrow.set_child(locale_label)

                    self.locales_list.append(newrow)
                    self.locales_list.connect("row-activated", self.selected_locale)
                    self.show_dialog()
                    self.last_selected_locale = None
                    self.select_locale_btn.set_sensitive(False)

    def selected_locale(self, widget, row) -> None:
        if row != self.last_selected_locale:
            self.last_selected_locale = row
            self.update_previews(row.get_child().get_label())
            self.select_locale_btn.set_sensitive(True)

    def update_previews(self, selected_locale) -> None:
        try:
            the_locale, encoding = selected_locale.split(" ")
            if not encoding == "UTF-8":
                the_locale += "." + encoding
        except ValueError:
            the_locale = selected_locale
        self.locale = selected_locale
        locale_ = bLocale.parse(the_locale)
        date = dates.format_date(date=datetime.utcnow(), format="full", locale=locale_)
        time = dates.format_time(time=datetime.utcnow(), format="long", locale=locale_)
        currency = numbers.get_territory_currencies(locale_.territory)[0] 
        currency_format = numbers.format_currency(1234.56, currency, locale=locale_)
        number_format = numbers.format_decimal(1234567.89, locale=locale_)
        self.date_preview.set_label(time + "  -  " + date)
        self.currency_preview.set_label(number_format + "  -  " + currency_format)

    def hide_dialog(self, stuff) -> None:
        try:
            # change the locale and update translations
            try:
                the_locale, encoding = self.locale.split(" ")
                if not encoding == "UTF-8":
                    the_locale += "." + encoding
            except ValueError:
                the_locale = self.locale
            win.queue_draw()
        except Exception as e:
            import traceback

            lp(traceback.format_exc(), mode="error")

        self.locale_dialog.hide()

    def show_dialog(self, *_) -> None:
        self.locales_list.unselect_all()
        self.locale_dialog.present()


class CheckThread(threading.Thread):
    def __init__(self, window):
        threading.Thread.__init__(self)
        self.window = window

    def run(self):
        while True:
            if user_event.is_set():
                break
            if (
                (self.window.get_username() is not None)
                and (self.window.get_hostname() is not None)
                and (self.window.get_password() is not None)
                and (self.window.get_fullname() is not None)
                and (self.window.validate_uid(self.window.uid_row) is not None)
            ):
                win.next_btn.set_sensitive(True)
            else:
                win.next_btn.set_sensitive(False)
            sleep(0.5)


class InstallThread(threading.Thread):
    def __init__(self, window, install_window):
        threading.Thread.__init__(self)
        self.window = window
        self.install_window = install_window

    def run(self):
        install_data = self.window.collect_data(show_pass=True)
        lp(
            "Starting install with data: "
            + str(self.window.collect_data(show_pass=False))
        )
        res = bakery.install(install_data)
        if res == 0:
            # Change to finish page
            self.window.current_page = self.window.pages.index("Finish")
            page_name = self.window.pages[self.window.current_page]
            page_id = self.window.get_page_id(page_name)
            self.window.stack1.set_visible_child_name(page_id)
            self.window.button_box.set_visible(True)
            self.window.back_btn.set_visible(False)
            self.window.next_btn.disconnect_by_func(self.window.on_install_btn_clicked)
            self.window.next_btn.connect("clicked", self.window.on_done_clicked)
            self.window.next_btn.set_label(_("Reboot"))  # pyright: ignore[reportCallIssue]
        else:
            GLib.timeout_add(500, self.window.err_dialog.present)


@Gtk.Template.from_file(script_dir + "/data/user_screen.ui")
class user_screen(Adw.Bin):
    __gtype_name__ = "user_screen"

    fullname_entry = Gtk.Template.Child()
    user_entry = Gtk.Template.Child()
    hostname_entry = Gtk.Template.Child()
    pass_entry = Gtk.Template.Child()
    confirm_pass_entry = Gtk.Template.Child()
    user_info = Gtk.Template.Child()

    uid_row = Gtk.Template.Child()
    nopasswd = Gtk.Template.Child()
    autologin = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window

        self.pass_entry.connect("changed", self.on_confirm_pass_changed)
        self.confirm_pass_entry.connect("changed", self.on_confirm_pass_changed)
        self.user_entry.connect("changed", self.on_username_changed)
        self.hostname_entry.connect("changed", self.on_hostname_changed)
        self.fullname_entry.connect("changed", self.on_fullname_changed)
        self.uid_row.connect("changed", self.validate_uid)
        self.validate_uid(self.uid_row)
        self.user_info_is_visible = False

    def on_fullname_changed(self, entry):
        fullname = entry.get_text()
        a = validate_fullname(fullname)
        if a == "":
            self.user_info.set_visible(False)
            self.user_info_is_visible = False
            self.fullname_entry.get_style_context().remove_class("error")
        else:
            self.user_info.set_label(a)
            self.fullname_entry.get_style_context().add_class("error")
            if not self.user_info_is_visible:
                self.user_info.set_visible(True)
                self.user_info_is_visible = True

    def validate_uid(self, spin_entry):
        uid = int(spin_entry.get_value())
        if not uidc(uid) and not gidc(uid):
            spin_entry.get_style_context().remove_class("error")
            return uid
        else:
            spin_entry.get_style_context().add_class("error")
            return None

    def on_hostname_changed(self, entry):
        hostname = entry.get_text()
        a = validate_hostname(hostname)
        if a == "":
            self.user_info.set_visible(False)
            self.user_info_is_visible = False
            self.hostname_entry.get_style_context().remove_class("error")
        else:
            self.user_info.set_label(a)
            self.hostname_entry.get_style_context().add_class("error")
            if not self.user_info_is_visible:
                self.user_info.set_visible(True)
                self.user_info_is_visible = True

    def on_username_changed(self, entry):
        username = entry.get_text()
        a = validate_username(username)
        if a == "":
            self.user_info.set_visible(False)
            self.user_info_is_visible = False
            self.user_entry.get_style_context().remove_class("error")
        else:
            self.user_info.set_label(a)
            self.user_entry.get_style_context().add_class("error")
            if not self.user_info_is_visible:
                self.user_info.set_visible(True)
                self.user_info_is_visible = True

    def on_confirm_pass_changed(self, entry):
        pass_text = self.pass_entry.get_text()
        confirm_pass_text = entry.get_text()

        if not pass_text == confirm_pass_text:
            self.confirm_pass_entry.get_style_context().add_class("error")
        elif (
            pass_text == confirm_pass_text
            or not len(pass_text)
            or not len(confirm_pass_text)
        ):
            self.confirm_pass_entry.get_style_context().remove_class("error")

    def get_fullname(self) -> str:
        if self.fullname_entry.get_text() == "":
            return None
        else:
            if validate_fullname(self.fullname_entry.get_text()) == "":
                return self.fullname_entry.get_text()
            else:
                return None

    def get_username(self) -> str:
        if self.user_entry.get_text() == "":
            return None
        else:
            if validate_username(self.user_entry.get_text()) == "":
                return self.user_entry.get_text()
            else:
                return None

    def get_hostname(self) -> str:
        if self.hostname_entry.get_text() == "":
            return None
        else:
            if validate_hostname(self.hostname_entry.get_text()) == "":
                return self.hostname_entry.get_text()
            else:
                return None

    def get_password(self) -> str:
        if self.pass_entry.get_text() == "":
            return None
        else:
            pass_text = self.pass_entry.get_text()
            confirm_pass_text = self.confirm_pass_entry.get_text()
            if pass_text == confirm_pass_text:
                return pass_text
            else:
                return None

    def collect_data(self) -> dict:
        data = {}
        data["fullname"] = self.get_fullname()
        data["username"] = self.get_username()
        data["password"] = self.get_password()
        data["uid"] = self.validate_uid(self.uid_row)
        data["gid"] = self.validate_uid(self.uid_row)
        data["sudo_nopasswd"] = self.nopasswd.get_active()
        data["autologin"] = self.autologin.get_active()
        data["shell"] = "/bin/bash"
        data["groups"] = ["wheel", "network", "video", "audio", "storage"]
        return data


@Gtk.Template.from_file(script_dir + "/data/timezone_screen.ui")
class timezone_screen(Adw.Bin):
    __gtype_name__ = "timezone_screen"

    regions_list = Gtk.Template.Child()
    zones_list = Gtk.Template.Child()
    curr_time = Gtk.Template.Child()
    preview_row = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.tz_list = tz_list()
        current_timezone = geoip()
        self.timezone = {}
        self.timezone["region"] = current_timezone["region"]
        self.timezone["zone"] = current_timezone["zone"]
        self.timezone["ntp"] = True

        self.zones_list.connect("notify::selected-item", self.on_zone_changed)
        self.zone_model = Gtk.StringList()
        self.zones_list.set_model(self.zone_model)

        self.regions_list.connect("notify::selected-item", self.on_region_changed)
        self.region_model = Gtk.StringList()
        self.regions_list.set_model(self.region_model)
        for item in list(self.tz_list.keys()):
            self.region_model.append(item)

        self.change_regions_list(current_timezone["region"])
        self.regions_list.set_selected(
            list(self.tz_list.keys()).index(current_timezone["region"])
        )
        self.select_zone(current_timezone["region"], current_timezone["zone"])

    def on_region_changed(self, dropdown, *_):
        selected = dropdown.props.selected_item
        if selected is not None:
            self.timezone["region"] = selected.props.string
            self.change_regions_list(selected.props.string)

    def on_zone_changed(self, dropdown, *_):
        selected = dropdown.props.selected_item
        if selected is not None:
            self.timezone["zone"] = selected.props.string
            self.preview_timezone(self.timezone["region"], selected.props.string)

    def change_regions_list(self, region) -> None:
        self.zone_model = Gtk.StringList()
        self.zones_list.set_model(self.zone_model)
        for zone in self.tz_list[region]:
            self.zone_model.append(zone)

    def select_zone(self, region, zone) -> None:
        # get the index of the zone in the list
        index = self.tz_list[region].index(zone)
        self.zones_list.set_selected(index)

    def preview_timezone(self, region, zone) -> None:
        # timezone expects region/zone
        try:
            tz = timezone(str(region + "/" + zone))
        except:
            tz = None
        if tz is not None:
            time = datetime.now(tz)
            self.curr_time.set_label(time.strftime("%Y-%m-%d %H:%M:%S"))
            self.preview_row.set_subtitle(_("Previewing time in ") + str(tz))  # pyright: ignore[reportCallIssue]


@Gtk.Template.from_file(script_dir + "/data/de_screen.ui")
class de_screen(Adw.Bin):
    __gtype_name__ = "de_screen"

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window

       
@Gtk.Template.from_file(script_dir + "/data/summary_screen.ui")
class summary_screen(Adw.Bin):
    __gtype_name__ = "summary_screen"

    locale_preview = Gtk.Template.Child()
    kb_lang = Gtk.Template.Child()
    kb_variant = Gtk.Template.Child()
    kb_model = Gtk.Template.Child()
    tz_preview = Gtk.Template.Child()

    name_preview = Gtk.Template.Child()
    username_preview = Gtk.Template.Child()
    hostname_preview = Gtk.Template.Child()

    autologin = Gtk.Template.Child()  # switch
    nopasswd = Gtk.Template.Child()  # switch

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window

    def page_shown(self) -> None:
        self.data = self.window.collect_data()
        self.locale_preview.set_label(self.data["locale"])
        self.kb_lang.set_label(kb_layouts()[self.data["layout"]["layout"]])
        self.kb_variant.set_label(self.data["layout"]["variant"])
        self.kb_model.set_label(kb_models()[self.data["layout"]["model"]])
        self.tz_preview.set_label(
            self.data["timezone"]["region"] + "/" + self.data["timezone"]["zone"]
        )
        self.name_preview.set_label(self.data["user"]["fullname"])
        self.username_preview.set_label(self.data["user"]["username"])
        self.hostname_preview.set_label(self.data["hostname"])
        self.autologin.set_active(self.data["user"]["autologin"])
        self.nopasswd.set_active(self.data["user"]["sudo_nopasswd"])


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


@time_fn
@Gtk.Template.from_file(script_dir + "/data/partitioning_screen.ui")
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
            self.sys_type.set_label(_("System type: ") + "UEFI")  # pyright: ignore[reportCallIssue]
        else:
            self.sys_type.set_label(_("System type: ") + "BIOS")  # pyright: ignore[reportCallIssue]
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
        self.part_table.set_label(_("Partition table: ") + str(partition_table))  # pyright: ignore[reportCallIssue]
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
            "kgx"  # GNOME Console
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
        context = box.get_style_context()
        context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        context.add_class("partition-box")
        context.add_class(color)

        if first:
            context.add_class("first-partition")
        if last:
            context.add_class("last-partition")

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
        color_box.get_style_context().add_class(color)
        # center the color box
        color_box.set_halign(Gtk.Align.CENTER)
        # dont vertically expand the color box
        color_box.set_valign(Gtk.Align.CENTER)
        context = color_box.get_style_context()
        context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
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
            self.selected_partition.get_style_context().remove_class("selected")
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
            self.selected_partition.get_style_context().remove_class("selected")

        if self.selectable:
            # Set the clicked box as the selected partition
            self.selected_partition = box
            # Add a selection style to the clicked box
            box.get_style_context().add_class("selected")
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


class CheckPartitioningThread(threading.Thread):
    def __init__(self, window):
        threading.Thread.__init__(self)
        self.window = window

    def run(self):
        while True:
            if part_event.is_set():
                break
            if self.window.validate_selection():
                win.next_btn.set_sensitive(True)
            else:
                win.next_btn.set_sensitive(False)
            sleep(0.5)


@Gtk.Template.from_file(script_dir + "/data/install_screen.ui")
class install_screen(Adw.Bin):
    __gtype_name__ = "install_screen"

    progress_bar = Gtk.Template.Child()
    curr_action = Gtk.Template.Child()
    console_text_view = Gtk.Template.Child()
    console = Gtk.Template.Child()  # GtkScrolledWindow

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.console_buffer = self.console_text_view.get_buffer()
        self.console_buffer.connect("changed", self.on_text_buffer_changed)

        self.colors = {
            "CRITICAL": "#a40000",
            "ERROR": "#ff0000",
            "EXCEPTION": "#ff0000",
            "WARNING": "#ffa500",
            "INFO": "#3584e4",
            "DEBUG": "#808080",
            "NOTSET": "#808080",
            "": "#808080",
            None: "#808080",
        }

    def on_text_buffer_changed(self, buffer):
        # Scroll to the end of the text buffer
        adj = self.console.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def console_logging(
        self,
        logging_level: int,
        message: str,
        *args,
        loginfo_filename="",
        loginfo_line_number=-1,
        loginfo_function_name="",
        loginfo_stack_info=None,
        **kwargs,
    ):
        logging_level_name = LoggingLevel(logging_level).name

        pos = message.find("%ST")
        if pos != -1:
            prs = message.rfind("%")
            stm = bakery.st_msgs[int(message[pos + 3 : prs])]
            self.progress_bar.set_fraction(stm[1] / 100)
            self.curr_action.set_label(stm[0])
        else:
            GLib.idle_add(
                lambda: (
                    self.console_buffer.insert_markup(
                        self.console_buffer.get_end_iter(),
                        "".join(
                            (
                                "- ",
                                '<span color="{:s}">',
                                logging_level_name.rjust(8, " "),
                                ": ",
                                "</span>",
                            )
                        ).format(self.colors[logging_level_name]),
                        -1,
                    )
                )
            )

            if LoggingLevel(logging_level) != LoggingLevel.DEBUG:
                GLib.idle_add(
                    lambda: (
                        self.console_buffer.insert(
                            self.console_buffer.get_end_iter(), "".join((message, "\n"))
                        )
                    )
                )
            else:
                GLib.idle_add(
                    lambda: (
                        self.console_buffer.insert_markup(
                            self.console_buffer.get_end_iter(),
                            "".join(
                                (
                                    '<span color="{:s}">',
                                    GLib.markup_escape_text(message),
                                    "</span>" "\n",
                                )
                            ).format(self.colors[logging_level_name]),
                            -1,
                        )
                    )
                )

@Gtk.Template.from_file(script_dir + "/data/packages_screen.ui")
class packages_screen(Gtk.Box):
    __gtype_name__ = "packages_screen"

    packages_box = Gtk.Template.Child()
    
    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        lp("Initializing packages screen", "info")
        
        # Get current architecture
        self.current_arch = platform.machine()
        lp(f"Current architecture: {self.current_arch}", "debug")
        
        # Load packages data
        self.packages = get_packages_list()
        lp(f"Loaded {len(self.packages) if isinstance(self.packages, list) else 1} top-level package groups", "info")
        
        # State tracking
        self.selection_state = {}  # key -> bool (selected state)
        self.checkboxes = {}       # key -> Gtk.CheckButton
        self.group_hierarchy = {}  # group_key -> {"packages": [pkg_keys], "subgroups": [grp_keys]}
        self.parent_map = {}       # child_key -> parent_key
        self._updating = False     # prevent signal loops during programmatic updates
        
        # Package tracking
        self.package_metadata = {}  # pkg_key -> {"name": str, "post_install": str}
        self.group_metadata = {}    # grp_key -> {"post_install": str}
        
        # UI state
        self.current_category = None
        self.filtered_packages = []
        
        # Build and show UI
        self._build_ui()
        lp("Package screen initialization complete", "info")
    

    def _escape_html(self, s, quote=True):
        """
        Replace special characters "&", "<" and ">" to HTML-safe sequences.
        If the optional flag quote is true (the default), the quotation mark
        characters, both double quote (") and single quote (') characters are also
        translated.
        """
        s = s.replace("&", "&amp;") # Must be done first!
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
        if quote:
            s = s.replace('"', "&quot;")
            s = s.replace('\'', "&#x27;")
        return s

    def _build_ui(self):
        """Build the complete package selection UI with two-panel layout (Box + Separator)"""
        lp("Building two-panel package selection UI", "info")
        
        # Create main horizontal box container
        main_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing=5)
        main_box.set_hexpand(True)
        main_box.set_vexpand(True)
        self.packages_box.append(main_box)
        
        # Left panel - Categories
        left_box = self._build_categories_panel()
        left_box.set_hexpand(False)
        left_box.set_size_request(280, -1)  # Fixed width for categories panel
        main_box.append(left_box)
        
        # Separator
        separator = Gtk.Separator.new(Gtk.Orientation.VERTICAL)
        separator.set_vexpand(True)
        main_box.append(separator)
        
        # Right panel - Applications
        right_box = self._build_applications_panel()
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

        lp("Built two-panel UI successfully", "info")

    def _build_categories_panel(self):
        """Build and return the left panel with categories and search"""
        # Create left panel container
        left_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, spacing=12)
        left_box.set_margin_top(12)
        left_box.set_margin_start(12)
        left_box.set_margin_bottom(12)
        left_box.set_margin_end(6)
        left_box.set_size_request(280, -1)
        left_box.set_hexpand(True)
        left_box.set_vexpand(True)
        
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
        reset_btn.connect("clicked", self._on_default_selections)
        header_row.append(reset_btn)

        left_box.append(header_row)
        
        # Search entry
        self.search_entry = Gtk.SearchEntry.new()
        self.search_entry.set_placeholder_text("Search applications and categories...")
        self.search_entry.connect("search-changed", self._on_search_changed)
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
        self.categories_list.connect("row-selected", self._on_category_selected)
        categories_scrolled.set_child(self.categories_list)
        
        # Populate categories
        self._populate_categories()
        
        return left_box

    def _build_applications_panel(self):
        """Build and return the right panel for application selection"""
        # Create right panel container
        right_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, spacing=12)
        right_box.set_margin_top(12)
        right_box.set_margin_end(12)
        right_box.set_margin_bottom(12)
        right_box.set_margin_start(6)
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
        self.applications_list.set_valign(Gtk.Align.START)  # <-- Set vertical alignment to start
        apps_scrolled.set_child(self.applications_list)
        
        return right_box

    def _populate_categories(self):
        """Populate the categories list"""
        groups = self.packages if isinstance(self.packages, list) else [self.packages]
        
        for grp_data in groups:
            if self._is_valid_group(grp_data) and self._is_arch_compatible(grp_data):
                self._add_category_row(grp_data, [])

    def _add_category_row(self, group_data, parent_path, depth=0):
        """Add a category row to the categories list"""
        name = group_data.get("name", "Unnamed")
        current_path = parent_path + [name]
        group_key = self._make_group_key(current_path)
        
        row = Gtk.ListBoxRow.new()
        row.group_data = group_data
        row.group_key = group_key
        row.depth = depth
        
        row_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing=8)
        row_box.set_margin_top(8)
        row_box.set_margin_bottom(8)
        row_box.set_margin_start(8 + (depth * 16))
        row_box.set_margin_end(8)
        
        icon_name = group_data.get("icon")
        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_icon_size(Gtk.IconSize.NORMAL)
            row_box.append(icon)
        
        label = Gtk.Label.new(name)
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        row_box.append(label)
        
        # Show expand arrow as a flat button if this group/subgroup has subgroups
        subgroups = group_data.get("subgroups", [])
        has_subgroups = any(self._is_valid_group(sg) and self._is_arch_compatible(sg) for sg in subgroups)
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
            def on_arrow_clicked(btn, row=row, group_data=group_data, depth=depth, arrow_icon=arrow_icon):
                if getattr(row, "expanded", False):
                    self._collapse_category(row)
                    arrow_icon.set_from_icon_name("go-next-symbolic")
                else:
                    self._expand_category(row, group_data, depth)
                    arrow_icon.set_from_icon_name("go-down-symbolic")
            arrow_btn.connect("clicked", on_arrow_clicked)
        
        row.set_child(row_box)
        self.categories_list.append(row)
        
        self.group_hierarchy[group_key] = {"packages": [], "subgroups": []}
        
        packages = group_data.get("packages", [])
        for pkg_data in packages:
            if self._is_valid_package(pkg_data) and self._is_arch_compatible(pkg_data):
                pkg_key = self._create_package_key(pkg_data, current_path, group_key)

    def _create_package_key(self, pkg_data, parent_path, group_key):
        """Create package key and store metadata"""
        if isinstance(pkg_data, str):
            name = pkg_data
            post_install = None
        else:
            name = pkg_data.get("name", "")
            post_install = pkg_data.get("post-install")
        
        pkg_key = self._make_package_key(parent_path, name)
        
        # Store package metadata
        self.package_metadata[pkg_key] = {
            "name": name,
            "post_install": post_install,
            "data": pkg_data
        }
        
        # Add to group hierarchy
        self.group_hierarchy[group_key]["packages"].append(pkg_key)
        self.parent_map[pkg_key] = group_key
        
        return pkg_key

    def _on_category_selected(self, list_box, row):
        """Handle category selection and expansion logic"""
        if not row:
            return

        group_data = getattr(row, "group_data", None)
        group_key = getattr(row, "group_key", None)
        has_subgroups = getattr(row, "has_subgroups", False)
        depth = getattr(row, "depth", 0)

        # Check if category is empty (no packages and no valid subgroups after arch filtering)
        packages = group_data.get("packages", []) if isinstance(group_data, dict) else []
        has_packages = any(
            self._is_valid_package(pkg) and self._is_arch_compatible(pkg)
            for pkg in packages
        )
        subgroups = group_data.get("subgroups", []) if isinstance(group_data, dict) else []
        has_valid_subgroups = any(
            self._is_valid_group(sg) and self._is_arch_compatible(sg)
            for sg in subgroups
        )
        if not has_packages and not has_valid_subgroups:
            return  # Do nothing if category is truly empty

        # Pre-select children if group/subgroup is selected
        if isinstance(group_data, dict) and group_data.get("selected", False):
            self._select_group_and_children(group_data, group_key)

        # If it has subgroups, expand always
        if has_subgroups:
            if not getattr(row, "expanded", False):
                self._expand_category(row, group_data, depth)
            # Only select and show packages if there are packages
            if has_packages:
                self.categories_list.select_row(row)
                self._show_category_packages(group_data, group_key)
        else:
            # Just select and show packages
            self.categories_list.select_row(row)
            self._show_category_packages(group_data, group_key)

    def _select_group_and_children(self, group_data, group_key):
        """Recursively select group/subgroup and its children packages/subgroups unless selected: false is set"""
        # Only select if selected is True or not specified (default True)
        selected = group_data.get("selected")
        if selected is False:
            return  # Do not select this group or its children

        # Select the group itself
        self.selection_state[group_key] = True

        # Select all packages in this group
        packages = group_data.get("packages", [])
        for pkg_data in packages:
            if self._is_valid_package(pkg_data) and self._is_arch_compatible(pkg_data):
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
            if self._is_valid_group(sg) and self._is_arch_compatible(sg):
                sg_name = sg.get("name", "Unnamed")
                sg_key = f"grp:{'/'.join(group_key.split('/')[1:] + [sg_name])}"
                self._select_group_and_children(sg, sg_key)

    def _expand_category(self, row, group_data, depth):
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
        row_index = self._get_row_index(row)
        subgroups = group_data.get("subgroups", [])
        parent_path = group_data.get("name", "").split("/")
        for i, sub_data in enumerate(subgroups):
            if self._is_valid_group(sub_data) and self._is_arch_compatible(sub_data):
                self._insert_category_row(sub_data, parent_path, depth + 1, row_index + i + 1)

    def _collapse_category(self, row):
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
        self._remove_subgroup_rows(row)

    def _insert_category_row(self, group_data, parent_path, depth, index):
        """Insert a category row at specific index"""
        name = group_data.get("name", "Unnamed")
        current_path = parent_path + [name]
        group_key = self._make_group_key(current_path)
        row = Gtk.ListBoxRow.new()
        row.group_data = group_data
        row.group_key = group_key
        row.depth = depth
        row.is_subgroup = True
        row_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing=8)
        row_box.set_margin_top(8)
        row_box.set_margin_bottom(8)
        row_box.set_margin_start(8 + (depth * 16))
        row_box.set_margin_end(8)
        icon_name = group_data.get("icon")
        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_icon_size(Gtk.IconSize.NORMAL)
            row_box.append(icon)
        label = Gtk.Label.new(name)
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        row_box.append(label)
        # Show expand arrow as a flat button if this subgroup has subgroups
        subgroups = group_data.get("subgroups", [])
        has_subgroups = any(self._is_valid_group(sg) and self._is_arch_compatible(sg) for sg in subgroups)
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
            def on_arrow_clicked(btn, row=row, group_data=group_data, depth=depth, arrow_icon=arrow_icon):
                if getattr(row, "expanded", False):
                    self._collapse_category(row)
                    arrow_icon.set_from_icon_name("go-next-symbolic")
                else:
                    self._expand_category(row, group_data, depth)
                    arrow_icon.set_from_icon_name("go-down-symbolic")
            arrow_btn.connect("clicked", on_arrow_clicked)
        row.set_child(row_box)
        self.categories_list.insert(row, index)

    def _get_row_index(self, target_row):
        """Get the index of a row in the list"""
        index = 0
        row = self.categories_list.get_row_at_index(0)
        while row:
            if row == target_row:
                return index
            index += 1
            row = self.categories_list.get_row_at_index(index)
        return -1

    def _remove_subgroup_rows(self, parent_row):
        """Remove all subgroup rows after the parent"""
        parent_index = self._get_row_index(parent_row)
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

    def _show_category_packages(self, group_data, group_key):
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
            desc_label.set_halign(Gtk.Align.START)
            desc_label.set_valign(Gtk.Align.START)
            desc_label.set_margin_bottom(8)
            desc_label.add_css_class("dim-label")
            # Insert after applications_label in the right panel
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
            if self._is_valid_package(pkg_data) and self._is_arch_compatible(pkg_data):
                pkg_row = self._create_application_row(pkg_data, group_key)
                if pkg_row:
                    self.applications_list.append(pkg_row)

    def _create_application_row(self, pkg_data, group_key):
        """Create an application row for the right panel"""
        # Normalize package data
        if isinstance(pkg_data, str):
            name = pkg_data
            description = ""
            selected = False
            immutable = False
        else:
            name = pkg_data.get("name", "")
            description = pkg_data.get("description", "")
            selected = pkg_data.get("selected", False)
            immutable = pkg_data.get("immutable", False) or pkg_data.get("critical", False)
        
        if not name:
            return None
        
        # Create package key (simplified for current category)
        pkg_key = f"pkg:{group_key}/{name}"
        
        # Initialize selection state if not exists
        if pkg_key not in self.selection_state:
            self.selection_state[pkg_key] = selected
        
        # Create action row
        action_row = Adw.ActionRow.new()
        action_row.set_title(name)
        
        if description:
            safe_description = self._escape_html(description)
            action_row.set_subtitle(safe_description)
        
        # Create checkbox
        checkbox = Gtk.CheckButton.new()
        checkbox.set_active(self.selection_state[pkg_key])
        checkbox.set_sensitive(not immutable)
        
        # Store checkbox reference
        self.checkboxes[pkg_key] = checkbox
        
        # Connect signal
        checkbox.connect("toggled", self._on_application_toggled, pkg_key)
        
        # Add checkbox to row
        action_row.add_suffix(checkbox)
        action_row.set_activatable_widget(checkbox)
        
        return action_row

    def _on_application_toggled(self, checkbox, pkg_key):
        """Handle application checkbox toggle"""
        if self._updating:
            return
        
        active = checkbox.get_active()
        self.selection_state[pkg_key] = active
        
        pkg_name = pkg_key.split("/")[-1]
        lp(f"Application '{pkg_name}' toggled to: {active}", "debug")

    def _on_search_changed(self, search_entry):
        """Handle search in categories and packages"""
        search_text = search_entry.get_text().lower().strip()

        # Remove previous search category if present
        def remove_search_category():
            child = self.categories_list.get_first_child()
            while child:
                group_data = getattr(child, "group_data", None)
                if isinstance(group_data, dict) and group_data.get("_is_search_category"):
                    self.categories_list.remove(child)
                    break
                child = child.get_next_sibling()

        remove_search_category()

        # Step 1: Expand all groups and subgroups
        def expand_all_rows():
            child = self.categories_list.get_first_child()
            while child:
                if getattr(child, "has_subgroups", False) and not getattr(child, "expanded", False):
                    self._expand_category(child, child.group_data, child.depth)
                child = child.get_next_sibling()
            # Recursively expand subgroups
            expanded = True
            while expanded:
                expanded = False
                child = self.categories_list.get_first_child()
                while child:
                    if getattr(child, "has_subgroups", False) and not getattr(child, "expanded", False):
                        self._expand_category(child, child.group_data, child.depth)
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
                if getattr(child, "has_subgroups", False) and getattr(child, "expanded", False):
                    self._collapse_category(child)
                child = child.get_next_sibling()
            # Show applications for selected category only
            selected_row = self.categories_list.get_selected_row()
            if selected_row:
                self._show_category_packages(selected_row.group_data, selected_row.group_key)
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
                        if search_text in pkg_name.lower() or search_text in pkg_desc.lower():
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
                        if search_text in pkg_name.lower() or search_text in pkg_desc.lower():
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
            def recurse(grp, group_key):
                packages = grp.get("packages", [])
                for pkg in packages:
                    if self._is_valid_package(pkg) and self._is_arch_compatible(pkg):
                        if isinstance(pkg, dict):
                            pkg_name = pkg.get("name", "")
                            pkg_desc = pkg.get("description", "")
                            if search_text in pkg_name.lower() or search_text in pkg_desc.lower():
                                matches.append(pkg)
                        elif isinstance(pkg, str):
                            if search_text in pkg.lower():
                                matches.append(pkg)
                for sg in grp.get("subgroups", []):
                    if self._is_valid_group(sg) and self._is_arch_compatible(sg):
                        recurse(sg, group_key)
            groups_list = groups if isinstance(groups, list) else [groups]
            for grp in groups_list:
                if self._is_valid_group(grp) and self._is_arch_compatible(grp):
                    recurse(grp, grp.get("name", ""))
            return matches

        matches = collect_matching_packages(self.packages)

        # Step 5: Create and insert the hidden search category
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
        self._show_category_packages(search_category_data, "grp:search")

    def _on_default_selections(self, button):
        """Handle default selections button"""
        lp("Applying default package selections", "info")
        
        # Reset all selections
        for key in self.selection_state:
            self.selection_state[key] = False
            checkbox = self.checkboxes.get(key)
            if checkbox:
                checkbox.set_active(False)
        
        # Apply default selections from package data
        groups = self.packages if isinstance(self.packages, list) else [self.packages]
        self._apply_default_selections(groups, [])

    def _apply_default_selections(self, groups, parent_path):
        """Recursively apply default selections"""
        for grp_data in groups:
            if not (self._is_valid_group(grp_data) and self._is_arch_compatible(grp_data)):
                continue
            
            name = grp_data.get("name", "Unnamed")
            current_path = parent_path + [name]
            
            # Apply defaults to packages in this group
            packages = grp_data.get("packages", [])
            for pkg_data in packages:
                if self._is_valid_package(pkg_data) and self._is_arch_compatible(pkg_data):
                    if isinstance(pkg_data, dict) and pkg_data.get("selected", False):
                        pkg_name = pkg_data.get("name", "")
                        pkg_key = f"pkg:{self._make_group_key(current_path)}/{pkg_name}"
                        if pkg_key in self.selection_state:
                            self.selection_state[pkg_key] = True
                            checkbox = self.checkboxes.get(pkg_key)
                            if checkbox:
                                checkbox.set_active(True)
            
            # Recurse into subgroups
            subgroups = grp_data.get("subgroups", [])
            if subgroups:
                self._apply_default_selections(subgroups, current_path)

    def _select_first_category(self):
        """Select the first group and deepest first subgroup (recursively) if present"""
        def select_deepest_subgroup(row):
            # Expand and select the first subgroup if available
            if getattr(row, "has_subgroups", False):
                self._expand_category(row, row.group_data, row.depth)
                # Find the next row (first subgroup after expansion)
                next_index = self._get_row_index(row) + 1
                subgroup_row = self.categories_list.get_row_at_index(next_index)
                if subgroup_row and getattr(subgroup_row, "is_subgroup", False):
                    self.categories_list.select_row(subgroup_row)
                    self._on_category_selected(self.categories_list, subgroup_row)
                    # Recursively go deeper if this subgroup also has subgroups
                    select_deepest_subgroup(subgroup_row)

        first_row = self.categories_list.get_row_at_index(0)
        if first_row:
            self.categories_list.select_row(first_row)
            self._on_category_selected(self.categories_list, first_row)
            select_deepest_subgroup(first_row)

    def _is_valid_group(self, data):
        """Check if group data is valid"""
        return isinstance(data, dict) and data.get("name")

    def _make_group_key(self, path):
        """Create unique key for group"""
        return "grp:" + "/".join(path)

    def _make_package_key(self, path, name):
        """Create unique key for package"""
        return "pkg:" + "/".join(path + [name])

    def _is_valid_package(self, data):
        """Check if package data is valid"""
        if isinstance(data, str):
            return True
        return isinstance(data, dict) and data.get("name")

    def get_selected_packages_with_metadata(self):
        """Get selected packages and post-install scripts"""
        selected_packages = []
        post_install_scripts = []
        
        # Collect selected packages
        for key, is_selected in self.selection_state.items():
            if key.startswith("pkg:") and is_selected:
                metadata = self.package_metadata.get(key, {})
                pkg_name = metadata.get("name", key.split("/")[-1])
                selected_packages.append(pkg_name)
                
                # Add post-install script if exists
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
        unique_packages = list(dict.fromkeys(selected_packages))
        unique_scripts = list(dict.fromkeys(post_install_scripts))
        
        lp(f"Selected {len(unique_packages)} packages with {len(unique_scripts)} post-install scripts", "info")
        
        return {
            "packages": sorted(unique_packages),
            "post_install_scripts": unique_scripts
        }

    def get_selected_packages(self):
        """Get list of selected package names (backward compatibility)"""
        metadata = self.get_selected_packages_with_metadata()
        result = metadata["packages"]
        
        # Print the current list of selected packages
        print(f"\n=== SELECTED PACKAGES ({len(result)}) ===")
        for i, pkg in enumerate(result, 1):
            print(f"{i:3d}. {pkg}")
        print("=" * 40)
        
        # Print post-install scripts if any
        scripts = metadata["post_install_scripts"]
        if scripts:
            print(f"\n=== POST-INSTALL SCRIPTS ({len(scripts)}) ===")
            for i, script in enumerate(scripts, 1):
                print(f"{i:3d}. {script}")
            print("=" * 40)
        
        return result

    def _is_arch_compatible(self, item_data):
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


@Gtk.Template.from_file(script_dir + "/data/finish_screen.ui")
class finish_screen(Adw.Bin):
    __gtype_name__ = "finish_screen"

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window


if __name__ == "__main__":
    app = BakeryApp(application_id="org.bredos.bakery")
    app.run(argv)
