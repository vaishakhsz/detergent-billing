"""
Detergent Billing System - Fully Working
With Cash Receipt Printing
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os
import base64

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="🧺 Detergent Billing System",
    page_icon="🧺",
    layout="wide"
)

# ==================== DATABASE SETUP ====================

def init_db():
    """Initialize SQLite database with all tables"""
    conn = sqlite3.connect('detergent_billing.db')
    c = conn.cursor()
    
    # Products Table
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT UNIQUE,
        name TEXT NOT NULL,
        rate REAL NOT NULL,
        stock REAL NOT NULL DEFAULT 0,
        brand TEXT,
        unit TEXT DEFAULT 'Pcs'
    )''')
    
    # Parties Table
    c.execute('''CREATE TABLE IF NOT EXISTS parties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        party_id TEXT UNIQUE,
        name TEXT NOT NULL,
        mobile TEXT,
        whatsapp TEXT,
        address TEXT,
        opening_balance REAL DEFAULT 0,
        gst_no TEXT
    )''')
    
    # Sales Table
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE,
        date TEXT NOT NULL,
        party TEXT NOT NULL,
        total REAL DEFAULT 0,
        status TEXT DEFAULT 'Unpaid'
    )''')
    
    # Sales Items Table
    c.execute('''CREATE TABLE IF NOT EXISTS sales_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT NOT NULL,
        product_id TEXT NOT NULL,
        product_name TEXT NOT NULL,
        qty REAL NOT NULL,
        rate REAL NOT NULL,
        amount REAL NOT NULL
    )''')
    
    # Receipts Table
    c.execute('''CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_no TEXT UNIQUE,
        date TEXT NOT NULL,
        party TEXT NOT NULL,
        invoice_no TEXT NOT NULL,
        amount REAL NOT NULL,
        payment_mode TEXT DEFAULT 'Cash',
        remarks TEXT
    )''')
    
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect('detergent_billing.db')

# ==================== PRODUCT FUNCTIONS ====================

def get_products():
    conn = get_conn()
    df = pd.read_sql_query("SELECT product_id, name, rate, stock, brand, unit FROM products ORDER BY name", conn)
    conn.close()
    return df

def add_product(product_id, name, rate, stock, brand, unit):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO products (product_id, name, rate, stock, brand, unit) VALUES (?, ?, ?, ?, ?, ?)",
              (product_id, name, rate, stock, brand, unit))
    conn.commit()
    conn.close()

def update_product(product_id, name, rate, stock, brand, unit):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE products SET name=?, rate=?, stock=?, brand=?, unit=? WHERE product_id=?",
              (name, rate, stock, brand, unit, product_id))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE product_id=?", (product_id,))
    conn.commit()
    conn.close()

def update_stock(product_name, change):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (change, product_name))
    conn.commit()
    conn.close()

def get_next_product_id():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT MAX(product_id) FROM products")
    result = c.fetchone()[0]
    conn.close()
    if result:
        num = int(result.replace('P', '')) + 1
        return f"P{num:03d}"
    return "P001"

# ==================== PARTY FUNCTIONS ====================

def get_parties():
    conn = get_conn()
    df = pd.read_sql_query("SELECT party_id, name, mobile, whatsapp, address, opening_balance, gst_no FROM parties ORDER BY name", conn)
    conn.close()
    return df

def add_party(party_id, name, mobile, whatsapp, address, opening_balance, gst_no):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO parties (party_id, name, mobile, whatsapp, address, opening_balance, gst_no) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (party_id, name, mobile, whatsapp, address, opening_balance, gst_no))
    conn.commit()
    conn.close()

def update_party(party_id, name, mobile, whatsapp, address, opening_balance, gst_no):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE parties SET name=?, mobile=?, whatsapp=?, address=?, opening_balance=?, gst_no=? WHERE party_id=?",
              (name, mobile, whatsapp, address, opening_balance, gst_no, party_id))
    conn.commit()
    conn.close()

def delete_party(party_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM parties WHERE party_id=?", (party_id,))
    conn.commit()
    conn.close()

def get_next_party_id():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT MAX(party_id) FROM parties")
    result = c.fetchone()[0]
    conn.close()
    if result:
        num = int(result.replace('PT', '')) + 1
        return f"PT{num:03d}"
    return "PT001"

# ==================== SALES FUNCTIONS ====================

def get_sales():
    conn = get_conn()
    df = pd.read_sql_query("SELECT invoice_no, date, party, total, status FROM sales ORDER BY date DESC", conn)
    conn.close()
    return df

def get_sale_items(invoice_no):
    conn = get_conn()
    df = pd.read_sql_query("SELECT product_name, qty, rate, amount FROM sales_items WHERE invoice_no = ?", 
                          conn, params=(invoice_no,))
    conn.close()
    return df

def get_next_invoice_no():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT MAX(invoice_no) FROM sales")
    result = c.fetchone()[0]
    conn.close()
    if result:
        num = int(result.replace('INV', '')) + 1
        return f"INV{num:04d}"
    return "INV0001"

def create_invoice(party, cart):
    """Create invoice and return invoice_no, total"""
    conn = get_conn()
    c = conn.cursor()
    
    invoice_no = get_next_invoice_no()
    total = sum(item['amount'] for item in cart)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Insert into sales
    c.execute("INSERT INTO sales (invoice_no, date, party, total, status) VALUES (?, ?, ?, ?, ?)",
              (invoice_no, now, party, total, 'Unpaid'))
    
    # Insert items and update stock
    for item in cart:
        c.execute("INSERT INTO sales_items (invoice_no, product_id, product_name, qty, rate, amount) VALUES (?, ?, ?, ?, ?, ?)",
                  (invoice_no, item['product_id'], item['name'], item['qty'], item['rate'], item['amount']))
        c.execute("UPDATE products SET stock = stock - ? WHERE name = ?", (item['qty'], item['name']))
    
    conn.commit()
    conn.close()
    
    return invoice_no, total

def get_invoice_total(invoice_no):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT total FROM sales WHERE invoice_no = ?", (invoice_no,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def get_invoice_paid(invoice_no):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM receipts WHERE invoice_no = ?", (invoice_no,))
    result = c.fetchone()[0]
    conn.close()
    return result if result else 0

# ==================== RECEIPT FUNCTIONS ====================

def get_receipts():
    conn = get_conn()
    df = pd.read_sql_query("SELECT receipt_no, date, party, invoice_no, amount, payment_mode, remarks FROM receipts ORDER BY date DESC", conn)
    conn.close()
    return df

def get_next_receipt_no():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT MAX(receipt_no) FROM receipts")
    result = c.fetchone()[0]
    conn.close()
    if result:
        num = int(result.replace('REC', '')) + 1
        return f"REC{num:04d}"
    return "REC0001"

def add_receipt(party, invoice_no, amount, payment_mode, remarks):
    conn = get_conn()
    c = conn.cursor()
    
    receipt_no = get_next_receipt_no()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    c.execute("INSERT INTO receipts (receipt_no, date, party, invoice_no, amount, payment_mode, remarks) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (receipt_no, now, party, invoice_no, amount, payment_mode, remarks))
    
    # Update invoice status
    total = get_invoice_total(invoice_no)
    paid = get_invoice_paid(invoice_no) + amount
    
    if paid >= total:
        status = 'Paid'
    elif paid > 0:
        status = 'Partially Paid'
    else:
        status = 'Unpaid'
    
    c.execute("UPDATE sales SET status = ? WHERE invoice_no = ?", (status, invoice_no))
    conn.commit()
    conn.close()
    
    return receipt_no

# ==================== HELPERS ====================

def safe_float(value):
    try:
        return float(value) if value else 0.0
    except:
        return 0.0

# ==================== INIT DATA ====================

def init_data():
    products = get_products()
    if products.empty:
        defaults = [
            ('P001', 'Dishwash Liquid 1L', 120, 100, 'Detergent', 'Pcs'),
            ('P002', 'Detergent Powder 1kg', 120, 100, 'Detergent', 'Pcs'),
            ('P003', 'Dishwash Liquid 7+1', 840, 50, 'Detergent', 'Pack'),
            ('P004', 'Detergent Powder 7+1', 840, 50, 'Detergent', 'Pack')
        ]
        for p in defaults:
            add_product(*p)

# ==================== RECEIPT HTML GENERATORS ====================

def get_invoice_receipt_html(invoice_no, party, cart, total, paid, balance):
    """Generate printable invoice receipt HTML"""
    
    items_html = ""
    for item in cart:
        items_html += f"""
        <tr>
            <td>{item['name']}</td>
            <td style="text-align:center">{item['qty']:.0f}</td>
            <td style="text-align:right">₹{item['rate']:.2f}</td>
            <td style="text-align:right">₹{item['amount']:.2f}</td>
        </tr>
        """
    
    status_class = 'paid' if balance <= 0 else 'partial' if paid > 0 else 'unpaid'
    status_text = '✅ PAID' if balance <= 0 else '⚠️ PARTIALLY PAID' if paid > 0 else '❌ UNPAID'
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Invoice {invoice_no}</title>
        <style>
            @media print {{
                .no-print {{ display: none; }}
                body {{ margin: 0; padding: 20px; }}
                .receipt {{ box-shadow: none; }}
            }}
            body {{
                font-family: 'Courier New', monospace;
                background: #f5f5f5;
                display: flex;
                justify-content: center;
                padding: 20px;
            }}
            .receipt {{
                background: white;
                width: 320px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border-radius: 8px;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px dashed #333;
                padding-bottom: 10px;
                margin-bottom: 10px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 20px;
                color: #003366;
            }}
            .header p {{
                margin: 2px 0;
                font-size: 12px;
                color: #666;
            }}
            .details {{
                font-size: 12px;
                margin-bottom: 10px;
                padding: 5px 0;
                border-bottom: 1px dotted #ccc;
            }}
            .details .row {{
                display: flex;
                justify-content: space-between;
                padding: 2px 0;
            }}
            table {{
                width: 100%;
                font-size: 12px;
                border-collapse: collapse;
                margin: 10px 0;
            }}
            th {{
                text-align: left;
                border-bottom: 1px solid #333;
                padding: 5px 2px;
                font-size: 11px;
            }}
            td {{
                padding: 4px 2px;
                border-bottom: 1px dotted #ddd;
            }}
            .right {{ text-align: right; }}
            .center {{ text-align: center; }}
            .total-section {{
                margin-top: 10px;
                padding-top: 10px;
                border-top: 2px dashed #333;
            }}
            .total-row {{
                display: flex;
                justify-content: space-between;
                font-size: 14px;
                padding: 3px 0;
            }}
            .total-row.bold {{
                font-weight: bold;
                font-size: 16px;
            }}
            .footer {{
                text-align: center;
                font-size: 11px;
                color: #666;
                margin-top: 15px;
                padding-top: 10px;
                border-top: 2px dashed #333;
            }}
            .footer .thank {{
                font-size: 14px;
                font-weight: bold;
                color: #003366;
            }}
            .status {{
                text-align: center;
                margin: 10px 0;
                padding: 5px;
                border-radius: 4px;
                font-weight: bold;
            }}
            .status.paid {{ background: #e8f5e9; color: #2e7d32; }}
            .status.unpaid {{ background: #ffebee; color: #c62828; }}
            .status.partial {{ background: #fff3e0; color: #e65100; }}
            .no-print {{
                text-align: center;
                margin-top: 20px;
            }}
            .no-print button {{
                padding: 10px 30px;
                font-size: 16px;
                background: #003366;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                margin: 0 5px;
            }}
            .no-print button:hover {{ background: #004488; }}
        </style>
    </head>
    <body>
        <div class="receipt">
            <div class="header">
                <h1>🧺 DETERGENT MART</h1>
                <p>123 Main Street, City</p>
                <p>Phone: +91 98765 43210</p>
            </div>
            
            <div class="details">
                <div class="row">
                    <span><strong>Invoice:</strong> {invoice_no}</span>
                    <span><strong>Date:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M')}</span>
                </div>
                <div class="row">
                    <span><strong>Party:</strong> {party}</span>
                </div>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Item</th>
                        <th class="center">Qty</th>
                        <th class="right">Rate</th>
                        <th class="right">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>
            
            <div class="total-section">
                <div class="total-row">
                    <span><strong>Total</strong></span>
                    <span><strong>₹{total:.2f}</strong></span>
                </div>
                <div class="total-row">
                    <span>Amount Paid</span>
                    <span>₹{paid:.2f}</span>
                </div>
                <div class="total-row bold">
                    <span>Balance</span>
                    <span>₹{balance:.2f}</span>
                </div>
            </div>
            
            <div class="status {status_class}">{status_text}</div>
            
            <div class="footer">
                <div class="thank">Thank You!</div>
                <p>Visit Again | Items once sold cannot be returned</p>
                <p>This is a system generated receipt</p>
            </div>
        </div>
        
        <div class="no-print">
            <button onclick="window.print()">🖨️ Print Receipt</button>
            <button onclick="window.close()">Close</button>
        </div>
    </body>
    </html>
    """
    return html


