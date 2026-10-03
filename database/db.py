import sqlite3
import os
from datetime import datetime, timedelta


def _get_db_dir():
    """
    Returns the directory where restaurant.db should be stored.
    - On Android (Kivy): uses the App's user_data_dir (writable app-private storage)
    - On Desktop (dev): uses the directory of this script
    """
    try:
        from kivy.app import App
        app = App.get_running_app()
        if app is not None:
            return app.user_data_dir
    except Exception:
        pass
    return os.path.dirname(os.path.abspath(__file__))


def get_db_path():
    return os.path.join(_get_db_dir(), 'restaurant.db')


def get_connection():
    """Returns a connection to the SQLite database."""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def initialize_database():
    """
    Creates all tables if they do not exist.
    Seeds default settings and cleanup date on first run.
    No external SQL files — fully self-contained.
    """
    conn = get_connection()
    try:
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS RestaurantSettings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_name TEXT,
                address TEXT,
                phone TEXT,
                logo_path TEXT,
                default_delivery_charge REAL DEFAULT 0,
                default_service_charge REAL DEFAULT 0,
                history_retention_days INTEGER DEFAULT 1,
                admin_pin TEXT DEFAULT '2580',
                custom_receipt_message TEXT DEFAULT '',
                printer_mac TEXT DEFAULT ''
            )
        """)
        
        # Migrate RestaurantSettings
        cols = [row[1] for row in c.execute("PRAGMA table_info(RestaurantSettings)").fetchall()]
        if 'default_delivery_charge' not in cols:
            c.execute("ALTER TABLE RestaurantSettings ADD COLUMN default_delivery_charge REAL DEFAULT 0")
        if 'default_service_charge' not in cols:
            c.execute("ALTER TABLE RestaurantSettings ADD COLUMN default_service_charge REAL DEFAULT 0")
        if 'history_retention_days' not in cols:
            c.execute("ALTER TABLE RestaurantSettings ADD COLUMN history_retention_days INTEGER DEFAULT 1")
        if 'admin_pin' not in cols:
            c.execute("ALTER TABLE RestaurantSettings ADD COLUMN admin_pin TEXT DEFAULT '2580'")
        if 'custom_receipt_message' not in cols:
            c.execute("ALTER TABLE RestaurantSettings ADD COLUMN custom_receipt_message TEXT DEFAULT ''")
        if 'printer_mac' not in cols:
            c.execute("ALTER TABLE RestaurantSettings ADD COLUMN printer_mac TEXT DEFAULT ''")

        c.execute("""
            CREATE TABLE IF NOT EXISTS Menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT UNIQUE,
                price REAL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS Customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT,
                phone TEXT,
                address TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS Bills (
                bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                bill_date TEXT,
                bill_time TEXT,
                subtotal_amount REAL DEFAULT 0,
                delivery_charge REAL DEFAULT 0,
                service_charge REAL DEFAULT 0,
                total_amount REAL,
                FOREIGN KEY(customer_id) REFERENCES Customers(id) ON DELETE CASCADE
            )
        """)
        
        # Migrate Bills
        cols = [row[1] for row in c.execute("PRAGMA table_info(Bills)").fetchall()]
        if 'subtotal_amount' not in cols:
            c.execute("ALTER TABLE Bills ADD COLUMN subtotal_amount REAL DEFAULT 0")
        if 'delivery_charge' not in cols:
            c.execute("ALTER TABLE Bills ADD COLUMN delivery_charge REAL DEFAULT 0")
        if 'service_charge' not in cols:
            c.execute("ALTER TABLE Bills ADD COLUMN service_charge REAL DEFAULT 0")

        c.execute("""
            CREATE TABLE IF NOT EXISTS BillItems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER,
                item_name TEXT,
                price REAL,
                quantity INTEGER,
                subtotal REAL,
                FOREIGN KEY(bill_id) REFERENCES Bills(bill_id) ON DELETE CASCADE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS LastCleanup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cleanup_date TEXT
            )
        """)

        # Seed default data on first run
        c.execute("SELECT COUNT(*) as count FROM LastCleanup")
        if c.fetchone()['count'] == 0:
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute("INSERT INTO LastCleanup (cleanup_date) VALUES (?)", (today,))

        c.execute("SELECT COUNT(*) as count FROM RestaurantSettings")
        if c.fetchone()['count'] == 0:
            c.execute(
                """INSERT INTO RestaurantSettings 
                   (restaurant_name, address, phone, logo_path, default_delivery_charge, default_service_charge, history_retention_days, admin_pin, custom_receipt_message, printer_mac) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("Restaurant Name", "Your Address Here", "+1 555-0100", "", 0.0, 0.0, 1, "2580", "", "")
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def perform_daily_cleanup():
    """Wrapper that calls perform_history_cleanup to reuse settings-based retention logic on startup."""
    perform_history_cleanup()


# ─── Settings ────────────────────────────────────────────────────────────────

