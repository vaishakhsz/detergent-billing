"""
Complete Detergent Billing System
OPTIMIZED: Minimal API calls, aggressive caching
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="🧺 Detergent Billing System",
    page_icon="🧺",
    layout="wide"
)

# ==================== SESSION STATE ====================

def init_session_state():
    """Initialize session state variables"""
    if 'cart' not in st.session_state:
        st.session_state.cart = []
    if 'data_cache' not in st.session_state:
        st.session_state.data_cache = {}
    if 'last_fetch' not in st.session_state:
        st.session_state.last_fetch = {}
    if 'refresh_counter' not in st.session_state:
        st.session_state.refresh_counter = 0

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

def get_data(service, sheet_name, force_refresh=False):
    """Get data from sheet with aggressive caching"""
    # Check if we have cached data and it's not forced refresh
    cache_key = f"{sheet_name}"
    
    if not force_refresh and cache_key in st.session_state.data_cache:
        # Check if cache is recent (within 60 seconds)
        if cache_key in st.session_state.last_fetch:
            elapsed = (datetime.now() - st.session_state.last_fetch[cache_key]).total_seconds()
            if elapsed < 30:  # Cache for 30 seconds
                return st.session_state.data_cache[cache_key]
    
    if not service:
        return pd.DataFrame()
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=get_sheet_id(),
            range=f"{sheet_name}!A:Z"
        ).execute()
        values = result.get('values', [])
        
        if not values:
            df = pd.DataFrame()
        else:
            headers = values[0]
            rows = values[1:]
            df = pd.DataFrame(rows, columns=headers)
        
        # Update cache
        st.session_state.data_cache[cache_key] = df
        st.session_state.last_fetch[cache_key] = datetime.now()
        
        return df
    except Exception as e:
        if "429" in str(e):
            st.warning("⏳ Rate limit reached. Using cached data...")
            # Return cached data if available
            if cache_key in st.session_state.data_cache:
                return st.session_state.data_cache[cache_key]
            return pd.DataFrame()
        return pd.DataFrame()

def add_row_only(service, sheet_name, row_data):
    """Add row to sheet - MINIMAL API CALLS"""
    try:
        body = {'values': [row_data]}
        result = service.spreadsheets().values().append(
            spreadsheetId=get_sheet_id(),
            range=f"{sheet_name}!A:Z",
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        # Clear cache for this sheet only
        if sheet_name in st.session_state.data_cache:
            del st.session_state.data_cache[sheet_name]
        if sheet_name in st.session_state.last_fetch:
            del st.session_state.last_fetch[sheet_name]
            
        return result.get('updates', {}).get('updatedRows', 0) > 0
    except Exception as e:
        if "429" in str(e):
            st.error("❌ Rate limit reached. Please wait 30 seconds and try again.")
            return False
        st.error(f"❌ Error adding row: {str(e)}")
        return False

def update_cell(service, sheet_name, range_name, value):
    """Update a single cell"""
    try:
        service.spreadsheets().values().update(
            spreadsheetId=get_sheet_id(),
            range=range_name,
            valueInputOption='USER_ENTERED',
            body={'values': [[str(value)]]}
        ).execute()
        
        # Clear cache for this sheet
        if sheet_name in st.session_state.data_cache:
            del st.session_state.data_cache[sheet_name]
        if sheet_name in st.session_state.last_fetch:
            del st.session_state.last_fetch[sheet_name]
            
        return True
    except Exception as e:
        if "429" in str(e):
            st.warning("⏳ Rate limit reached. Please wait.")
            return False
        st.error(f"Error updating cell: {str(e)}")
        return False

def create_sheet_if_not_exists(service, sheet_name, headers):
    """Create sheet if not exists - MINIMAL API CALLS"""
    try:
        # First check if sheet exists using cached data
        try:
            spreadsheet = service.spreadsheets().get(
                spreadsheetId=get_sheet_id()
            ).execute()
            sheets = spreadsheet.get('sheets', [])
            sheet_names = [sheet['properties']['title'] for sheet in sheets]
            
            if sheet_name in sheet_names:
                return True
        except Exception as e:
            if "429" in str(e):
                st.warning("⏳ Rate limit. Sheet creation skipped.")
                return True  # Assume it exists
            
        # Only create if it doesn't exist
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
        
        # Add headers
        values = [headers]
        service.spreadsheets().values().update(
            spreadsheetId=get_sheet_id(),
            range=f"{sheet_name}!A1",
            valueInputOption='USER_ENTERED',
            body={'values': values}
        ).execute()
        return True
    except Exception as e:
        if "429" in str(e):
            st.warning("⏳ Rate limit reached. Please wait.")
            return True  # Assume it exists
        st.error(f"Error creating sheet: {str(e)}")
        return False

# ==================== INIT ====================

def init_sheets(service):
    """Initialize sheets - MINIMAL API CALLS"""
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
        
        # Check if products exist - use cached data
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

# ==================== HELPERS ====================

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
        
        update_cell(service, 'Products', f"D{row_num}", new_stock)
        return True
    except Exception as e:
        st.error(f"Error updating stock: {str(e)}")
        return False

def get_invoice_paid_amount(service, invoice_no):
    """Get total paid amount for an invoice"""
    receipts = get_data(service, 'Receipts')
    if receipts.empty or 'Invoice No' not in receipts.columns:
        return 0
    paid = receipts[receipts['Invoice No'] == invoice_no]['Amount'].apply(safe_float).sum()
    return paid

def update_invoice_status(service, invoice_no):
    """Update invoice status based on payments"""
    sales = get_data(service, 'Sales')
    if sales.empty or 'Invoice No' not in sales.columns:
        return
    
    idx = sales[sales['Invoice No'] == invoice_no].index
    if idx.empty:
        return
    
    total = safe_float(sales.loc[idx[0], 'Total'])
    paid = get_invoice_paid_amount(service, invoice_no)
    
    if paid >= total:
        status = 'Paid'
    elif paid > 0:
        status = 'Partially Paid'
    else:
        status = 'Unpaid'
    
    row_num = idx[0] + 2
    update_cell(service, 'Sales', f"E{row_num}", status)

def check_columns(df, required_columns):
    """Check if required columns exist in DataFrame"""
    if df.empty:
        return False, []
    missing = [col for col in required_columns if col not in df.columns]
    return len(missing) == 0, missing

def force_refresh():
    """Force refresh all data"""
    st.session_state.data_cache = {}
    st.session_state.last_fetch = {}
    st.session_state.refresh_counter += 1
    st.rerun()

# ==================== MAIN APP ====================

def main():
    # Initialize session state
    init_session_state()
    
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
                st.sidebar.warning("⏳ Rate limit. Using cached data.")
            else:
                st.sidebar.error(f"❌ Error: {str(e)[:50]}...")
    else:
        st.sidebar.warning("⚠️ Check secrets.toml")
    
    # Refresh Button
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        st.sidebar.write(f"🔄 Refresh Data")
    with col2:
        if st.sidebar.button("🔄", help="Refresh all data"):
            force_refresh()
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"📊 Cache: {len(st.session_state.data_cache)} items")
    st.sidebar.info("Made with ❤️ using Streamlit")
    
    # Menu
    menu = st.sidebar.radio(
        "Navigate",
        ["📊 Dashboard", "📦 Products", "🏪 Parties", "🧾 Billing", 
         "💰 Cash Receipt", "📒 Party Ledger", "📈 Reports"]
    )
    
    st.sidebar.markdown("---")

    # ==================== REST OF THE APP ====================
    # [Same as previous - keep all the menu logic]
    # But with get_data(service, 'SheetName') using cache

    # ==================== PARTIES (Fixed) ====================
    if menu == "🏪 Parties":
        st.header("🏪 Party Master")
        
        if not service:
            st.error("❌ Not connected")
            return
        
        # Use cached data
        parties = get_data(service, 'Parties')
        
        tab1, tab2 = st.tabs(["Manage Parties", "Add Party"])
        
        with tab1:
            st.subheader("📋 All Parties")
            
            if parties.empty:
                st.warning("⚠️ No parties found")
                st.info("💡 Click 'Add Party' to add a new party")
                st.info("💡 Click 🔄 refresh button to reload")
            else:
                if 'Party Name' not in parties.columns:
                    st.error("❌ 'Party Name' column not found!")
                    st.write("Current columns:", list(parties.columns))
                else:
                    st.success(f"✅ Found {len(parties)} parties")
                    st.dataframe(parties, use_container_width=True)
        
        with tab2:
            st.subheader("➕ Add New Party")
            
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
                
                submitted = st.form_submit_button("✅ Add Party", type="primary")
                
                if submitted:
                    if not party_name:
                        st.error("❌ Party Name is required!")
                    else:
                        party_id = get_next_party_id(service)
                        row_data = [party_id, party_name, mobile, whatsapp, address, str(opening_balance), gst_no]
                        
                        success = add_row_only(service, 'Parties', row_data)
                        
                        if success:
                            st.success(f"✅ Party '{party_name}' added successfully!")
                            st.balloons()
                            time.sleep(1)
                            force_refresh()
                        else:
                            st.error("❌ Failed to add party. Rate limit may be exceeded.")

# ==================== RUN ====================

if __name__ == "__main__":
    main()
