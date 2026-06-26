"""
Detergent Billing Software - Streamlit Version
Products: Dishwash Liquid 1L (₹120), Detergent Powder 1kg (₹120), 
         Dishwash Liquid 7+1 (₹840), Detergent Powder 7+1 (₹840)
Google Sheets Database with Streamlit Secrets
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import io
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="🧺 Detergent Billing System",
    page_icon="🧺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== DEFAULT PRODUCTS ====================
DEFAULT_PRODUCTS = [
    {'name': 'Dishwash Liquid 1L', 'rate': 120, 'stock': 100, 'brand': 'Detergent', 'unit': 'Pcs'},
    {'name': 'Detergent Powder 1kg', 'rate': 120, 'stock': 100, 'brand': 'Detergent', 'unit': 'Pcs'},
    {'name': 'Dishwash Liquid 7+1', 'rate': 840, 'stock': 50, 'brand': 'Detergent', 'unit': 'Pack'},
    {'name': 'Detergent Powder 7+1', 'rate': 840, 'stock': 50, 'brand': 'Detergent', 'unit': 'Pack'},
]

# ==================== GOOGLE SHEETS SETUP ====================

def get_google_sheets_client():
    """Authenticate using Streamlit Secrets"""
    try:
        # Check if secrets exist
        if 'google_sheets' not in st.secrets:
            st.error("❌ Google Sheets credentials not found in secrets!")
            st.info("""
            Please set up your secrets:
            1. Create `.streamlit/secrets.toml` file
            2. Add your Google Sheets credentials
            3. Or set up in Streamlit Cloud dashboard
            """)
            return None
        
        # Get credentials from secrets
        creds_dict = dict(st.secrets['google_sheets'])
        
        # Define scope
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Create credentials
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        st.sidebar.success("✅ Connected to Google Sheets")
        return client
        
    except Exception as e:
        st.error(f"❌ Authentication error: {str(e)}")
        st.info("Make sure your secrets.toml has the correct format")
        return None

def get_spreadsheet(client):
    """Get the spreadsheet"""
    try:
        # Your spreadsheet ID from the URL
        sheet_id = "1jaat8u_k7rQyqhPcdL4zmUkkuG8gpwwk6z-Tvv2SMrQ"
        spreadsheet = client.open_by_key(sheet_id)
        return spreadsheet
    except Exception as e:
        st.error(f"❌ Error opening spreadsheet: {str(e)}")
        st.info("Make sure you've shared the sheet with: detergent-billing@detergent-billing.iam.gserviceaccount.com")
        return None

# ==================== DATABASE FUNCTIONS ====================

def initialize_sheets(spreadsheet):
    """Initialize sheets if they don't exist"""
    try:
        required_sheets = ['Products', 'Parties', 'Invoices', 'Invoice_Items', 
                          'Payments', 'Sales_Returns', 'Ledger_Adjustments']
        
        existing_sheets = [sheet.title for sheet in spreadsheet.worksheets()]
        
        for sheet_name in required_sheets:
            if sheet_name not in existing_sheets:
                spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                st.info(f"📝 Created sheet: {sheet_name}")
        
        # Initialize Products with default data if empty
        products_df = get_sheet_data(spreadsheet, 'Products')
        if products_df.empty:
            df = pd.DataFrame(DEFAULT_PRODUCTS)
            update_sheet_data(spreadsheet, 'Products', df)
            st.success("✅ Default products added to sheet!")
        
        return True
    except Exception as e:
        st.error(f"❌ Error initializing sheets: {str(e)}")
        return False

def get_sheet_data(spreadsheet, sheet_name):
    """Get data from a Google Sheet as DataFrame"""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_values()
        if not data:
            return pd.DataFrame()
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        return df
    except Exception as e:
        return pd.DataFrame()

def update_sheet_data(spreadsheet, sheet_name, df):
    """Update a Google Sheet with DataFrame data"""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
        if not df.empty:
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.error(f"Error updating sheet {sheet_name}: {str(e)}")
        return False

def add_row_to_sheet(spreadsheet, sheet_name, row_data):
    """Add a row to a Google Sheet"""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"Error adding row to {sheet_name}: {str(e)}")
        return False

# ==================== PRODUCT FUNCTIONS ====================

def get_products(spreadsheet):
    """Get all products"""
    if not spreadsheet:
        return pd.DataFrame(DEFAULT_PRODUCTS)
    df = get_sheet_data(spreadsheet, 'Products')
    if df.empty:
        df = pd.DataFrame(DEFAULT_PRODUCTS)
        update_sheet_data(spreadsheet, 'Products', df)
    return df

