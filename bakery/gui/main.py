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

import threading
from time import sleep

from bakery import config, lp, lrun, _, log_file
from bakery.misc import upload_log, reboot, detect_install_source
from bredos.logging import setup_handler
from bredos.utilities import (
    debounce,
    detect_device,
    detect_session_configuration,
    time_fn,
)
from pyrunning import LoggingHandler
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Gdk, GLib  # type: ignore

from .desktops import de_screen
from .finish import finish_screen
from .install import InstallThread, install_screen
from .keyboard import kb_screen
from .timezone import timezone_screen
from .locale import locale_screen
from .user import user_screen
from .partitioning import partitioning_screen
from .packages import packages_screen
from .summary import summary_screen


class BakeryApp(Adw.Application):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)
        # Force dark mode
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        self.css_provider = self.load_css()

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
            self.set_styling()
        win.present()

    def on_preferences_action(self, widget, _) -> None:
        """Callback for the app.preferences action."""
        # Implement your preferences logic here
        pass

    def on_about_action(self, widget, py) -> None:
        """Callback for the app.about action."""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name=_("BredOS Installer"),  # pyright: ignore[reportCallIssue]
            application_icon="org.bredos.bakery",
            developer_name="BredOS",
            debug_info=self.win.collect_data(show_pass=False),
            version=config.installer_version,
            developers=["Panda <panda@bredos.org>", "bill88t <bill88t@bredos.org>"],
            designers=["Panda <panda@bredos.org>", "DustyDaimler"],
            documenters=["Panda <panda@bredos.org>", "DroidMaster"],
            translator_credits=_(
                "translator-credits"
            ),  # pyright: ignore[reportCallIssue]
            copyright=_(
                "Copyright The BredOS developers"
            ),  # pyright: ignore[reportCallIssue]
            comments=_(
                "Bakery is a simple installer for BredOS"
            ),  # pyright: ignore[reportCallIssue]
            license_type=Gtk.License.GPL_3_0,
            website="https://BredOS.org",
            issue_url="https://github.com/BredOS/Bakery/issues",
            support_url="https://discord.gg/jwhxuyKXaa",
        )
        translators = ["Bill88t  <bill88t@bredos.org>", "Panda <panda@bredos.org>"]
        about.add_credit_section(
            _("Translated by"), translators
        )  # pyright: ignore[reportCallIssue]
        about.add_acknowledgement_section(
            _("Special thanks to"), ["Shivanandvp"]
        )  # pyright: ignore[reportCallIssue]
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

    def load_css(self):
        """create a provider for custom styling"""
        global css_provider
        css_provider = Gtk.CssProvider()
        try:
            css_provider.load_from_resource(
                resource_path="/org/bredos/bakery/ui/main.css"
            )
        except GLib.Error as e:
            lp(f"Error loading CSS : {e} ", mode="error")
            return None
        lp(f"loading custom styling", mode="debug")
        return css_provider

    def set_styling(self):
        if css_provider:
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_USER,
            )


@Gtk.Template(resource_path="/org/bredos/bakery/ui/window.ui")
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
        self.install_device = detect_device()
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
                self.log_dialog.set_heading(
                    _("Log upload failed")
                )  # pyright: ignore[reportCallIssue]
                self.log_dialog.set_body(
                    _(
                        "The log file could not be uploaded it can still be found at"
                    )  # pyright: ignore[reportCallIssue]
                    + '<br><a href="file://'
                    + log_file
                    + '">'
                    + log_file
                    + "</a>"
                )
            else:
                self.log_dialog.set_heading(
                    _("Log uploaded")
                )  # pyright: ignore[reportCallIssue]
                self.log_dialog.set_body(
                    _(
                        "The log file has been uploaded, you can find it at"
                    )  # pyright: ignore[reportCallIssue]
                    + '\n<a href="'
                    + logurl
                    + '">'
                    + logurl
                    + "</a>"
                    + '\n<a href="file://'
                    + log_file
                    + '">'
                    + log_file
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
                self.next_btn.set_label(
                    _("Install")
                )  # pyright: ignore[reportCallIssue]
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
                self.next_btn.set_label(
                    _("Install")
                )  # pyright: ignore[reportCallIssue]
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
                data["packages"]["extra_to_install"] = all_pages[
                    "Packages"
                ].collect_data()
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
        self.step_names = []  # Store name labels

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
                separator.add_css_class("step-separator")
                if i - 1 < self.current_page:
                    separator.add_css_class("separator-completed")
                elif i - 1 == self.current_page - 1:
                    separator.add_css_class("separator-current")
                else:
                    separator.add_css_class("separator-inactive")
                overlay.add_overlay(separator)
                self.step_separators.append(separator)

            # Step container (name label on top, circle below)
            step_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            step_container.set_size_request(75, -1)
            step_container.add_css_class("step-indicator-container")

            page_display_name = (
                pages_dict[page_name][1] if page_name in pages_dict else page_name
            )
            name_label = Gtk.Label(label=page_display_name)
            name_label.add_css_class("step-name")
            name_label.set_halign(Gtk.Align.CENTER)
            name_label.set_valign(Gtk.Align.CENTER)
            step_container.append(name_label)
            self.step_names.append(name_label)  # Store reference

            circle_button = Gtk.Button(label="")
            circle_button.set_can_target(False)
            circle_button.set_size_request(24, 24)
            circle_button.set_halign(Gtk.Align.CENTER)
            circle_button.set_valign(Gtk.Align.CENTER)
            circle_button.add_css_class("circular")
            if i == self.current_page:
                circle_button.add_css_class("current-step")
            elif i < self.current_page:
                circle_button.add_css_class("completed-step")
            else:
                circle_button.add_css_class("inactive-step")
            step_container.append(circle_button)
            self.step_circles.append(circle_button)  # Store reference

            overlay.set_child(step_container)
            self.steps_box.append(overlay)
            self.step_indicators.append(overlay)

    def update_step_indicators(self):
        """Update step indicators to show current progress and separator colors"""
        if not self.step_indicators:
            return
        for i, overlay in enumerate(self.step_indicators):
            # Use stored circle_button reference
            circle_button = self.step_circles[i]
            circle_button.remove_css_class("current-step")
            circle_button.remove_css_class("completed-step")
            circle_button.remove_css_class("inactive-step")
            if i == self.current_page:
                circle_button.add_css_class("current-step")
            elif i < self.current_page:
                circle_button.add_css_class("completed-step")
            else:
                circle_button.add_css_class("inactive-step")
            # Update separator color if present
            if i > 0:
                separator = self.step_separators[i - 1]
                separator.remove_css_class("separator-completed")
                separator.remove_css_class("separator-current")
                separator.remove_css_class("separator-inactive")
                if i - 1 < self.current_page:
                    separator.add_css_class("separator-completed")
                elif i - 1 == self.current_page - 1:
                    separator.add_css_class("separator-current")
                else:
                    separator.add_css_class("separator-inactive")
            # Update name label style for current step
            name_label = self.step_names[i]
            name_label.remove_css_class("current-step-name")
            if i == self.current_page:
                name_label.add_css_class("current-step-name")

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

        setup_handler([all_pages["Install"].console_logging])
        self.install_type = install_type
        self.current_page = 0

        # Create step indicators after pages are determined
        self.create_step_indicators()

        self.update_buttons()
        self.main_stk.set_visible_child(self.install_page.get_child())


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
