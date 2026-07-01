"""
Detergent Billing System
PRIMARY: SQLite (local database)
BACKUP: Google Sheets (optional sync)
NO RATE LIMIT ISSUES
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import json
import time

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="🧺 Detergent Billing System",
    page_icon="🧺",
    layout="wide"
)

# ==================== DATABASE SETUP ====================

def init_local_db():
    """Initialize SQLite database"""
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

def get_db_connection():
    return sqlite3.connect('detergent_billing.db')

# ==================== DATABASE FUNCTIONS ====================

def get_products():
    """Get all products from local DB"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT product_id, name, rate, stock, brand, unit FROM products ORDER BY name", conn)
    conn.close()
    return df

def add_product(product_id, name, rate, stock, brand='', unit='Pcs'):
    """Add product to local DB"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO products (product_id, name, rate, stock, brand, unit) VALUES (?, ?, ?, ?, ?, ?)",
              (product_id, name, rate, stock, brand, unit))
    conn.commit()
    conn.close()

def update_product_stock(name, change):
    """Update product stock"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (change, name))
    conn.commit()
    conn.close()

def get_parties():
    """Get all parties from local DB"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT party_id, name, mobile, whatsapp, address, opening_balance, gst_no FROM parties ORDER BY name", conn)
    conn.close()
    return df

def add_party(party_id, name, mobile, whatsapp, address, opening_balance, gst_no):
    """Add party to local DB"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO parties (party_id, name, mobile, whatsapp, address, opening_balance, gst_no) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (party_id, name, mobile, whatsapp, address, opening_balance, gst_no))
    conn.commit()
    conn.close()

def get_sales():
    """Get all sales from local DB"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT invoice_no, date, party, total, status FROM sales ORDER BY date DESC", conn)
    conn.close()
    return df

def add_sale(invoice_no, date, party, total, status='Unpaid'):
    """Add sale to local DB"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO sales (invoice_no, date, party, total, status) VALUES (?, ?, ?, ?, ?)",
              (invoice_no, date, party, total, status))
    conn.commit()
    conn.close()

def add_sale_item(invoice_no, product_id, product_name, qty, rate, amount):
    """Add sale item to local DB"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO sales_items (invoice_no, product_id, product_name, qty, rate, amount) VALUES (?, ?, ?, ?, ?, ?)",
              (invoice_no, product_id, product_name, qty, rate, amount))
    conn.commit()
    conn.close()

def get_sale_items(invoice_no):
    """Get items for an invoice"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT product_id, product_name, qty, rate, amount FROM sales_items WHERE invoice_no = ?", 
                          conn, params=(invoice_no,))
    conn.close()
    return df

def get_receipts():
    """Get all receipts from local DB"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT receipt_no, date, party, invoice_no, amount, payment_mode, remarks FROM receipts ORDER BY date DESC", conn)
    conn.close()
    return df

def add_receipt(receipt_no, date, party, invoice_no, amount, payment_mode, remarks=''):
    """Add receipt to local DB"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO receipts (receipt_no, date, party, invoice_no, amount, payment_mode, remarks) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (receipt_no, date, party, invoice_no, amount, payment_mode, remarks))
    conn.commit()
    conn.close()

def get_next_invoice_no():
    """Generate next invoice number"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT MAX(invoice_no) FROM sales")
    result = c.fetchone()[0]
    conn.close()
    if result:
        num = int(result.replace('INV', '')) + 1
        return f"INV{num:04d}"
    return "INV0001"

def get_next_receipt_no():
    """Generate next receipt number"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT MAX(receipt_no) FROM receipts")
    result = c.fetchone()[0]
    conn.close()
    if result:
        num = int(result.replace('REC', '')) + 1
        return f"REC{num:04d}"
    return "REC0001"