def add_product(spreadsheet, product_data):
    """Add a new product"""
    df = get_products(spreadsheet)
    new_row = pd.DataFrame([product_data])
    df = pd.concat([df, new_row], ignore_index=True)
    update_sheet_data(spreadsheet, 'Products', df)

def update_product_stock(spreadsheet, product_name, quantity_change):
    """Update product stock"""
    df = get_products(spreadsheet)
    if not df.empty:
        idx = df[df['name'] == product_name].index
        if not idx.empty:
            current_stock = float(df.loc[idx[0], 'stock'])
            df.loc[idx[0], 'stock'] = current_stock + quantity_change
            update_sheet_data(spreadsheet, 'Products', df)
            return True
    return False

# ==================== PARTY FUNCTIONS ====================

def get_parties(spreadsheet):
    """Get all parties"""
    if not spreadsheet:
        return pd.DataFrame(columns=['id', 'shop_name', 'mobile', 'address', 'opening_balance'])
    df = get_sheet_data(spreadsheet, 'Parties')
    if df.empty:
        df = pd.DataFrame(columns=['id', 'shop_name', 'mobile', 'address', 'opening_balance'])
        update_sheet_data(spreadsheet, 'Parties', df)
    return df

def add_party(spreadsheet, party_data):
    """Add a new party"""
    df = get_parties(spreadsheet)
    if df.empty:
        party_id = 1
    else:
        party_id = max(df['id'].astype(int)) + 1 if 'id' in df else 1
    
    new_row = pd.DataFrame([{
        'id': party_id,
        'shop_name': party_data['shop_name'],
        'mobile': party_data['mobile'],
        'address': party_data['address'],
        'opening_balance': party_data['opening_balance']
    }])
    
    df = pd.concat([df, new_row], ignore_index=True)
    update_sheet_data(spreadsheet, 'Parties', df)

# ==================== INVOICE FUNCTIONS ====================

def get_next_invoice_no(spreadsheet):
    """Generate next invoice number"""
    df = get_sheet_data(spreadsheet, 'Invoices')
    if df.empty:
        return "INV-000001"
    try:
        max_inv = max(df['invoice_no'].astype(str))
        num = int(max_inv.split('-')[1]) + 1
        return f"INV-{num:06d}"
    except:
        return "INV-000001"

def create_invoice(spreadsheet, party_id, cart, paid_amount):
    """Create a new invoice"""
    try:
        invoice_no = get_next_invoice_no(spreadsheet)
        total_amount = sum(item['amount'] for item in cart)
        balance = total_amount - paid_amount
        
        # Add to Invoices sheet
        invoice_data = [
            invoice_no,
            str(party_id),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(total_amount),
            str(paid_amount),
            str(max(0, balance))
        ]
        
        add_row_to_sheet(spreadsheet, 'Invoices', invoice_data)
        
        # Get invoice ID (row number)
        invoices_df = get_sheet_data(spreadsheet, 'Invoices')
        invoice_id = len(invoices_df)
        
        # Add invoice items and update stock
        for item in cart:
            item_data = [
                str(invoice_id),
                str(item['product_id']),
                str(item['quantity']),
                str(item['rate']),
                str(item['amount'])
            ]
            add_row_to_sheet(spreadsheet, 'Invoice_Items', item_data)
            
            # Update stock
            update_product_stock(spreadsheet, item['name'], -item['quantity'])
        
        return invoice_no, total_amount, balance
    
    except Exception as e:
        st.error(f"Error creating invoice: {str(e)}")
        return None, None, None

# ==================== PAYMENT FUNCTIONS ====================

def add_payment(spreadsheet, party_id, invoice_id, amount, payment_type, note=""):
    """Record a payment"""
    try:
        payment_data = [
            str(party_id),
            str(invoice_id),
            datetime.now().strftime("%Y-%m-%d"),
            str(amount),
            payment_type,
            note
        ]
        add_row_to_sheet(spreadsheet, 'Payments', payment_data)
        return True
    except Exception as e:
        st.error(f"Error recording payment: {str(e)}")
        return False

# ==================== MAIN APPLICATION ====================

