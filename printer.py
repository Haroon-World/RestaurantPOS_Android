import os
import time

def is_android():
    try:
        from kivy.utils import platform
        return platform == 'android'
    except Exception:
        return 'ANDROID_ARGUMENT' in os.environ or 'ANDROID_BOOTLOGO' in os.environ

ESC = b'\x1b'
GS = b'\x1d'

def get_paired_printers():
    """
    Returns a dict of { "Device Name": "MAC_Address" } of paired Bluetooth devices.
    """
    if not is_android():
        print("[Desktop Fallback] get_paired_printers() called")
        return {"Desktop Printer 1": "00:11:22:33:44:55", "Desktop Printer 2": "AA:BB:CC:DD:EE:FF"}

    try:
        from jnius import autoclass
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        adapter = BluetoothAdapter.getDefaultAdapter()
        if not adapter:
            return {}

        if not adapter.isEnabled():
            return {}

        paired_devices = adapter.getBondedDevices().toArray()
        printers = {}
        for device in paired_devices:
            name = device.getName()
            mac = device.getAddress()
            if name and mac:
                print(f"[Bluetooth Debug] Found paired device: {name} - MAC: {mac}")
                printers[name] = mac
        
        print(f"[Bluetooth Debug] Total devices found: {len(printers)}")
        return printers
    except Exception as e:
        print(f"Error getting paired printers: {e}")
        return {}


def print_raw_data(mac_address, data_bytes):
    """
    Connects to the Bluetooth device via SPP and sends data_bytes.
    """
    if not mac_address:
        return False, "No printer MAC address provided."

    if not is_android():
        print(f"[Desktop Fallback] Pretending to print {len(data_bytes)} bytes to {mac_address}")
        return True, "Printed on Desktop"

    try:
        from jnius import autoclass
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        UUID = autoclass('java.util.UUID')

        adapter = BluetoothAdapter.getDefaultAdapter()
        if not adapter:
            return False, "No Bluetooth adapter found on this device."
        
        device = adapter.getRemoteDevice(mac_address)
        
        # Standard SPP (Serial Port Profile) UUID
        uuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
        
        # Create an insecure RFCOMM socket to bypass pairing prompts if already paired
        socket = device.createInsecureRfcommSocketToServiceRecord(uuid)
        
        # Cancel discovery as it slows down connections significantly
        adapter.cancelDiscovery()
        
        socket.connect()
        output_stream = socket.getOutputStream()
        
        # Write in chunks of 1024 bytes
        chunk_size = 1024
        for i in range(0, len(data_bytes), chunk_size):
            chunk = data_bytes[i:i+chunk_size]
            output_stream.write(chunk)
            output_stream.flush()
            time.sleep(0.05) # small delay to prevent buffer overflow on cheap printers
            
        time.sleep(0.2) # wait for the final chunk to be sent completely
        socket.close()
        
        return True, "Printed successfully"
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"Bluetooth printing error: {e}\n{tb}")
        return False, str(e)


def print_test(mac_address):
    """
    Prints a simple test receipt to verify connection and formatting.
    """
    init_printer = ESC + b'@'
    bold_on = ESC + b'E' + b'\x01'
    bold_off = ESC + b'E' + b'\x00'
    align_center = ESC + b'a' + b'\x01'
    align_left = ESC + b'a' + b'\x00'
    cut_paper = GS + b'V' + b'\x42' + b'\x00'
    
    import datetime
    dt_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data = init_printer
    data += align_center + bold_on + b"Restaurant POS Test\n" + bold_off
    data += b"Printer Connected Successfully\n"
    data += dt_str.encode('ascii') + b"\n\n\n\n"
    data += cut_paper
    
    return print_raw_data(mac_address, data)


