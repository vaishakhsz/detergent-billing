"""
Simple Detergent Billing - Using Streamlit's Native Google Sheets
No google-api-python-client needed!
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="🧺 Detergent Billing",
    page_icon="🧺",
    layout="wide"
)

# ==================== GOOGLE SHEETS USING STREAMLIT NATIVE ====================

def get_sheets():
    """Connect using Streamlit's native Google Sheets"""
    try:
        # Streamlit's native connection (requires secrets)
        conn = st.connection("gsheets", type="GSheetsConnection")
        return conn
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return None

def get_data(conn, sheet_name):
    """Get data from sheet"""
    try:
        df = conn.read(worksheet=sheet_name, ttl=60)
        return df
    except:
        return pd.DataFrame()

def add_row(conn, sheet_name, row_data):
    """Add row to sheet"""
    try:
        df = get_data(conn, sheet_name)
        if df.empty:
            # Create new dataframe with headers
            headers = {
                'Products': ['Product ID', 'Product Name', 'Rate', 'Stock'],
                'Parties': ['Party ID', 'Party Name', 'Mobile'],
                'Sales': ['Invoice No', 'Date', 'Party', 'Total', 'Status']
            }
            df = pd.DataFrame(columns=headers.get(sheet_name, []))
        
        # Add row
        new_row = pd.DataFrame([row_data], columns=df.columns)
        df = pd.concat([df, new_row], ignore_index=True)
        conn.write(dataframe=df, worksheet=sheet_name)
        return True
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return False

# ==================== INIT ====================

def init_sheets(conn):
    """Initialize sheets with default data"""
    try:
        products = get_data(conn, 'Products')
        if products.empty:
            defaults = [
                ['P001', 'Dishwash Liquid 1L', 120, 100],
                ['P002', 'Detergent Powder 1kg', 120, 100],
                ['P003', 'Dishwash Liquid 7+1', 840, 50],
                ['P004', 'Detergent Powder 7+1', 840, 50]
            ]
            df = pd.DataFrame(defaults, columns=['Product ID', 'Product Name', 'Rate', 'Stock'])
            conn.write(dataframe=df, worksheet='Products')
        
        # Initialize other sheets
        for sheet in ['Parties', 'Sales']:
            df = get_data(conn, sheet)
            if df.empty:
                if sheet == 'Parties':
                    df = pd.DataFrame(columns=['Party ID', 'Party Name', 'Mobile'])
                elif sheet == 'Sales':
                    df = pd.DataFrame(columns=['Invoice No', 'Date', 'Party', 'Total', 'Status'])
                conn.write(dataframe=df, worksheet=sheet)
        
        return True
    except Exception as e:
        st.error(f"Init error: {str(e)}")
        return False

def get_next_invoice(conn):
    """Generate next invoice number"""
    sales = get_data(conn, 'Sales')
    if sales.empty or 'Invoice No' not in sales.columns:
        return "INV001"
    nums = [int(str(x).replace('INV', '')) for x in sales['Invoice No'] if str(x).startswith('INV')]
    next_num = max(nums) + 1 if nums else 1
    return f"INV{next_num:03d}"

# ==================== MAIN APP ====================

def main():
    st.title("🧺 Simple Detergent Billing")
    
    # Connect
    conn = get_sheets()
    if conn:
        init_sheets(conn)
        st.sidebar.success("✅ Connected")
    else:
        st.sidebar.warning("⚠️ Offline")
    
    # Menu
    menu = st.sidebar.radio("Menu", ["📊 Dashboard", "📦 Products", "🏪 Parties", "🧾 Billing"])
    
    # ==================== DASHBOARD ====================
    if menu == "📊 Dashboard":
        st.header("Dashboard")
        
        products = get_data(conn, 'Products') if conn else pd.DataFrame()
        sales = get_data(conn, 'Sales') if conn else pd.DataFrame()
        parties = get_data(conn, 'Parties') if conn else pd.DataFrame()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Products", len(products))
        col2.metric("Parties", len(parties))
        col3.metric("Total Sales", f"₹{sales['Total'].astype(float).sum():,.2f}" if not sales.empty and 'Total' in sales.columns else "₹0")
        
        st.subheader("Recent Sales")
        if not sales.empty:
            st.dataframe(sales.tail(5), use_container_width=True)
    
    # ==================== PRODUCTS ====================
    elif menu == "📦 Products":
        st.header("Product Master")
        
        if not conn:
            st.error("Not connected")
            return
        
        products = get_data(conn, 'Products')
        
        tab1, tab2 = st.tabs(["View Products", "Add Product"])
        
        with tab1:
            if not products.empty:
                st.dataframe(products, use_container_width=True)
                
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
                            conn.write(dataframe=products, worksheet='Products')
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
                        products = get_data(conn, 'Products')
                        product_id = f"P{len(products)+1:03d}"
                        add_row(conn, 'Products', [product_id, name, rate, stock])
                        st.success(f"Added {name}")
                        st.rerun()
    
    # ==================== PARTIES ====================
    elif menu == "🏪 Parties":
        st.header("Party Master")
        
        if not conn:
            st.error("Not connected")
            return
        
        parties = get_data(conn, 'Parties')
        
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
                        parties = get_data(conn, 'Parties')
                        party_id = f"PT{len(parties)+1:03d}" if not parties.empty else "PT001"
                        add_row(conn, 'Parties', [party_id, name, mobile])
                        st.success(f"Added {name}")
                        st.rerun()
    
    # ==================== BILLING ====================
    elif menu == "🧾 Billing":
        st.header("Sales Billing")
        
        if not conn:
            st.error("Not connected")
            return
        
        products = get_data(conn, 'Products')
        parties = get_data(conn, 'Parties')
        
        if products.empty:
            st.warning("No products! Add products first.")
            return
        
        if parties.empty:
            st.warning("No parties! Add parties first.")
            return
        
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
        
        st.markdown("---")
        st.subheader("Create Invoice")
        
        party_names = parties['Party Name'].tolist()
        party = st.selectbox("Party", party_names)
        
        if st.button("Generate Invoice", type="primary"):
            if not st.session_state.cart:
                st.error("Cart is empty!")
            else:
                invoice_no = get_next_invoice(conn)
                total = sum(item['Amount'] for item in st.session_state.cart)
                
                add_row(conn, 'Sales', [
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
                conn.write(dataframe=products, worksheet='Products')
                
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
