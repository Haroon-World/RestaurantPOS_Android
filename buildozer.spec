[app]
# ─── App identity ─────────────────────────────────────────────────────────────
title = Restaurant POS
package.name = restaurantpos
package.domain = org.restaurantpos
version = 1.1

# ─── Source ───────────────────────────────────────────────────────────────────
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,ico

# ─── Requirements ─────────────────────────────────────────────────────────────
# reportlab 4.x: pure Python (removed _rl_accel C ext that broke on Python 3.11)
# Custom p4a recipe (p4a-recipes/reportlab/) downloads from PyPI instead of
# the broken hg.reportlab.com URL that returns 404 for 4.x tags.
# pillow==10.4.0: pinned to a version p4a's cross-compile environment can resolve.
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.1,pillow==10.4.0,reportlab==4.2.5,plyer==2.1.0

# Custom p4a recipes override the built-in ones (fixes reportlab 4.x download URL)
p4a.local_recipes = ./p4a-recipes

# ─── Orientation ──────────────────────────────────────────────────────────────
orientation = portrait

# ─── Android ──────────────────────────────────────────────────────────────────
android.api = 34
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,INTERNET,READ_MEDIA_IMAGES,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a

# Do NOT include android.sdk — it is deprecated and causes warnings/errors
# The SDK is managed by the workflow / Buildozer automatically

# Full-screen mode (hide status bar)
android.fullscreen = 0

# Accept SDK licenses automatically
android.accept_sdk_license = True

# ─── Appearance ───────────────────────────────────────────────────────────────
# presplash.filename = %(source.dir)s/assets/logo.png
# icon.filename      = %(source.dir)s/assets/icon.png

# ─── Build ────────────────────────────────────────────────────────────────────
[buildozer]
log_level = 2
warn_on_root = 1
