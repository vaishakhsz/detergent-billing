%%writefile app.py
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import plotly.express as px
import io
from openpyxl import Workbook

# ==========================================
# 1. PAGE SETUP & STYLING ENGINE
# ==========================================
st.set_page_config(
    page_title="Detergent Billing System",
    page_icon="🧼",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .main-header { font-size: 2.2rem; color: #1B5E20; font-weight: 700; margin-bottom: 5px; }
        .sub-header { font-size: 1.1rem; color: #555555; margin-bottom: 25px; }
        .metric-card {
            background-color: #F4F6F4;
            padding: 20px;
            border-radius: 8px;
            border-left: 5px solid #2E7D32;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🧼 Detergent Billing & Inventory Suite</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">All-in-One Real-Time Workspace Engine</div>', unsafe_allow_html=True)

# Schema definitions used as local fallback when Google drops out
sheet_schemas = {
    "Products": ["Product ID", "Product Name", "Rate", "Stock"],
    "Parties": ["Party ID", "Party Name", "Shop Name", "Mobile", "Address", "Opening Balance"],
    "Sales": ["Invoice No", "Date", "Party ID", "Party Name", "Total Amount", "Status"],
    "Sales Items": ["Invoice No", "Product ID", "Product Name", "Qty", "Rate", "Amount"],
    "Receipts": ["Receipt No", "Date", "Party ID", "Invoice No", "Amount", "Payment Mode", "Remarks"],
    "Sales Return": ["Return No", "Date", "Invoice No", "Product ID", "Qty Returned", "Amount"]
}

# ==========================================
# 2. BULLETPROOF DATABASE CONNECTOR WITH TIMEOUTS
# ==========================================
@st.cache_resource(ttl=600)  # Cache client connection for 10 minutes max
def init_gclient():
    try:
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

        # Verify credentials block exists
        if "google_sheets" not in st.secrets:
            return "MISSING_GOOGLE_SHEETS_KEY"
        if "spreadsheet_key" not in st.secrets:
            return "MISSING_SPREADSHEET_KEY"

        credentials_info = dict(st.secrets["google_sheets"])
        if "private_key" in credentials_info:
            credentials_info["private_key"] = credentials_info["private_key"].replace("\\n", "\n")

        creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_info, scopes)
        # Authorize client with a explicit 10-second request timeout limit so it doesn't hang forever
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["spreadsheet_key"])
    except Exception as e:
        return f"ERROR: {str(e)}"

# Attempt connection
db_client = init_gclient()

# Check connection status immediately without freezing the front-end screen
if isinstance(db_client, str):
    st.error("### 🛑 Database Connection Blocked")
    if db_client == "MISSING_GOOGLE_SHEETS_KEY":
        st.warning("Your `.streamlit/secrets.toml` file is missing the `[google_sheets]` configuration section.")
    elif db_client == "MISSING_SPREADSHEET_KEY":
        st.warning("Your `.streamlit/secrets.toml` file is missing the `spreadsheet_key = '...'` definition.")
    elif "API_KEY_INVALID" in db_client or "credential" in db_client.lower():
        st.error("Google rejected the credentials inside your secret file. Double-check your copied keys.")
    else:
        st.error(f"Details: {db_client}")
        st.info("💡 **Most likely fix:** Open your Google Sheet in your browser, hit **Share**, and grant **Editor** access to: `detergent-billing@detergent-billing.iam.gserviceaccount.com`")
    st.stop()

# Auto-Initialize empty sheets with headers securely
def safe_init_sheet(sheet_name: str, expected_headers: list):
    try:
        try:
            sheet = db_client.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            sheet = db_client.add_worksheet(title=sheet_name, rows="1000", cols="20")

        headers = sheet.row_values(1)
        if not headers:
            sheet.append_row(expected_headers)
    except Exception as e:
        st.warning(f"⚠️ Could not sync tab structure for '{sheet_name}'. App will use temporary memory fallback. Error: {e}")

# Run layout sync arrays
for name, schema in sheet_schemas.items():
    safe_init_sheet(name, schema)

def get_dataframe(sheet_name: str) -> pd.DataFrame:
    try:
        sheet = db_client.worksheet(sheet_name)
        records = sheet.get_all_records()
        if not records:
            return pd.DataFrame(columns=sheet_schemas[sheet_name])
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame(columns=sheet_schemas[sheet_name])

def append_row(sheet_name: str, data_row: list):
    try:
        db_client.worksheet(sheet_name).append_row(data_row)
    except Exception as e:
        st.error(f"Failed to save data row to Google Sheets: {e}")

# ==========================================
# 3. SEQUENCE AUTO-ID IDENTIFIER UTILITIES
# ==========================================
def generate_next_id(df: pd.DataFrame, column_name: str, prefix: str) -> str:
    if df.empty or column_name not in df.columns:
        return f"{prefix}0001"
    valid_ids = df[column_name].astype(str).str.strip()
    valid_ids = valid_ids[valid_ids.str.startswith(prefix)]
    if valid_ids.empty:
        return f"{prefix}0001"
    try:
        last_id = valid_ids.iloc[-1]
        numeric_part = int(last_id[len(prefix):])
        return f"{prefix}{str(numeric_part + 1).zfill(4)}"
    except Exception:
        return f"{prefix}{str(len(valid_ids) + 1).zfill(4)}"

# Load Data Matrices safely
df_products = get_dataframe("Products")
df_parties = get_dataframe("Parties")
df_sales = get_dataframe("Sales")
df_receipts = get_dataframe("Receipts")
df_returns = get_dataframe("Sales Return")

# ==========================================
# 4. MAIN WORKSPACE ENGINE TABS
# ==========================================
app_workspace = st.tabs(["📊 Dashboard", "📦 Product Master", "👥 Party Master", "🧾 Sales Billing", "💰 Receipt Entry", "🔄 Sales Return", "📈 Reports Engine"])

# MODULE 1: DASHBOARD
with app_workspace[0]:
    st.subheader("Operational Summary (Today)")
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    today_sales_val = df_sales[df_sales['Date'] == today_str]['Total Amount'].sum() if not df_sales.empty else 0.0
    today_rec_val = df_receipts[df_receipts['Date'] == today_str]['Amount'].sum() if not df_receipts.empty else 0.0
    total_parties = len(df_parties) if not df_parties.empty else 0

    open_bal_sum = pd.to_numeric(df_parties['Opening Balance'], errors='coerce').sum() if not df_parties.empty else 0.0
    sales_sum = pd.to_numeric(df_sales['Total Amount'], errors='coerce').sum() if not df_sales.empty else 0.0
    receipts_sum = pd.to_numeric(df_receipts['Amount'], errors='coerce').sum() if not df_receipts.empty else 0.0
    returns_sum = pd.to_numeric(df_returns['Amount'], errors='coerce').sum() if not df_returns.empty else 0.0
    total_outstanding = (open_bal_sum + sales_sum) - (receipts_sum + returns_sum)

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    kpi_col1.markdown(f"<div class='metric-card'><p style='margin:0;color:#666;'>TODAY'S SALES</p><h2 style='margin:5px 0 0 0;color:#2E7D32;'>₹ {today_sales_val:,.2f}</h2></div>", unsafe_allow_html=True)
    kpi_col2.markdown(f"<div class='metric-card'><p style='margin:0;color:#666;'>TODAY'S RECEIPTS</p><h2 style='margin:5px 0 0 0;color:#1565C0;'>₹ {today_rec_val:,.2f}</h2></div>", unsafe_allow_html=True)
    kpi_col3.markdown(f"<div class='metric-card'><p style='margin:0;color:#666;'>TOTAL OUTSTANDING</p><h2 style='margin:5px 0 0 0;color:#C62828;'>₹ {total_outstanding:,.2f}</h2></div>", unsafe_allow_html=True)
    kpi_col4.markdown(f"<div class='metric-card'><p style='margin:0;color:#666;'>ACTIVE PARTIES</p><h2 style='margin:5px 0 0 0;color:#37474F;'>{total_parties}</h2></div>", unsafe_allow_html=True)

    st.markdown("---")
    g_col1, g_col2 = st.columns([2, 1])
    with g_col1:
        st.subheader("📈 Sales Velocity Performance")
        if not df_sales.empty and 'Date' in df_sales.columns:
            df_chart_data = df_sales.copy()
            df_chart_data['Parsed Date'] = pd.to_datetime(df_chart_data['Date'])
            df_monthly = df_chart_data.groupby(df_chart_data['Parsed Date'].dt.strftime('%Y-%m'))['Total Amount'].sum().reset_index()
            fig = px.line(df_monthly, x='Parsed Date', y='Total Amount', markers=True, color_discrete_sequence=['#2E7D32'])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No transaction data recorded yet.")
    with g_col2:
        st.subheader("⚠️ Low Stock Flags")
        if not df_products.empty and 'Stock' in df_products.columns:
            df_low = df_products[pd.to_numeric(df_products['Stock'], errors='coerce') < 50][['Product Name', 'Stock']]
            st.dataframe(df_low, hide_index=True, use_container_width=True) if not df_low.empty else st.success("Stock levels healthy.")

# MODULE 2: PRODUCT MASTER
with app_workspace[1]:
    st.subheader("Product Inventory Configuration")
    p_tab1, p_tab2 = st.tabs(["✨ Add Product SKU", "📦 View & Adjust Stocks"])
    with p_tab1:
        next_p_id = generate_next_id(df_products, "Product ID", "P")
        with st.form("prod_form", clear_on_submit=True):
            st.text_input("Product ID", value=next_p_id, disabled=True)
            p_name = st.text_input("Product Description Name")
            p_rate = st.number_input("Selling Rate per Unit (₹)", min_value=0.0, step=1.0)
            p_stock = st.number_input("Opening Inventory Volume", min_value=0, step=1)
            if st.form_submit_button("Save SKU Row"):
                if p_name.strip():
                    append_row("Products", [next_p_id, p_name.strip(), p_rate, p_stock])
                    st.success("Product posted successfully!"); st.rerun()
                else: st.error("Name required.")
    with p_tab2:
        st.dataframe(df_products, hide_index=True, use_container_width=True) if not df_products.empty else st.info("No products found.")

# MODULE 3: PARTY MASTER
with app_workspace[2]:
    st.subheader("Client Party Profile Registry")
    next_party_id = generate_next_id(df_parties, "Party ID", "PAR")
    with st.form("party_form", clear_on_submit=True):
        st.text_input("Party ID", value=next_party_id, disabled=True)
        p_name = st.text_input("Party Name (Owner Contact)")
        s_name = st.text_input("Shop/Business Trade Name")
        mobile = st.text_input("10-Digit Mobile Contact")
        address = st.text_area("Full Billing Address")
        open_bal = st.number_input("Opening Balance (₹)", min_value=0.0, step=10.0)
        if st.form_submit_button("Provision Party Profile"):
            if s_name.strip():
                append_row("Parties", [next_party_id, p_name.strip(), s_name.strip(), mobile.strip(), address.strip(), open_bal])
                st.success("Party registered safely!"); st.rerun()
            else: st.error("Shop Name is mandatory.")

# MODULE 4: SALES BILLING
with app_workspace[3]:
    st.subheader("Transactional Checkout Register")
    next_inv = generate_next_id(df_sales, "Invoice No", "INV")
    if 'cart' not in st.session_state: st.session_state.cart = []

    b_col1, b_col2 = st.columns(2)
    with b_col1:
        inv_no = st.text_input("Active Invoice ID", value=next_inv, disabled=True)
        b_date = st.date_input("Billing Date Anchor", datetime.date.today())
    with b_col2:
        if not df_parties.empty:
            party_choice = st.selectbox("Assign Customer Entity", options=df_parties['Party ID'] + " - " + df_parties['Shop Name'])
            sel_party_id = party_choice.split(" - ")[0]
        else: st.error("Please configure parties first."); sel_party_id = None

    st.markdown("---")
    if not df_products.empty and sel_party_id:
        i_col1, i_col2, i_col3 = st.columns([3, 1, 1])
        with i_col1:
            prod_choice = st.selectbox("Select Catalog Detergent Variant", options=df_products['Product ID'] + " - " + df_products['Product Name'])
            sel_prod_id = prod_choice.split(" - ")[0]
        with i_col2:
            order_qty = st.number_input("Line Quantity", min_value=1, value=1, step=1)

        p_row = df_products[df_products['Product ID'] == sel_prod_id].iloc[0]
        p_rate, s_level = float(p_row['Rate']), int(p_row['Stock'])

        with i_col3:
            st.write(f"**Unit Price:** ₹{p_rate:.2f}")
            st.write(f"**Stock Match:** {s_level}")
            if st.button("🛒 Append Line Item"):
                if order_qty > s_level: st.error("Insufficient inventory bounds.")
                else:
                    st.session_state.cart.append({"Product ID": sel_prod_id, "Product Name": p_row['Product Name'], "Qty": order_qty, "Rate": p_rate, "Amount": order_qty * p_rate})
                    st.rerun()

    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        st.table(df_cart)
        g_tot = df_cart['Amount'].sum()
        st.metric("Gross Total Payable", f"₹ {g_tot:,.2f}")
        p_stat = st.selectbox("Invoice Settlement Mode", ["Unpaid", "Partially Paid", "Paid"])

        if st.button("💾 Post & Commit Sales Record"):
            p_name_val = df_parties[df_parties['Party ID'] == sel_party_id].iloc[0]['Party Name']
            append_row("Sales", [inv_no, str(b_date), sel_party_id, p_name_val, g_tot, p_stat])

            p_worksheet = db_client.worksheet("Products")
            p_records = p_worksheet.get_all_records()
            for row in st.session_state.cart:
                append_row("Sales Items", [inv_no, row['Product ID'], row['Product Name'], row['Qty'], row['Rate'], row['Amount']])
                r_idx = next(idx for idx, record in enumerate(p_records) if record["Product ID"] == row['Product ID']) + 2
                p_worksheet.update_cell(r_idx, 4, int(p_records[r_idx-2]["Stock"]) - row['Qty'])
            st.success("Invoice committed directly!"); st.session_state.cart = []; st.rerun()

# MODULE 5: RECEIPT ENTRY
with app_workspace[4]:
    st.subheader("Cash Collection Inward Receipt Logging")
    if not df_sales.empty:
        next_rec_id = generate_next_id(df_receipts, "Receipt No", "REC")
        with st.form("receipt_form", clear_on_submit=True):
            r_col1, r_col2 = st.columns(2)
            with r_col1:
                st.text_input("Receipt ID Tracking", value=next_rec_id, disabled=True)
                r_date = st.date_input("Inward Collection Date", datetime.date.today())
                target_inv = st.selectbox("Select Target Invoice Frame", options=df_sales['Invoice No'] + " - " + df_sales['Party Name'])
                match_inv_id = target_inv.split(" - ")[0]
            with r_col2:
                matched_sale = df_sales[df_sales['Invoice No'] == match_inv_id].iloc[0]
                st.info(f"**Invoice Value:** ₹{matched_sale['Total Amount']:.2f}")
                rec_amt = st.number_input("Injected Cash Payment Amount (₹)", min_value=0.0, step=50.0)
                p_mode = st.selectbox("Payment Mode Channels", ["Cash", "UPI", "Bank Transfer"])
                remarks = st.text_input("Operational Remarks Notation")
            if st.form_submit_button("Post Liquid Receipt Entry"):
                append_row("Receipts", [next_rec_id, str(r_date), matched_sale['Party ID'], match_inv_id, rec_amt, p_mode, remarks])
                st.success("Receipt applied safely."); st.rerun()
    else: st.info("No active sales benchmarks found.")

# MODULE 6: SALES RETURN
with app_workspace[5]:
    st.subheader("Reversal Sales Returns")
    df_sales_items = get_dataframe("Sales Items")

    if not df_sales_items.empty:
        next_sr_id = generate_next_id(df_returns, "Return No", "SR")
        with st.form("return_form", clear_on_submit=True):
            ret_col1, ret_col2 = st.columns(2)
            with ret_col1:
                st.text_input("Sales Return ID Tracking", value=next_sr_id, disabled=True)
                sr_date = st.date_input("Return Logging Date", datetime.date.today())
                ret_inv = st.selectbox("Target Origin Invoice Row", options=df_sales_items['Invoice No'].unique())
            with ret_col2:
                filtered_items = df_sales_items[df_sales_items['Invoice No'] == ret_inv]
                ret_prod = st.selectbox("Choose Product Variant Returned", options=filtered_items['Product ID'] + " - " + filtered_items['Product Name'])
                sel_ret_prod_id = ret_prod.split(" - ")[0]
                matched_line = filtered_items[filtered_items['Product ID'] == sel_ret_prod_id].iloc[0]
                ret_qty = st.number_input("Return Volume Count Quantity", min_value=1, max_value=int(matched_line['Qty']), step=1)
            if st.form_submit_button("Post Authorization Credit Note"):
                calc_refund = ret_qty * float(matched_line['Rate'])
                append_row("Sales Return", [next_sr_id, str(sr_date), ret_inv, sel_ret_prod_id, ret_qty, calc_refund])

                p_sheet = db_client.worksheet("Products")
                p_recs = p_sheet.get_all_records()
                r_idx = next(i for i, r in enumerate(p_recs) if r["Product ID"] == sel_ret_prod_id) + 2
                p_sheet.update_cell(r_idx, 4, int(p_recs[r_idx-2]["Stock"]) + ret_qty)
            st.success("Credit Note generated. Stock updated."); st.rerun()
    else: st.info("No transactional invoice metadata records found.")

# MODULE 7: REPORTS ENGINE
with app_workspace[6]:
    st.subheader("Enterprise Accounts Report & Data Exporters")
    if not df_parties.empty:
        rep_rows = []
        for _, p in df_parties.iterrows():
            pid = p['Party ID']
            s_total = pd.to_numeric(df_sales[df_sales['Party ID'] == pid]['Total Amount'], errors='coerce').sum() if not df_sales.empty else 0.0
            r_total = pd.to_numeric(df_receipts[df_receipts['Party ID'] == pid]['Amount'], errors='coerce').sum() if not df_receipts.empty else 0.0
            ret_total = pd.to_numeric(df_returns[df_returns['Invoice No'].isin(df_sales[df_sales['Party ID'] == pid]['Invoice No'].unique())]['Amount'], errors='coerce').sum() if (not df_returns.empty and not df_sales.empty) else 0.0
            balance_due = float(p['Opening Balance']) + s_total - r_total - ret_total
            rep_rows.append({"Client ID": pid, "Shop Entity Name": p['Shop Name'], "Contact Profile": p['Mobile'], "Outstanding Sum (₹)": balance_due})

        df_final_rep = pd.DataFrame(rep_rows)
        st.dataframe(df_final_rep.style.format({"Outstanding Sum (₹)": "₹{:,.2f}"}), hide_index=True, use_container_width=True)

        wb = Workbook()
        ws = wb.active
        ws.title = "Dues Summary"
        ws.append(["Client ID", "Shop Entity Name", "Contact Profile", "Outstanding Sum"])
        for record in rep_rows: ws.append([record["Client ID"], record["Shop Entity Name"], record["Contact Profile"], record["Outstanding Sum (₹)"]])
        ex_io = io.BytesIO(); wb.save(ex_io); ex_io.seek(0)
        st.download_button("📥 Download Excel Summary Matrix", data=ex_io, file_name="Dues_Master.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else: st.info("No customer accounts on file.")
