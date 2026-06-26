"""
Detergent Billing Software - Google Sheets Version
Using Google API Client (More Reliable)
Products: Dishwash Liquid 1L (₹120), Detergent Powder 1kg (₹120), 
         Dishwash Liquid 7+1 (₹840), Detergent Powder 7+1 (₹840)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Google API imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="🧺 Detergent Billing System",
    page_icon="🧺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== GOOGLE SHEETS SETUP ====================

def get_sheets_service():
    """Get Google Sheets API service"""
    try:
        # Get credentials from secrets
        if 'google_sheets' in st.secrets:
            creds_dict = dict(st.secrets['google_sheets'])
        else:
            st.warning("⚠️ Please upload your Service Account JSON file")
            uploaded_file = st.file_uploader("Upload Service Account JSON", type=['json'])
            if uploaded_file:
                creds_dict = json.load(uploaded_file)
            else:
                return None
        
        # Create credentials
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Build service
        service = build('sheets', 'v4', credentials=creds)
        return service
        
    except Exception as e:
        st.error(f"❌ Connection error: {str(e)}")
        return None

def get_spreadsheet_id():
    """Get spreadsheet ID from URL"""
    sheet_url = "https://docs.google.com/spreadsheets/d/1jaat8u_k7rQyqhPcdL4zmUkkuG8gpwwk6z-Tvv2SMrQ/edit?usp=sharing"
    sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    return sheet_id

# ==================== DATABASE HELPERS ====================

def get_data(service, sheet_name):
    """Get data from a Google Sheet"""
    try:
        sheet_id = get_spreadsheet_id()
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!A:Z"
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return pd.DataFrame()
        
        headers = values[0]
        rows = values[1:]
        df = pd.DataFrame(rows, columns=headers)
        return df
        
    except Exception as e:
        return pd.DataFrame()

def add_row(service, sheet_name, row_data):
    """Add a row to a Google Sheet"""
    try:
        sheet_id = get_spreadsheet_id()
        body = {
            'values': [row_data]
        }
        result = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!A:Z",
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error adding row: {str(e)}")
        return False

def update_data(service, sheet_name, df):
    """Update a Google Sheet"""
    try:
        sheet_id = get_spreadsheet_id()
        # Clear existing data
        service.spreadsheets().values().clear(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!A:Z",
            body={}
        ).execute()
        
        # Update with new data
        if not df.empty:
            values = [df.columns.values.tolist()] + df.values.tolist()
            body = {'values': values}
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
        return True
    except Exception as e:
        st.error(f"Error updating: {str(e)}")
        return False

def create_sheet_if_not_exists(service, sheet_name):
    """Create a sheet if it doesn't exist"""
    try:
        sheet_id = get_spreadsheet_id()
        
        # Check if sheet exists
        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = spreadsheet.get('sheets', [])
        sheet_names = [sheet['properties']['title'] for sheet in sheets]
        
        if sheet_name not in sheet_names:
            # Create sheet
            body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body=body
            ).execute()
            return True
        return True
    except Exception as e:
        st.error(f"Error creating sheet {sheet_name}: {str(e)}")
        return False

# ==================== INITIALIZE SHEETS ====================

def init_sheets(service):
    """Initialize sheets with default data"""
    try:
        required_sheets = ['Products', 'Parties', 'Invoices', 'Invoice_Items', 'Payments']
        
        for sheet_name in required_sheets:
            create_sheet_if_not_exists(service, sheet_name)
        
        # Initialize Products with default data
        products = get_data(service, 'Products')
        if products.empty:
            default_products = [
                ['Dishwash Liquid 1L', 120, 100, 'Detergent', 'Pcs'],
                ['Detergent Powder 1kg', 120, 100, 'Detergent', 'Pcs'],
                ['Dishwash Liquid 7+1', 840, 50, 'Detergent', 'Pack'],
                ['Detergent Powder 7+1', 840, 50, 'Detergent', 'Pack']
            ]
            headers = ['name', 'rate', 'stock', 'brand', 'unit']
            df = pd.DataFrame(default_products, columns=headers)
            update_data(service, 'Products', df)
            st.success("✅ Default products added!")
        
        # Initialize Parties
        parties = get_data(service, 'Parties')
        if parties.empty:
            headers = ['id', 'shop_name', 'mobile', 'address', 'opening_balance']
            df = pd.DataFrame(columns=headers)
            update_data(service, 'Parties', df)
        
        return True
    except Exception as e:
        st.error(f"Error initializing: {str(e)}")
        return False