def main():
    st.title("🧺 Detergent Billing System")
    
    # Sidebar
    st.sidebar.title("📋 Menu")
    st.sidebar.markdown("---")
    
    # Connect to Google Sheets using Secrets
    client = get_google_sheets_client()
    spreadsheet = None
    
    if client:
        spreadsheet = get_spreadsheet(client)
        if spreadsheet:
            if initialize_sheets(spreadsheet):
                st.sidebar.success("✅ Connected to Google Sheets")
                st.sidebar.info(f"📊 Sheet: {spreadsheet.title}")
                st.sidebar.info("🔑 Using Streamlit Secrets")
    
    if not spreadsheet:
        st.sidebar.warning("⚠️ Offline Mode - Using local data")
    
    # Navigation
    menu = st.sidebar.radio(
        "Navigate",
        ["📊 Dashboard", "📦 Products", "🏪 Parties", "🧾 Sales Billing", 
         "📒 Party Ledger", "💵 Payment Entry", "📈 Reports", "⚙️ Settings"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("Made with ❤️ using Streamlit")
    
    # Initialize session state for cart
    if 'cart' not in st.session_state:
        st.session_state.cart = []

    # ==================== DASHBOARD ====================
    if menu == "📊 Dashboard":
        st.header("📊 Dashboard")
        
        products = get_products(spreadsheet) if spreadsheet else pd.DataFrame(DEFAULT_PRODUCTS)
        invoices = get_sheet_data(spreadsheet, 'Invoices') if spreadsheet else pd.DataFrame()
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Today's Sales
        today = datetime.now().strftime("%Y-%m-%d")
        if not invoices.empty and 'date' in invoices:
            today_invoices = invoices[invoices['date'].str.startswith(today)]
            today_sales = today_invoices['total_amount'].astype(float).sum() if not today_invoices.empty else 0
        else:
            today_sales = 0
        col1.metric("Today's Sales", f"₹{today_sales:,.2f}")
        
        # Outstanding
        if not invoices.empty and 'balance' in invoices:
            outstanding = invoices['balance'].astype(float).sum()
        else:
            outstanding = 0
        col2.metric("Outstanding", f"₹{outstanding:,.2f}", delta="Due" if outstanding > 0 else "Settled")
        
        # Low Stock
        if not products.empty:
            low_stock = len(products[products['stock'].astype(float) < 10])
        else:
            low_stock = 0
        col3.metric("Low Stock Items", low_stock, delta="Need to reorder" if low_stock > 0 else "Stock OK")
        
        col4.metric("Total Products", len(products))
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Last 7 Days Sales")
            if not invoices.empty and 'date' in invoices:
                dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
                daily_sales = []
                for date in dates:
                    day_sales = invoices[invoices['date'].str.startswith(date)]
                    daily_sales.append(day_sales['total_amount'].astype(float).sum() if not day_sales.empty else 0)
                
                fig = px.line(x=dates, y=daily_sales, labels={'x': 'Date', 'y': 'Sales Amount'})
                fig.update_layout(showlegend=False, height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No sales data available")
        
        with col2:
            st.subheader("🏷️ Product Stock Status")
            if not products.empty:
                fig = px.bar(products, x='name', y='stock', 
                           color='stock', 
                           color_continuous_scale=['red', 'yellow', 'green'],
                           labels={'x': 'Product', 'y': 'Stock'})
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No products available")

    # ==================== PRODUCTS ====================
    elif menu == "📦 Products":
        st.header("📦 Product Master")
        
        tab1, tab2 = st.tabs(["Manage Products", "Add New Product"])
        
        with tab1:
            products = get_products(spreadsheet) if spreadsheet else pd.DataFrame(DEFAULT_PRODUCTS)
            if not products.empty:
                st.dataframe(products, use_container_width=True, hide_index=True)
                
                st.subheader("Quick Stock Update")
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    product_to_update = st.selectbox("Select Product", products['name'].tolist())
                with col2:
                    stock_change = st.number_input("Add/Deduct Stock", value=0.0, step=1.0)
                with col3:
                    if st.button("Update Stock"):
                        if stock_change != 0 and spreadsheet:
                            if update_product_stock(spreadsheet, product_to_update, stock_change):
                                st.success(f"Stock updated! Change: {stock_change}")
                                st.rerun()
            else:
                st.info("No products added yet.")
        
        with tab2:
            with st.form("add_product_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Product Name *")
                    rate = st.number_input("Rate (₹) *", min_value=0.0, step=1.0)
                with col2:
                    stock = st.number_input("Stock Quantity *", min_value=0.0, step=1.0)
                    brand = st.text_input("Brand", "Detergent")
                    unit = st.selectbox("Unit", ["Pcs", "Pack", "Kg", "Ltr"])
                
                submitted = st.form_submit_button("Add Product")
                if submitted and name and rate > 0 and spreadsheet:
                    add_product(spreadsheet, {'name': name, 'rate': rate, 'stock': stock, 'brand': brand, 'unit': unit})
                    st.success(f"Product '{name}' added successfully!")
                    st.rerun()

    # ==================== PARTIES ====================
    elif menu == "🏪 Parties":
        st.header("🏪 Party Master")
        
        tab1, tab2 = st.tabs(["Manage Parties", "Add New Party"])
        
        with tab1:
            parties = get_parties(spreadsheet) if spreadsheet else pd.DataFrame()
            if not parties.empty:
                st.dataframe(parties, use_container_width=True, hide_index=True)
            else:
                st.info("No parties added yet.")
        
        with tab2:
            with st.form("add_party_form"):
                col1, col2 = st.columns(2)
                with col1:
                    shop_name = st.text_input("Shop Name *")
                    mobile = st.text_input("Mobile Number")
                with col2:
                    address = st.text_area("Address")
                    opening_balance = st.number_input("Opening Balance (₹)", min_value=0.0, step=100.0)
                
                submitted = st.form_submit_button("Add Party")
                if submitted and shop_name and spreadsheet:
                    add_party(spreadsheet, {'shop_name': shop_name, 'mobile': mobile, 'address': address, 'opening_balance': opening_balance})
                    st.success(f"Party '{shop_name}' added successfully!")
                    st.rerun()

    # ==================== SALES BILLING ====================
    elif menu == "🧾 Sales Billing":
        st.header("🧾 Sales Billing")
        
        if not spreadsheet:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Add Items to Cart")
            products = get_products(spreadsheet)
            
            if products.empty:
                st.warning("No products available!")
            else:
                product_names = products['name'].tolist()
                selected_product = st.selectbox("Select Product", product_names)
                
                if selected_product:
                    product_data = products[products['name'] == selected_product].iloc[0]
                    stock = float(product_data['stock'])
                    rate = float(product_data['rate'])
                    st.info(f"📦 Stock: {stock} | Rate: ₹{rate:,.2f}")
                    
                    col_qty, col_add = st.columns([2, 1])
                    with col_qty:
                        quantity = st.number_input("Quantity", min_value=0.0, max_value=stock, step=1.0)
                    with col_add:
                        if st.button("➕ Add to Cart"):
                            if quantity > 0:
                                st.session_state.cart.append({
                                    'product_id': len(products),
                                    'name': selected_product,
                                    'rate': rate,
                                    'quantity': quantity,
                                    'amount': rate * quantity
                                })
                                st.success(f"Added {quantity} {selected_product}")
                                st.rerun()
        
        with col2:
            st.subheader("Cart")
            if st.session_state.cart:
                cart_df = pd.DataFrame(st.session_state.cart)
                st.dataframe(cart_df[['name', 'quantity', 'rate', 'amount']], use_container_width=True)
                total = cart_df['amount'].sum()
                st.metric("Total Amount", f"₹{total:,.2f}")
                if st.button("🗑️ Clear Cart"):
                    st.session_state.cart = []
                    st.rerun()
            else:
                st.info("Cart is empty")
        
        st.markdown("---")
        st.subheader("Create Invoice")
        
        parties = get_parties(spreadsheet)
        if parties.empty:
            st.warning("No parties available!")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                party_name = st.selectbox("Select Party", parties['shop_name'].tolist())
            with col2:
                paid_amount = st.number_input("Paid Amount (₹)", min_value=0.0, step=100.0)
            with col3:
                if st.button("💳 Generate Invoice", type="primary"):
                    if not st.session_state.cart:
                        st.error("Cart is empty!")
                    else:
                        party_id = int(parties[parties['shop_name'] == party_name].iloc[0]['id'])
                        invoice_no, total, balance = create_invoice(spreadsheet, party_id, st.session_state.cart, paid_amount)
                        if invoice_no:
                            st.success(f"Invoice {invoice_no} generated!")
                            
                            # Show invoice preview
                            with st.expander("📄 Invoice Preview"):
                                st.write(f"**Invoice No:** {invoice_no}")
                                st.write(f"**Party:** {party_name}")
                                st.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                                st.write("---")
                                items_df = pd.DataFrame(st.session_state.cart)
                                st.dataframe(items_df[['name', 'quantity', 'rate', 'amount']], use_container_width=True)
                                st.write("---")
                                st.write(f"**Total:** ₹{total:,.2f}")
                                st.write(f"**Paid:** ₹{paid_amount:,.2f}")
                                st.write(f"**Balance:** ₹{max(0, balance):,.2f}")
                            
                            st.session_state.cart = []

    # ==================== PARTY LEDGER ====================
    elif menu == "📒 Party Ledger":
        st.header("📒 Party Ledger")
        
        if not spreadsheet:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        parties = get_parties(spreadsheet)
        if not parties.empty:
            selected_party = st.selectbox("Select Party", parties['shop_name'].tolist())
            
            if selected_party:
                parties_df = get_parties(spreadsheet)
                party = parties_df[parties_df['shop_name'] == selected_party]
                if not party.empty:
                    party_id = int(party.iloc[0]['id'])
                    
                    # Get invoices
                    invoices_df = get_sheet_data(spreadsheet, 'Invoices')
                    party_invoices = invoices_df[invoices_df['party_id'].astype(str) == str(party_id)]
                    
                    # Get payments
                    payments_df = get_sheet_data(spreadsheet, 'Payments')
                    party_payments = payments_df[payments_df['party_id'].astype(str) == str(party_id)]
                    
                    st.subheader(f"Statement for {selected_party}")
                    
                    # Show invoices
                    if not party_invoices.empty:
                        st.write("**Invoices**")
                        st.dataframe(party_invoices[['invoice_no', 'date', 'total_amount', 'paid_amount', 'balance']], 
                                   use_container_width=True, hide_index=True)
                    
                    # Show payments
                    if not party_payments.empty:
                        st.write("**Payments**")
                        st.dataframe(party_payments[['date', 'amount', 'payment_type', 'note']], 
                                   use_container_width=True, hide_index=True)
                    
                    # Summary
                    col1, col2, col3 = st.columns(3)
                    total_sales = party_invoices['total_amount'].astype(float).sum() if not party_invoices.empty else 0
                    total_paid = party_payments['amount'].astype(float).sum() if not party_payments.empty else 0
                    total_balance = total_sales - total_paid
                    
                    col1.metric("Total Sales", f"₹{total_sales:,.2f}")
                    col2.metric("Total Paid", f"₹{total_paid:,.2f}")
                    col3.metric("Outstanding", f"₹{total_balance:,.2f}", 
                              delta="Due" if total_balance > 0 else "Settled")

    # ==================== PAYMENT ENTRY ====================
    elif menu == "💵 Payment Entry":
        st.header("💵 Payment Entry")
        
        if not spreadsheet:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        parties = get_parties(spreadsheet)
        if not parties.empty:
            party_name = st.selectbox("Select Party", parties['shop_name'].tolist())
            
            if party_name:
                party_id = int(parties[parties['shop_name'] == party_name].iloc[0]['id'])
                invoices_df = get_sheet_data(spreadsheet, 'Invoices')
                party_invoices = invoices_df[invoices_df['party_id'].astype(str) == str(party_id)]
                party_invoices = party_invoices[party_invoices['balance'].astype(float) > 0]
                
                if not party_invoices.empty:
                    st.dataframe(party_invoices[['invoice_no', 'total_amount', 'paid_amount', 'balance']], 
                               use_container_width=True)
                    
                    invoice_no = st.selectbox("Select Invoice", party_invoices['invoice_no'].tolist())
                    if invoice_no:
                        invoice = party_invoices[party_invoices['invoice_no'] == invoice_no].iloc[0]
                        st.info(f"Outstanding: ₹{float(invoice['balance']):,.2f}")
                        
                        with st.form("payment_form"):
                            amount = st.number_input("Payment Amount", min_value=0.0, 
                                                    max_value=float(invoice['balance']), step=100.0)
                            payment_type = st.selectbox("Payment Type", ["Cash", "UPI", "Bank Transfer", "Cheque"])
                            note = st.text_area("Note (Optional)")
                            
                            if st.form_submit_button("Record Payment"):
                                if amount > 0:
                                    invoice_id = int(party_invoices[party_invoices['invoice_no'] == invoice_no].index[0]) + 1
                                    if add_payment(spreadsheet, party_id, invoice_id, amount, payment_type, note):
                                        # Update invoice
                                        new_paid = float(invoice['paid_amount']) + amount
                                        new_balance = float(invoice['total_amount']) - new_paid
                                        
                                        st.success(f"Payment of ₹{amount:,.2f} recorded!")
                                        st.rerun()
                else:
                    st.info("No outstanding invoices for this party")

    # ==================== REPORTS ====================
    elif menu == "📈 Reports":
        st.header("📈 Reports")
        
        if not spreadsheet:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        report_type = st.selectbox("Select Report", 
                                  ["Daily Sales", "Monthly Sales", "Product-wise Sales", 
                                   "Party-wise Sales", "Outstanding Report"])
        
        if report_type == "Daily Sales":
            date = st.date_input("Select Date", datetime.now())
            date_str = date.strftime("%Y-%m-%d")
            invoices_df = get_sheet_data(spreadsheet, 'Invoices')
            daily_invoices = invoices_df[invoices_df['date'].str.startswith(date_str)]
            
            if not daily_invoices.empty:
                st.dataframe(daily_invoices, use_container_width=True, hide_index=True)
                st.metric("Total Sales", f"₹{daily_invoices['total_amount'].astype(float).sum():,.2f}")
            else:
                st.info("No sales for this date")
        
        elif report_type == "Monthly Sales":
            month = st.selectbox("Select Month", range(1, 13), 
                               format_func=lambda x: datetime(2024, x, 1).strftime("%B"))
            year = st.number_input("Year", min_value=2020, max_value=2030, value=datetime.now().year)
            
            month_str = f"{year}-{month:02d}"
            invoices_df = get_sheet_data(spreadsheet, 'Invoices')
            monthly_invoices = invoices_df[invoices_df['date'].str.startswith(month_str)]
            
            if not monthly_invoices.empty:
                st.dataframe(monthly_invoices, use_container_width=True, hide_index=True)
                st.metric("Total Sales", f"₹{monthly_invoices['total_amount'].astype(float).sum():,.2f}")
            else:
                st.info("No sales for this month")
        
        elif report_type == "Product-wise Sales":
            items_df = get_sheet_data(spreadsheet, 'Invoice_Items')
            products_df = get_products(spreadsheet)
            
            if not items_df.empty and not products_df.empty:
                # Map product names
                product_sales = items_df.groupby('product_id')['amount'].sum().reset_index()
                product_sales = product_sales.merge(products_df, left_on='product_id', right_index=True, how='left')
                st.dataframe(product_sales[['name', 'amount']], use_container_width=True, hide_index=True)
                
                # Pie chart
                fig = px.pie(product_sales, values='amount', names='name', title='Product-wise Sales Distribution')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No sales data available")
        
        elif report_type == "Party-wise Sales":
            invoices_df = get_sheet_data(spreadsheet, 'Invoices')
            parties_df = get_parties(spreadsheet)
            
            if not invoices_df.empty and not parties_df.empty:
                party_sales = invoices_df.groupby('party_id')['total_amount'].sum().reset_index()
                party_sales = party_sales.merge(parties_df, left_on='party_id', right_on='id', how='left')
                st.dataframe(party_sales[['shop_name', 'total_amount']], use_container_width=True, hide_index=True)
                
                # Bar chart
                fig = px.bar(party_sales, x='shop_name', y='total_amount', title='Party-wise Sales')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available")
        
        elif report_type == "Outstanding Report":
            invoices_df = get_sheet_data(spreadsheet, 'Invoices')
            outstanding = invoices_df[invoices_df['balance'].astype(float) > 0]
            
            if not outstanding.empty:
                parties_df = get_parties(spreadsheet)
                outstanding = outstanding.merge(parties_df, left_on='party_id', right_on='id', how='left')
                st.dataframe(outstanding[['invoice_no', 'shop_name', 'total_amount', 'paid_amount', 'balance']], 
                           use_container_width=True, hide_index=True)
                st.metric("Total Outstanding", f"₹{outstanding['balance'].astype(float).sum():,.2f}")
            else:
                st.info("No outstanding dues")

    # ==================== SETTINGS ====================
    elif menu == "⚙️ Settings":
        st.header("⚙️ Settings")
        
        st.subheader("🔐 Google Sheets Connection Status")
        if spreadsheet:
            st.success("✅ Connected to Google Sheets using Streamlit Secrets")
            st.info(f"📊 Spreadsheet: {spreadsheet.title}")
            st.info(f"🔑 Service Account: detergent-billing@detergent-billing.iam.gserviceaccount.com")
        else:
            st.error("❌ Not connected to Google Sheets")
        
        st.subheader("📦 Default Products")
        st.dataframe(pd.DataFrame(DEFAULT_PRODUCTS), use_container_width=True, hide_index=True)
        


# ==================== RUN APPLICATION ====================

if __name__ == "__main__":
    main()
