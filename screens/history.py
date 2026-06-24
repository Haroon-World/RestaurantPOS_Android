from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, RoundedRectangle

from database.db import (
    get_todays_bills, search_todays_bills,
    get_bill_details, get_settings
)
from receipt import generate_receipt

# ─── Shared colour constants ───────────────────────────────────────────────────

BG     = (0.08, 0.08, 0.10, 1)
CARD   = (0.12, 0.13, 0.16, 1)
ACCENT = (0.12, 0.33, 0.55, 1)
GREEN  = (0.16, 0.65, 0.27, 1)
DANGER = (0.86, 0.20, 0.21, 1)
TEXT   = (0.95, 0.95, 0.95, 1)
SUBTEXT= (0.65, 0.65, 0.70, 1)


class RoundedButton(Button):
    def __init__(self, bg_color=ACCENT, radius=8, **kwargs):
        self.bg_color = bg_color
        self.radius = radius
        super().__init__(
            background_normal='',
            background_color=(0,0,0,0),
            color=TEXT,
            font_size=dp(14),
            bold=True,
            size_hint_y=None,
            height=dp(46),
            **kwargs
        )
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(self.radius)])
        self.bind(pos=self._update_rect, size=self._update_rect)
        
    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

def styled_btn(text, bg=ACCENT, **kw):
    return RoundedButton(text=text, bg_color=bg, **kw)


def show_popup(title, message):
    content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
    content.add_widget(Label(
        text=message, color=TEXT, font_size=dp(13),
        halign='center', size_hint_y=None, height=dp(80)
    ))
    btn = styled_btn('OK', bg=ACCENT)
    content.add_widget(btn)
    p = Popup(title=title, content=content,
              size_hint=(0.85, None), height=dp(200),
              background_color=CARD, title_color=TEXT,
              separator_color=ACCENT)
    btn.bind(on_press=p.dismiss)
    p.open()


# ─── Bill row widget ───────────────────────────────────────────────────────────

class BillRow(Button):
    def __init__(self, bill, on_tap, **kwargs):
        text = (
            f"[b]#{bill['bill_id']}[/b]  {bill['customer_name']}\n"
            f"[color=aaaaaa]{bill['bill_time']}[/color]  "
            f"[color=4d9ee0]Rs {bill['total_amount']:.2f}[/color]"
        )
        super().__init__(
            text=text, markup=True,
            background_normal='', background_color=(0,0,0,0),
            color=TEXT, font_size=dp(13),
            size_hint_y=None, height=dp(62),
            halign='left', valign='middle',
            **kwargs
        )
        self.bind(size=self.setter('text_size'))
        self.bill = bill
        with self.canvas.before:
            Color(*CARD)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect, on_press=lambda *_: on_tap(bill))

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


# ─── History Screen ────────────────────────────────────────────────────────────

class HistoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
        with root.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda i, v: setattr(self._bg, 'pos', v),
            size=lambda i, v: setattr(self._bg, 'size', v)
        )

        # Title
        root.add_widget(Label(
            text="[b]Today's Sales History[/b]", markup=True,
            font_size=dp(20), color=ACCENT,
            size_hint_y=None, height=dp(46), halign='left'
        ))

        # Search bar
        self.search_inp = TextInput(
            hint_text='🔍 Search by Bill No or Customer Name…',
            background_color=(0.18, 0.19, 0.23, 1),
            foreground_color=TEXT, hint_text_color=SUBTEXT,
            cursor_color=TEXT, font_size=dp(14),
            size_hint_y=None, height=dp(46),
            padding=[dp(10), dp(10)], multiline=False
        )
        self.search_inp.bind(text=self._on_search)
        root.add_widget(self.search_inp)

        # Bill list
        scroll = ScrollView()
        self.bill_list = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        self.bill_list.bind(minimum_height=self.bill_list.setter('height'))
        scroll.add_widget(self.bill_list)
        root.add_widget(scroll)

        # Total bar
        self.total_label = Label(
            text="Today's Total Sales: Rs 0.00",
            font_size=dp(16), bold=True, color=ACCENT,
            size_hint_y=None, height=dp(44)
        )
        root.add_widget(self.total_label)

        self.add_widget(root)

    def on_enter(self):
        self.refresh_data()

    def refresh_data(self):
        self.search_inp.text = ''
        self._load_bills()

    def _load_bills(self, data=None):
        self.bill_list.clear_widgets()
        bills = data if data is not None else get_todays_bills()

        if not bills:
            self.bill_list.add_widget(Label(
                text='No bills recorded today.',
                color=SUBTEXT, font_size=dp(14),
                size_hint_y=None, height=dp(60)
            ))
            self.total_label.text = "Today's Total Sales: Rs 0.00"
            return

        total = 0.0
        for bill in bills:
            row = BillRow(bill, on_tap=self._on_bill_tap)
            self.bill_list.add_widget(row)
            total += float(bill['total_amount'])

        self.total_label.text = f"Today's Total Sales: Rs {total:.2f}"

    def _on_search(self, instance, text):
        if text.strip():
            self._load_bills(search_todays_bills(text))
        else:
            self._load_bills()

    def _on_bill_tap(self, bill):
        details = get_bill_details(bill['bill_id'])
        if not details:
            show_popup('Error', 'Bill details not found.')
            return
        self._show_details_popup(details)

    def _show_details_popup(self, details):
        info  = details['info']
        items = details['items']

        # Scrollable content
        scroll = ScrollView()
        content_grid = GridLayout(cols=1, spacing=dp(6),
                                  size_hint_y=None, padding=dp(12))
        content_grid.bind(minimum_height=content_grid.setter('height'))

        def row_lbl(txt, size=13, bold=False, color=TEXT):
            lbl = Label(
                text=f'[b]{txt}[/b]' if bold else txt,
                markup=bold, color=color,
                font_size=dp(size), halign='left', valign='middle',
                size_hint_y=None, height=dp(28)
            )
            lbl.bind(size=lbl.setter('text_size'))
            return lbl

        content_grid.add_widget(row_lbl(f"Bill #{info['bill_id']}", size=16, bold=True, color=ACCENT))
        content_grid.add_widget(row_lbl(f"Date: {info['bill_date']}  |  Time: {info['bill_time']}"))
        content_grid.add_widget(row_lbl(f"Customer: {info['customer_name']}", bold=True))
        if info.get('phone'):
            content_grid.add_widget(row_lbl(f"Phone: {info['phone']}"))
        if info.get('address'):
            content_grid.add_widget(row_lbl(f"Address: {info['address']}"))

        # Divider label
        content_grid.add_widget(Label(
            text='─' * 32, color=SUBTEXT,
            font_size=dp(11), size_hint_y=None, height=dp(20)
        ))

        # Items
        for i, it in enumerate(items, 1):
            content_grid.add_widget(row_lbl(
                f"{i}. {it['item_name']}  Rs{it['price']:.0f} × {it['quantity']} = Rs{it['subtotal']:.0f}"
            ))

        content_grid.add_widget(Label(
            text='─' * 32, color=SUBTEXT,
            font_size=dp(11), size_hint_y=None, height=dp(20)
        ))
        
        if float(info.get('delivery_charge', 0)) > 0 or float(info.get('service_charge', 0)) > 0:
            content_grid.add_widget(row_lbl(f"Subtotal: Rs {info.get('subtotal_amount', 0):.2f}", bold=True))
            if float(info.get('delivery_charge', 0)) > 0:
                content_grid.add_widget(row_lbl(f"Delivery Charge: Rs {info.get('delivery_charge', 0):.2f}"))
            if float(info.get('service_charge', 0)) > 0:
                content_grid.add_widget(row_lbl(f"Service Charge: Rs {info.get('service_charge', 0):.2f}"))
                
        content_grid.add_widget(row_lbl(
            f"Grand Total: Rs {info['total_amount']:.2f}",
            size=16, bold=True, color=ACCENT
        ))
        scroll.add_widget(content_grid)

        # Popup wrapper
        outer = BoxLayout(orientation='vertical', spacing=dp(8), padding=(0, 0, 0, dp(8)))
        outer.add_widget(scroll)

        btn_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8),
                            padding=(dp(8), 0))
        btn_reprint = styled_btn('🖨 Reprint Receipt', bg=GREEN)
        btn_close   = styled_btn('Close', bg=(0.35, 0.35, 0.40, 1))
        btn_row.add_widget(btn_reprint)
        btn_row.add_widget(btn_close)
        outer.add_widget(btn_row)

        popup = Popup(
            title=f"Bill Details — #{info['bill_id']}",
            content=outer,
            size_hint=(0.92, 0.80),
            background_color=CARD,
            title_color=TEXT,
            separator_color=ACCENT
        )

        def do_reprint(*_):
            settings = get_settings()
            cust_info = {
                'customer_name': info['customer_name'],
                'phone': info.get('phone', ''),
                'address': info.get('address', '')
            }
            try:
                filepath = generate_receipt(
                    info['bill_id'], info['bill_date'], info['bill_time'],
                    cust_info, items, info.get('subtotal_amount', info['total_amount']),
                    info['total_amount'], settings,
                    delivery_charge=info.get('delivery_charge', 0),
                    service_charge=info.get('service_charge', 0)
                )
                popup.dismiss()
                show_popup('Receipt Saved', f'Receipt saved to:\n{filepath}')
            except Exception as e:
                show_popup('Error', f'Failed to generate receipt:\n{e}')

        btn_reprint.bind(on_press=do_reprint)
        btn_close.bind(on_press=popup.dismiss)
        popup.open()
