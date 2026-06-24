from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.relativelayout import RelativeLayout
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line

import os
from database.db import get_menu_items, get_settings, save_bill
from receipt import generate_receipt
import printer

# ─── Colours & style constants ──────────────────────────────────────────────────

BG       = (0.08, 0.08, 0.10, 1)
CARD     = (0.12, 0.13, 0.16, 1)
ACCENT   = (0.12, 0.33, 0.55, 1)      # Blue
ACCENT2  = (0.16, 0.65, 0.27, 1)      # Green
DANGER   = (0.86, 0.20, 0.21, 1)      # Red
TEXT     = (0.95, 0.95, 0.95, 1)
SUBTEXT  = (0.65, 0.65, 0.70, 1)
PURPLE   = (0.44, 0.25, 0.55, 1)      # Purple
ORANGE   = (0.85, 0.45, 0.08, 1)      # Orange
ROW_BG   = (0.16, 0.17, 0.20, 1)      # Lighter card for item rows


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
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(self.radius)])
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
        height=dp(40),
        padding=[dp(10), dp(10)],
        multiline=False,
        **kw
    )


def styled_small_input(hint='', **kw):
    return TextInput(
        hint_text=hint,
        background_color=(0.18, 0.19, 0.23, 1),
        foreground_color=TEXT,
        hint_text_color=SUBTEXT,
        cursor_color=TEXT,
        font_size=dp(12),
        size_hint_y=None,
        height=dp(28),
        padding=[dp(6), dp(4)],
        multiline=False,
        **kw
    )


def show_popup(title, message):
    content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
    content.add_widget(Label(
        text=message, color=TEXT, font_size=dp(14),
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


# ─── Order item row widget ─────────────────────────────────────────────────────

class OrderItemRow(BoxLayout):
    def __init__(self, item_data, on_qty_change, on_remove, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None,
                         height=dp(56), spacing=dp(6), **kwargs)
        self.item_data = item_data

        with self.canvas.before:
            Color(*ROW_BG)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=self._update_bg, size=self._update_bg)

        text_box = BoxLayout(orientation='vertical', size_hint_x=0.45, padding=[dp(6), dp(4)])
        name_lbl = Label(
            text=item_data['item_name'], font_size=dp(13), bold=True, color=TEXT,
            halign='left', valign='middle', size_hint_y=0.6, shorten=True, shorten_from='right'
        )
        name_lbl.bind(size=name_lbl.setter('text_size'))

        price_lbl = Label(
            text=f"Rs {item_data['price']:.0f} each", font_size=dp(11), color=SUBTEXT,
            halign='left', valign='middle', size_hint_y=0.4
        )
        price_lbl.bind(size=price_lbl.setter('text_size'))

        text_box.add_widget(name_lbl)
        text_box.add_widget(price_lbl)
        self.add_widget(text_box)

        qty_box = BoxLayout(orientation='horizontal', size_hint_x=0.25, spacing=dp(4), padding=[0, dp(12)])

        btn_minus = RoundedButton(
            text='-', bg_color=CARD, radius=4, size_hint_x=0.3, height=dp(32),
            font_size=dp(18), bold=True
        )
        btn_minus.bind(on_press=lambda *_: on_qty_change(item_data, -1))

        self.qty_lbl = Label(
            text=str(item_data['quantity']), font_size=dp(12), bold=True, color=TEXT,
            halign='center', valign='middle', size_hint_x=0.4
        )

        btn_plus = RoundedButton(
            text='+', bg_color=ACCENT, radius=4, size_hint_x=0.3, height=dp(32),
            font_size=dp(18), bold=True
        )
        btn_plus.bind(on_press=lambda *_: on_qty_change(item_data, 1))

        qty_box.add_widget(btn_minus)
        qty_box.add_widget(self.qty_lbl)
        qty_box.add_widget(btn_plus)
        self.add_widget(qty_box)

        subtotal_lbl = Label(
            text=f"Rs {item_data['subtotal']:.0f}", font_size=dp(13), bold=True,
            color=ACCENT, halign='right', valign='middle', size_hint_x=0.2
        )
        subtotal_lbl.bind(size=subtotal_lbl.setter('text_size'))
        self.add_widget(subtotal_lbl)

        btn_del = RoundedButton(
            text='X', bg_color=DANGER, radius=6, size_hint_x=None, width=dp(32),
            height=dp(32), pos_hint={'center_y': 0.5}, font_size=dp(12), bold=True
        )
        btn_del.bind(on_press=lambda *_: on_remove(item_data))
        self.add_widget(btn_del)

    def _update_bg(self, instance, value):
        self._bg_rect.pos = instance.pos
        self._bg_rect.size = instance.size


# ─── Menu item tile ────────────────────────────────────────────────────────────

class MenuTile(Button):
    def __init__(self, item, on_tap, **kwargs):
        super().__init__(
            text=f"[b]{item['item_name']}[/b]\n[size=11]Rs {item['price']:.0f}[/size]",
            markup=True,
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=TEXT,
            font_size=dp(13),
            size_hint_y=None,
            height=dp(66),
            halign='center',
            valign='middle',
            shorten=True,
            shorten_from='right',
            **kwargs
        )
        self.item = item
        self.bind(size=self.setter('text_size'))
        with self.canvas.before:
            Color(*CARD)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect, on_press=lambda *_: on_tap(item))
        self.bind(state=self._on_state)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def _on_state(self, instance, state):
        self.canvas.before.clear()
        with self.canvas.before:
            if state == 'down':
                Color(CARD[0] * 1.3, CARD[1] * 1.3, CARD[2] * 1.3, CARD[3])
            else:
                Color(*CARD)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])