def get_next_party_id():
    """Generate next party ID"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT MAX(party_id) FROM parties")
    result = c.fetchone()[0]
    conn.close()
    if result:
        num = int(result.replace('PT', '')) + 1
        return f"PT{num:04d}"
    return "PT0001"

def safe_float(value):
    try:
        if value is None or value == '':
            return 0.0
        return float(str(value).strip())
    except:
        return 0.0

def safe_int(value):
    try:
        if value is None or value == '':
            return 0
        return int(float(str(value).strip()))
    except:
        return 0

# ==================== INIT ====================

def init_data():
    """Initialize with default data if empty"""
    # Initialize products if empty
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

# ==================== MAIN APP ====================

def main():
    # Initialize local database
    init_local_db()
    init_data()
    
    st.title("🧺 Detergent Billing System")
    
    # Sidebar
    st.sidebar.title("📋 Menu")
    st.sidebar.markdown("---")
    st.sidebar.success("✅ Local Database Active")
    st.sidebar.info("📊 Data stored locally - No rate limits!")
    
    # Menu
    menu = st.sidebar.radio(
        "Navigate",
        ["📊 Dashboard", "📦 Products", "🏪 Parties", "🧾 Billing", 
         "💰 Cash Receipt", "📒 Party Ledger", "📈 Reports"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("Made with ❤️ using Streamlit")
    
    # Initialize cart
    if 'cart' not in st.session_state:
        st.session_state.cart = []

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
        
        total_sales = sales['total'].sum() if not sales.empty else 0
        col3.metric("💰 Total Sales", f"₹{total_sales:,.2f}")
        
        total_receipts = receipts['amount'].sum() if not receipts.empty else 0
        col4.metric("💳 Total Receipts", f"₹{total_receipts:,.2f}")
        
        st.subheader("📄 Recent Invoices")
        if not sales.empty:
            st.dataframe(sales.head(10), use_container_width=True)
        else:
            st.info("No sales yet")

    # ==================== PRODUCTS ====================
    elif menu == "📦 Products":
        st.header("📦 Product Master")
        
        products = get_products()
        
        tab1, tab2 = st.tabs(["Manage Products", "Add Product"])
        
        with tab1:
            if not products.empty:
                st.dataframe(products, use_container_width=True)
                
                st.subheader("Quick Stock Update")
                col1, col2 = st.columns([2, 1])
                with col1:
                    selected = st.selectbox("Select Product", products['name'].tolist())
                with col2:
                    change = st.number_input("Change (+/-)", value=0, step=1)
                    if st.button("Update Stock"):
                        if change != 0:
                            update_product_stock(selected, change)
                            st.success(f"✅ Stock updated! {selected}: {change}")
                            st.rerun()
            else:
                st.info("No products available")
        
        with tab2:
            with st.form("add_product"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Product Name *")
                    rate = st.number_input("Rate (₹) *", min_value=0.0, step=1.0)
                with col2:
                    stock = st.number_input("Stock Quantity *", min_value=0, step=1)
                    brand = st.text_input("Brand")
                    unit = st.selectbox("Unit", ["Pcs", "Pack", "Kg", "Ltr"])
                
                if st.form_submit_button("Add Product"):
                    if name and rate > 0:
                        products = get_products()
                        product_id = f"P{len(products)+1:03d}"
                        add_product(product_id, name, rate, stock, brand, unit)
                        st.success(f"✅ Product '{name}' added!")
                        st.rerun()

    # ==================== PARTIES ====================
    elif menu == "🏪 Parties":
        st.header("🏪 Party Master")
        
        parties = get_parties()
        
        tab1, tab2 = st.tabs(["Manage Parties", "Add Party"])
        
        with tab1:
            if parties.empty:
                st.info("No parties added yet")
            else:
                st.dataframe(parties, use_container_width=True)
        
        with tab2:
            with st.form("add_party_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Party Name *")
                    mobile = st.text_input("Mobile Number")
                    whatsapp = st.text_input("WhatsApp Number")
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
            st.warning("⚠️ No products!")
            return
        
        if parties.empty:
            st.warning("⚠️ No parties!")
            return
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🛒 Add Items")
            
            product_names = products['name'].tolist()
            selected = st.selectbox("Select Product", product_names)
            
            if selected:
                product = products[products['name'] == selected].iloc[0]
                stock = safe_float(product['stock'])
                rate = safe_float(product['rate'])
                product_id = product['product_id']
                st.info(f"📦 Stock: {stock} | 💰 Rate: ₹{rate:.2f}")
                
                qty = st.number_input("Quantity", min_value=1.0, max_value=stock, step=1.0)
                if st.button("➕ Add to Cart"):
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
                st.metric("💰 Total", f"₹{total:,.2f}")
                if st.button("🗑️ Clear Cart"):
                    st.session_state.cart = []
                    st.rerun()
            else:
                st.info("Cart empty")
        
        st.markdown("---")
        st.subheader("📄 Create Invoice")
        
        party_names = parties['name'].tolist()
        party = st.selectbox("Select Party", party_names)
        
        if st.button("💳 Generate Invoice", type="primary"):
            if not st.session_state.cart:
                st.error("❌ Cart empty!")
            else:
                invoice_no = get_next_invoice_no()
                total = sum(item['amount'] for item in st.session_state.cart)
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                add_sale(invoice_no, now, party, total, 'Unpaid')
                
                for item in st.session_state.cart:
                    add_sale_item(invoice_no, item['product_id'], item['name'], item['qty'], item['rate'], item['amount'])
                    update_product_stock(item['name'], -item['qty'])
                
                st.success(f"✅ Invoice {invoice_no} generated! Total: ₹{total:,.2f}")
                st.session_state.cart = []
                st.rerun()

    # ==================== CASH RECEIPT ====================
    elif menu == "💰 Cash Receipt":
        st.header("💰 Cash Receipt Entry")
        
        parties = get_parties()
        sales = get_sales()
        
        if parties.empty:
            st.warning("⚠️ No parties!")
            return
        
        if sales.empty:
            st.warning("⚠️ No invoices!")
            return
        
        st.subheader("📝 Enter Receipt Details")
        
        with st.form("receipt_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                party_names = parties['name'].tolist()
                party = st.selectbox("Party *", party_names)
                
                # Get unpaid invoices
                unpaid = sales[sales['status'] != 'Paid'] if not sales.empty else pd.DataFrame()
                party_invoices = unpaid[unpaid['party'] == party] if party else pd.DataFrame()
                
                invoice_options = [''] + party_invoices['invoice_no'].tolist() if not party_invoices.empty else ['']
                invoice_no = st.selectbox("Select Invoice Number", invoice_options)
            
            with col2:
                manual_invoice = st.text_input("Or Enter Invoice Number Manually", placeholder="e.g., INV0001")
                final_invoice = manual_invoice if manual_invoice else invoice_no
                
                amount = st.number_input("Payment Amount (₹) *", min_value=0.0, step=100.0)
                payment_mode = st.selectbox("Payment Mode", ["Cash", "UPI", "Bank Transfer", "Cheque"])
                remarks = st.text_area("Remarks (Optional)")
            
            submitted = st.form_submit_button("💳 Record Receipt", type="primary")
            
            if submitted:
                if not party:
                    st.error("❌ Please select a party!")
                elif not final_invoice:
                    st.error("❌ Please enter or select an invoice number!")
                elif amount <= 0:
                    st.error("❌ Amount must be greater than 0!")
                else:
                    # Verify invoice
                    invoice_data = sales[sales['invoice_no'] == final_invoice]
                    if invoice_data.empty:
                        st.error(f"❌ Invoice {final_invoice} not found!")
                    else:
                        receipt_no = get_next_receipt_no()
                        now = datetime.now().strftime("%Y-%m-%d %H:%M")
                        
                        add_receipt(receipt_no, now, party, final_invoice, amount, payment_mode, remarks)
                        
                        # Update invoice status
                        total = safe_float(invoice_data.iloc[0]['total'])
                        receipts = get_receipts()
                        paid = receipts[receipts['invoice_no'] == final_invoice]['amount'].sum() if not receipts.empty else 0
                        
                        if paid >= total:
                            status = 'Paid'
                        elif paid > 0:
                            status = 'Partially Paid'
                        else:
                            status = 'Unpaid'
                        
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("UPDATE sales SET status = ? WHERE invoice_no = ?", (status, final_invoice))
                        conn.commit()
                        conn.close()
                        
                        st.success(f"✅ Receipt {receipt_no} recorded! Amount: ₹{amount:,.2f}")
                        st.balloons()
                        st.rerun()

    # ==================== PARTY LEDGER ====================
    elif menu == "📒 Party Ledger":
        st.header("📒 Party Ledger")
        
        parties = get_parties()
        sales = get_sales()
        receipts = get_receipts()
        
        if parties.empty:
            st.warning("⚠️ No parties!")
            return
        
        st.subheader("📋 Select Party")
        
        party_names = parties['name'].tolist()
        selected_party = st.selectbox("Select Party", party_names)
        
        if selected_party:
            party_sales = sales[sales['party'] == selected_party] if not sales.empty else pd.DataFrame()
            party_receipts = receipts[receipts['party'] == selected_party] if not receipts.empty else pd.DataFrame()
            
            if party_sales.empty and party_receipts.empty:
                st.info(f"No transactions for {selected_party}")
            else:
                tab1, tab2 = st.tabs(["📊 Complete Ledger", "📄 Invoice-wise Collection"])
                
                with tab1:
                    st.subheader(f"📊 Complete Ledger - {selected_party}")
                    
                    transactions = []
                    balance = 0
                    
                    # Opening balance
                    party_data = parties[parties['name'] == selected_party].iloc[0]
                    opening = safe_float(party_data['opening_balance'])
                    balance = opening
                    transactions.append({
                        'Date': 'Opening',
                        'Particulars': 'Opening Balance',
                        'Invoice': '',
                        'Debit': opening,
                        'Credit': 0,
                        'Balance': balance
                    })
                    
                    for _, row in party_sales.iterrows():
                        amt = safe_float(row['total'])
                        balance += amt
                        transactions.append({
                            'Date': row['date'][:10] if row['date'] else '',
                            'Particulars': f"Sale - {row['invoice_no']}",
                            'Invoice': row['invoice_no'],
                            'Debit': amt,
                            'Credit': 0,
                            'Balance': balance
                        })
                    
                    for _, row in party_receipts.iterrows():
                        amt = safe_float(row['amount'])
                        balance -= amt
                        transactions.append({
                            'Date': row['date'][:10] if row['date'] else '',
                            'Particulars': f"Receipt - {row['receipt_no']}",
                            'Invoice': row['invoice_no'],
                            'Debit': 0,
                            'Credit': amt,
                            'Balance': balance
                        })
                    
                    df = pd.DataFrame(transactions)
                    st.dataframe(df, use_container_width=True)
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Sales", f"₹{party_sales['total'].sum():,.2f}" if not party_sales.empty else "₹0")
                    col2.metric("Total Receipts", f"₹{party_receipts['amount'].sum():,.2f}" if not party_receipts.empty else "₹0")
                    col3.metric("Balance", f"₹{balance:,.2f}", delta="Due" if balance > 0 else "Settled")
                
                with tab2:
                    st.subheader(f"📄 Invoice-wise Collection - {selected_party}")
                    
                    invoice_data = []
                    for _, row in party_sales.iterrows():
                        inv_no = row['invoice_no']
                        total = safe_float(row['total'])
                        inv_receipts = party_receipts[party_receipts['invoice_no'] == inv_no] if not party_receipts.empty else pd.DataFrame()
                        paid = inv_receipts['amount'].sum() if not inv_receipts.empty else 0
                        balance = total - paid
                        
                        status = '✅ Paid' if balance <= 0 else '⚠️ Partially Paid' if paid > 0 else '❌ Unpaid'
                        
                        invoice_data.append({
                            'Invoice No': inv_no,
                            'Date': row['date'][:10] if row['date'] else '',
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
            ["Daily Sales Report", "Outstanding Report", "Receipt Summary"]
        )
        
        if report_type == "Daily Sales Report":
            st.subheader("📅 Sales Report by Date Range")
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("From Date", datetime.now() - timedelta(days=7))
            with col2:
                end_date = st.date_input("To Date", datetime.now())
            
            if st.button("📊 Generate Report"):
                sales = get_sales()
                if not sales.empty:
                    sales['date_only'] = sales['date'].str[:10]
                    filtered = sales[(sales['date_only'] >= str(start_date)) & (sales['date_only'] <= str(end_date))]
                    
                    if not filtered.empty:
                        st.dataframe(filtered[['invoice_no', 'date', 'party', 'total', 'status']], use_container_width=True)
                        st.metric("Total Sales", f"₹{filtered['total'].sum():,.2f}")
                    else:
                        st.info("No sales in this period")
        
        elif report_type == "Outstanding Report":
            sales = get_sales()
            if not sales.empty:
                outstanding = sales[sales['status'] != 'Paid']
                if not outstanding.empty:
                    st.dataframe(outstanding, use_container_width=True)
                    st.metric("Total Outstanding", f"₹{outstanding['total'].sum():,.2f}")
                else:
                    st.success("✅ No outstanding dues!")
        
        elif report_type == "Receipt Summary":
            receipts = get_receipts()
            if not receipts.empty:
                st.dataframe(receipts, use_container_width=True)
                st.metric("Total Receipts", f"₹{receipts['amount'].sum():,.2f}")
            else:
                st.info("No receipts recorded")

# ==================== RUN ====================

if __name__ == "__main__":
    main()
