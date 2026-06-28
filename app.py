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
    """Connect to Google Sheets"""
    try:
        if 'google_sheets' in st.secrets:
            creds_dict = dict(st.secrets['google_sheets'])
        else:
            st.warning("Please upload your Service Account JSON")
            uploaded = st.file_uploader("Upload JSON", type=['json'])
            if uploaded:
                creds_dict = json.load(uploaded)
            else:
                return None
        
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
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
        return pd.DataFrame(values[1:], columns=values[0])
    except:
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
        st.error(f"Error: {str(e)}")
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
    except:
        return False

# ==================== INIT ====================

def init_sheets(service):
    """Initialize sheets"""
    sheets = {
        'Products': ['Product ID', 'Product Name', 'Rate', 'Stock'],
        'Parties': ['Party ID', 'Party Name', 'Mobile'],
        'Sales': ['Invoice No', 'Date', 'Party', 'Total', 'Status']
    }
    
    for sheet_name, headers in sheets.items():
        df = get_data(service, sheet_name)
        if df.empty:
            df = pd.DataFrame(columns=headers)
            update_data(service, sheet_name, df)
    
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

def get_next_invoice(service):
    """Generate next invoice number"""
    sales = get_data(service, 'Sales')
    if sales.empty:
        return "INV001"
    nums = [int(str(x).replace('INV', '')) for x in sales['Invoice No'] if str(x).startswith('INV')]
    next_num = max(nums) + 1 if nums else 1
    return f"INV{next_num:03d}"

# ==================== MAIN APP ====================

