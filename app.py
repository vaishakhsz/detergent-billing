"""
Simple Detergent Billing App - Parties Display Fixed
Products: Dishwash Liquid 1L (₹120), Detergent Powder 1kg (₹120), 
         Dishwash Liquid 7+1 (₹840), Detergent Powder 7+1 (₹840)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="🧺 Detergent Billing",
    page_icon="🧺",
    layout="wide"
)

# ==================== GOOGLE SHEETS SETUP ====================

def get_sheets_service():
    """Connect to Google Sheets using secrets"""
    try:
        if 'google_sheets' in st.secrets:
            creds_dict = dict(st.secrets['google_sheets'])
        else:
            st.warning("⚠️ No secrets found!")
            return None
        
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        st.error(f"❌ Connection error: {str(e)}")
        return None

def get_sheet_id():
    return "1jaat8u_k7rQyqhPcdL4zmUkkuG8gpwwk6z-Tvv2SMrQ"

def get_data(service, sheet_name):
    """Get data from sheet"""
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
        st.error(f"Error reading data: {str(e)}")
        return pd.DataFrame()

def add_row(service, sheet_name, row_data):
    """Add row to sheet"""
    try:
        body = {'values': [row_data]}
        service.spreadsheets().values().append(
            spreadsheetId=get_sheet_id(),
            range=f"{sheet_name}!A:Z",
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error adding row: {str(e)}")
        return False

def update_data(service, sheet_name, df):
    """Update entire sheet"""
    try:
        service.spreadsheets().values().clear(
            spreadsheetId=get_sheet_id(),
            range=f"{sheet_name}!A:Z",
            body={}
        ).execute()
        if not df.empty:
            values = [df.columns.tolist()] + df.values.tolist()
            service.spreadsheets().values().update(
                spreadsheetId=get_sheet_id(),
                range=f"{sheet_name}!A1",
                valueInputOption='USER_ENTERED',
                body={'values': values}
            ).execute()
        return True
    except Exception as e:
        st.error(f"Error updating: {str(e)}")
        return False

def create_sheet_if_not_exists(service, sheet_name, headers):
    """Create sheet with headers if not exists"""
    try:
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=get_sheet_id()
        ).execute()
        sheets = spreadsheet.get('sheets', [])
        sheet_names = [sheet['properties']['title'] for sheet in sheets]
        
        if sheet_name not in sheet_names:
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
            
            df = pd.DataFrame(columns=headers)
            update_data(service, sheet_name, df)
            return True
        else:
            # Check if headers exist
            df = get_data(service, sheet_name)
            if df.empty:
                df = pd.DataFrame(columns=headers)
                update_data(service, sheet_name, df)
        return True
    except Exception as e:
        st.error(f"Error creating sheet: {str(e)}")
        return False

# ==================== INIT ====================

def init_sheets(service):
    """Initialize sheets with headers"""
    try:
        sheets = {
            'Products': ['Product ID', 'Product Name', 'Rate', 'Stock'],
            'Parties': ['Party ID', 'Party Name', 'Mobile', 'Address', 'Opening Balance', 'GST No'],
            'Sales': ['Invoice No', 'Date', 'Party', 'Total', 'Status']
        }
        
        for sheet_name, headers in sheets.items():
            create_sheet_if_not_exists(service, sheet_name, headers)
        
        # Add default products
        products = get_data(service, 'Products')
        if products.empty:
            defaults = [
                ['P001', 'Dishwash Liquid 1L', 120, 100],
                ['P002', 'Detergent Powder 1kg', 120, 100],
                ['P003', 'Dishwash Liquid 7+1', 840, 50],
                ['P004', 'Detergent Powder 7+1', 840, 50]
            ]
            df = pd.DataFrame(defaults, columns=['Product ID', 'Product Name', 'Rate', 'Stock'])
            update_data(service, 'Products', df)
        
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

# ==================== MAIN APP ====================

def main():
    st.title("🧺 Simple Detergent Billing")
    
    # Sidebar
    st.sidebar.title("📋 Menu")
    st.sidebar.markdown("---")
    
    # Connect
    service = get_sheets_service()
    if service:
        init_sheets(service)
        st.sidebar.success("✅ Connected to Google Sheets")
    else:
        st.sidebar.warning("⚠️ Check your secrets.toml file")
    
    # Menu
    menu = st.sidebar.radio(
        "Navigate",
        ["📊 Dashboard", "📦 Products", "🏪 Parties", "🧾 Billing"]
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
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📦 Products", len(products))
        col2.metric("🏪 Parties", len(parties))
        col3.metric("💰 Total Sales", f"₹{sales['Total'].astype(float).sum():,.2f}" if not sales.empty and 'Total' in sales.columns else "₹0")
        
        st.subheader("📄 Recent Invoices")
        if not sales.empty:
            st.dataframe(sales.tail(10), use_container_width=True)
        else:
            st.info("No sales yet")

    # ==================== PRODUCTS ====================
    elif menu == "📦 Products":
        st.header("📦 Product Master")
        
        if not service:
            st.error("❌ Not connected to Google Sheets")
            return
        
        products = get_data(service, 'Products')
        
        tab1, tab2 = st.tabs(["Manage Products", "Add Product"])
        
        with tab1:
            if not products.empty:
                st.dataframe(products, use_container_width=True)
                
                st.subheader("Quick Stock Update")
                col1, col2 = st.columns([2, 1])
                with col1:
                    selected = st.selectbox("Select Product", products['Product Name'].tolist())
                with col2:
                    change = st.number_input("Change (+/-)", value=0, step=1)
                    if st.button("Update Stock"):
                        if change != 0:
                            idx = products[products['Product Name'] == selected].index[0]
                            products.loc[idx, 'Stock'] = int(products.loc[idx, 'Stock']) + change
                            update_data(service, 'Products', products)
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
                
                if st.form_submit_button("Add Product"):
                    if name and rate > 0:
                        products = get_data(service, 'Products')
                        product_id = f"P{len(products)+1:03d}"
                        add_row(service, 'Products', [product_id, name, rate, stock])
                        st.success(f"✅ Product '{name}' added!")
                        st.rerun()
                    else:
                        st.error("Please fill all required fields")

    # ==================== PARTIES ====================
    elif menu == "🏪 Parties":
        st.header("🏪 Party Master")
        
        if not service:
            st.error("❌ Not connected to Google Sheets")
            return
        
        # FORCE REFRESH - Get fresh data from Google Sheets
        parties = get_data(service, 'Parties')
        
        tab1, tab2 = st.tabs(["Manage Parties", "Add Party"])
        
        with tab1:
            st.subheader("📋 All Parties")
            
            # Check if parties data exists
            if parties is None or parties.empty:
                st.warning("⚠️ No parties found in Google Sheets")
                st.info("Go to 'Add Party' tab to add a new party")
            else:
                # Display the parties table
                st.dataframe(parties, use_container_width=True)
                st.caption(f"Total Parties: {len(parties)}")
                
                # Show party details on selection
                if 'Party Name' in parties.columns and not parties.empty:
                    st.subheader("📌 Party Details")
                    selected_party = st.selectbox("Select a party to view details", parties['Party Name'].tolist())
                    if selected_party:
                        party_data = parties[parties['Party Name'] == selected_party].iloc[0]
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Party ID:** {party_data.get('Party ID', 'N/A')}")
                            st.write(f"**Mobile:** {party_data.get('Mobile', 'N/A')}")
                            st.write(f"**Address:** {party_data.get('Address', 'N/A')}")
                        with col2:
                            st.write(f"**Opening Balance:** ₹{party_data.get('Opening Balance', 0)}")
                            st.write(f"**GST No:** {party_data.get('GST No', 'N/A')}")
        
        with tab2:
            with st.form("add_party_form"):
                st.subheader("➕ Add New Party")
                
                col1, col2 = st.columns(2)
                with col1:
                    party_name = st.text_input("Party Name *", placeholder="e.g., Rajesh Store")
                    mobile = st.text_input("Mobile Number", placeholder="e.g., 9876543210")
                    opening_balance = st.number_input("Opening Balance (₹)", min_value=0.0, step=100.0, value=0.0)
                with col2:
                    address = st.text_area("Address", placeholder="Enter full address")
                    gst_no = st.text_input("GST No (Optional)", placeholder="e.g., GST123456")
                
                submitted = st.form_submit_button("✅ Add Party", type="primary")
                
                if submitted:
                    if not party_name:
                        st.error("❌ Party Name is required!")
                    else:
                        # Get current parties to generate ID
                        current_parties = get_data(service, 'Parties')
                        if current_parties.empty:
                            party_id = "PT001"
                        else:
                            # Find max ID
                            ids = current_parties['Party ID'].astype(str).tolist()
                            nums = []
                            for pid in ids:
                                if pid and pid.startswith('PT'):
                                    try:
                                        num = int(pid.replace('PT', ''))
                                        nums.append(num)
                                    except:
                                        pass
                            next_num = max(nums) + 1 if nums else 1
                            party_id = f"PT{next_num:03d}"
                        
                        # Add row with correct column order
                        # Columns: Party ID, Party Name, Mobile, Address, Opening Balance, GST No
                        success = add_row(service, 'Parties', [
                            party_id, 
                            party_name, 
                            mobile, 
                            address, 
                            opening_balance, 
                            gst_no
                        ])
                        
                        if success:
                            st.success(f"✅ Party '{party_name}' added successfully!")
                            st.info(f"**Party ID:** {party_id}")
                            st.balloons()  # Celebration!
                            # Force refresh by rerunning the app
                            st.rerun()
                        else:
                            st.error("❌ Failed to add party. Please try again.")

    # ==================== BILLING ====================
    elif menu == "🧾 Billing":
        st.header("🧾 Sales Billing")
        
        if not service:
            st.error("❌ Not connected to Google Sheets")
            return
        
        products = get_data(service, 'Products')
        parties = get_data(service, 'Parties')
        
        if products.empty:
            st.warning("⚠️ No products! Add products first.")
            return
        
        if parties.empty:
            st.warning("⚠️ No parties! Add parties first.")
            return
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🛒 Add Items to Cart")
            
            product_names = products['Product Name'].tolist()
            selected = st.selectbox("Select Product", product_names)
            
            if selected:
                product = products[products['Product Name'] == selected].iloc[0]
                stock = int(product['Stock'])
                rate = float(product['Rate'])
                st.info(f"📦 Stock: {stock} | 💰 Rate: ₹{rate:.2f}")
                
                qty = st.number_input("Quantity", min_value=1, max_value=stock, step=1)
                if st.button("➕ Add to Cart", type="primary"):
                    st.session_state.cart.append({
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
                st.metric("💰 Total Amount", f"₹{total:,.2f}")
                
                if st.button("🗑️ Clear Cart"):
                    st.session_state.cart = []
                    st.rerun()
            else:
                st.info("🛒 Cart is empty")
        
        # Create Invoice
        st.markdown("---")
        st.subheader("📄 Create Invoice")
        
        party_names = parties['Party Name'].tolist()
        party = st.selectbox("Select Party", party_names)
        
        if st.button("💳 Generate Invoice", type="primary"):
            if not st.session_state.cart:
                st.error("❌ Cart is empty!")
            else:
                invoice_no = get_next_invoice(service)
                total = sum(item['Amount'] for item in st.session_state.cart)
                
                add_row(service, 'Sales', [
                    invoice_no,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    party,
                    total,
                    'Unpaid'
                ])
                
                for item in st.session_state.cart:
                    idx = products[products['Product Name'] == item['Product']].index[0]
                    products.loc[idx, 'Stock'] = int(products.loc[idx, 'Stock']) - item['Qty']
                update_data(service, 'Products', products)
                
                st.success(f"✅ Invoice {invoice_no} generated! Total: ₹{total:,.2f}")
                
                st.markdown("---")
                st.subheader("🧾 Receipt")
                receipt = f"""
╔══════════════════════════════════════╗
║         🧺 DETERGENT MART           ║
║        123 Main Street, City        ║
║        Phone: +91 98765 43210       ║
╠══════════════════════════════════════╣
║ Invoice: {invoice_no}                    ║
║ Date: {datetime.now().strftime("%d-%m-%Y %H:%M")}    ║
║ Party: {party}                        ║
╠══════════════════════════════════════╣
"""
                for item in st.session_state.cart:
                    receipt += f"║ {item['Product']:<20} x{item['Qty']:<3} ₹{item['Amount']:>8,.2f} ║\n"
                receipt += f"""
╠══════════════════════════════════════╣
║ {'Total':<20} {'':<8} ₹{total:>8,.2f} ║
║ {'Status':<20} {'':<8} {'Unpaid':>8} ║
╚══════════════════════════════════════╝
║         Thank You! Visit Again       ║
╚══════════════════════════════════════╝
"""
                st.code(receipt)
                
                st.session_state.cart = []

# ==================== RUN ====================

if __name__ == "__main__":
    main()
