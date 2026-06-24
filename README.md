# Restaurant POS — Android

A full-featured Point of Sale system for restaurants, built with Python and Kivy for Android.
Generates PDF receipts, prints to Bluetooth thermal printers, and stores all data locally in SQLite.

---

## Features

- **Billing System** — Fast order entry with a searchable menu grid, quantity controls, and automatic totals
- **Menu Management** — Add, edit, and delete menu items with live search
- **Sales History** — View and reprint today's bills; records auto-pruned by configurable retention period
- **Restaurant Settings** — Configure name, address, phone, delivery/service charges, and receipt footer
- **Logo Upload** — Attach your restaurant logo to PDF receipts via the device gallery
- **PDF Receipt Generation** — 80 mm thermal-printer-formatted PDFs saved to `Documents/RestaurantPOS/Receipts/`
- **Bluetooth Thermal Printer Support** — ESC/POS printing to any paired Bluetooth printer
- **Android Storage Integration** — Uses Android scoped storage APIs; requests only required permissions

---

## Requirements

| Package     | Version  | Purpose                              |
|-------------|----------|--------------------------------------|
| kivy        | 2.3.1    | UI framework                         |
| reportlab   | 4.2.5    | PDF receipt generation               |
| plyer       | 2.1.0    | Native file picker (logo selection)  |
| Pillow      | 10.4.0   | Image handling for logo embedding    |
| pyjnius     | (p4a)    | Android Java bridge (Bluetooth, APIs)|

> **Note:** `pyjnius` and the `android` module are provided automatically by
> [python-for-android](https://python-for-android.readthedocs.io/) during APK builds.
> They are not required for desktop development.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/RestaurantPOS_Android.git
cd RestaurantPOS_Android

# 2. Install Python dependencies (desktop dev/testing)
pip install -r requirements.txt

# 3. Run on desktop
python main.py
```

---

## Build APK with Buildozer

> Buildozer requires a **Linux** environment (Ubuntu 20.04+ recommended) or WSL2 on Windows.

```bash
# Install Buildozer
pip install buildozer

# Build a debug APK
buildozer android debug

# The APK is output to:
#   bin/restaurantpos-1.1-arm64-v8a-debug.apk
```

Install on a connected Android device:

```bash
buildozer android deploy run
```

---

## Project Structure

```
RestaurantPOS_Android_GitHub/
├── main.py               # App entry point; 3-stage startup model
├── receipt.py            # PDF receipt generation (reportlab)
├── printer.py            # Bluetooth ESC/POS printing
├── buildozer.spec        # Buildozer build configuration
├── requirements.txt      # Python package dependencies
├── build_apk.sh          # Helper script for WSL2 / Linux builds
│
├── screens/
│   ├── billing.py        # Billing screen — order entry & payment
│   ├── menu.py           # Menu management screen
│   ├── history.py        # Sales history screen
│   └── settings.py       # Restaurant settings screen
│
└── database/
    └── db.py             # SQLite helpers (schema, CRUD, cleanup)
```

---

## Android Permissions Used

| Permission                  | Reason                                      |
|-----------------------------|---------------------------------------------|
| `WRITE_EXTERNAL_STORAGE`    | Save PDF receipts to Documents folder       |
| `READ_EXTERNAL_STORAGE`     | Read logo image from device storage         |
| `READ_MEDIA_IMAGES`         | Android 13+ image access for logo upload    |
| `BLUETOOTH` / `BLUETOOTH_CONNECT` / `BLUETOOTH_SCAN` | Thermal printer communication |

---

## Database

All data is stored locally in **SQLite** (`restaurant.db`) under the app's private storage directory.
No internet connection or external server is required.

Tables:
- `RestaurantSettings` — Single-row restaurant configuration
- `Menu` — Menu items with name and price
- `Customers` — Customer details per bill
- `Bills` — Bill header (date, time, totals, charges)
- `BillItems` — Line items per bill

---

## License

This project is released for personal and commercial use. No activation or licensing system is included.
