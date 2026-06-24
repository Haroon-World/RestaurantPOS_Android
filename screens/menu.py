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
    get_menu_items, add_menu_item, update_menu_item,
    delete_menu_item, search_menu_items
)

# ─── Shared style constants ────────────────────────────────────────────────────

BG     = (0.08, 0.08, 0.10, 1)
CARD   = (0.12, 0.13, 0.16, 1)
ACCENT = (0.12, 0.33, 0.55, 1)
GREEN  = (0.16, 0.65, 0.27, 1)
DANGER = (0.86, 0.20, 0.21, 1)
GREY   = (0.35, 0.35, 0.40, 1)
TEXT   = (0.95, 0.95, 0.95, 1)
SUBTEXT= (0.65, 0.65, 0.70, 1)


def styled_btn(text, bg=ACCENT, **kw):
    return Button(
        text=text, background_normal='', background_color=bg,
        color=TEXT, font_size=dp(14), bold=True,
        size_hint_y=None, height=dp(46), **kw
    )


def styled_input(hint='', **kw):
    return TextInput(
        hint_text=hint, background_color=(0.18, 0.19, 0.23, 1),
        foreground_color=TEXT, hint_text_color=SUBTEXT,
        cursor_color=TEXT, font_size=dp(15),
        size_hint_y=None, height=dp(46),
        padding=[dp(10), dp(10)], multiline=False, **kw
    )


def show_popup(title, message):
    content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
    content.add_widget(Label(text=message, color=TEXT, font_size=dp(13),
                             halign='center', size_hint_y=None, height=dp(80)))
    btn = styled_btn('OK', bg=ACCENT)
    content.add_widget(btn)
    p = Popup(title=title, content=content,
              size_hint=(0.85, None), height=dp(200),
              background_color=CARD, title_color=TEXT,
              separator_color=ACCENT)
    btn.bind(on_press=p.dismiss)
    p.open()


# ─── Menu Item Row ─────────────────────────────────────────────────────────────

