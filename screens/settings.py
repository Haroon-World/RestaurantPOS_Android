import os
import shutil
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.image import Image
from kivy.uix.filechooser import FileChooserIconView

# Only import what still exists in db.py (license/PIN functions were removed)
from database.db import (
    get_settings, save_settings,
    update_history_retention, perform_history_cleanup
)
import printer

BG     = (0.08, 0.08, 0.10, 1)
CARD   = (0.12, 0.13, 0.16, 1)
ACCENT = (0.12, 0.33, 0.55, 1)
GREEN  = (0.16, 0.65, 0.27, 1)
DANGER = (0.86, 0.20, 0.21, 1)
GREY   = (0.35, 0.35, 0.40, 1)
TEXT   = (0.95, 0.95, 0.95, 1)
SUBTEXT = (0.65, 0.65, 0.70, 1)


def get_logo_dir():
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        context = PythonActivity.mActivity
        logo_dir = os.path.join(context.getExternalFilesDir(None).getAbsolutePath(), 'logo')
        os.makedirs(logo_dir, exist_ok=True)
        return logo_dir
    except Exception:
        pass
    # Desktop fallback
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_dir = os.path.join(base, 'logo')
    os.makedirs(logo_dir, exist_ok=True)
    return logo_dir


class RoundedButton(Button):
    def __init__(self, bg_color=ACCENT, radius=8, **kwargs):
        self.bg_color = bg_color
        self.radius = radius
        defaults = {
            'background_normal': '',
            'background_color': (0, 0, 0, 0),
            'color': TEXT,
            'font_size': dp(14),
            'bold': True,
            'size_hint_y': None,
            'height': dp(46)
        }
        defaults.update(kwargs)
        super().__init__(**defaults)
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(self.radius)]
            )
        self.bind(pos=self._update_rect, size=self._update_rect)
        self.bind(state=self._on_state)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def _on_state(self, instance, state):
        self.canvas.before.clear()
        with self.canvas.before:
            if state == 'down':
                Color(self.bg_color[0] * 0.8, self.bg_color[1] * 0.8, self.bg_color[2] * 0.8, self.bg_color[3])
            else:
                Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(self.radius)])


def styled_btn(text, bg=ACCENT, **kw):
    return RoundedButton(text=text, bg_color=bg, **kw)


def styled_input(hint='', **kw):
    return TextInput(
        hint_text=hint,
        background_color=(0.18, 0.19, 0.23, 1),
        foreground_color=TEXT,
        hint_text_color=SUBTEXT,
        cursor_color=TEXT,
        font_size=dp(14),
        size_hint_y=None,
        height=dp(44),
        padding=[dp(10), dp(10)],
        multiline=False,
        **kw
    )


def show_popup(title, message):
    content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
    content.add_widget(Label(
        text=message, color=TEXT, font_size=dp(13),
        size_hint_y=None, height=dp(80), halign='center'
    ))
    btn = styled_btn('OK', bg=ACCENT)
    content.add_widget(btn)
    p = Popup(
        title=title,
        content=content,
        size_hint=(0.85, None),
        height=dp(200),
        background_color=CARD,
        title_color=TEXT,
        separator_color=ACCENT
    )
    btn.bind(on_press=p.dismiss)
    p.open()