# ─── Billing Screen ────────────────────────────────────────────────────────────

class BillingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_items = []
        self.subtotal_amount = 0.0
        self.grand_total = 0.0
        self.menu_data = []
        self.settings = {}

        # ── Root layout ────────────────────────────────────────────────────────
        # The layout has 4 tiers added to root in order:
        #   1. header_card   (size_hint_y=None) — restaurant name
        #   2. body          (size_hint_y=1)    — scrollable menu + order list
        #   3. summary_row   (size_hint_y=None) — totals, ALWAYS VISIBLE
        #   4. btn_row       (size_hint_y=None) — action buttons, ALWAYS VISIBLE
        #
        # Kivy allocates space to fixed-height (size_hint_y=None) children
        # FIRST, then gives all remaining space to size_hint_y=1 children.
        # This guarantees tiers 3 and 4 are never pushed off screen.
        root = BoxLayout(orientation='vertical', padding=[dp(8), dp(6)], spacing=dp(6))
        with root.canvas.before:
            Color(*BG)
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)

        # ── Tier 1: Header ─────────────────────────────────────────────────────
        header_card = BoxLayout(orientation='horizontal', padding=[dp(12), dp(8)],
                                size_hint_y=None, height=dp(50))
        with header_card.canvas.before:
            Color(*CARD)
            self.header_bg = RoundedRectangle(pos=header_card.pos, size=header_card.size, radius=[dp(8)])
        header_card.bind(pos=lambda i, v: setattr(self.header_bg, 'pos', v),
                         size=lambda i, v: setattr(self.header_bg, 'size', v))

        self.title_label = Label(
            text='[b]Restaurant POS[/b]', markup=True,
            font_size=dp(18), color=ACCENT, halign='left', valign='middle'
        )
        self.title_label.bind(size=self.title_label.setter('text_size'))
        header_card.add_widget(self.title_label)

        lbl_billing_indicator = Label(
            text='Billing', font_size=dp(14), bold=True, color=TEXT,
            halign='right', valign='middle', size_hint_x=None, width=dp(80)
        )
        lbl_billing_indicator.bind(size=lbl_billing_indicator.setter('text_size'))
        header_card.add_widget(lbl_billing_indicator)
        root.add_widget(header_card)

        # ── Body: Left panel (42%) + Right panel (58%) ────────────────────────
        body = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=1)

        # ══════════════════════════════════════════════════════════════════════
        # LEFT PANEL (50%) — Customer Info & Menu Items
        # ══════════════════════════════════════════════════════════════════════
        left_panel = BoxLayout(orientation='vertical', size_hint_x=0.5, spacing=dp(6))

        # ── 1. Customer Info (collapsible) ─────────────────────────────────
        cust_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(4))
        cust_box.bind(minimum_height=cust_box.setter('height'))
        with cust_box.canvas.before:
            Color(*CARD)
            self.cust_bg = RoundedRectangle(pos=cust_box.pos, size=cust_box.size, radius=[dp(8)])
        cust_box.bind(pos=lambda i, v: setattr(self.cust_bg, 'pos', v),
                      size=lambda i, v: setattr(self.cust_bg, 'size', v))

        cust_header = BoxLayout(size_hint_y=None, height=dp(36), padding=[dp(8), 0])
        self.title_cust = Label(
            text='[b]Cust. Info[/b] (Walk-in)', markup=True,
            font_size=dp(12), color=TEXT, halign='left', valign='middle',
            shorten=True, shorten_from='right'
        )
        self.title_cust.bind(size=self.title_cust.setter('text_size'))
        self.btn_toggle_cust = Button(
            text='Show', size_hint_x=None, width=dp(55),
            background_normal='', background_color=(0, 0, 0, 0), color=ACCENT,
            font_size=dp(11), bold=True
        )
        self.btn_toggle_cust.bind(on_press=self.toggle_customer_info)
        cust_header.add_widget(self.title_cust)
        cust_header.add_widget(self.btn_toggle_cust)
        cust_box.add_widget(cust_header)

        self.cust_inputs = GridLayout(cols=1, size_hint_y=None, spacing=dp(4), padding=[dp(8), dp(4)])
        self.cust_inputs.bind(minimum_height=self.cust_inputs.setter('height'))
        self.inp_name    = styled_input('Customer Name')
        self.inp_phone   = styled_input('Phone (11 digits)', input_type='number')
        self.inp_address = styled_input('Address')
        self.cust_inputs.add_widget(self.inp_name)
        self.cust_inputs.add_widget(self.inp_phone)
        self.cust_inputs.add_widget(self.inp_address)
        self.cust_inputs.height = 0
        self.cust_inputs.opacity = 0
        self.cust_inputs.disabled = True
        cust_box.add_widget(self.cust_inputs)
        left_panel.add_widget(cust_box)

        # ── 2. Menu Items Header & Search ───────────────────────────
        menu_header = BoxLayout(size_hint_y=None, height=dp(36), padding=[dp(8), 0])
        with menu_header.canvas.before:
            Color(*CARD)
            self._menu_hdr_bg = RoundedRectangle(pos=menu_header.pos, size=menu_header.size, radius=[dp(8)])
        menu_header.bind(pos=lambda i, v: setattr(self._menu_hdr_bg, 'pos', v),
                         size=lambda i, v: setattr(self._menu_hdr_bg, 'size', v))
        
        lbl_menu = Label(
            text='[b]Menu Items[/b]', markup=True,
            font_size=dp(12), color=TEXT, halign='left', valign='middle'
        )
        lbl_menu.bind(size=lbl_menu.setter('text_size'))
        
        self.lbl_total_items = Label(
            text='Total Items: 0', font_size=dp(11), color=SUBTEXT,
            size_hint_x=None, width=dp(100), halign='right', valign='middle'
        )
        self.lbl_total_items.bind(size=self.lbl_total_items.setter('text_size'))
        
        menu_header.add_widget(lbl_menu)
        menu_header.add_widget(self.lbl_total_items)
        left_panel.add_widget(menu_header)

        self.menu_search = styled_input('Search menu...')
        self.menu_search.bind(text=self._on_menu_search_change)
        left_panel.add_widget(self.menu_search)

        # ── 3. Menu Grid (Fills remaining height) ───────────────────────────
        menu_scroll = ScrollView(size_hint_y=1)
        self.menu_grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.menu_grid.bind(minimum_height=self.menu_grid.setter('height'))
        self.menu_grid.bind(width=self._on_grid_width)
        menu_scroll.add_widget(self.menu_grid)
        left_panel.add_widget(menu_scroll)
        
        body.add_widget(left_panel)

        # ══════════════════════════════════════════════════════════════════════
        # RIGHT PANEL (50%) — Current Order, Summary, and Action Buttons
        # ══════════════════════════════════════════════════════════════════════
        order_panel = BoxLayout(orientation='vertical', size_hint_x=0.5, spacing=dp(6))
        
        # ── 1. Current Order List (Scrollable) ───────────────────────────
        order_panel.add_widget(Label(
            text='[b]Current Order[/b]', markup=True,
            font_size=dp(13), color=ACCENT,
            size_hint_y=None, height=dp(20), halign='center'
        ))

        self.order_scroll = ScrollView(size_hint_y=1)
        self.order_list = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        self.order_list.bind(minimum_height=self.order_list.setter('height'))
        self.order_scroll.add_widget(self.order_list)
        order_panel.add_widget(self.order_scroll)

        # ── 2. Order Summary card ───────────────────────────────────────────
        self.summary_card = BoxLayout(
            orientation='vertical',
            padding=[dp(8), dp(6)], spacing=dp(4),
            size_hint_y=None, height=dp(130)
        )
        with self.summary_card.canvas.before:
            Color(*CARD)
            self.summary_bg = RoundedRectangle(
                pos=self.summary_card.pos, size=self.summary_card.size, radius=[dp(8)]
            )
        self.summary_card.bind(
            pos=lambda i, v: setattr(self.summary_bg, 'pos', v),
            size=lambda i, v: setattr(self.summary_bg, 'size', v)
        )

        lbl_sum_title = Label(
            text="[b]Order Summary[/b]", markup=True, font_size=dp(12), color=ACCENT,
            size_hint_y=None, height=dp(16), halign='left'
        )
        lbl_sum_title.bind(size=lbl_sum_title.setter('text_size'))
        self.summary_card.add_widget(lbl_sum_title)

        row_subtotal = BoxLayout(size_hint_y=None, height=dp(16))
        lbl_sub = Label(text="Subtotal", color=SUBTEXT, font_size=dp(11), halign='left')
        lbl_sub.bind(size=lbl_sub.setter('text_size'))
        row_subtotal.add_widget(lbl_sub)
        self.lbl_subtotal = Label(text="Rs 0.00", color=TEXT, font_size=dp(11), halign='right')
        self.lbl_subtotal.bind(size=self.lbl_subtotal.setter('text_size'))
        row_subtotal.add_widget(self.lbl_subtotal)
        self.summary_card.add_widget(row_subtotal)

        row_delivery = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(6))
        lbl_del = Label(text="Delivery", color=SUBTEXT, font_size=dp(11),
                        halign='left', size_hint_x=0.5)
        lbl_del.bind(size=lbl_del.setter('text_size'))
        row_delivery.add_widget(lbl_del)
        self.inp_delivery = styled_small_input('0')
        self.inp_delivery.bind(text=self._on_charge_change)
        row_delivery.add_widget(self.inp_delivery)
        self.summary_card.add_widget(row_delivery)

        row_service = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(6))
        lbl_srv = Label(text="Service", color=SUBTEXT, font_size=dp(11),
                        halign='left', size_hint_x=0.5)
        lbl_srv.bind(size=lbl_srv.setter('text_size'))
        row_service.add_widget(lbl_srv)
        self.inp_service = styled_small_input('0')
        self.inp_service.bind(text=self._on_charge_change)
        row_service.add_widget(self.inp_service)
        self.summary_card.add_widget(row_service)

        row_total = BoxLayout(size_hint_y=None, height=dp(22))
        lbl_gt = Label(text="Grand Total", color=TEXT, font_size=dp(13), bold=True, halign='left')
        lbl_gt.bind(size=lbl_gt.setter('text_size'))
        row_total.add_widget(lbl_gt)
        self.lbl_grand_total = Label(text="Rs 0.00", color=ACCENT, font_size=dp(14), bold=True, halign='right')
        self.lbl_grand_total.bind(size=self.lbl_grand_total.setter('text_size'))
        row_total.add_widget(self.lbl_grand_total)
        self.summary_card.add_widget(row_total)

        order_panel.add_widget(self.summary_card)

        # ── 3. Action Buttons (Clear & Print) ───────────────────────────────
        button_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(6))
        
        btn_clear = RoundedButton(
            text='Clear', bg_color=DANGER,
            size_hint_x=0.35, size_hint_y=None, height=dp(40),
            font_size=dp(13), bold=True
        )
        btn_clear.bind(on_press=lambda *_: self.clear_form())
        button_row.add_widget(btn_clear)

        btn_save_bill = RoundedButton(
            text='Save & Print', bg_color=ACCENT2,
            size_hint_x=0.65, size_hint_y=None, height=dp(40),
            font_size=dp(13), bold=True
        )
        btn_save_bill.bind(on_press=lambda *_: self.process_save_bill())
        button_row.add_widget(btn_save_bill)
        
        order_panel.add_widget(button_row)

        # ── 5. Bottom padding (ensures buttons never touch the NavBar) ──────
        order_panel.add_widget(Label(size_hint_y=None, height=dp(80)))

        body.add_widget(order_panel)
        root.add_widget(body)

        self.add_widget(root)

    def _update_bg(self, instance, value):
        self._bg_rect.pos = instance.pos
        self._bg_rect.size = instance.size

    def on_enter(self):
        self.refresh_data()
        self._refresh_order_list()

    def refresh_data(self):
        self.settings = get_settings()
        rest_name = self.settings.get('restaurant_name', 'Restaurant POS')
        self.title_label.text = f'[b]{rest_name}[/b]'
        self.menu_data = get_menu_items()

        self.inp_delivery.text = str(self.settings.get('default_delivery_charge', 0.0))
        self.inp_service.text = str(self.settings.get('default_service_charge', 0.0))

        self.lbl_total_items.text = f"Total Items: {len(self.menu_data)}"

        self._build_menu_grid(self.menu_data)

    def _on_grid_width(self, instance, width):
        if width > dp(240):
            instance.cols = 2
        else:
            instance.cols = 1

    def toggle_customer_info(self, *args):
        if self.cust_inputs.height == 0:
            self.cust_inputs.height = dp(120)
            self.cust_inputs.opacity = 1
            self.cust_inputs.disabled = False
            self.btn_toggle_cust.text = 'Hide'
            self.title_cust.text = '[b]Cust. Info[/b]'
        else:
            self.cust_inputs.height = 0
            self.cust_inputs.opacity = 0
            self.cust_inputs.disabled = True
            self.btn_toggle_cust.text = 'Show'
            self.title_cust.text = '[b]Cust. Info[/b] (Walk-in)'

    def _on_menu_search_change(self, instance, text):
        Clock.unschedule(self._do_menu_search)
        Clock.schedule_once(lambda dt: self._do_menu_search(text), 0.3)

    def _do_menu_search(self, text):
        if text.strip():
            filtered = [i for i in self.menu_data
                        if text.lower() in i['item_name'].lower()]
        else:
            filtered = self.menu_data
        self._build_menu_grid(filtered)

    def _build_menu_grid(self, items):
        self.menu_grid.clear_widgets()
        if not items:
            self.menu_grid.add_widget(Label(
                text='No items found', color=SUBTEXT,
                font_size=dp(13), size_hint_y=None, height=dp(40)
            ))
            return
        for item in items:
            tile = MenuTile(item, on_tap=self._on_menu_tap)
            self.menu_grid.add_widget(tile)

    def _on_menu_tap(self, item):
        self._add_to_order(item, 1)

    def _add_to_order(self, item, qty):
        subtotal = item['price'] * qty
        for existing in self.current_items:
            if existing['item_name'] == item['item_name']:
                existing['quantity'] += qty
                existing['subtotal'] += subtotal
                self._refresh_order_list()
                return
        self.current_items.append({
            'item_name': item['item_name'],
            'price': item['price'],
            'quantity': qty,
            'subtotal': subtotal
        })
        self._refresh_order_list()

    def _change_item_qty(self, item_data, delta):
        for existing in self.current_items:
            if existing['item_name'] == item_data['item_name']:
                new_qty = existing['quantity'] + delta
                if new_qty <= 0:
                    self._remove_from_order(item_data)
                else:
                    existing['quantity'] = new_qty
                    existing['subtotal'] = existing['price'] * new_qty
                    self._refresh_order_list()
                return

    def _remove_from_order(self, item_data):
        self.current_items = [i for i in self.current_items
                              if i['item_name'] != item_data['item_name']]
        self._refresh_order_list()

    def _on_charge_change(self, instance, text):
        self._refresh_order_list()

    def _refresh_order_list(self):
        self.order_list.clear_widgets()
        self.subtotal_amount = sum(i['subtotal'] for i in self.current_items)

        if not self.current_items:
            lbl_empty = Label(
                text='No items added yet\nTap a menu item to start an order',
                color=SUBTEXT, font_size=dp(13), halign='center', valign='middle',
                size_hint_y=None, height=dp(100)
            )
            lbl_empty.bind(size=lbl_empty.setter('text_size'))
            self.order_list.add_widget(lbl_empty)
        else:
            for item in self.current_items:
                row = OrderItemRow(item, on_qty_change=self._change_item_qty, on_remove=self._remove_from_order)
                self.order_list.add_widget(row)

        try:
            del_charge = float(self.inp_delivery.text.strip() or '0')
            srv_charge = float(self.inp_service.text.strip() or '0')
        except ValueError:
            del_charge = 0.0
            srv_charge = 0.0

        self.grand_total = self.subtotal_amount + del_charge + srv_charge

        self.lbl_subtotal.text = f"Rs {self.subtotal_amount:.2f}"
        self.lbl_grand_total.text = f"Rs {self.grand_total:.2f}"

    def clear_form(self):
        """Clears the current order. Only called when user explicitly presses Clear Order."""
        self.inp_name.text = ''
        self.inp_phone.text = ''
        self.inp_address.text = ''
        self.current_items = []
        self.cust_inputs.height = 0
        self.cust_inputs.opacity = 0
        self.cust_inputs.disabled = True
        self.btn_toggle_cust.text = 'Show'
        self.title_cust.text = '[b]Cust. Info[/b] (Walk-in)'
        self._refresh_order_list()

    def _validate_and_collect(self):
        if not self.current_items:
            show_popup('Empty Bill', 'Please add at least one item.')
            return None
        cust_name  = self.inp_name.text.strip() or 'Walk-in Customer'
        cust_phone = self.inp_phone.text.strip()
        cust_addr  = self.inp_address.text.strip()
        if cust_phone and (not cust_phone.isdigit() or len(cust_phone) != 11):
            show_popup('Validation Error', 'Phone must be exactly 11 digits.')
            return None
        return cust_name, cust_phone, cust_addr

    def process_save_bill(self, silent=False):
        """
        Save & Print Bill flow:
          1. Validate inputs
          2. Save to SQLite database
          3. Generate PDF receipt to Documents/RestaurantPOS/Receipts/
          4. Print to Bluetooth thermal printer
          5. Show success/error popup
          Order is NOT cleared — only clear_form() does that.
        """
        data = self._validate_and_collect()
        if not data:
            return None
        cust_name, cust_phone, cust_addr = data

        try:
            del_charge = float(self.inp_delivery.text.strip() or '0')
            srv_charge = float(self.inp_service.text.strip() or '0')
        except ValueError:
            show_popup('Validation Error', 'Charges must be valid numbers.')
            return None

        try:
            bill_id, bill_date, bill_time = save_bill(
                cust_name, cust_phone, cust_addr,
                self.current_items, self.subtotal_amount,
                delivery_charge=del_charge, service_charge=srv_charge
            )

            cust_info = {'customer_name': cust_name, 'phone': cust_phone, 'address': cust_addr}
            filepath = generate_receipt(
                bill_id, bill_date, bill_time,
                cust_info, self.current_items,
                self.subtotal_amount, self.grand_total, self.settings,
                delivery_charge=del_charge, service_charge=srv_charge
            )
            
            pdf_saved = os.path.exists(filepath)

            if not silent:
                printer_mac = self.settings.get('printer_mac', '')
                if not printer_mac:
                    msg = f"Bill #{bill_id} saved.\nPDF generated at:\n{filepath}\n\nNo printer selected in Settings."
                    if not pdf_saved:
                        msg += "\nWarning: PDF file may not have saved correctly."
                    show_popup('Bill Saved (No Printer)', msg)
                else:
                    success, error_msg = printer.print_bill(
                        printer_mac, bill_id, bill_date, bill_time,
                        cust_info, self.current_items,
                        self.subtotal_amount, self.grand_total, self.settings,
                        delivery_charge=del_charge, service_charge=srv_charge
                    )
                    
                    if success:
                        msg = f"Bill #{bill_id} saved and printed.\nPDF Location:\n{filepath}"
                        if not pdf_saved:
                            msg += "\nWarning: PDF file may not have saved correctly."
                        show_popup('Success', msg)
                    else:
                        msg = f"Bill #{bill_id} saved.\nPDF Location:\n{filepath}\n\nPrinter Error:\n{error_msg}"
                        show_popup('Printer Error', msg)

            return bill_id, bill_date, bill_time, cust_name, cust_phone, cust_addr, del_charge, srv_charge

        except Exception as e:
            import traceback
            traceback.print_exc()
            show_popup('Error', f'Failed to save or generate receipt:\n{e}')
            return None
