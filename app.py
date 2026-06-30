"""
Complete Detergent Billing App - With Invoice-wise Receipt & Party Ledger
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="🧺 Detergent Billing System",
    page_icon="🧺",
    layout="wide"
)

# ==================== GOOGLE SHEETS SETUP ====================

def get_sheets_service():
    """Connect to Google Sheets using secrets"""
    try:
        if 'google_sheets' not in st.secrets:
            st.sidebar.error("❌ No 'google_sheets' key in secrets.toml!")
            return None
        
        creds_dict = dict(st.secrets['google_sheets'])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        st.sidebar.error(f"❌ Connection error: {str(e)}")
        return None

def get_sheet_id():
    return "1jaat8u_k7rQyqhPcdL4zmUkkuG8gpwwk6z-Tvv2SMrQ"

@st.cache_data(ttl=60)
def get_data_cached(service_key, sheet_name):
    """Get data from sheet with caching"""
    service = get_sheets_service()
    if not service:
        return pd.DataFrame()
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=get_sheet_id(),
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
        if "429" in str(e):
            st.warning("⏳ Rate limit reached. Please wait a moment.")
            return pd.DataFrame()
        return pd.DataFrame()

def get_data(service, sheet_name):
    return get_data_cached("cached", sheet_name)

def add_row_only(service, sheet_name, row_data):
    """Add row to sheet"""
    try:
        body = {'values': [row_data]}
        result = service.spreadsheets().values().append(
            spreadsheetId=get_sheet_id(),
            range=f"{sheet_name}!A:Z",
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        st.cache_data.clear()
        return result.get('updates', {}).get('updatedRows', 0) > 0
    except Exception as e:
        st.error(f"❌ Error adding row: {str(e)}")
        return False

def create_sheet_if_not_exists(service, sheet_name, headers):
    """Create sheet if not exists"""
    try:
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=get_sheet_id()
        ).execute()
        sheets = spreadsheet.get('sheets', [])
        sheet_names = [sheet['properties']['title'] for sheet in sheets]
        
        if sheet_name in sheet_names:
            df = get_data(service, sheet_name)
            if df.empty:
                values = [headers]
                service.spreadsheets().values().update(
                    spreadsheetId=get_sheet_id(),
                    range=f"{sheet_name}!A1",
                    valueInputOption='USER_ENTERED',
                    body={'values': values}
                ).execute()
            return True
        
        body = {
            'requests': [{
                'addSheet': {
                    'properties': {'title': sheet_name}
                }
            }]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=get_sheet_id(),
            body=body
        ).execute()
        
        values = [headers]
        service.spreadsheets().values().update(
            spreadsheetId=get_sheet_id(),
            range=f"{sheet_name}!A1",
            valueInputOption='USER_ENTERED',
            body={'values': values}
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error creating sheet: {str(e)}")
        return False

# ==================== INIT ====================

def init_sheets(service):
    """Initialize sheets"""
    try:
        sheets = {
            'Products': ['Product ID', 'Product Name', 'Rate', 'Stock'],
            'Parties': ['Party ID', 'Party Name', 'Mobile', 'WhatsApp', 'Address', 'Opening Balance', 'GST No'],
            'Sales': ['Invoice No', 'Date', 'Party', 'Total', 'Status'],
            'Sales_Items': ['Invoice No', 'Product ID', 'Product Name', 'Qty', 'Rate', 'Amount'],
            'Receipts': ['Receipt No', 'Date', 'Party', 'Invoice No', 'Amount', 'Payment Mode', 'Remarks']
        }
        
        for sheet_name, headers in sheets.items():
            create_sheet_if_not_exists(service, sheet_name, headers)
        
        products = get_data(service, 'Products')
        if products.empty:
            defaults = [
                ['P001', 'Dishwash Liquid 1L', '120', '100'],
                ['P002', 'Detergent Powder 1kg', '120', '100'],
                ['P003', 'Dishwash Liquid 7+1', '840', '50'],
                ['P004', 'Detergent Powder 7+1', '840', '50']
            ]
            for product in defaults:
                add_row_only(service, 'Products', product)
        
        return True
    except Exception as e:
        st.error(f"Init error: {str(e)}")
        return False

def get_next_invoice(service):
    """Generate next invoice number"""
    sales = get_data(service, 'Sales')
    if sales.empty or 'Invoice No' not in sales.columns:
        return "INV001"
    try:
        invoices = sales['Invoice No'].astype(str).tolist()
        nums = []
        for inv in invoices:
            if inv and inv.startswith('INV'):
                num = int(inv.replace('INV', ''))
                nums.append(num)
        next_num = max(nums) + 1 if nums else 1
        return f"INV{next_num:03d}"
    except:
        return "INV001"

def get_next_receipt_no(service):
    """Generate next receipt number"""
    receipts = get_data(service, 'Receipts')
    if receipts.empty or 'Receipt No' not in receipts.columns:
        return "REC001"
    try:
        recs = receipts['Receipt No'].astype(str).tolist()
        nums = []
        for rec in recs:
            if rec and rec.startswith('REC'):
                num = int(rec.replace('REC', ''))
                nums.append(num)
        next_num = max(nums) + 1 if nums else 1
        return f"REC{next_num:03d}"
    except:
        return "REC001"

def get_next_party_id(service):
    """Generate next party ID"""
    parties = get_data(service, 'Parties')
    if parties.empty:
        return "PT001"
    try:
        ids = parties['Party ID'].astype(str).tolist()
        nums = []
        for pid in ids:
            if pid and pid.startswith('PT'):
                num = int(pid.replace('PT', ''))
                nums.append(num)
        next_num = max(nums) + 1 if nums else 1
        return f"PT{next_num:03d}"
    except:
        return "PT001"

def update_stock(service, product_name, change):
    """Update stock"""
    try:
        products = get_data(service, 'Products')
        if products.empty:
            return False
        
        idx = products[products['Product Name'] == product_name].index
        if idx.empty:
            return False
        
        current_stock_str = str(products.loc[idx[0], 'Stock']).strip()
        try:
            current_stock = int(float(current_stock_str))
        except:
            current_stock = 0
        
        new_stock = current_stock + change
        row_num = idx[0] + 2
        
        service.spreadsheets().values().update(
            spreadsheetId=get_sheet_id(),
            range=f"Products!D{row_num}",
            valueInputOption='USER_ENTERED',
            body={'values': [[str(new_stock)]]}
        ).execute()
        
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error updating stock: {str(e)}")
        return False

def update_invoice_status(service, invoice_no):
    """Update invoice status based on payments"""
    sales = get_data(service, 'Sales')
    receipts = get_data(service, 'Receipts')
    
    idx = sales[sales['Invoice No'] == invoice_no].index
    if idx.empty:
        return
    
    total = safe_float(sales.loc[idx[0], 'Total'])
    paid = 0
    
    if not receipts.empty:
        paid = receipts[receipts['Invoice No'] == invoice_no]['Amount'].apply(safe_float).sum()
    
    if paid >= total:
        status = 'Paid'
    elif paid > 0:
        status = 'Partially Paid'
    else:
        status = 'Unpaid'
    
    row_num = idx[0] + 2
    service.spreadsheets().values().update(
        spreadsheetId=get_sheet_id(),
        range=f"Sales!E{row_num}",
        valueInputOption='USER_ENTERED',
        body={'values': [[status]]}
    ).execute()
    st.cache_data.clear()

def get_invoice_paid_amount(service, invoice_no):
    """Get total paid amount for an invoice"""
    receipts = get_data(service, 'Receipts')
    if receipts.empty:
        return 0
    paid = receipts[receipts['Invoice No'] == invoice_no]['Amount'].apply(safe_float).sum()
    return paid

def safe_int(value):
    try:
        if value is None or value == '':
            return 0
        return int(float(str(value).strip()))
    except:
        return 0

def safe_float(value):
    try:
        if value is None or value == '':
            return 0.0
        return float(str(value).strip())
    except:
        return 0.0

# ==================== MAIN APP ====================

def main():
    st.title("🧺 Detergent Billing System")
    
    # Sidebar
    st.sidebar.title("📋 Menu")
    st.sidebar.markdown("---")
    
    # Connect
    service = get_sheets_service()
    if service:
        try:
            test = service.spreadsheets().get(spreadsheetId=get_sheet_id()).execute()
            st.sidebar.success(f"✅ Connected")
            init_sheets(service)
            st.sidebar.success("✅ Sheets ready")
        except Exception as e:
            if "429" in str(e):
                st.sidebar.warning("⏳ Rate limit reached. Please wait.")
            else:
                st.sidebar.error(f"❌ Error: {str(e)[:50]}...")
    else:
        st.sidebar.warning("⚠️ Check secrets.toml")
    
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
        
        products = get_data(service, 'Products') if service else pd.DataFrame()
        sales = get_data(service, 'Sales') if service else pd.DataFrame()
        parties = get_data(service, 'Parties') if service else pd.DataFrame()
        receipts = get_data(service, 'Receipts') if service else pd.DataFrame()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📦 Products", len(products))
        col2.metric("🏪 Parties", len(parties))
        
        total_sales = 0
        if not sales.empty and 'Total' in sales.columns:
            for val in sales['Total']:
                total_sales += safe_float(val)
        col3.metric("💰 Total Sales", f"₹{total_sales:,.2f}")
        
        total_receipts = 0
        if not receipts.empty and 'Amount' in receipts.columns:
            for val in receipts['Amount']:
                total_receipts += safe_float(val)
        col4.metric("💳 Total Receipts", f"₹{total_receipts:,.2f}")
        
        st.subheader("📄 Recent Invoices")
        if not sales.empty:
            st.dataframe(sales.tail(10), use_container_width=True)
        else:
            st.info("No sales yet")

    # ==================== PRODUCTS ====================
    elif menu == "📦 Products":
        st.header("📦 Product Master")
        
        if not service:
            st.error("❌ Not connected")
            return
        
        products = get_data(service, 'Products')
        
        tab1, tab2 = st.tabs(["Manage Products", "Add Product"])
        
        with tab1:
            if not products.empty:
                display_products = products.copy()
                if 'Stock' in display_products.columns:
                    display_products['Stock'] = display_products['Stock'].apply(safe_int)
                if 'Rate' in display_products.columns:
                    display_products['Rate'] = display_products['Rate'].apply(safe_float)
                
                st.dataframe(display_products, use_container_width=True)
                
                st.subheader("Quick Stock Update")
                col1, col2 = st.columns([2, 1])
                with col1:
                    selected = st.selectbox("Select Product", products['Product Name'].tolist())
                with col2:
                    change = st.number_input("Change (+/-)", value=0, step=1)
                    if st.button("Update Stock"):
                        if change != 0:
                            if update_stock(service, selected, change):
                                st.success(f"✅ Stock updated!")
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
                
                if st.form_submit_button("Add Product"):
                    if name and rate > 0:
                        products = get_data(service, 'Products')
                        product_id = f"P{len(products)+1:03d}"
                        add_row_only(service, 'Products', [product_id, name, str(rate), str(stock)])
                        st.success(f"✅ Product '{name}' added!")
                        st.rerun()

    # ==================== PARTIES ====================
    elif menu == "🏪 Parties":
        st.header("🏪 Party Master")
        
        if not service:
            st.error("❌ Not connected")
            return
        
        parties = get_data(service, 'Parties')
        
        tab1, tab2 = st.tabs(["Manage Parties", "Add Party"])
        
        with tab1:
            if parties.empty:
                st.info("No parties added yet")
            else:
                if 'Party Name' not in parties.columns:
                    st.error("❌ 'Party Name' column not found!")
                else:
                    st.dataframe(parties, use_container_width=True)
        
        with tab2:
            with st.form("add_party_form"):
                col1, col2 = st.columns(2)
                with col1:
                    party_name = st.text_input("Party Name *")
                    mobile = st.text_input("Mobile Number")
                    whatsapp = st.text_input("WhatsApp Number")
                with col2:
                    address = st.text_area("Address")
                    opening_balance = st.number_input("Opening Balance (₹)", min_value=0.0, step=100.0, value=0.0)
                    gst_no = st.text_input("GST No (Optional)")
                
                if st.form_submit_button("Add Party"):
                    if party_name:
                        party_id = get_next_party_id(service)
                        row_data = [party_id, party_name, mobile, whatsapp, address, str(opening_balance), gst_no]
                        if add_row_only(service, 'Parties', row_data):
                            st.success(f"✅ Party '{party_name}' added!")
                            st.rerun()

    # ==================== BILLING ====================
    elif menu == "🧾 Billing":
        st.header("🧾 Sales Billing")
        
        if not service:
            st.error("❌ Not connected")
            return
        
        products = get_data(service, 'Products')
        parties = get_data(service, 'Parties')
        
        if products.empty:
            st.warning("⚠️ No products!")
            return
        
        if parties.empty:
            st.warning("⚠️ No parties!")
            return
        
        if 'Party Name' not in parties.columns:
            st.error("❌ 'Party Name' column not found!")
            return
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🛒 Add Items")
            
            product_names = products['Product Name'].tolist()
            selected = st.selectbox("Select Product", product_names)
            
            if selected:
                product = products[products['Product Name'] == selected].iloc[0]
                stock = safe_int(product['Stock'])
                rate = safe_float(product['Rate'])
                product_id = product['Product ID']
                st.info(f"📦 Stock: {stock} | 💰 Rate: ₹{rate:.2f}")
                
                qty = st.number_input("Quantity", min_value=1, max_value=stock, step=1)
                if st.button("➕ Add to Cart"):
                    st.session_state.cart.append({
                        'Product ID': product_id,
                        'Product': selected,
                        'Rate': rate,
                        'Qty': qty,
                        'Amount': rate * qty
                    })
                    st.success(f"✅ Added {qty} {selected}")
                    st.rerun()
        
        with col2:
            st.subheader("🛍️ Cart")
            if st.session_state.cart:
                cart_df = pd.DataFrame(st.session_state.cart)
                st.dataframe(cart_df[['Product', 'Qty', 'Rate', 'Amount']], use_container_width=True)
                total = cart_df['Amount'].sum()
                st.metric("💰 Total", f"₹{total:,.2f}")
                if st.button("🗑️ Clear Cart"):
                    st.session_state.cart = []
                    st.rerun()
            else:
                st.info("Cart empty")
        
        st.markdown("---")
        st.subheader("📄 Create Invoice")
        
        party_names = parties['Party Name'].tolist()
        party = st.selectbox("Select Party", party_names)
        
        if st.button("💳 Generate Invoice", type="primary"):
            if not st.session_state.cart:
                st.error("❌ Cart empty!")
            else:
                invoice_no = get_next_invoice(service)
                total = sum(item['Amount'] for item in st.session_state.cart)
                
                add_row_only(service, 'Sales', [
                    invoice_no,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    party,
                    str(total),
                    'Unpaid'
                ])
                
                for item in st.session_state.cart:
                    add_row_only(service, 'Sales_Items', [
                        invoice_no,
                        item['Product ID'],
                        item['Product'],
                        str(item['Qty']),
                        str(item['Rate']),
                        str(item['Amount'])
                    ])
                    update_stock(service, item['Product'], -item['Qty'])
                
                st.success(f"✅ Invoice {invoice_no} generated! Total: ₹{total:,.2f}")
                st.session_state.cart = []
                st.rerun()

    # ==================== CASH RECEIPT ====================
    elif menu == "💰 Cash Receipt":
        st.header("💰 Cash Receipt Entry")
        
        if not service:
            st.error("❌ Not connected")
            return
        
        parties = get_data(service, 'Parties')
        sales = get_data(service, 'Sales')
        
        if parties.empty:
            st.warning("⚠️ No parties available!")
            return
        
        if sales.empty:
            st.warning("⚠️ No invoices found!")
            return
        
        st.subheader("📝 Enter Receipt Details")
        
        with st.form("receipt_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Select Party
                party_names = parties['Party Name'].tolist()
                party = st.selectbox("Party *", party_names)
                
                # Get unpaid invoices for selected party
                unpaid_invoices = sales[sales['Status'] != 'Paid'] if 'Status' in sales.columns else sales
                party_invoices = unpaid_invoices[unpaid_invoices['Party'] == party] if party else pd.DataFrame()
                
                # Show outstanding amount
                if party and not party_invoices.empty:
                    total_outstanding = 0
                    for _, row in party_invoices.iterrows():
                        inv_no = row['Invoice No']
                        total = safe_float(row['Total'])
                        paid = get_invoice_paid_amount(service, inv_no)
                        total_outstanding += (total - paid)
                    st.info(f"💰 Total Outstanding for {party}: ₹{total_outstanding:,.2f}")
                
                # Invoice Reference Number - Manual Entry OR Select
                st.subheader("Invoice Reference")
                
                # Option 1: Select from dropdown
                if party and not party_invoices.empty:
                    invoice_options = [''] + party_invoices['Invoice No'].tolist()
                    invoice_no = st.selectbox("Select Invoice Number (OR type below)", invoice_options)
                    
                    if invoice_no:
                        invoice_data = party_invoices[party_invoices['Invoice No'] == invoice_no].iloc[0]
                        total = safe_float(invoice_data['Total'])
                        paid = get_invoice_paid_amount(service, invoice_no)
                        balance = total - paid
                        st.info(f"💳 Invoice: {invoice_no} | Total: ₹{total:,.2f} | Paid: ₹{paid:,.2f} | Balance: ₹{balance:,.2f}")
                else:
                    invoice_no = ""
                    if party and party_invoices.empty:
                        st.success(f"✅ No pending invoices for {party}")
            
            with col2:
                # Option 2: Manual entry
                manual_invoice = st.text_input("Or Enter Invoice Number Manually", 
                                              placeholder="e.g., INV001", 
                                              help="Enter invoice number if not in dropdown")
                
                # Use manual entry if provided, else use dropdown selection
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
                    # Verify invoice exists
                    invoice_exists = not sales[sales['Invoice No'] == final_invoice].empty
                    if not invoice_exists:
                        st.error(f"❌ Invoice {final_invoice} not found! Please check the invoice number.")
                    else:
                        # Check if invoice belongs to selected party
                        invoice_party = sales[sales['Invoice No'] == final_invoice]['Party'].iloc[0]
                        if invoice_party != party:
                            st.error(f"❌ Invoice {final_invoice} belongs to {invoice_party}, not {party}!")
                        else:
                            # Get outstanding balance
                            total = safe_float(sales[sales['Invoice No'] == final_invoice]['Total'].iloc[0])
                            paid = get_invoice_paid_amount(service, final_invoice)
                            balance = total - paid
                            
                            if amount > balance:
                                st.error(f"❌ Amount cannot exceed balance! Balance: ₹{balance:,.2f}")
                            else:
                                receipt_no = get_next_receipt_no(service)
                                
                                success = add_row_only(service, 'Receipts', [
                                    receipt_no,
                                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    party,
                                    final_invoice,
                                    str(amount),
                                    payment_mode,
                                    remarks
                                ])
                                
                                if success:
                                    update_invoice_status(service, final_invoice)
                                    st.success(f"✅ Receipt {receipt_no} recorded!")
                                    st.info(f"**Invoice:** {final_invoice} | **Amount:** ₹{amount:,.2f} | **Mode:** {payment_mode}")
                                    st.balloons()
                                    st.rerun()

    # ==================== PARTY LEDGER ====================
    elif menu == "📒 Party Ledger":
        st.header("📒 Party Ledger")
        
        if not service:
            st.error("❌ Not connected")
            return
        
        parties = get_data(service, 'Parties')
        sales = get_data(service, 'Sales')
        receipts = get_data(service, 'Receipts')
        sales_items = get_data(service, 'Sales_Items')
        
        if parties.empty:
            st.warning("⚠️ No parties available!")
            return
        
        st.subheader("📋 Select Party")
        
        party_names = parties['Party Name'].tolist()
        selected_party = st.selectbox("Select Party", party_names)
        
        if selected_party:
            st.subheader(f"📒 Ledger for {selected_party}")
            
            # Get invoices for this party
            party_invoices = sales[sales['Party'] == selected_party] if not sales.empty else pd.DataFrame()
            
            if party_invoices.empty:
                st.info(f"No transactions found for {selected_party}")
            else:
                # Build ledger
                ledger_data = []
                
                # Opening Balance
                party_data = parties[parties['Party Name'] == selected_party].iloc[0]
                opening_balance = safe_float(party_data.get('Opening Balance', 0))
                balance = opening_balance
                
                ledger_data.append({
                    'Date': 'Opening',
                    'Particulars': 'Opening Balance',
                    'Invoice No': '',
                    'Debit': opening_balance if opening_balance > 0 else 0,
                    'Credit': 0,
                    'Balance': balance
                })
                
                # Process invoices in date order
                for _, row in party_invoices.iterrows():
                    inv_no = row['Invoice No']
                    date = str(row['Date'])[:10] if 'Date' in row else ''
                    total = safe_float(row['Total'])
                    
                    # Debit (Sale)
                    balance += total
                    ledger_data.append({
                        'Date': date,
                        'Particulars': f'Sale',
                        'Invoice No': inv_no,
                        'Debit': total,
                        'Credit': 0,
                        'Balance': balance
                    })
                    
                    # Get payments for this invoice
                    inv_receipts = receipts[receipts['Invoice No'] == inv_no] if not receipts.empty else pd.DataFrame()
                    for _, rec in inv_receipts.iterrows():
                        amount = safe_float(rec['Amount'])
                        balance -= amount
                        ledger_data.append({
                            'Date': str(rec['Date'])[:10] if 'Date' in rec else '',
                            'Particulars': f'Payment - {rec.get("Payment Mode", "Cash")}',
                            'Invoice No': inv_no,
                            'Debit': 0,
                            'Credit': amount,
                            'Balance': balance
                        })
                
                # Display ledger
                ledger_df = pd.DataFrame(ledger_data)
                st.dataframe(ledger_df, use_container_width=True)
                
                # Summary
                col1, col2, col3, col4 = st.columns(4)
                total_sales = ledger_df['Debit'].sum()
                total_payments = ledger_df['Credit'].sum()
                col1.metric("Total Sales", f"₹{total_sales:,.2f}")
                col2.metric("Total Payments", f"₹{total_payments:,.2f}")
                col3.metric("Opening Balance", f"₹{opening_balance:,.2f}")
                col4.metric("Closing Balance", f"₹{balance:,.2f}", 
                           delta="Due" if balance > 0 else "Settled")
                
                # Invoice-wise Collection Summary
                st.subheader("📄 Invoice-wise Collection Details")
                
                invoice_summary = []
                for _, row in party_invoices.iterrows():
                    inv_no = row['Invoice No']
                    total = safe_float(row['Total'])
                    paid = get_invoice_paid_amount(service, inv_no)
                    balance_amount = total - paid
                    status = 'Paid' if balance_amount <= 0 else 'Partially Paid' if paid > 0 else 'Unpaid'
                    
                    invoice_summary.append({
                        'Invoice No': inv_no,
                        'Date': str(row['Date'])[:10] if 'Date' in row else '',
                        'Total': total,
                        'Paid': paid,
                        'Balance': balance_amount,
                        'Status': status
                    })
                
                summary_df = pd.DataFrame(invoice_summary)
                st.dataframe(summary_df, use_container_width=True)

    # ==================== REPORTS ====================
    elif menu == "📈 Reports":
        st.header("📈 Reports")
        
        if not service:
            st.error("❌ Not connected")
            return
        
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
            
            if st.button("📊 Generate Report", type="primary"):
                if start_date > end_date:
                    st.error("❌ Start date cannot be after end date!")
                else:
                    sales_items = get_data(service, 'Sales_Items')
                    sales = get_data(service, 'Sales')
                    
                    if sales_items.empty:
                        st.warning("⚠️ No sales items found!")
                        return
                    
                    start_str = start_date.strftime("%Y-%m-%d")
                    end_str = end_date.strftime("%Y-%m-%d")
                    
                    filtered_invoices = []
                    if not sales.empty and 'Invoice No' in sales.columns and 'Date' in sales.columns:
                        for _, row in sales.iterrows():
                            date_str = str(row['Date'])[:10]
                            if start_str <= date_str <= end_str:
                                filtered_invoices.append(row['Invoice No'])
                    
                    if not filtered_invoices:
                        st.info(f"No sales found between {start_date} and {end_date}")
                        return
                    
                    filtered_items = sales_items[sales_items['Invoice No'].isin(filtered_invoices)]
                    
                    if filtered_items.empty:
                        st.info("No items found for these invoices")
                        return
                    
                    report_data = filtered_items.groupby(['Product ID', 'Product Name']).agg({
                        'Qty': lambda x: sum(safe_int(v) for v in x),
                        'Amount': lambda x: sum(safe_float(v) for v in x)
                    }).reset_index()
                    
                    report_data.columns = ['Item Code', 'Item Name', 'Qty Sold', 'Sold Amount']
                    report_data['Qty Sold'] = report_data['Qty Sold'].apply(safe_int)
                    report_data['Sold Amount'] = report_data['Sold Amount'].apply(safe_float)
                    report_data = report_data.sort_values('Sold Amount', ascending=False)
                    
                    st.subheader(f"📊 Sales Report: {start_date} to {end_date}")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Items Sold", f"{report_data['Qty Sold'].sum():,.0f}")
                    col2.metric("Total Sales", f"₹{report_data['Sold Amount'].sum():,.2f}")
                    col3.metric("Unique Products", len(report_data))
                    
                    st.dataframe(report_data, use_container_width=True)
                    
                    csv = report_data.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Report (CSV)",
                        data=csv,
                        file_name=f"Sales_Report_{start_date}_to_{end_date}.csv",
                        mime="text/csv"
                    )
        
        elif report_type == "Outstanding Report":
            st.subheader("📋 Outstanding Report")
            
            sales = get_data(service, 'Sales')
            receipts = get_data(service, 'Receipts')
            parties = get_data(service, 'Parties')
            
            if sales.empty:
                st.info("No sales data available")
                return
            
            outstanding_data = []
            for _, row in sales.iterrows():
                inv_no = row['Invoice No']
                party = row['Party']
                total = safe_float(row['Total'])
                paid = get_invoice_paid_amount(service, inv_no)
                balance = total - paid
                
                if balance > 0:
                    outstanding_data.append({
                        'Invoice No': inv_no,
                        'Party': party,
                        'Date': str(row['Date'])[:10] if 'Date' in row else '',
                        'Total': total,
                        'Paid': paid,
                        'Balance': balance,
                        'Status': 'Partially Paid' if paid > 0 else 'Unpaid'
                    })
            
            if outstanding_data:
                df = pd.DataFrame(outstanding_data)
                st.dataframe(df, use_container_width=True)
                st.metric("Total Outstanding", f"₹{df['Balance'].sum():,.2f}")
                
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Outstanding Report (CSV)",
                    data=csv,
                    file_name="Outstanding_Report.csv",
                    mime="text/csv"
                )
            else:
                st.success("✅ No outstanding dues!")
        
        elif report_type == "Receipt Summary":
            st.subheader("💳 Receipt Summary")
            
            receipts = get_data(service, 'Receipts')
            if receipts.empty:
                st.info("No receipts recorded yet")
                return
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("From Date", datetime.now() - timedelta(days=30))
            with col2:
                end_date = st.date_input("To Date", datetime.now())
            
            if st.button("📊 Show Receipts", type="primary"):
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")
                
                filtered = []
                for _, row in receipts.iterrows():
                    date_str = str(row['Date'])[:10] if 'Date' in row else ''
                    if start_str <= date_str <= end_str:
                        filtered.append(row)
                
                if filtered:
                    df = pd.DataFrame(filtered)
                    st.dataframe(df, use_container_width=True)
                    st.metric("Total Receipts", f"₹{df['Amount'].apply(safe_float).sum():,.2f}")
                else:
                    st.info("No receipts found for this period")

# ==================== RUN ====================

if __name__ == "__main__":
    main()