def _make_card(color=CARD, radius=10):
    box = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(12),
                    size_hint_y=None)
    box.bind(minimum_height=box.setter('height'))
    with box.canvas.before:
        Color(*color)
        rect = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(radius)])
    box.bind(pos=lambda i, v: setattr(rect, 'pos', v),
             size=lambda i, v: setattr(rect, 'size', v))
    return box


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.logo_path = ""
        self.settings = {}
        self.selected_printer_mac = ""
        self.printers_dict = {}

        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
        with root.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda i, v: setattr(self._bg, 'pos', v),
            size=lambda i, v: setattr(self._bg, 'size', v)
        )

        # ── Title ──────────────────────────────────────────────────────────────
        root.add_widget(Label(
            text="[b]⚙  Restaurant Settings[/b]", markup=True,
            font_size=dp(20), color=ACCENT,
            size_hint_y=None, height=dp(46), halign='left'
        ))

        scroll = ScrollView()
        self.container = GridLayout(cols=1, spacing=dp(12), size_hint_y=None)
        self.container.bind(minimum_height=self.container.setter('height'))

        # ── SECTION 1: Restaurant Info ─────────────────────────────────────────
        sec_info = _make_card()
        sec_info.add_widget(Label(
            text="🏪  Restaurant Information",
            font_size=dp(14), bold=True, color=ACCENT,
            size_hint_y=None, height=dp(28), halign='left'
        ))

        def _lbl(txt):
            return Label(text=txt, color=TEXT, font_size=dp(12),
                         size_hint_y=None, height=dp(18), halign='left')

        sec_info.add_widget(_lbl("Restaurant Name:"))
        self.inp_name = styled_input("Restaurant Name")
        sec_info.add_widget(self.inp_name)

        sec_info.add_widget(_lbl("Phone Number:"))
        self.inp_phone = styled_input("Phone Number")
        sec_info.add_widget(self.inp_phone)

        sec_info.add_widget(_lbl("Address:"))
        self.inp_address = styled_input("Address")
        sec_info.add_widget(self.inp_address)

        sec_info.add_widget(_lbl("Default Delivery Charge (Rs):"))
        self.inp_delivery = styled_input("0", input_type='number')
        sec_info.add_widget(self.inp_delivery)

        sec_info.add_widget(_lbl("Default Service Charge (Rs):"))
        self.inp_service = styled_input("0", input_type='number')
        sec_info.add_widget(self.inp_service)

        sec_info.add_widget(_lbl("Custom Receipt Footer Message:"))
        self.inp_receipt_msg = TextInput(
            hint_text="e.g. Thank you for visiting!",
            background_color=(0.18, 0.19, 0.23, 1),
            foreground_color=TEXT, hint_text_color=SUBTEXT, cursor_color=TEXT,
            font_size=dp(13), size_hint_y=None, height=dp(70),
            padding=[dp(10), dp(10)], multiline=True
        )
        sec_info.add_widget(self.inp_receipt_msg)

        # ── Restaurant Logo Upload UI ──
        sec_info.add_widget(_lbl("Restaurant Logo:"))
        logo_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        
        self.logo_preview = Image(source='', size_hint=(None, None), size=(dp(48), dp(48)), allow_stretch=True)
        logo_row.add_widget(self.logo_preview)
        
        self.lbl_logo_status = Label(
            text="No logo selected", color=SUBTEXT, font_size=dp(11),
            size_hint_x=0.5, halign='left', valign='middle'
        )
        self.lbl_logo_status.bind(size=self.lbl_logo_status.setter('text_size'))
        logo_row.add_widget(self.lbl_logo_status)
        
        logo_btns = BoxLayout(orientation='vertical', size_hint_x=0.35, spacing=dp(2))
        btn_select_logo = styled_btn("Choose Logo", bg=ACCENT, height=dp(24), font_size=dp(11))
        btn_remove_logo = styled_btn("Remove Logo", bg=DANGER, height=dp(24), font_size=dp(11))
        
        # Adjust text padding/wrapping for small buttons
        for btn in [btn_select_logo, btn_remove_logo]:
            btn.halign = 'center'
            btn.valign = 'middle'
            btn.bind(size=btn.setter('text_size'))
            
        btn_select_logo.bind(on_press=self.choose_logo)
        btn_remove_logo.bind(on_press=self.remove_logo)
        
        logo_btns.add_widget(btn_select_logo)
        logo_btns.add_widget(btn_remove_logo)
        logo_row.add_widget(logo_btns)
        
        sec_info.add_widget(logo_row)

        btn_save = styled_btn("💾  Save Settings", bg=GREEN)
        btn_save.bind(on_press=self.save_restaurant_info)
        sec_info.add_widget(btn_save)
        self.container.add_widget(sec_info)

        # ── SECTION 2: History Retention ──────────────────────────────────────
        sec_ret = _make_card()
        sec_ret.add_widget(Label(
            text="📊  Customer History Retention",
            font_size=dp(14), bold=True, color=ACCENT,
            size_hint_y=None, height=dp(28), halign='left'
        ))
        sec_ret.add_widget(Label(
            text="Records older than the selected period are automatically pruned.",
            font_size=dp(11), color=SUBTEXT,
            size_hint_y=None, height=dp(28), halign='left', valign='top'
        ))
        self.retention_spinner = Spinner(
            text='1 Day',
            values=('1 Day', '2 Days', '3 Days'),
            background_normal='',
            background_color=(0.18, 0.19, 0.23, 1),
            color=TEXT,
            font_size=dp(14),
            size_hint_y=None,
            height=dp(44)
        )
        self.retention_spinner.bind(text=self.on_retention_change)
        sec_ret.add_widget(self.retention_spinner)
        self.container.add_widget(sec_ret)

        # ── SECTION 3: Receipt Printer ─────────────────────────────────────────
        sec_printer = _make_card()
        sec_printer.add_widget(Label(
            text="🖨️  Receipt Printer (Bluetooth)",
            font_size=dp(14), bold=True, color=ACCENT,
            size_hint_y=None, height=dp(28), halign='left'
        ))
        
        self.lbl_printer_debug = Label(
            text="Found 0 paired Bluetooth devices",
            font_size=dp(11), color=SUBTEXT,
            size_hint_y=None, height=dp(18), halign='left'
        )
        self.lbl_printer_debug.bind(size=self.lbl_printer_debug.setter('text_size'))
        sec_printer.add_widget(self.lbl_printer_debug)
        
        self.btn_select_printer = styled_btn("Select Printer", bg=(0.18, 0.19, 0.23, 1))
        self.btn_select_printer.bind(on_press=self.open_printer_popup)
        sec_printer.add_widget(self.btn_select_printer)
        
        btn_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(46), spacing=dp(8))

        btn_test_printer = styled_btn("Test Printer", bg=ACCENT)
        btn_test_printer.bind(on_press=self.test_printer)
        btn_row.add_widget(btn_test_printer)
        
        sec_printer.add_widget(btn_row)
        
        self.container.add_widget(sec_printer)

        scroll.add_widget(self.container)
        root.add_widget(scroll)
        self.add_widget(root)

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def on_enter(self):
        self.load_settings_data()

    def load_settings_data(self):
        self.settings = get_settings()
        if self.settings:
            self.inp_name.text      = self.settings.get('restaurant_name', '') or ''
            self.inp_phone.text     = self.settings.get('phone', '') or ''
            self.inp_address.text   = self.settings.get('address', '') or ''
            self.inp_delivery.text  = str(self.settings.get('default_delivery_charge', 0.0))
            self.inp_service.text   = str(self.settings.get('default_service_charge', 0.0))
            self.inp_receipt_msg.text = self.settings.get('custom_receipt_message', '') or ''
            self.logo_path          = self.settings.get('logo_path', '') or ''

            if self.logo_path and os.path.exists(self.logo_path):
                self.lbl_logo_status.text = f"Selected: {os.path.basename(self.logo_path)}"
                self.logo_preview.source = self.logo_path
                self.logo_preview.reload()
            else:
                self.logo_path = ""
                self.lbl_logo_status.text = "No logo selected"
                self.logo_preview.source = ""

            days_map = {1: '1 Day', 2: '2 Days', 3: '3 Days'}
            ret_days = self.settings.get('history_retention_days', 1)
            self.retention_spinner.text = days_map.get(ret_days, '1 Day')

            self.printers_dict = printer.get_paired_printers()
            count = len(self.printers_dict)
            self.lbl_printer_debug.text = f"Found {count} paired Bluetooth devices"
            
            self.selected_printer_mac = self.settings.get('printer_mac', '')
            
            selected_name = 'Select Printer'
            for name, mac in self.printers_dict.items():
                if mac == self.selected_printer_mac:
                    selected_name = f"{name}\n[size=11]{mac}[/size]"
                    break
                    
            if self.selected_printer_mac and selected_name == 'Select Printer':
                selected_name = f"Unknown Printer\n[size=11]{self.selected_printer_mac}[/size]"
                
            self.btn_select_printer.text = selected_name
            self.btn_select_printer.markup = True

    # ── Actions ────────────────────────────────────────────────────────────────

    def choose_logo(self, *args):
        try:
            from plyer import filechooser
            # Open the native file picker
            filechooser.open_file(on_selection=self._on_logo_selected, filters=[("Image files", "*.png", "*.jpg", "*.jpeg")])
        except Exception as e:
            # Fallback or error message
            show_popup("Error", f"Could not open gallery:\n{e}")

    def _on_logo_selected(self, selection):
        if not selection or not selection[0]:
            return
        from kivy.clock import Clock
        # Ensure UI updates run on the main thread
        Clock.schedule_once(lambda dt: self._process_selected_logo(selection[0]), 0)

    def _process_selected_logo(self, selected_file):
        try:
            ext = os.path.splitext(selected_file)[1].lower()
            if not ext:
                ext = ".png"
            dest_dir = get_logo_dir()
            dest_path = os.path.join(dest_dir, f"logo{ext}")
            
            shutil.copy2(selected_file, dest_path)
            
            self.logo_path = dest_path
            self.lbl_logo_status.text = f"Selected: {os.path.basename(dest_path)}"
            self.logo_preview.source = dest_path
            self.logo_preview.reload()
        except Exception as e:
            show_popup("Copy Error", f"Failed to save logo image:\n{e}")

    def remove_logo(self, *args):
        self.logo_path = ""
        self.lbl_logo_status.text = "No logo selected"
        self.logo_preview.source = ""

    def save_restaurant_info(self, *args):
        name        = self.inp_name.text.strip()
        phone       = self.inp_phone.text.strip()
        address     = self.inp_address.text.strip()
        delivery    = self.inp_delivery.text.strip() or "0"
        service     = self.inp_service.text.strip() or "0"
        receipt_msg = self.inp_receipt_msg.text.strip()

        if not name:
            show_popup("Validation Error", "Restaurant Name is required.")
            return

        try:
            delivery_val = float(delivery)
            service_val  = float(service)
        except ValueError:
            show_popup("Validation Error", "Charges must be valid numbers.")
            return

        try:
            save_settings(name, address, phone, self.logo_path,
                          delivery_val, service_val, receipt_msg, self.selected_printer_mac)
            show_popup("Saved ✓", "Settings saved successfully.")
            
            # Refresh billing screen title/charges if it's already loaded
            from kivy.app import App
            app = App.get_running_app()
            if app.sm.has_screen('billing'):
                app.sm.get_screen('billing').refresh_data()
        except Exception as e:
            show_popup("Database Error", f"Failed to save settings:\n{e}")

    def on_retention_change(self, spinner, text):
        days_map = {'1 Day': 1, '2 Days': 2, '3 Days': 3}
        days = days_map.get(text, 1)
        try:
            update_history_retention(days)
            perform_history_cleanup()
        except Exception as e:
            show_popup("Error", f"Failed to update retention:\n{e}")

    def open_printer_popup(self, *args):
        content = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(8))
        
        scroll = ScrollView(size_hint_y=1)
        grid = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        
        self.printers_dict = printer.get_paired_printers()
        count = len(self.printers_dict)
        self.lbl_printer_debug.text = f"Found {count} paired Bluetooth devices"
        
        if not self.printers_dict:
            grid.add_widget(Label(text="No paired printers found", color=SUBTEXT, size_hint_y=None, height=dp(40)))
        else:
            for name, mac in self.printers_dict.items():
                btn = styled_btn(f"{name}\n[size=11]{mac}[/size]", bg=CARD, radius=6)
                btn.markup = True
                btn.height = dp(56)
                btn.bind(on_press=lambda instance, n=name, m=mac: self._select_printer(n, m))
                grid.add_widget(btn)
                
        scroll.add_widget(grid)
        content.add_widget(scroll)
        
        btn_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(46), spacing=dp(8))
        btn_refresh = styled_btn("Refresh", bg=ACCENT)
        btn_refresh.bind(on_press=lambda *_: self._refresh_popup_list(grid))
        btn_cancel = styled_btn("Cancel", bg=DANGER)
        
        btn_row.add_widget(btn_refresh)
        btn_row.add_widget(btn_cancel)
        content.add_widget(btn_row)
        
        self.printer_popup = Popup(
            title="Select Bluetooth Printer",
            content=content,
            size_hint=(0.9, 0.8),
            background_color=BG,
            title_color=TEXT,
            separator_color=ACCENT
        )
        btn_cancel.bind(on_press=self.printer_popup.dismiss)
        self.printer_popup.open()
        
    def _refresh_popup_list(self, grid):
        grid.clear_widgets()
        self.printers_dict = printer.get_paired_printers()
        count = len(self.printers_dict)
        self.lbl_printer_debug.text = f"Found {count} paired Bluetooth devices"
        
        if not self.printers_dict:
            grid.add_widget(Label(text="No paired printers found", color=SUBTEXT, size_hint_y=None, height=dp(40)))
        else:
            for name, mac in self.printers_dict.items():
                btn = styled_btn(f"{name}\n[size=11]{mac}[/size]", bg=CARD, radius=6)
                btn.markup = True
                btn.height = dp(56)
                btn.bind(on_press=lambda instance, n=name, m=mac: self._select_printer(n, m))
                grid.add_widget(btn)

    def _select_printer(self, name, mac):
        self.selected_printer_mac = mac
        self.btn_select_printer.text = f"{name}\n[size=11]{mac}[/size]"
        if hasattr(self, 'printer_popup'):
            self.printer_popup.dismiss()
            
    def test_printer(self, *args):
        if not hasattr(self, 'selected_printer_mac') or not self.selected_printer_mac:
            show_popup("Error", "Please select a printer from the dropdown first.")
            return
            
        success, msg = printer.print_test(self.selected_printer_mac)
        if success:
            show_popup("Success", "Test receipt sent to printer.")
        else:
            show_popup("Printer Error", f"Failed to print test:\n{msg}")