def print_bill(mac_address, bill_id, bill_date, bill_time, customer_info, items, subtotal_amount, total_amount, settings, delivery_charge=0.0, service_charge=0.0):
    """
    Formats the bill data into ESC/POS commands and sends it to the printer.
    Assumes standard 58mm printer (32 characters per line) for maximum compatibility.
    """
    init_printer = ESC + b'@'
    bold_on = ESC + b'E' + b'\x01'
    bold_off = ESC + b'E' + b'\x00'
    align_center = ESC + b'a' + b'\x01'
    align_left = ESC + b'a' + b'\x00'
    align_right = ESC + b'a' + b'\x02'
    cut_paper = GS + b'V' + b'\x42' + b'\x00'
    double_size = GS + b'!' + b'\x11'
    normal_size = GS + b'!' + b'\x00'

    def left_right(left_str, right_str, width=32):
        space_len = width - len(left_str) - len(right_str)
        if space_len < 1:
            space_len = 1
        return left_str + " " * space_len + right_str

    data = init_printer
    
    # Header
    data += align_center + bold_on + double_size
    rest_name = settings.get('restaurant_name', 'Restaurant')[:16]
    data += rest_name.encode('ascii', errors='replace') + b"\n"
    data += normal_size + bold_off
    
    address = settings.get('address', '')
    if address:
        data += address.encode('ascii', errors='replace') + b"\n"
        
    phone = settings.get('phone', '')
    if phone:
        data += b"Ph: " + phone.encode('ascii', errors='replace') + b"\n"
        
    data += b"-" * 32 + b"\n"
    
    # Bill Info
    data += align_left + bold_on + f"Bill #: {bill_id}\n".encode('ascii', errors='replace') + bold_off
    data += left_right(f"Date: {bill_date}", f"Time: {bill_time}").encode('ascii', errors='replace') + b"\n"
    
    # Customer Info
    cust_name = customer_info.get('customer_name', '').strip()
    cust_phone = customer_info.get('phone', '').strip()
    cust_addr = customer_info.get('address', '').strip()
    has_cust = (cust_name and cust_name.lower() != 'walk-in customer') or cust_phone or cust_addr
    
    if has_cust:
        data += b"-" * 32 + b"\n"
        data += bold_on + b"Customer:\n" + bold_off
        if cust_name and cust_name.lower() != 'walk-in customer':
            data += cust_name[:32].encode('ascii', errors='replace') + b"\n"
        if cust_phone:
            data += f"Ph: {cust_phone}\n".encode('ascii', errors='replace')
        if cust_addr:
            data += cust_addr[:32].encode('ascii', errors='replace') + b"\n"
            
    data += b"-" * 32 + b"\n"
    
    # Items Header
    data += bold_on
    data += left_right("Item", "Total").encode('ascii', errors='replace') + b"\n"
    data += bold_off
    data += b"-" * 32 + b"\n"
    
    # Items
    for item in items:
        name = str(item['item_name'])
        qty_price = f"{item['quantity']}x{item['price']:.0f}"
        subt = f"{item['subtotal']:.0f}"
        
        # if name is long, print it on first line, and qty/price on second
        if len(name) > 20:
            data += name[:32].encode('ascii', errors='replace') + b"\n"
            data += left_right(f"  {qty_price}", subt).encode('ascii', errors='replace') + b"\n"
        else:
            line1 = left_right(name, subt, 32)
            data += line1.encode('ascii', errors='replace') + b"\n"
            data += f"  {qty_price}\n".encode('ascii', errors='replace')
            
    data += b"-" * 32 + b"\n"
    
    # Subtotal and Charges
    if float(delivery_charge) > 0 or float(service_charge) > 0:
        data += left_right("Subtotal:", f"Rs {subtotal_amount:.2f}").encode('ascii', errors='replace') + b"\n"
        if float(delivery_charge) > 0:
            data += left_right("Delivery:", f"Rs {delivery_charge:.2f}").encode('ascii', errors='replace') + b"\n"
        if float(service_charge) > 0:
            data += left_right("Service:", f"Rs {service_charge:.2f}").encode('ascii', errors='replace') + b"\n"
        data += b"-" * 32 + b"\n"
        
    # Grand Total
    data += bold_on + double_size
    data += left_right("TOTAL:", f"Rs {total_amount:.0f}").encode('ascii', errors='replace') + b"\n"
    data += normal_size + bold_off
    
    data += b"\n"
    
    # Footer
    data += align_center
    footer_msg = (settings.get('custom_receipt_message', '') or '').strip()
    if not footer_msg:
        footer_msg = "Thank You For Visiting!"
    for line in footer_msg.split('\n'):
        line = line.strip()
        if line:
            data += line[:32].encode('ascii', errors='replace') + b"\n"
            
    data += b"\n\n\n\n"
    data += cut_paper
    
    return print_raw_data(mac_address, data)