def get_settings():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM RestaurantSettings ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def save_settings(name, address, phone, logo_path, delivery_charge=0.0, service_charge=0.0, custom_receipt_message='', printer_mac=''):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as count FROM RestaurantSettings")
        if c.fetchone()['count'] == 0:
            c.execute(
                """INSERT INTO RestaurantSettings 
                   (restaurant_name, address, phone, logo_path, default_delivery_charge, default_service_charge, custom_receipt_message, printer_mac) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, address, phone, logo_path, float(delivery_charge), float(service_charge), custom_receipt_message, printer_mac)
            )
        else:
            c.execute(
                """UPDATE RestaurantSettings SET 
                   restaurant_name=?, address=?, phone=?, logo_path=?, 
                   default_delivery_charge=?, default_service_charge=?, custom_receipt_message=?, printer_mac=?""",
                (name, address, phone, logo_path, float(delivery_charge), float(service_charge), custom_receipt_message, printer_mac)
            )
        conn.commit()
    finally:
        conn.close()


# ─── Menu ─────────────────────────────────────────────────────────────────────

def get_menu_items():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM Menu ORDER BY item_name")
        return [dict(row) for row in c.fetchall()]
    finally:
        conn.close()


def search_menu_items(query):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM Menu WHERE item_name LIKE ? ORDER BY item_name", (f"%{query}%",))
        return [dict(row) for row in c.fetchall()]
    finally:
        conn.close()


def add_menu_item(name, price):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO Menu (item_name, price) VALUES (?, ?)", (name, float(price)))
        conn.commit()
        return True, "Item added successfully."
    except sqlite3.IntegrityError:
        return False, "Item already exists."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def update_menu_item(item_id, name, price):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("UPDATE Menu SET item_name=?, price=? WHERE id=?", (name, float(price), item_id))
        conn.commit()
        return True, "Item updated successfully."
    except sqlite3.IntegrityError:
        return False, "Item name already exists."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def delete_menu_item(item_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM Menu WHERE id=?", (item_id,))
        conn.commit()
        return True, "Item deleted."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


# ─── Billing ──────────────────────────────────────────────────────────────────

def save_bill(customer_name, phone, address, items, subtotal_amount, delivery_charge=0.0, service_charge=0.0):
    """
    items: list of dicts with keys: item_name, price, quantity, subtotal
    Returns: (bill_id, bill_date, bill_time)
    """
    total_amount = subtotal_amount + float(delivery_charge) + float(service_charge)
    conn = get_connection()
    try:
        c = conn.cursor()

        c.execute(
            "INSERT INTO Customers (customer_name, phone, address) VALUES (?, ?, ?)",
            (customer_name, phone, address)
        )
        customer_id = c.lastrowid

        now = datetime.now()
        bill_date = now.strftime("%Y-%m-%d")
        bill_time = now.strftime("%I:%M %p")

        c.execute(
            "INSERT INTO Bills (customer_id, bill_date, bill_time, subtotal_amount, delivery_charge, service_charge, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (customer_id, bill_date, bill_time, subtotal_amount, float(delivery_charge), float(service_charge), total_amount)
        )
        bill_id = c.lastrowid

        for item in items:
            c.execute(
                "INSERT INTO BillItems (bill_id, item_name, price, quantity, subtotal) VALUES (?, ?, ?, ?, ?)",
                (bill_id, item['item_name'], item['price'], item['quantity'], item['subtotal'])
            )

        # Automatically clean up history when a new bill is created
        _perform_history_cleanup_with_cursor(c)

        conn.commit()
        return bill_id, bill_date, bill_time
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ─── History ──────────────────────────────────────────────────────────────────

def get_todays_bills():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT b.bill_id, cu.customer_name, b.bill_time, b.total_amount
            FROM Bills b
            JOIN Customers cu ON b.customer_id = cu.id
            WHERE b.bill_date = ?
            ORDER BY b.bill_id DESC
        """, (today,))
        return [dict(row) for row in c.fetchall()]
    finally:
        conn.close()


def search_todays_bills(term):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        c = conn.cursor()
        pat = f"%{term}%"
        c.execute("""
            SELECT b.bill_id, cu.customer_name, b.bill_time, b.total_amount
            FROM Bills b
            JOIN Customers cu ON b.customer_id = cu.id
            WHERE b.bill_date = ? AND (cu.customer_name LIKE ? OR CAST(b.bill_id AS TEXT) LIKE ?)
            ORDER BY b.bill_id DESC
        """, (today, pat, pat))
        return [dict(row) for row in c.fetchall()]
    finally:
        conn.close()


def get_bill_details(bill_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT b.bill_id, b.bill_date, b.bill_time, b.subtotal_amount, 
                   b.delivery_charge, b.service_charge, b.total_amount,
                   cu.customer_name, cu.phone, cu.address
            FROM Bills b
            JOIN Customers cu ON b.customer_id = cu.id
            WHERE b.bill_id = ?
        """, (bill_id,))
        bill_info = c.fetchone()
        if not bill_info:
            return None

        c.execute("""
            SELECT item_name, price, quantity, subtotal
            FROM BillItems WHERE bill_id = ?
        """, (bill_id,))
        items = c.fetchall()

        return {
            'info': dict(bill_info),
            'items': [dict(row) for row in items]
        }
    finally:
        conn.close()


# ─── Retention Helpers ───────────────────────────────────────────────────────


def _perform_history_cleanup_with_cursor(c):
    try:
        c.execute("SELECT history_retention_days FROM RestaurantSettings ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        retention_days = row['history_retention_days'] if row and row['history_retention_days'] is not None else 1
        
        threshold_date = datetime.now() - timedelta(days=retention_days - 1)
        threshold_str = threshold_date.strftime("%Y-%m-%d")
        
        c.execute("DELETE FROM Bills WHERE bill_date < ?", (threshold_str,))
        c.execute("DELETE FROM BillItems WHERE bill_id NOT IN (SELECT bill_id FROM Bills)")
        c.execute("DELETE FROM Customers WHERE id NOT IN (SELECT DISTINCT customer_id FROM Bills)")
    except Exception as e:
        print(f"Inline cleanup error: {e}")


def perform_history_cleanup():
    conn = get_connection()
    try:
        c = conn.cursor()
        _perform_history_cleanup_with_cursor(c)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Cleanup error: {e}")
    finally:
        conn.close()


def update_history_retention(days):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("UPDATE RestaurantSettings SET history_retention_days = ?", (int(days),))
        conn.commit()
    finally:
        conn.close()