# ==================== PRODUCT FUNCTIONS ====================

def get_products(service):
    """Get all products"""
    df = get_data(service, 'Products')
    if not df.empty:
        df['rate'] = pd.to_numeric(df['rate'], errors='coerce')
        df['stock'] = pd.to_numeric(df['stock'], errors='coerce')
    return df

def update_stock(service, product_name, quantity_change):
    """Update product stock"""
    df = get_products(service)
    if not df.empty:
        idx = df[df['name'] == product_name].index
        if not idx.empty:
            current_stock = float(df.loc[idx[0], 'stock'])
            df.loc[idx[0], 'stock'] = current_stock + quantity_change
            update_data(service, 'Products', df)
            return True
    return False

# ==================== PARTY FUNCTIONS ====================

def get_parties(service):
    """Get all parties"""
    df = get_data(service, 'Parties')
    if not df.empty and 'id' in df:
        df['id'] = pd.to_numeric(df['id'], errors='coerce')
    return df

def add_party(service, name, mobile, address, balance):
    """Add a new party"""
    df = get_parties(service)
    if df.empty:
        party_id = 1
    else:
        party_id = max(df['id'].astype(int)) + 1
    
    new_row = [str(party_id), name, mobile, address, str(balance)]
    add_row(service, 'Parties', new_row)
    return True

# ==================== INVOICE FUNCTIONS ====================

def get_next_invoice_no(service):
    """Generate next invoice number"""
    df = get_data(service, 'Invoices')
    if df.empty:
        return "INV-000001"
    try:
        max_inv = max(df['invoice_no'].astype(str))
        num = int(max_inv.split('-')[1]) + 1
        return f"INV-{num:06d}"
    except:
        return "INV-000001"

def create_invoice(service, party_id, cart, paid_amount):
    """Create a new invoice"""
    try:
        invoice_no = get_next_invoice_no(service)
        total_amount = sum(item['amount'] for item in cart)
        balance = total_amount - paid_amount
        
        # Add to Invoices
        invoice_row = [
            invoice_no,
            str(party_id),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(total_amount),
            str(paid_amount),
            str(max(0, balance))
        ]
        add_row(service, 'Invoices', invoice_row)
        
        # Get invoice ID
        invoices_df = get_data(service, 'Invoices')
        invoice_id = len(invoices_df)
        
        # Add items and update stock
        for item in cart:
            item_row = [
                str(invoice_id),
                str(item['product_id']),
                str(item['quantity']),
                str(item['rate']),
                str(item['amount'])
            ]
            add_row(service, 'Invoice_Items', item_row)
            update_stock(service, item['name'], -item['quantity'])
        
        return invoice_no, total_amount, balance
    
    except Exception as e:
        st.error(f"Error creating invoice: {str(e)}")
        return None, None, None

# ==================== RECEIPT GENERATION ====================