def main():
    st.title("🧺 Simple Detergent Billing")
    
    # Connect
    service = get_sheets_service()
    if service:
        init_sheets(service)
        st.sidebar.success("✅ Connected")
    else:
        st.sidebar.warning("⚠️ Offline")
    
    # Menu
    menu = st.sidebar.radio("Menu", ["📊 Dashboard", "📦 Products", "🏪 Parties", "🧾 Billing"])
    
    # ==================== DASHBOARD ====================
    if menu == "📊 Dashboard":
        st.header("Dashboard")
        
        products = get_data(service, 'Products') if service else pd.DataFrame()
        sales = get_data(service, 'Sales') if service else pd.DataFrame()
        parties = get_data(service, 'Parties') if service else pd.DataFrame()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Products", len(products))
        col2.metric("Parties", len(parties))
        col3.metric("Total Sales", f"₹{sales['Total'].astype(float).sum():,.2f}" if not sales.empty else "₹0")
        
        st.subheader("Recent Sales")
        if not sales.empty:
            st.dataframe(sales.tail(5), use_container_width=True)
    
    # ==================== PRODUCTS ====================
    elif menu == "📦 Products":
        st.header("Product Master")
        
        if not service:
            st.error("Not connected to Google Sheets")
            return
        
        products = get_data(service, 'Products')
        
        tab1, tab2 = st.tabs(["View Products", "Add Product"])
        
        with tab1:
            if not products.empty:
                st.dataframe(products, use_container_width=True)
                
                # Quick stock update
                st.subheader("Update Stock")
                col1, col2 = st.columns(2)
                with col1:
                    selected = st.selectbox("Select Product", products['Product Name'].tolist())
                with col2:
                    change = st.number_input("Change (+/-)", value=0, step=1)
                    if st.button("Update"):
                        if change != 0:
                            idx = products[products['Product Name'] == selected].index[0]
                            products.loc[idx, 'Stock'] = int(products.loc[idx, 'Stock']) + change
                            update_data(service, 'Products', products)
                            st.success("Stock updated!")
                            st.rerun()
            else:
                st.info("No products")
        
        with tab2:
            with st.form("add_product"):
                name = st.text_input("Product Name")
                rate = st.number_input("Rate (₹)", min_value=0.0, step=1.0)
                stock = st.number_input("Stock", min_value=0, step=1)
                
                if st.form_submit_button("Add Product"):
                    if name:
                        products = get_data(service, 'Products')
                        product_id = f"P{len(products)+1:03d}"
                        add_row(service, 'Products', [product_id, name, rate, stock])
                        st.success(f"Added {name}")
                        st.rerun()
    
    # ==================== PARTIES ====================
    elif menu == "🏪 Parties":
        st.header("Party Master")
        
        if not service:
            st.error("Not connected to Google Sheets")
            return
        
        parties = get_data(service, 'Parties')
        
        tab1, tab2 = st.tabs(["View Parties", "Add Party"])
        
        with tab1:
            if not parties.empty:
                st.dataframe(parties, use_container_width=True)
            else:
                st.info("No parties")
        
        with tab2:
            with st.form("add_party"):
                name = st.text_input("Party Name")
                mobile = st.text_input("Mobile")
                
                if st.form_submit_button("Add Party"):
                    if name:
                        party_id = f"PT{len(parties)+1:03d}" if not parties.empty else "PT001"
                        add_row(service, 'Parties', [party_id, name, mobile])
                        st.success(f"Added {name}")
                        st.rerun()
    
    # ==================== BILLING ====================
    elif menu == "🧾 Billing":
        st.header("Sales Billing")
        
        if not service:
            st.error("Not connected to Google Sheets")
            return
        
        products = get_data(service, 'Products')
        parties = get_data(service, 'Parties')
        
        if products.empty:
            st.warning("No products! Add products first.")
            return
        
        if parties.empty:
            st.warning("No parties! Add parties first.")
            return
        
        # Cart in session
        if 'cart' not in st.session_state:
            st.session_state.cart = []
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Add Items")
            
            product_names = products['Product Name'].tolist()
            selected = st.selectbox("Product", product_names)
            
            if selected:
                product = products[products['Product Name'] == selected].iloc[0]
                stock = int(product['Stock'])
                rate = float(product['Rate'])
                st.info(f"Stock: {stock} | Rate: ₹{rate}")
                
                qty = st.number_input("Qty", min_value=1, max_value=stock, step=1)
                if st.button("Add to Cart"):
                    st.session_state.cart.append({
                        'Product': selected,
                        'Rate': rate,
                        'Qty': qty,
                        'Amount': rate * qty
                    })
                    st.success(f"Added {qty} {selected}")
                    st.rerun()
        
        with col2:
            st.subheader("Cart")
            if st.session_state.cart:
                cart_df = pd.DataFrame(st.session_state.cart)
                st.dataframe(cart_df[['Product', 'Qty', 'Rate', 'Amount']], use_container_width=True)
                total = cart_df['Amount'].sum()
                st.metric("Total", f"₹{total:,.2f}")
                
                if st.button("Clear Cart"):
                    st.session_state.cart = []
                    st.rerun()
            else:
                st.info("Cart empty")
        
        # Create Invoice
        st.markdown("---")
        st.subheader("Create Invoice")
        
        party_names = parties['Party Name'].tolist()
        party = st.selectbox("Party", party_names)
        
        if st.button("Generate Invoice", type="primary"):
            if not st.session_state.cart:
                st.error("Cart is empty!")
            else:
                invoice_no = get_next_invoice(service)
                total = sum(item['Amount'] for item in st.session_state.cart)
                
                # Save invoice
                add_row(service, 'Sales', [
                    invoice_no,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    party,
                    total,
                    'Unpaid'
                ])
                
                # Update stock
                for item in st.session_state.cart:
                    idx = products[products['Product Name'] == item['Product']].index[0]
                    products.loc[idx, 'Stock'] = int(products.loc[idx, 'Stock']) - item['Qty']
                update_data(service, 'Products', products)
                
                st.success(f"Invoice {invoice_no} generated! Total: ₹{total:,.2f}")
                
                # Show receipt
                st.markdown("---")
                st.subheader("🧾 Receipt")
                receipt = f"""
                DETERGENT MART
                ==============
                Invoice: {invoice_no}
                Date: {datetime.now().strftime("%d-%m-%Y %H:%M")}
                Party: {party}
                ----------
                """
                for item in st.session_state.cart:
                    receipt += f"{item['Product']} x{item['Qty']} = ₹{item['Amount']:,.2f}\n"
                receipt += f"""
                ----------
                Total: ₹{total:,.2f}
                Status: Unpaid
                ==============
                Thank You!
                """
                st.code(receipt)
                
                st.session_state.cart = []

# ==================== RUN ====================

if __name__ == "__main__":
    main()
