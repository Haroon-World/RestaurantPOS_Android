"""
Restaurant POS — Kivy Android App
===================================
Entry point. Fast 3-stage startup model:

  Stage 1  build()       — Only LoadingScreen created → renders immediately
  Stage 2  on_start()    — DB init runs on a background thread (non-blocking)
  Stage 3  _add_*()      — Screens created one per frame after DB is ready
                           so Android's layout engine resolves each screen's
                           sizes before the next one is added (no stacking).

Run on desktop:  python main.py
Build APK:       see build_apk.sh  (requires WSL2 / Linux + Buildozer)
"""

import os
import sys
import traceback
import threading

# ── Kivy environment must be configured BEFORE importing kivy modules ──────────
if os.name == "nt":
    os.environ["KIVY_GL_BACKEND"] = "angle_sdl2"   # Windows compatibility

# ─── Startup Logging ──────────────────────────────────────────────────────────
def safe_log_startup(message):
    print(f"[STARTUP] {message}")
    try:
        log_dir = "."
        if os.name == 'posix':
            log_dir = "/data/data/org.restaurantpos.restaurantpos/files/app"
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "pos_startup.log"), "a", encoding="utf-8") as f:
            import datetime
            f.write(f"{datetime.datetime.now()}: {message}\n")
    except Exception as e:
        print(f"[LOG ERROR] {e}")

def safe_log_crash(tb_msg):
    print(f"[CRASH]\n{tb_msg}", file=sys.stderr)
    try:
        log_dir = "."
        if os.name == 'posix':
            log_dir = "/data/data/org.restaurantpos.restaurantpos/files/app"
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "pos_startup_crash.log"), "a", encoding="utf-8") as f:
            import datetime
            f.write(f"{datetime.datetime.now()}:\n{tb_msg}\n")
    except Exception:
        pass

safe_log_startup("App process started.")

# ─── Stage 1 imports — only what's needed to show the loading screen ──────────
try:
    from kivy.app import App
    from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.metrics import dp
    from kivy.core.window import Window
    from kivy.graphics import Color, Rectangle
    from kivy.clock import Clock

    # Only import the DB bootstrap functions here — screen modules are imported lazily
    from database.db import initialize_database, perform_daily_cleanup

    safe_log_startup("Core imports done.")
except Exception as e:
    safe_log_crash(traceback.format_exc())
    sys.exit(1)


# ─── Colour palette ───────────────────────────────────────────────────────────
BG_DARK  = (0.08, 0.08, 0.10, 1)
NAV_BG   = (0.10, 0.11, 0.14, 1)
ACCENT   = (0.12, 0.33, 0.55, 1)
TEXT     = (0.95, 0.95, 0.95, 1)
SUBTEXT  = (0.55, 0.55, 0.60, 1)
DANGER   = (0.86, 0.20, 0.21, 1)

Window.clearcolor = BG_DARK


# ─── Loading Screen ───────────────────────────────────────────────────────────
class LoadingScreen(Screen):
    """Minimal screen shown immediately on launch. No DB dependency."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(16))
        with layout.canvas.before:
            Color(*BG_DARK)
            self._bg = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(pos=lambda i, v: setattr(self._bg, 'pos', v),
                    size=lambda i, v: setattr(self._bg, 'size', v))

        layout.add_widget(Label(size_hint_y=0.25))

        layout.add_widget(Label(
            text='🍴',
            font_size=dp(56),
            size_hint_y=None,
            height=dp(70),
            halign='center',
        ))

        layout.add_widget(Label(
            text='Restaurant POS',
            font_size=dp(24),
            color=TEXT,
            bold=True,
            halign='center',
            size_hint_y=None,
            height=dp(40),
        ))

        self._status_lbl = Label(
            text='Starting up.',
            font_size=dp(14),
            color=SUBTEXT,
            halign='center',
            size_hint_y=None,
            height=dp(28),
        )
        layout.add_widget(self._status_lbl)
        layout.add_widget(Label(size_hint_y=0.5))

        self.add_widget(layout)

        # Animated dots — gives immediate visual feedback that the app is alive
        self._dots = 0
        Clock.schedule_interval(self._tick_dots, 0.45)

    def _tick_dots(self, dt):
        self._dots = (self._dots % 3) + 1
        self._status_lbl.text = 'Starting up' + '.' * self._dots

    def show_error(self, message):
        Clock.unschedule(self._tick_dots)
        self._status_lbl.text = f'[color=ff4444]{message}[/color]'
        self._status_lbl.markup = True
        self._status_lbl.color = (1, 1, 1, 1)


# ─── Bottom Navigation Bar ────────────────────────────────────────────────────
class NavBar(BoxLayout):
    """Horizontal bottom nav. Tabs are inert until their screen is registered."""

    TABS = [
        ('billing',  '🧾', 'Billing'),
        ('menu',     '📋', 'Menu'),
        ('history',  '📊', 'History'),
        ('settings', '⚙',  'Settings'),
    ]

    def __init__(self, screen_manager, **kwargs):
        super().__init__(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(62),
            spacing=0,
            **kwargs
        )
        self.sm = screen_manager
        self._btns = {}

        with self.canvas.before:
            Color(*NAV_BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda i, v: setattr(self._bg, 'pos', v),
                  size=lambda i, v: setattr(self._bg, 'size', v))

        for name, icon, label in self.TABS:
            btn = Button(
                text=f'{icon}\n{label}',
                background_normal='',
                background_color=NAV_BG,
                color=SUBTEXT,
                font_size=dp(11),
                bold=False,
                halign='center',
                valign='middle',
            )
            btn.bind(on_press=lambda _, n=name: self.switch(n))
            self._btns[name] = btn
            self.add_widget(btn)

        self.sm.bind(current=self.on_screen_change)
        self.on_screen_change(None, self.sm.current)

    def switch(self, name):
        """Navigate to a tab. Silently ignored if the screen isn't ready yet."""
        if self.sm.has_screen(name):
            self.sm.current = name

    def on_screen_change(self, instance, current_screen):
        if current_screen == 'loading':
            # Hide nav bar completely while on loading screen
            self.height = 0
            self.opacity = 0
            self.disabled = True
        else:
            self.height = dp(62)
            self.opacity = 1
            self.disabled = False
            for n, btn in self._btns.items():
                if n == current_screen:
                    btn.background_color = ACCENT
                    btn.color = TEXT
                    btn.bold = True
                else:
                    btn.background_color = NAV_BG
                    btn.color = SUBTEXT
                    btn.bold = False


