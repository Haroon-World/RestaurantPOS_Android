import os
import sys
from datetime import datetime
from reportlab.pdfgen import canvas as rl_canvas


def get_receipts_dir():
    """
    Returns the receipts directory.
    On Android: /storage/emulated/0/Documents/RestaurantPOS/Receipts/
    On Desktop: ./receipts/ (beside the script)
    """
    from kivy.utils import platform
    
    if platform == 'android':
        try:
            from jnius import autoclass
            Environment = autoclass('android.os.Environment')
            docs_path = Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOCUMENTS
            ).getAbsolutePath()
            d = os.path.join(docs_path, 'RestaurantPOS', 'Receipts')
            os.makedirs(d, exist_ok=True)
            return d
        except Exception as e:
            # On Android, do not silently fallback!
            import traceback
            tb = traceback.format_exc()
            raise RuntimeError(f"Failed to create or access public Documents directory.\nEnsure storage permissions are granted.\nError: {e}\nTraceback: {tb}")
    else:
        # Desktop / fallback: save beside the source file
        base = os.path.dirname(os.path.abspath(__file__))
        d = os.path.join(base, 'receipts')
        os.makedirs(d, exist_ok=True)
        return d


def generate_receipt(bill_id, bill_date, bill_time, customer_info, items, subtotal_amount, total_amount, settings, delivery_charge=0.0, service_charge=0.0):
    """
    Generates a PDF receipt formatted for an 80mm thermal printer.
    Returns the absolute file path of the saved PDF.
    """
    receipts_dir = get_receipts_dir()
    # Timestamped filename so each receipt is unique and easy to find
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(receipts_dir, f"Receipt_{ts}.pdf")

    # 80 mm receipt width (3.15 in × 72 pt/in ≈ 226.8 pt)
    width = 226.8
    logo_path = settings.get('logo_path', '')
    logo_exists = logo_path and os.path.exists(logo_path)
    logo_h = 90 if logo_exists else 0
    base_h = 330
    items_h = len(items) * 15
    charges_h = 0
    if float(delivery_charge) > 0: charges_h += 13
    if float(service_charge) > 0: charges_h += 13
    if charges_h > 0: charges_h += 13  # Subtotal line
    height = base_h + logo_h + items_h + charges_h

    c = rl_canvas.Canvas(filepath, pagesize=(width, height))
    y = height - 15
    margin = 10

    # Logo
    if logo_exists:
        try:
            c.drawImage(logo_path, (width - 100) / 2, y - 80,
                        width=100, height=80, preserveAspectRatio=True, mask='auto')
            y -= 90
        except Exception:
            pass

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, settings.get('restaurant_name', 'Restaurant'))
    y -= 18
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, y, settings.get('address', ''))
    y -= 11
    c.drawCentredString(width / 2, y, f"Ph: {settings.get('phone', '')}")
    y -= 14

    # Divider
    c.setDash(2, 2)
    c.line(margin, y, width - margin, y)
    c.setDash()
    y -= 13

    # Bill info
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin, y, f"Bill #: {bill_id}")
    y -= 11
    c.setFont("Helvetica", 7)
    c.drawString(margin, y, f"Date: {bill_date}")
    c.drawRightString(width - margin, y, f"Time: {bill_time}")
    y -= 13

    # Customer info
    cust_name = customer_info.get('customer_name', '').strip()
    cust_phone = customer_info.get('phone', '').strip()
    cust_addr = customer_info.get('address', '').strip()

    has_cust = (cust_name and cust_name.lower() != 'walk-in customer') or cust_phone or cust_addr
    if has_cust:
        c.setDash(2, 2)
        c.line(margin, y, width - margin, y)
        c.setDash()
        y -= 11
        c.setFont("Helvetica-Bold", 8)
        c.drawString(margin, y, "Customer:")
        y -= 11
        c.setFont("Helvetica", 7)
        if cust_name and cust_name.lower() != 'walk-in customer':
            c.drawString(margin, y, cust_name[:28])
            y -= 10
        if cust_phone:
            c.drawString(margin, y, f"Ph: {cust_phone}")
            y -= 10
        if cust_addr:
            c.drawString(margin, y, cust_addr[:32])
            y -= 10
        y -= 3

    c.setDash(2, 2)
    c.line(margin, y, width - margin, y)
    c.setDash()
    y -= 12

    # Items header
    c.setFont("Helvetica-Bold", 7)
    c.drawString(margin, y, "Item")
    c.drawString(width - 90, y, "Price")
    c.drawString(width - 52, y, "Qty")
    c.drawRightString(width - margin, y, "Total")
    y -= 9
    c.setDash(2, 2)
    c.line(margin, y, width - margin, y)
    c.setDash()
    y -= 13

    # Items
    c.setFont("Helvetica", 7)
    for item in items:
        name = str(item['item_name'])[:14]
        c.drawString(margin, y, name)
        c.drawString(width - 90, y, f"{item['price']:.0f}")
        c.drawString(width - 50, y, str(item['quantity']))
        c.drawRightString(width - margin, y, f"{item['subtotal']:.0f}")
        y -= 13

    y -= 4
    c.setDash(2, 2)
    c.line(margin, y, width - margin, y)
    c.setDash()
    y -= 13

    # Subtotal and Charges
    if float(delivery_charge) > 0 or float(service_charge) > 0:
        c.setFont("Helvetica-Bold", 7)
        c.drawString(margin, y, "Subtotal:")
        c.drawRightString(width - margin, y, f"Rs {subtotal_amount:.2f}")
        y -= 13
        
        c.setFont("Helvetica", 7)
        if float(delivery_charge) > 0:
            c.drawString(margin, y, "Delivery Charge:")
            c.drawRightString(width - margin, y, f"Rs {delivery_charge:.2f}")
            y -= 13
        if float(service_charge) > 0:
            c.drawString(margin, y, "Service Charge:")
            c.drawRightString(width - margin, y, f"Rs {service_charge:.2f}")
            y -= 13
            
        y -= 4
        c.setDash(2, 2)
        c.line(margin, y, width - margin, y)
        c.setDash()
        y -= 18
    else:
        y -= 5

    # Grand total
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Grand Total:")
    c.drawRightString(width - margin, y, f"Rs {total_amount:.2f}")
    y -= 28

    # Footer — supports multi-line messages (split on newlines)
    c.setFont("Helvetica-Oblique", 8)
    footer_msg = (settings.get('custom_receipt_message', '') or '').strip() if settings else ''
    if not footer_msg:
        footer_msg = "Thank You For Visiting!"
    for line in footer_msg.split('\n'):
        line = line.strip()
        if line:
            c.drawCentredString(width / 2, y, line)
            y -= 11

    c.save()
    
    # Verify the file was actually written to the disk
    if not os.path.exists(filepath):
        raise IOError(f"File was not saved successfully. Permission denied or path inaccessible: {filepath}")
        
    return filepath