def generate_receipt_html(invoice_no, party_name, party_mobile, party_address, 
                          items, total, paid, balance, date):
    """Generate HTML receipt for printing"""
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Receipt - {invoice_no}</title>
        <style>
            @media print {{
                .no-print {{ display: none !important; }}
                body {{ margin: 0; padding: 20px; }}
                .receipt {{ box-shadow: none !important; }}
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
                font-size: 24px;
                font-weight: bold;
                color: #003366;
            }}
            
            .header p {{
                margin: 2px 0;
                font-size: 12px;
                color: #666;
            }}
            
            .invoice-details {{
                font-size: 12px;
                margin-bottom: 10px;
                padding: 5px 0;
                border-bottom: 1px dotted #ccc;
            }}
            
            .invoice-details .row {{
                display: flex;
                justify-content: space-between;
                padding: 2px 0;
            }}
            
            .items {{
                width: 100%;
                font-size: 12px;
                border-collapse: collapse;
                margin: 10px 0;
            }}
            
            .items th {{
                text-align: left;
                border-bottom: 1px solid #333;
                padding: 5px 2px;
                font-size: 11px;
            }}
            
            .items td {{
                padding: 4px 2px;
                border-bottom: 1px dotted #ddd;
            }}
            
            .items .right {{
                text-align: right;
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
            
            .total-row .label {{
                text-transform: uppercase;
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
            
            .party-info {{
                font-size: 12px;
                margin: 5px 0;
                padding: 5px;
                background: #f9f9f9;
                border-radius: 4px;
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
            
            .no-print button:hover {{
                background: #004488;
            }}
        </style>
    </head>
    <body>
        <div class="receipt" id="receipt">
            <div class="header">
                <h1>🧺 Detergent Mart</h1>
                <p>123 Main Street, City</p>
                <p>Phone: +91 98765 43210</p>
            </div>
            
            <div class="invoice-details">
                <div class="row">
                    <span><strong>Invoice:</strong> {invoice_no}</span>
                    <span><strong>Date:</strong> {date}</span>
                </div>
            </div>
            
            <div class="party-info">
                <strong>{party_name}</strong>
                {f'<br>{party_mobile}' if party_mobile else ''}
                {f'<br>{party_address}' if party_address else ''}
            </div>
            
            <table class="items">
                <thead>
                    <tr>
                        <th>Item</th>
                        <th class="right">Qty</th>
                        <th class="right">Rate</th>
                        <th class="right">Amount</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for item in items:
        html += f"""
                    <tr>
                        <td>{item['name']}</td>
                        <td class="right">{item['quantity']}</td>
                        <td class="right">₹{item['rate']:.2f}</td>
                        <td class="right">₹{item['amount']:.2f}</td>
                    </tr>
        """
    
    html += f"""
                </tbody>
            </table>
            
            <div class="total-section">
                <div class="total-row">
                    <span class="label">Total Amount</span>
                    <span>₹{total:.2f}</span>
                </div>
                <div class="total-row">
                    <span class="label">Amount Paid</span>
                    <span>₹{paid:.2f}</span>
                </div>
                <div class="total-row bold">
                    <span class="label">Balance</span>
                    <span>₹{balance:.2f}</span>
                </div>
            </div>
            
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

# ==================== MAIN APPLICATION ====================

def main():
    st.title("🧺 Detergent Billing System")
    
    # Sidebar
    st.sidebar.title("📋 Menu")
    st.sidebar.markdown("---")
    
    # Connect to Google Sheets
    service = get_sheets_service()
    
    if service:
        if init_sheets(service):
            st.sidebar.success("✅ Connected to Google Sheets")
    else:
        st.sidebar.warning("⚠️ Offline Mode - Using local data")
    
    # Navigation
    menu = st.sidebar.radio(
        "Navigate",
        ["📊 Dashboard", "📦 Products", "🏪 Parties", "🧾 Sales Billing", 
         "📒 Party Ledger", "💵 Payment Entry", "📈 Reports"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("Made with ❤️ using Streamlit")
    
    # Initialize cart
    if 'cart' not in st.session_state:
        st.session_state.cart = []

    # ==================== DASHBOARD ====================
    if menu == "📊 Dashboard":
        st.header("📊 Dashboard")
        
        products = get_products(service) if service else pd.DataFrame()
        invoices = get_data(service, 'Invoices') if service else pd.DataFrame()
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Today's Sales
        today = datetime.now().strftime("%Y-%m-%d")
        if not invoices.empty:
            today_invoices = invoices[invoices['date'].str.startswith(today)]
            today_sales = today_invoices['total_amount'].astype(float).sum() if not today_invoices.empty else 0
        else:
            today_sales = 0
        col1.metric("Today's Sales", f"₹{today_sales:,.2f}")
        
        # Outstanding
        if not invoices.empty:
            outstanding = invoices['balance'].astype(float).sum()
        else:
            outstanding = 0
        col2.metric("Outstanding", f"₹{outstanding:,.2f}", delta="Due" if outstanding > 0 else "Settled")
        
        # Low Stock
        if not products.empty:
            low_stock = len(products[products['stock'] < 10])
        else:
            low_stock = 0
        col3.metric("Low Stock Items", low_stock)
        
        # Total Products
        col4.metric("Total Products", len(products))
        
        # Recent Invoices
        st.subheader("📄 Recent Invoices")
        if not invoices.empty:
            recent = invoices.tail(10)[['invoice_no', 'date', 'total_amount', 'paid_amount', 'balance']]
            st.dataframe(recent, use_container_width=True, hide_index=True)
        else:
            st.info("No invoices yet")

    # ==================== PRODUCTS ====================
    elif menu == "📦 Products":
        st.header("📦 Product Master")
        
        if not service:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        tab1, tab2 = st.tabs(["Manage Products", "Add Product"])
        
        with tab1:
            products = get_products(service)
            if not products.empty:
                st.dataframe(products, use_container_width=True, hide_index=True)
                
                st.subheader("Update Stock")
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    product = st.selectbox("Select Product", products['name'].tolist())
                with col2:
                    change = st.number_input("Quantity Change", value=0.0, step=1.0)
                with col3:
                    if st.button("Update"):
                        if change != 0:
                            if update_stock(service, product, change):
                                st.success(f"Stock updated! {product}: {change}")
                                st.rerun()
            else:
                st.info("No products available")

    # ==================== PARTIES ====================
    elif menu == "🏪 Parties":
        st.header("🏪 Party Master")
        
        if not service:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        tab1, tab2 = st.tabs(["Manage Parties", "Add Party"])
        
        with tab1:
            parties = get_parties(service)
            if not parties.empty:
                st.dataframe(parties, use_container_width=True, hide_index=True)
            else:
                st.info("No parties added yet")
        
        with tab2:
            with st.form("add_party"):
                name = st.text_input("Shop Name *")
                mobile = st.text_input("Mobile Number")
                address = st.text_area("Address")
                balance = st.number_input("Opening Balance (₹)", min_value=0.0, step=100.0)
                
                if st.form_submit_button("Add Party"):
                    if name:
                        if add_party(service, name, mobile, address, balance):
                            st.success(f"Party '{name}' added!")
                            st.rerun()

    # ==================== SALES BILLING ====================
    elif menu == "🧾 Sales Billing":
        st.header("🧾 Sales Billing")
        
        if not service:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Add Items")
            products = get_products(service)
            
            if products.empty:
                st.warning("No products available!")
            else:
                product_names = products['name'].tolist()
                selected = st.selectbox("Select Product", product_names)
                
                if selected:
                    product = products[products['name'] == selected].iloc[0]
                    stock = float(product['stock'])
                    rate = float(product['rate'])
                    st.info(f"📦 Stock: {stock} | Rate: ₹{rate:,.2f}")
                    
                    qty = st.number_input("Quantity", min_value=0.0, max_value=stock, step=1.0)
                    if st.button("➕ Add to Cart"):
                        if qty > 0:
                            st.session_state.cart.append({
                                'product_id': len(products),
                                'name': selected,
                                'rate': rate,
                                'quantity': qty,
                                'amount': rate * qty
                            })
                            st.success(f"Added {qty} {selected}")
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
        
        parties = get_parties(service)
        if parties.empty:
            st.warning("No parties available!")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                party_name = st.selectbox("Party", parties['shop_name'].tolist())
            with col2:
                paid = st.number_input("Paid Amount (₹)", min_value=0.0, step=100.0)
            with col3:
                if st.button("💳 Generate Invoice & Receipt", type="primary"):
                    if not st.session_state.cart:
                        st.error("Cart is empty!")
                    else:
                        party = parties[parties['shop_name'] == party_name].iloc[0]
                        party_id = int(party['id'])
                        
                        invoice_no, total, balance = create_invoice(
                            service, party_id, st.session_state.cart, paid
                        )
                        
                        if invoice_no:
                            st.success(f"Invoice {invoice_no} generated!")
                            
                            # Show receipt
                            st.markdown("---")
                            st.subheader("🧾 Receipt")
                            
                            # Generate receipt HTML
                            receipt_html = generate_receipt_html(
                                invoice_no,
                                party_name,
                                party.get('mobile', ''),
                                party.get('address', ''),
                                st.session_state.cart,
                                total,
                                paid,
                                balance,
                                datetime.now().strftime("%d-%m-%Y %H:%M")
                            )
                            
                            # Display receipt
                            st.components.v1.html(receipt_html, height=700)
                            
                            # Clear cart
                            st.session_state.cart = []

    # ==================== PARTY LEDGER ====================
    elif menu == "📒 Party Ledger":
        st.header("📒 Party Ledger")
        
        if not service:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        parties = get_parties(service)
        if not parties.empty:
            selected = st.selectbox("Select Party", parties['shop_name'].tolist())
            
            if selected:
                party = parties[parties['shop_name'] == selected]
                party_id = int(party.iloc[0]['id'])
                
                invoices = get_data(service, 'Invoices')
                party_invoices = invoices[invoices['party_id'].astype(str) == str(party_id)]
                
                payments = get_data(service, 'Payments')
                party_payments = payments[payments['party_id'].astype(str) == str(party_id)]
                
                st.subheader(f"Statement for {selected}")
                
                col1, col2, col3 = st.columns(3)
                total_sales = party_invoices['total_amount'].astype(float).sum() if not party_invoices.empty else 0
                total_paid = party_payments['amount'].astype(float).sum() if not party_payments.empty else 0
                balance = total_sales - total_paid
                
                col1.metric("Total Sales", f"₹{total_sales:,.2f}")
                col2.metric("Total Paid", f"₹{total_paid:,.2f}")
                col3.metric("Balance", f"₹{balance:,.2f}", delta="Due" if balance > 0 else "Settled")
                
                if not party_invoices.empty:
                    st.write("**Invoices**")
                    st.dataframe(party_invoices[['invoice_no', 'date', 'total_amount', 'paid_amount', 'balance']], 
                               use_container_width=True, hide_index=True)

    # ==================== PAYMENT ENTRY ====================
    elif menu == "💵 Payment Entry":
        st.header("💵 Payment Entry")
        
        if not service:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        parties = get_parties(service)
        if not parties.empty:
            party = st.selectbox("Select Party", parties['shop_name'].tolist())
            
            if party:
                party_id = int(parties[parties['shop_name'] == party].iloc[0]['id'])
                invoices = get_data(service, 'Invoices')
                party_invoices = invoices[invoices['party_id'].astype(str) == str(party_id)]
                party_invoices = party_invoices[party_invoices['balance'].astype(float) > 0]
                
                if not party_invoices.empty:
                    st.dataframe(party_invoices[['invoice_no', 'total_amount', 'paid_amount', 'balance']], 
                               use_container_width=True)
                    
                    invoice_no = st.selectbox("Select Invoice", party_invoices['invoice_no'].tolist())
                    if invoice_no:
                        invoice = party_invoices[party_invoices['invoice_no'] == invoice_no].iloc[0]
                        st.info(f"Outstanding: ₹{float(invoice['balance']):,.2f}")
                        
                        with st.form("payment"):
                            amount = st.number_input("Amount", min_value=0.0, max_value=float(invoice['balance']), step=100.0)
                            payment_type = st.selectbox("Payment Type", ["Cash", "UPI", "Bank Transfer", "Cheque"])
                            note = st.text_area("Note")
                            
                            if st.form_submit_button("Record Payment"):
                                if amount > 0:
                                    payment_row = [
                                        str(party_id),
                                        str(party_invoices[party_invoices['invoice_no'] == invoice_no].index[0] + 1),
                                        datetime.now().strftime("%Y-%m-%d"),
                                        str(amount),
                                        payment_type,
                                        note
                                    ]
                                    add_row(service, 'Payments', payment_row)
                                    st.success(f"Payment of ₹{amount:,.2f} recorded!")
                                    st.rerun()

    # ==================== REPORTS ====================
    elif menu == "📈 Reports":
        st.header("📈 Reports")
        
        if not service:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        report_type = st.selectbox("Select Report", 
                                  ["Daily Sales", "Outstanding Report", "Party-wise Sales"])
        
        if report_type == "Daily Sales":
            date = st.date_input("Select Date", datetime.now())
            date_str = date.strftime("%Y-%m-%d")
            invoices = get_data(service, 'Invoices')
            daily = invoices[invoices['date'].str.startswith(date_str)]
            
            if not daily.empty:
                st.dataframe(daily[['invoice_no', 'total_amount', 'paid_amount', 'balance']], 
                           use_container_width=True, hide_index=True)
                st.metric("Total Sales", f"₹{daily['total_amount'].astype(float).sum():,.2f}")
            else:
                st.info("No sales for this date")
        
        elif report_type == "Outstanding Report":
            invoices = get_data(service, 'Invoices')
            outstanding = invoices[invoices['balance'].astype(float) > 0]
            
            if not outstanding.empty:
                parties = get_parties(service)
                outstanding = outstanding.merge(parties, left_on='party_id', right_on='id', how='left')
                st.dataframe(outstanding[['invoice_no', 'shop_name', 'total_amount', 'paid_amount', 'balance']], 
                           use_container_width=True, hide_index=True)
                st.metric("Total Outstanding", f"₹{outstanding['balance'].astype(float).sum():,.2f}")
            else:
                st.info("No outstanding dues")

# ==================== RUN ====================

if __name__ == "__main__":
    main()