# ─── Main Application ─────────────────────────────────────────────────────────
class RestaurantPOSApp(App):
    title = 'Restaurant POS'

    # ── Stage 1: build() — fast, no DB, no heavy screens ──────────────────────
    def build(self):
        safe_log_startup("Stage 1: Building minimal UI...")
        try:
            root = BoxLayout(orientation='vertical')
            with root.canvas.before:
                Color(*BG_DARK)
                self._root_bg = Rectangle(pos=root.pos, size=root.size)
            root.bind(
                pos=lambda i, v: setattr(self._root_bg, 'pos', v),
                size=lambda i, v: setattr(self._root_bg, 'size', v),
            )

            sm = ScreenManager(transition=FadeTransition(duration=0.15))
            self.sm = sm

            # ONLY the loading screen — nothing else blocks the first frame
            sm.add_widget(LoadingScreen(name='loading'))

            nav = NavBar(screen_manager=sm)
            self.nav = nav

            root.add_widget(sm)
            root.add_widget(nav)

            safe_log_startup("Stage 1 complete — LoadingScreen rendered.")
            return root

        except Exception as e:
            safe_log_crash(traceback.format_exc())
            return Label(
                text=f"Fatal startup error:\n\n{traceback.format_exc()}",
                color=(1, 0.3, 0.3, 1),
                font_size=dp(11),
                halign='left',
                valign='top',
            )

    # ── Stage 2: on_start() — kick off background DB work ─────────────────────
    def on_start(self):
        safe_log_startup("Stage 2: Scheduling background DB initialisation...")
        if os.name != 'nt':
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.READ_EXTERNAL_STORAGE,
                    "android.permission.READ_MEDIA_IMAGES"
                ])
                safe_log_startup("Requested Android permissions.")
            except Exception as e:
                safe_log_startup(f"Could not request permissions: {e}")
        # Small delay so the loading screen animation has time to render at least once
        Clock.schedule_once(self._launch_bg_thread, 0.15)

    def _launch_bg_thread(self, dt):
        threading.Thread(target=self._bg_db_init, daemon=True).start()

    def _bg_db_init(self):
        """Runs on a background thread. Calls Clock to return to the main thread."""
        try:
            safe_log_startup("BG thread: initialize_database()...")
            initialize_database()
            safe_log_startup("BG thread: perform_daily_cleanup()...")
            perform_daily_cleanup()
            safe_log_startup("BG thread: DB ready — scheduling first screen.")
            Clock.schedule_once(self._add_billing_screen, 0)
        except Exception as e:
            safe_log_crash(traceback.format_exc())
            Clock.schedule_once(
                lambda dt: self._show_db_error(str(e)), 0
            )

    # ── Stage 3: staggered screen creation — one per frame ────────────────────
    # Each method creates exactly one screen then schedules the next.
    # This spreads widget construction across frames so Android's layout engine
    # resolves sizes between additions, preventing the top-left stacking bug.

    def _add_billing_screen(self, dt):
        safe_log_startup("Frame: adding BillingScreen...")
        try:
            from screens.billing import BillingScreen
            screen = BillingScreen(name='billing')
            self.sm.add_widget(screen)
            # Switch on the next frame so the layout engine resolves widget bounds first
            Clock.schedule_once(lambda dt: self._switch_to_billing(screen), 0)
        except Exception:
            safe_log_crash(traceback.format_exc())
        # Schedule next screen for the following frame
        Clock.schedule_once(self._add_menu_screen, 0)

    def _switch_to_billing(self, screen):
        self.sm.current = 'billing'
        screen.refresh_data()
        safe_log_startup("BillingScreen active — app usable.")

    def _add_menu_screen(self, dt):
        safe_log_startup("Frame: adding MenuScreen...")
        try:
            from screens.menu import MenuScreen
            self.sm.add_widget(MenuScreen(name='menu'))
        except Exception:
            safe_log_crash(traceback.format_exc())
        Clock.schedule_once(self._add_history_screen, 0)

    def _add_history_screen(self, dt):
        safe_log_startup("Frame: adding HistoryScreen...")
        try:
            from screens.history import HistoryScreen
            self.sm.add_widget(HistoryScreen(name='history'))
        except Exception:
            safe_log_crash(traceback.format_exc())
        Clock.schedule_once(self._add_settings_screen, 0)

    def _add_settings_screen(self, dt):
        safe_log_startup("Frame: adding SettingsScreen...")
        try:
            from screens.settings import SettingsScreen
            self.sm.add_widget(SettingsScreen(name='settings'))
            safe_log_startup("All screens ready.")
        except Exception:
            safe_log_crash(traceback.format_exc())

    def _show_db_error(self, message):
        """Shows an error on the loading screen if DB init fails."""
        for screen in self.sm.screens:
            if screen.name == 'loading':
                screen.show_error(f"Database Error:\n{message}")
                break


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    try:
        RestaurantPOSApp().run()
    except Exception as e:
        safe_log_crash(traceback.format_exc())
        sys.exit(1)