class MenuItemRow(BoxLayout):
    def __init__(self, item, on_edit, on_delete, **kwargs):
        super().__init__(orientation='horizontal',
                         size_hint_y=None, height=dp(52),
                         spacing=dp(6), **kwargs)
        self.item = item

        with self.canvas.before:
            Color(*CARD)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=self._upd, size=self._upd)

        name_lbl = Label(
            text=item['item_name'], font_size=dp(14), color=TEXT,
            size_hint_x=0.50, halign='left', valign='middle'
        )
        name_lbl.bind(size=name_lbl.setter('text_size'))
        self.add_widget(name_lbl)

        self.add_widget(Label(
            text=f"Rs {item['price']:.2f}", font_size=dp(13),
            color=ACCENT, size_hint_x=0.25
        ))

        edit_btn = Button(
            text='✏', background_normal='', background_color=ACCENT,
            color=TEXT, font_size=dp(16),
            size_hint_x=None, width=dp(44)
        )
        edit_btn.bind(on_press=lambda *_: on_edit(item))
        self.add_widget(edit_btn)

        del_btn = Button(
            text='🗑', background_normal='', background_color=DANGER,
            color=TEXT, font_size=dp(16),
            size_hint_x=None, width=dp(44)
        )
        del_btn.bind(on_press=lambda *_: on_delete(item))
        self.add_widget(del_btn)

    def _upd(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


# ─── Menu Screen ───────────────────────────────────────────────────────────────

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._editing_id = None

        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
        with root.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda i, v: setattr(self._bg, 'pos', v),
                  size=lambda i, v: setattr(self._bg, 'size', v))

        # Title
        root.add_widget(Label(
            text='[b]Menu Management[/b]', markup=True,
            font_size=dp(20), color=ACCENT,
            size_hint_y=None, height=dp(46), halign='left'
        ))

        # ── Add / Edit form ────────────────────────────────────────────────────
        form_box = BoxLayout(orientation='vertical', size_hint_y=None,
                             height=dp(165), spacing=dp(6))
        form_box.add_widget(Label(
            text='[b]Add / Edit Item[/b]', markup=True,
            font_size=dp(13), color=ACCENT,
            size_hint_y=None, height=dp(24), halign='left'
        ))
        self.inp_name  = styled_input('Item Name')
        self.inp_price = styled_input('Price (Rs)', input_type='number')
        form_box.add_widget(self.inp_name)
        form_box.add_widget(self.inp_price)

        btn_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.btn_add    = styled_btn('➕ Add',    bg=GREEN)
        self.btn_update = styled_btn('✔ Update',  bg=ACCENT)
        self.btn_clear  = styled_btn('✖ Clear',   bg=GREY)

        self.btn_update.disabled = True
        self.btn_add.bind(on_press=lambda *_: self.do_add())
        self.btn_update.bind(on_press=lambda *_: self.do_update())
        self.btn_clear.bind(on_press=lambda *_: self.clear_form())

        btn_row.add_widget(self.btn_add)
        btn_row.add_widget(self.btn_update)
        btn_row.add_widget(self.btn_clear)
        form_box.add_widget(btn_row)
        root.add_widget(form_box)

        # ── Search ────────────────────────────────────────────────────────────
        self.search_inp = styled_input('🔍 Search items…')
        self.search_inp.bind(text=self._on_search)
        root.add_widget(self.search_inp)

        # ── Item list ─────────────────────────────────────────────────────────
        scroll = ScrollView()
        self.item_list = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        self.item_list.bind(minimum_height=self.item_list.setter('height'))
        scroll.add_widget(self.item_list)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_enter(self):
        self.load_items()

    def load_items(self, data=None):
        self.item_list.clear_widgets()
        items = data if data is not None else get_menu_items()
        if not items:
            self.item_list.add_widget(Label(
                text='No menu items yet. Add one above.',
                color=SUBTEXT, font_size=dp(14),
                size_hint_y=None, height=dp(60)
            ))
            return
        for item in items:
            row = MenuItemRow(
                item,
                on_edit=self._on_edit,
                on_delete=self._on_delete
            )
            self.item_list.add_widget(row)

    def _on_search(self, instance, text):
        if text.strip():
            self.load_items(search_menu_items(text))
        else:
            self.load_items()

    def clear_form(self):
        self.inp_name.text  = ''
        self.inp_price.text = ''
        self._editing_id    = None
        self.btn_add.disabled    = False
        self.btn_update.disabled = True
        self.load_items()

    def _on_edit(self, item):
        self._editing_id     = item['id']
        self.inp_name.text   = item['item_name']
        self.inp_price.text  = str(item['price'])
        self.btn_add.disabled    = True
        self.btn_update.disabled = False

    def _on_delete(self, item):
        """Show confirmation popup then delete."""
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        content.add_widget(Label(
            text=f"Delete '{item['item_name']}'?",
            color=TEXT, font_size=dp(14), halign='center',
            size_hint_y=None, height=dp(50)
        ))
        btn_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        btn_yes = styled_btn('Yes, Delete', bg=DANGER)
        btn_no  = styled_btn('Cancel',      bg=GREY)
        btn_row.add_widget(btn_yes)
        btn_row.add_widget(btn_no)
        content.add_widget(btn_row)

        p = Popup(title='Confirm Delete', content=content,
                  size_hint=(0.80, None), height=dp(180),
                  background_color=CARD, title_color=TEXT,
                  separator_color=DANGER)

        def confirm(*_):
            success, msg = delete_menu_item(item['id'])
            p.dismiss()
            if success:
                self.load_items()
            else:
                show_popup('Error', msg)

        btn_yes.bind(on_press=confirm)
        btn_no.bind(on_press=p.dismiss)
        p.open()

    def _get_form_values(self):
        name  = self.inp_name.text.strip()
        price_str = self.inp_price.text.strip()
        if not name or not price_str:
            show_popup('Validation', 'Both name and price are required.')
            return None, None
        try:
            price = float(price_str)
        except ValueError:
            show_popup('Validation', 'Price must be a valid number.')
            return None, None
        return name, price

    def do_add(self):
        name, price = self._get_form_values()
        if name is None:
            return
        success, msg = add_menu_item(name, price)
        if success:
            show_popup('Success', msg)
            self.clear_form()
        else:
            show_popup('Error', msg)

    def do_update(self):
        if not self._editing_id:
            return
        name, price = self._get_form_values()
        if name is None:
            return
        success, msg = update_menu_item(self._editing_id, name, price)
        if success:
            show_popup('Updated', msg)
            self.clear_form()
        else:
            show_popup('Error', msg)