def get_payment_receipt_html(receipt_no, party, invoice_no, amount, payment_mode, remarks, balance, total):
    """Generate printable payment receipt HTML"""
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Payment Receipt {receipt_no}</title>
        <style>
            @media print {{
                .no-print {{ display: none; }}
                body {{ margin: 0; padding: 20px; }}
                .receipt {{ box-shadow: none; }}
            }}
            body {{
                font-family: 'Courier New', monospace;
                background: #f5f5f5;
                display: flex;
                justify-content: center;
                padding: 20px;
            }}
            .receipt {{
                background: white;
                width: 320px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border-radius: 8px;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px dashed #333;
                padding-bottom: 10px;
                margin-bottom: 10px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 20px;
                color: #003366;
            }}
            .header p {{
                margin: 2px 0;
                font-size: 12px;
                color: #666;
            }}
            .details {{
                font-size: 12px;
                margin-bottom: 10px;
                padding: 5px 0;
                border-bottom: 1px dotted #ccc;
            }}
            .details .row {{
                display: flex;
                justify-content: space-between;
                padding: 2px 0;
            }}
            .payment-info {{
                background: #f0f7ff;
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
            }}
            .payment-info .row {{
                display: flex;
                justify-content: space-between;
                padding: 4px 0;
                font-size: 14px;
            }}
            .payment-info .row.bold {{
                font-weight: bold;
                font-size: 16px;
            }}
            .total-section {{
                margin-top: 10px;
                padding-top: 10px;
                border-top: 2px dashed #333;
            }}
            .total-row {{
                display: flex;
                justify-content: space-between;
                font-size: 14px;
                padding: 3px 0;
            }}
            .total-row.bold {{
                font-weight: bold;
                font-size: 16px;
            }}
            .footer {{
                text-align: center;
                font-size: 11px;
                color: #666;
                margin-top: 15px;
                padding-top: 10px;
                border-top: 2px dashed #333;
            }}
            .footer .thank {{
                font-size: 14px;
                font-weight: bold;
                color: #003366;
            }}
            .status {{
                text-align: center;
                margin: 10px 0;
                padding: 5px;
                border-radius: 4px;
                font-weight: bold;
                background: #e8f5e9;
                color: #2e7d32;
            }}
            .no-print {{
                text-align: center;
                margin-top: 20px;
            }}
            .no-print button {{
                padding: 10px 30px;
                font-size: 16px;
                background: #003366;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                margin: 0 5px;
            }}
            .no-print button:hover {{ background: #004488; }}
            .remarks {{
                font-size: 11px;
                color: #666;
                margin-top: 5px;
                padding: 5px;
                background: #f9f9f9;
                border-radius: 4px;
            }}
        </style>
    </head>
    <body>
        <div class="receipt">
            <div class="header">
                <h1>🧺 DETERGENT MART</h1>
                <p>123 Main Street, City</p>
                <p>Phone: +91 98765 43210</p>
            </div>
            
            <div class="details">
                <div class="row">
                    <span><strong>Payment Receipt</strong></span>
                    <span><strong>#{receipt_no}</strong></span>
                </div>
                <div class="row">
                    <span><strong>Date:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M')}</span>
                </div>
            </div>
            
            <div class="payment-info">
                <div class="row">
                    <span>Party:</span>
                    <span><strong>{party}</strong></span>
                </div>
                <div class="row">
                    <span>Invoice No:</span>
                    <span><strong>{invoice_no}</strong></span>
                </div>
                <div class="row bold">
                    <span>Amount Received:</span>
                    <span><strong>₹{amount:.2f}</strong></span>
                </div>
                <div class="row">
                    <span>Payment Mode:</span>
                    <span><strong>{payment_mode}</strong></span>
                </div>
            </div>
            
            <div class="total-section">
                <div class="total-row">
                    <span>Invoice Total</span>
                    <span>₹{total:.2f}</span>
                </div>
                <div class="total-row">
                    <span>Total Paid</span>
                    <span>₹{total - balance:.2f}</span>
                </div>
                <div class="total-row bold">
                    <span>Balance Due</span>
                    <span>₹{balance:.2f}</span>
                </div>
            </div>
            
            <div class="status">
                {'✅ PAID IN FULL' if balance <= 0 else f'⚠️ BALANCE DUE: ₹{balance:.2f}'}
            </div>
            
            {f'<div class="remarks"><strong>Remarks:</strong> {remarks}</div>' if remarks else ''}
            
            <div class="footer">
                <div class="thank">Thank You for Your Payment!</div>
                <p>This is a system generated payment receipt</p>
            </div>
        </div>
        
        <div class="no-print">
            <button onclick="window.print()">🖨️ Print Receipt</button>
            <button onclick="window.close()">Close</button>
        </div>
    </body>
    </html>
    """
    return html

# ==================== MAIN APP ====================

def main():
    # Initialize
    init_db()
    init_data()
    
    st.title("🧺 Detergent Billing System")
    
    # Sidebar
    st.sidebar.title("📋 Menu")
    st.sidebar.markdown("---")
    st.sidebar.success("✅ Database Ready")
    
    menu = st.sidebar.radio(
        "Navigate",
        ["📊 Dashboard", "📦 Products", "🏪 Parties", "🧾 Billing", 
         "💰 Cash Receipt", "📒 Party Ledger", "📈 Reports"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("Made with ❤️ using Streamlit")
    
    # Initialize cart in session state
    if 'cart' not in st.session_state:
        st.session_state.cart = []
    
    # Store last payment receipt
    if 'last_payment' not in st.session_state:
        st.session_state.last_payment = None

    # ==================== DASHBOARD ====================
    if menu == "📊 Dashboard":
        st.header("📊 Dashboard")
        
        products = get_products()
        sales = get_sales()
        parties = get_parties()
        receipts = get_receipts()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📦 Products", len(products))
        col2.metric("🏪 Parties", len(parties))
        col3.metric("💰 Total Sales", f"₹{sales['total'].sum():,.2f}" if not sales.empty else "₹0")
        col4.metric("💳 Total Receipts", f"₹{receipts['amount'].sum():,.2f}" if not receipts.empty else "₹0")
        
        st.subheader("📄 Recent Invoices")
        if not sales.empty:
            st.dataframe(sales.head(10), use_container_width=True)
        else:
            st.info("No sales yet")

    # ==================== PRODUCTS ====================
    elif menu == "📦 Products":
        st.header("📦 Product Master")
        
        products = get_products()
        
        st.subheader("📋 All Products")
        
        if not products.empty:
            for idx, row in products.iterrows():
                col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1.2, 1, 1, 0.8, 0.8, 0.8])
                with col1:
                    st.write(f"**{row['name']}**")
                with col2:
                    st.write(f"₹{row['rate']:.2f}")
                with col3:
                    st.write(f"{row['stock']:.0f}")
                with col4:
                    st.write(row['product_id'])
                with col5:
                    if st.button("✏️", key=f"edit_p_{idx}"):
                        st.session_state.edit_product_id = row['product_id']
                        st.rerun()
                with col6:
                    if st.button("🗑️", key=f"del_p_{idx}"):
                        delete_product(row['product_id'])
                        st.success(f"✅ {row['name']} deleted!")
                        st.rerun()
                with col7:
                    if st.button("📦", key=f"stock_p_{idx}"):
                        st.session_state.stock_product = row['product_id']
                        st.rerun()
                st.divider()
            
            # Stock update modal
            if 'stock_product' in st.session_state:
                product = products[products['product_id'] == st.session_state.stock_product].iloc[0]
                with st.expander(f"📦 Update Stock: {product['name']}", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_stock = st.number_input("New Stock Quantity", value=float(product['stock']), step=1.0)
                    with col2:
                        if st.button("💾 Update Stock"):
                            change = new_stock - float(product['stock'])
                            update_stock(product['name'], change)
                            st.success(f"✅ Stock updated to {new_stock}")
                            del st.session_state.stock_product
                            st.rerun()
                    if st.button("❌ Cancel"):
                        del st.session_state.stock_product
                        st.rerun()
            
            # Edit modal
            if 'edit_product_id' in st.session_state:
                product = products[products['product_id'] == st.session_state.edit_product_id].iloc[0]
                with st.expander(f"✏️ Editing: {product['name']}", expanded=True):
                    with st.form("edit_product_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            name = st.text_input("Product Name", value=product['name'])
                            rate = st.number_input("Rate (₹)", value=float(product['rate']), step=1.0)
                        with col2:
                            stock = st.number_input("Stock", value=float(product['stock']), step=1.0)
                            brand = st.text_input("Brand", value=product['brand'] if product['brand'] else '')
                            unit = st.selectbox("Unit", ["Pcs", "Pack", "Kg", "Ltr"], 
                                              index=["Pcs", "Pack", "Kg", "Ltr"].index(product['unit']) if product['unit'] in ["Pcs", "Pack", "Kg", "Ltr"] else 0)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Save"):
                                update_product(product['product_id'], name, rate, stock, brand, unit)
                                st.success(f"✅ Product updated!")
                                del st.session_state.edit_product_id
                                st.rerun()
                        with col2:
                            if st.form_submit_button("❌ Cancel"):
                                del st.session_state.edit_product_id
                                st.rerun()
        
        # Add Product
        st.subheader("➕ Add New Product")
        with st.form("add_product_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Product Name *")
                rate = st.number_input("Rate (₹) *", min_value=0.0, step=1.0)
            with col2:
                stock = st.number_input("Stock *", min_value=0, step=1)
                brand = st.text_input("Brand")
                unit = st.selectbox("Unit", ["Pcs", "Pack", "Kg", "Ltr"])
            
            if st.form_submit_button("Add Product"):
                if name and rate > 0:
                    product_id = get_next_product_id()
                    add_product(product_id, name, rate, stock, brand, unit)
                    st.success(f"✅ Product '{name}' added!")
                    st.rerun()

    # ==================== PARTIES ====================
    elif menu == "🏪 Parties":
        st.header("🏪 Party Master")
        
        parties = get_parties()
        
        st.subheader("📋 All Parties")
        
        if not parties.empty:
            for idx, row in parties.iterrows():
                col1, col2, col3, col4, col5, col6 = st.columns([2, 1.2, 1, 0.8, 0.8, 0.8])
                with col1:
                    st.write(f"**{row['name']}**")
                with col2:
                    st.write(row['mobile'] if row['mobile'] else '-')
                with col3:
                    st.write(f"₹{row['opening_balance']:.0f}")
                with col4:
                    st.write(row['party_id'])
                with col5:
                    if st.button("✏️", key=f"edit_pt_{idx}"):
                        st.session_state.edit_party_id = row['party_id']
                        st.rerun()
                with col6:
                    if st.button("🗑️", key=f"del_pt_{idx}"):
                        sales = get_sales()
                        has_sales = not sales[sales['party'] == row['name']].empty
                        if has_sales:
                            st.error(f"❌ Cannot delete {row['name']} - has sales!")
                        else:
                            delete_party(row['party_id'])
                            st.success(f"✅ {row['name']} deleted!")
                            st.rerun()
                st.divider()
            
            # Edit modal
            if 'edit_party_id' in st.session_state:
                party = parties[parties['party_id'] == st.session_state.edit_party_id].iloc[0]
                with st.expander(f"✏️ Editing: {party['name']}", expanded=True):
                    with st.form("edit_party_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            name = st.text_input("Party Name", value=party['name'])
                            mobile = st.text_input("Mobile", value=party['mobile'] if party['mobile'] else '')
                            whatsapp = st.text_input("WhatsApp", value=party['whatsapp'] if party['whatsapp'] else '')
                        with col2:
                            address = st.text_area("Address", value=party['address'] if party['address'] else '')
                            opening_balance = st.number_input("Opening Balance (₹)", value=float(party['opening_balance']), step=100.0)
                            gst_no = st.text_input("GST No", value=party['gst_no'] if party['gst_no'] else '')
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Save"):
                                update_party(party['party_id'], name, mobile, whatsapp, address, opening_balance, gst_no)
                                st.success(f"✅ Party updated!")
                                del st.session_state.edit_party_id
                                st.rerun()
                        with col2:
                            if st.form_submit_button("❌ Cancel"):
                                del st.session_state.edit_party_id
                                st.rerun()
        
        # Add Party
        st.subheader("➕ Add New Party")
        with st.form("add_party_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Party Name *")
                mobile = st.text_input("Mobile")
                whatsapp = st.text_input("WhatsApp")
            with col2:
                address = st.text_area("Address")
                opening_balance = st.number_input("Opening Balance (₹)", min_value=0.0, step=100.0, value=0.0)
                gst_no = st.text_input("GST No (Optional)")
            
            if st.form_submit_button("Add Party"):
                if name:
                    party_id = get_next_party_id()
                    add_party(party_id, name, mobile, whatsapp, address, opening_balance, gst_no)
                    st.success(f"✅ Party '{name}' added!")
                    st.rerun()

    # ==================== BILLING ====================
    elif menu == "🧾 Billing":
        st.header("🧾 Sales Billing")
        
        products = get_products()
        parties = get_parties()
        
        if products.empty:
            st.warning("⚠️ No products! Add products first.")
            return
        
        if parties.empty:
            st.warning("⚠️ No parties! Add parties first.")
            return
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🛒 Add Items to Cart")
            
            product_names = products['name'].tolist()
            selected = st.selectbox("Select Product", product_names)
            
            if selected:
                product = products[products['name'] == selected].iloc[0]
                stock = float(product['stock'])
                rate = float(product['rate'])
                product_id = product['product_id']
                st.info(f"📦 Stock: {stock:.0f} | 💰 Rate: ₹{rate:.2f}")
                
                col_qty, col_btn = st.columns([2, 1])
                with col_qty:
                    qty = st.number_input("Quantity", min_value=1.0, max_value=stock, step=1.0, key="qty_input")
                with col_btn:
                    if st.button("➕ Add to Cart", use_container_width=True):
                        if qty > 0:
                            st.session_state.cart.append({
                                'product_id': product_id,
                                'name': selected,
                                'rate': rate,
                                'qty': qty,
                                'amount': rate * qty
                            })
                            st.success(f"✅ Added {qty} {selected}")
                            st.rerun()
        
        with col2:
            st.subheader("🛍️ Cart")
            if st.session_state.cart:
                cart_df = pd.DataFrame(st.session_state.cart)
                st.dataframe(cart_df[['name', 'qty', 'rate', 'amount']], use_container_width=True)
                total = cart_df['amount'].sum()
                st.metric("💰 Total Amount", f"₹{total:,.2f}")
                if st.button("🗑️ Clear Cart", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()
            else:
                st.info("🛒 Cart is empty")
        
        st.markdown("---")
        st.subheader("📄 Create Invoice")
        
        party_names = parties['name'].tolist()
        party = st.selectbox("Select Party", party_names)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💳 Generate Invoice", type="primary", use_container_width=True):
                if not st.session_state.cart:
                    st.error("❌ Cart is empty!")
                else:
                    invoice_no, total = create_invoice(party, st.session_state.cart)
                    st.success(f"✅ Invoice {invoice_no} generated! Total: ₹{total:,.2f}")
                    
                    # Show receipt
                    st.markdown("---")
                    st.subheader("🧾 Invoice Receipt")
                    
                    receipt_html = get_invoice_receipt_html(
                        invoice_no, 
                        party, 
                        st.session_state.cart, 
                        total, 
                        0, 
                        total
                    )
                    st.components.v1.html(receipt_html, height=700)
                    
                    st.session_state.cart = []
                    st.rerun()
        
        with col2:
            # Print last invoice if exists
            if 'last_invoice' in st.session_state:
                if st.button("🖨️ Print Last Invoice", use_container_width=True):
                    inv = st.session_state.last_invoice
                    receipt_html = get_invoice_receipt_html(
                        inv['invoice_no'],
                        inv['party'],
                        inv['cart'],
                        inv['total'],
                        inv['paid'],
                        inv['balance']
                    )
                    st.components.v1.html(receipt_html, height=700)

    # ==================== CASH RECEIPT ====================
    elif menu == "💰 Cash Receipt":
        st.header("💰 Cash Receipt Entry")
        
        parties = get_parties()
        sales = get_sales()
        receipts = get_receipts()
        
        if parties.empty:
            st.warning("⚠️ No parties!")
            return
        
        if sales.empty:
            st.warning("⚠️ No invoices!")
            return
        
        st.subheader("📝 Record Payment")
        
        with st.form("receipt_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                party = st.selectbox("Party *", parties['name'].tolist())
                
                # Get unpaid invoices for this party
                unpaid = sales[sales['status'] != 'Paid'] if not sales.empty else pd.DataFrame()
                party_invoices = unpaid[unpaid['party'] == party] if party else pd.DataFrame()
                
                if not party_invoices.empty:
                    st.info(f"📋 {len(party_invoices)} unpaid invoices")
                    invoice_options = [''] + party_invoices['invoice_no'].tolist()
                    invoice_no = st.selectbox("Select Invoice", invoice_options)
                    
                    if invoice_no:
                        invoice_data = party_invoices[party_invoices['invoice_no'] == invoice_no].iloc[0]
                        total = float(invoice_data['total'])
                        paid = get_invoice_paid(invoice_no)
                        balance = total - paid
                        st.info(f"💳 Invoice: {invoice_no} | Balance: ₹{balance:,.2f}")
                else:
                    st.success(f"✅ No pending invoices for {party}")
                    invoice_no = ""
            
            with col2:
                manual_invoice = st.text_input("Or Enter Invoice No", placeholder="e.g., INV0001")
                final_invoice = manual_invoice if manual_invoice else invoice_no
                
                amount = st.number_input("Amount (₹) *", min_value=0.0, step=100.0)
                payment_mode = st.selectbox("Payment Mode", ["Cash", "UPI", "Bank Transfer", "Cheque"])
                remarks = st.text_area("Remarks (Optional)")
            
            submitted = st.form_submit_button("💳 Record Payment", type="primary")
            
            if submitted:
                if not party:
                    st.error("❌ Select a party!")
                elif not final_invoice:
                    st.error("❌ Enter/select an invoice!")
                elif amount <= 0:
                    st.error("❌ Amount must be > 0!")
                else:
                    # Verify invoice
                    invoice_data = sales[sales['invoice_no'] == final_invoice]
                    if invoice_data.empty:
                        st.error(f"❌ Invoice {final_invoice} not found!")
                    else:
                        # Check if invoice belongs to party
                        if invoice_data.iloc[0]['party'] != party:
                            st.error(f"❌ Invoice belongs to {invoice_data.iloc[0]['party']}, not {party}!")
                        else:
                            total = float(invoice_data.iloc[0]['total'])
                            paid = get_invoice_paid(final_invoice)
                            balance = total - paid
                            
                            if amount > balance:
                                st.error(f"❌ Amount exceeds balance! Balance: ₹{balance:,.2f}")
                            else:
                                receipt_no = add_receipt(party, final_invoice, amount, payment_mode, remarks)
                                st.success(f"✅ Receipt {receipt_no} recorded! Amount: ₹{amount:,.2f}")
                                st.balloons()
                                
                                # Store payment details for printing
                                st.session_state.last_payment = {
                                    'receipt_no': receipt_no,
                                    'party': party,
                                    'invoice_no': final_invoice,
                                    'amount': amount,
                                    'payment_mode': payment_mode,
                                    'remarks': remarks,
                                    'balance': balance - amount,
                                    'total': total
                                }
                                
                                st.rerun()
        
        # ==================== SHOW PAYMENT RECEIPT ====================
        if 'last_payment' in st.session_state and st.session_state.last_payment:
            st.markdown("---")
            st.subheader("🧾 Payment Receipt")
            
            payment = st.session_state.last_payment
            receipt_html = get_payment_receipt_html(
                payment['receipt_no'],
                payment['party'],
                payment['invoice_no'],
                payment['amount'],
                payment['payment_mode'],
                payment['remarks'],
                payment['balance'],
                payment['total']
            )
            st.components.v1.html(receipt_html, height=650)

    # ==================== PARTY LEDGER ====================
    elif menu == "📒 Party Ledger":
        st.header("📒 Party Ledger")
        
        parties = get_parties()
        
        if parties.empty:
            st.warning("⚠️ No parties!")
            return
        
        selected_party = st.selectbox("Select Party", parties['name'].tolist())
        
        if selected_party:
            sales = get_sales()
            receipts = get_receipts()
            
            party_sales = sales[sales['party'] == selected_party] if not sales.empty else pd.DataFrame()
            party_receipts = receipts[receipts['party'] == selected_party] if not receipts.empty else pd.DataFrame()
            
            if party_sales.empty and party_receipts.empty:
                st.info(f"No transactions for {selected_party}")
            else:
                tab1, tab2 = st.tabs(["📊 Complete Ledger", "📄 Invoice-wise"])
                
                with tab1:
                    st.subheader(f"📊 Ledger - {selected_party}")
                    
                    transactions = []
                    balance = 0
                    
                    # Opening balance
                    party_data = parties[parties['name'] == selected_party].iloc[0]
                    opening = float(party_data['opening_balance'])
                    balance = opening
                    transactions.append({
                        'Date': 'Opening',
                        'Particulars': 'Opening Balance',
                        'Debit': opening,
                        'Credit': 0,
                        'Balance': balance
                    })
                    
                    # Sales
                    for _, row in party_sales.iterrows():
                        amt = float(row['total'])
                        balance += amt
                        transactions.append({
                            'Date': row['date'][:10],
                            'Particulars': f"Sale - {row['invoice_no']}",
                            'Debit': amt,
                            'Credit': 0,
                            'Balance': balance
                        })
                    
                    # Receipts
                    for _, row in party_receipts.iterrows():
                        amt = float(row['amount'])
                        balance -= amt
                        transactions.append({
                            'Date': row['date'][:10],
                            'Particulars': f"Receipt - {row['receipt_no']}",
                            'Debit': 0,
                            'Credit': amt,
                            'Balance': balance
                        })
                    
                    df = pd.DataFrame(transactions)
                    st.dataframe(df, use_container_width=True)
                    
                    col1, col2, col3 = st.columns(3)
                    total_sales = party_sales['total'].sum() if not party_sales.empty else 0
                    total_receipts = party_receipts['amount'].sum() if not party_receipts.empty else 0
                    col1.metric("Total Sales", f"₹{total_sales:,.2f}")
                    col2.metric("Total Receipts", f"₹{total_receipts:,.2f}")
                    col3.metric("Balance", f"₹{balance:,.2f}", delta="Due" if balance > 0 else "Settled")
                
                with tab2:
                    st.subheader(f"📄 Invoice-wise - {selected_party}")
                    
                    invoice_data = []
                    for _, row in party_sales.iterrows():
                        inv_no = row['invoice_no']
                        total = float(row['total'])
                        paid = get_invoice_paid(inv_no)
                        balance = total - paid
                        
                        if balance <= 0:
                            status = '✅ Paid'
                        elif paid > 0:
                            status = '⚠️ Partially Paid'
                        else:
                            status = '❌ Unpaid'
                        
                        invoice_data.append({
                            'Invoice': inv_no,
                            'Date': row['date'][:10],
                            'Total': total,
                            'Received': paid,
                            'Balance': balance,
                            'Status': status
                        })
                    
                    if invoice_data:
                        df = pd.DataFrame(invoice_data)
                        st.dataframe(df, use_container_width=True)
                        st.metric("Total Outstanding", f"₹{df['Balance'].sum():,.2f}")

    # ==================== REPORTS ====================
    elif menu == "📈 Reports":
        st.header("📈 Reports")
        
        report_type = st.selectbox(
            "Select Report",
            ["Daily Sales", "Outstanding", "Receipt Summary"]
        )
        
        if report_type == "Daily Sales":
            st.subheader("📅 Daily Sales Report")
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("From", datetime.now() - timedelta(days=7))
            with col2:
                end_date = st.date_input("To", datetime.now())
            
            if st.button("📊 Generate"):
                sales = get_sales()
                if not sales.empty:
                    sales['date_only'] = sales['date'].str[:10]
                    filtered = sales[(sales['date_only'] >= str(start_date)) & (sales['date_only'] <= str(end_date))]
                    
                    if not filtered.empty:
                        st.dataframe(filtered[['invoice_no', 'date', 'party', 'total', 'status']], use_container_width=True)
                        st.metric("Total Sales", f"₹{filtered['total'].sum():,.2f}")
                    else:
                        st.info("No sales in this period")
        
        elif report_type == "Outstanding":
            st.subheader("📋 Outstanding Report")
            
            sales = get_sales()
            if not sales.empty:
                outstanding = sales[sales['status'] != 'Paid']
                if not outstanding.empty:
                    st.dataframe(outstanding, use_container_width=True)
                    st.metric("Total Outstanding", f"₹{outstanding['total'].sum():,.2f}")
                else:
                    st.success("✅ No outstanding dues!")
        
        elif report_type == "Receipt Summary":
            st.subheader("💳 Receipt Summary")
            
            receipts = get_receipts()
            if not receipts.empty:
                st.dataframe(receipts, use_container_width=True)
                st.metric("Total Receipts", f"₹{receipts['amount'].sum():,.2f}")
            else:
                st.info("No receipts recorded")

# ==================== RUN ====================

if __name__ == "__main__":
    main()
