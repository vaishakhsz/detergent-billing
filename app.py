"""
Detergent Billing Software
Complete Solution with all modules
Google Sheets Database | No GST
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import io
import base64
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import openpyxl

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
        if 'google_sheets' in st.secrets:
            creds_dict = dict(st.secrets['google_sheets'])
        else:
            st.warning("⚠️ Please upload your Service Account JSON file")
            uploaded_file = st.file_uploader("Upload Service Account JSON", type=['json'])
            if uploaded_file:
                creds_dict = json.load(uploaded_file)
            else:
                return None
        
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=creds)
        return service
        
    except Exception as e:
        st.error(f"❌ Connection error: {str(e)}")
        return None

def get_spreadsheet_id():
    """Get spreadsheet ID from URL"""
    sheet_id = "1jaat8u_k7rQyqhPcdL4zmUkkuG8gpwwk6z-Tvv2SMrQ"
    return sheet_id

def get_data(service, sheet_name, range_name="A:Z"):
    """Get data from a Google Sheet"""
    try:
        sheet_id = get_spreadsheet_id()
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!{range_name}"
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
        body = {'values': [row_data]}
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
        service.spreadsheets().values().clear(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!A:Z",
            body={}
        ).execute()
        
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
        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
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
    """Initialize all sheets with headers"""
    try:
        sheets_config = {
            'Products': ['Product ID', 'Product Name', 'Rate', 'Stock', 'Brand', 'Unit'],
            'Parties': ['Party ID', 'Party Name', 'Shop Name', 'Mobile', 'Address', 'Opening Balance'],
            'Sales': ['Invoice No', 'Date', 'Party ID', 'Party Name', 'Total Amount', 'Status'],
            'Sales_Items': ['Invoice No', 'Product ID', 'Product Name', 'Qty', 'Rate', 'Amount'],
            'Receipts': ['Receipt No', 'Date', 'Party ID', 'Invoice No', 'Amount', 'Payment Mode', 'Remarks'],
            'Sales_Return': ['Return No', 'Date', 'Invoice No', 'Product', 'Qty Returned', 'Amount', 'Reason']
        }
        
        for sheet_name, headers in sheets_config.items():
            create_sheet_if_not_exists(service, sheet_name)
            df = get_data(service, sheet_name)
            if df.empty:
                df = pd.DataFrame(columns=headers)
                update_data(service, sheet_name, df)
        
        # Initialize Products with default data
        products = get_data(service, 'Products')
        if products.empty:
            default_products = [
                ['P001', 'Dishwash Liquid 1 Litre', 120, 500, 'Detergent', 'Pcs'],
                ['P002', 'Detergent Powder 1 Kg', 120, 500, 'Detergent', 'Pcs'],
                ['P003', 'Dishwash Liquid 7+1', 840, 100, 'Detergent', 'Pack'],
                ['P004', 'Detergent Powder 7+1', 840, 100, 'Detergent', 'Pack']
            ]
            df = pd.DataFrame(default_products, columns=['Product ID', 'Product Name', 'Rate', 'Stock', 'Brand', 'Unit'])
            update_data(service, 'Products', df)
            st.success("✅ Default products added!")
        
        return True
    except Exception as e:
        st.error(f"Error initializing: {str(e)}")
        return False

# ==================== ID GENERATORS ====================

def get_next_id(service, sheet_name, id_column):
    """Generate next ID for a sheet"""
    df = get_data(service, sheet_name)
    if df.empty or id_column not in df.columns:
        return f"{id_column[:3]}001"
    
    try:
        ids = df[id_column].astype(str).tolist()
        # Extract numeric part
        numbers = []
        for id_str in ids:
            if id_str:
                num = int(''.join(filter(str.isdigit, id_str)))
                numbers.append(num)
        
        if numbers:
            next_num = max(numbers) + 1
        else:
            next_num = 1
        
        prefix = id_column[:3].upper()
        return f"{prefix}{next_num:04d}"
    except:
        return f"{id_column[:3]}001"

def get_next_invoice_no(service):
    """Generate next invoice number"""
    df = get_data(service, 'Sales')
    if df.empty or 'Invoice No' not in df.columns:
        return "INV0001"
    
    try:
        invoices = df['Invoice No'].astype(str).tolist()
        numbers = []
        for inv in invoices:
            if inv:
                num = int(''.join(filter(str.isdigit, inv)))
                numbers.append(num)
        
        next_num = max(numbers) + 1 if numbers else 1
        return f"INV{next_num:04d}"
    except:
        return "INV0001"

# ==================== PRODUCT FUNCTIONS ====================

def get_products(service):
    """Get all products"""
    df = get_data(service, 'Products')
    if not df.empty:
        df['Rate'] = pd.to_numeric(df['Rate'], errors='coerce')
        df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce')
    return df

def update_stock(service, product_id, quantity_change):
    """Update product stock"""
    df = get_products(service)
    if not df.empty:
        idx = df[df['Product ID'] == product_id].index
        if not idx.empty:
            current_stock = float(df.loc[idx[0], 'Stock'])
            df.loc[idx[0], 'Stock'] = current_stock + quantity_change
            update_data(service, 'Products', df)
            return True
    return False

# ==================== PARTY FUNCTIONS ====================

def get_parties(service):
    """Get all parties"""
    df = get_data(service, 'Parties')
    if not df.empty:
        df['Opening Balance'] = pd.to_numeric(df['Opening Balance'], errors='coerce')
    return df

def add_party(service, party_name, shop_name, mobile, address, opening_balance):
    """Add a new party"""
    party_id = get_next_id(service, 'Parties', 'Party ID')
    new_row = [party_id, party_name, shop_name, mobile, address, str(opening_balance)]
    add_row(service, 'Parties', new_row)
    return party_id

def get_party_balance(service, party_id):
    """Get party outstanding balance"""
    # Get all sales for this party
    sales = get_data(service, 'Sales')
    party_sales = sales[sales['Party ID'] == party_id] if not sales.empty else pd.DataFrame()
    
    # Get all receipts for this party
    receipts = get_data(service, 'Receipts')
    party_receipts = receipts[receipts['Party ID'] == party_id] if not receipts.empty else pd.DataFrame()
    
    total_sales = party_sales['Total Amount'].astype(float).sum() if not party_sales.empty else 0
    total_receipts = party_receipts['Amount'].astype(float).sum() if not party_receipts.empty else 0
    
    # Opening balance
    parties = get_parties(service)
    party = parties[parties['Party ID'] == party_id] if not parties.empty else pd.DataFrame()
    opening_balance = float(party.iloc[0]['Opening Balance']) if not party.empty else 0
    
    return opening_balance + total_sales - total_receipts

# ==================== INVOICE FUNCTIONS ====================

def create_invoice(service, party_id, party_name, cart):
    """Create a new invoice"""
    try:
        invoice_no = get_next_invoice_no(service)
        total_amount = sum(item['Amount'] for item in cart)
        
        # Add to Sales sheet
        sales_row = [invoice_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    party_id, party_name, str(total_amount), 'Unpaid']
        add_row(service, 'Sales', sales_row)
        
        # Add items to Sales_Items
        for item in cart:
            item_row = [invoice_no, item['Product ID'], item['Product Name'], 
                       str(item['Qty']), str(item['Rate']), str(item['Amount'])]
            add_row(service, 'Sales_Items', item_row)
            
            # Update stock
            update_stock(service, item['Product ID'], -item['Qty'])
        
        return invoice_no, total_amount
    
    except Exception as e:
        st.error(f"Error creating invoice: {str(e)}")
        return None, None

def get_invoice_status(service, invoice_no):
    """Get invoice payment status"""
    sales = get_data(service, 'Sales')
    invoice = sales[sales['Invoice No'] == invoice_no] if not sales.empty else pd.DataFrame()
    if not invoice.empty:
        total = float(invoice.iloc[0]['Total Amount'])
        receipts = get_data(service, 'Receipts')
        received = receipts[receipts['Invoice No'] == invoice_no]['Amount'].astype(float).sum() if not receipts.empty else 0
        
        if received >= total:
            return 'Paid'
        elif received > 0:
            return 'Partially Paid'
        else:
            return 'Unpaid'
    return 'Unknown'

def update_invoice_status(service, invoice_no):
    """Update invoice status"""
    status = get_invoice_status(service, invoice_no)
    sales = get_data(service, 'Sales')
    idx = sales[sales['Invoice No'] == invoice_no].index
    if not idx.empty:
        sales.loc[idx[0], 'Status'] = status
        update_data(service, 'Sales', sales)
    return status

# ==================== RECEIPT FUNCTIONS ====================

def add_receipt(service, party_id, invoice_no, amount, payment_mode, remarks=""):
    """Add a receipt"""
    try:
        receipt_no = get_next_id(service, 'Receipts', 'Receipt No')
        receipt_row = [receipt_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                      party_id, invoice_no, str(amount), payment_mode, remarks]
        add_row(service, 'Receipts', receipt_row)
        
        # Update invoice status
        update_invoice_status(service, invoice_no)
        
        return receipt_no
    except Exception as e:
        st.error(f"Error adding receipt: {str(e)}")
        return None

# ==================== SALES RETURN FUNCTIONS ====================

def add_sales_return(service, invoice_no, product_name, qty_returned, amount, reason=""):
    """Add a sales return"""
    try:
        return_no = get_next_id(service, 'Sales_Return', 'Return No')
        return_row = [return_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                     invoice_no, product_name, str(qty_returned), str(amount), reason]
        add_row(service, 'Sales_Return', return_row)
        
        # Find product ID and update stock
        products = get_products(service)
        product = products[products['Product Name'] == product_name] if not products.empty else pd.DataFrame()
        if not product.empty:
            product_id = product.iloc[0]['Product ID']
            update_stock(service, product_id, qty_returned)
            
            # Update invoice total
            sales = get_data(service, 'Sales')
            idx = sales[sales['Invoice No'] == invoice_no].index
            if not idx.empty:
                current_total = float(sales.loc[idx[0], 'Total Amount'])
                sales.loc[idx[0], 'Total Amount'] = current_total - amount
                update_data(service, 'Sales', sales)
                update_invoice_status(service, invoice_no)
        
        return return_no
    except Exception as e:
        st.error(f"Error adding sales return: {str(e)}")
        return None

# ==================== REPORT FUNCTIONS ====================

def get_party_statement(service, party_id, from_date=None, to_date=None):
    """Get party statement of account"""
    sales = get_data(service, 'Sales')
    receipts = get_data(service, 'Receipts')
    returns = get_data(service, 'Sales_Return')
    
    # Filter by party
    party_sales = sales[sales['Party ID'] == party_id] if not sales.empty else pd.DataFrame()
    party_receipts = receipts[receipts['Party ID'] == party_id] if not receipts.empty else pd.DataFrame()
    
    # Filter by date if provided
    if from_date and not party_sales.empty:
        party_sales = party_sales[party_sales['Date'] >= from_date]
    if to_date and not party_sales.empty:
        party_sales = party_sales[party_sales['Date'] <= to_date]
    
    if from_date and not party_receipts.empty:
        party_receipts = party_receipts[party_receipts['Date'] >= from_date]
    if to_date and not party_receipts.empty:
        party_receipts = party_receipts[party_receipts['Date'] <= to_date]
    
    # Build statement
    statements = []
    
    # Opening Balance
    parties = get_parties(service)
    party = parties[parties['Party ID'] == party_id] if not parties.empty else pd.DataFrame()
    opening = float(party.iloc[0]['Opening Balance']) if not party.empty else 0
    
    statements.append({
        'Date': 'Opening',
        'Particulars': 'Opening Balance',
        'Debit': 0,
        'Credit': 0,
        'Balance': opening
    })
    
    balance = opening
    
    # Sales (Debit)
    if not party_sales.empty:
        for _, row in party_sales.iterrows():
            amount = float(row['Total Amount'])
            balance += amount
            statements.append({
                'Date': row['Date'][:10] if 'Date' in row else '',
                'Particulars': f"Invoice: {row['Invoice No']}",
                'Debit': amount,
                'Credit': 0,
                'Balance': balance
            })
    
    # Receipts (Credit)
    if not party_receipts.empty:
        for _, row in party_receipts.iterrows():
            amount = float(row['Amount'])
            balance -= amount
            statements.append({
                'Date': row['Date'][:10] if 'Date' in row else '',
                'Particulars': f"Receipt: {row['Receipt No']}",
                'Debit': 0,
                'Credit': amount,
                'Balance': balance
            })
    
    # Returns (Credit)
    if not returns.empty:
        party_returns = returns[returns['Invoice No'].isin(party_sales['Invoice No'].tolist())] if not party_sales.empty else pd.DataFrame()
        for _, row in party_returns.iterrows():
            amount = float(row['Amount'])
            balance -= amount
            statements.append({
                'Date': row['Date'][:10] if 'Date' in row else '',
                'Particulars': f"Return: {row['Return No']}",
                'Debit': 0,
                'Credit': amount,
                'Balance': balance
            })
    
    return pd.DataFrame(statements)

# ==================== PDF GENERATION ====================

def generate_invoice_pdf(invoice_no, party_name, party_address, party_mobile, items, total, received, balance):
    """Generate PDF invoice"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#003366'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    elements.append(Paragraph("🧺 DETERGENT MART", title_style))
    
    # Company details
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER
    )
    elements.append(Paragraph("123 Main Street, City", info_style))
    elements.append(Paragraph("Phone: +91 98765 43210", info_style))
    elements.append(Spacer(1, 10))
    
    # Invoice details
    inv_style = ParagraphStyle(
        'InvStyle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    elements.append(Paragraph(f"<b>INVOICE</b>", inv_style))
    
    # Invoice info table
    info_data = [
        ['Invoice No:', invoice_no, 'Date:', datetime.now().strftime("%d-%m-%Y")],
        ['Party:', party_name, 'Mobile:', party_mobile],
        ['Address:', party_address, '', '']
    ]
    info_table = Table(info_data, colWidths=[80, 120, 80, 100])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOLD', (0, 0), (1, 0), True),
        ('BOLD', (2, 0), (3, 0), True),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))
    
    # Items table
    item_data = [['#', 'Product', 'Qty', 'Rate', 'Amount']]
    for i, item in enumerate(items, 1):
        item_data.append([str(i), item['Product Name'], str(item['Qty']), f"₹{item['Rate']:.2f}", f"₹{item['Amount']:.2f}"])
    
    item_table = Table(item_data, colWidths=[40, 200, 60, 80, 100])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOLD', (0, 0), (-1, 0), True),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 10))
    
    # Total section
    total_style = ParagraphStyle(
        'TotalStyle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_RIGHT
    )
    elements.append(Paragraph(f"<b>Total Amount:</b> ₹{total:,.2f}", total_style))
    elements.append(Paragraph(f"<b>Amount Received:</b> ₹{received:,.2f}", total_style))
    elements.append(Paragraph(f"<b>Balance:</b> ₹{balance:,.2f}", total_style))
    elements.append(Spacer(1, 20))
    
    # Footer
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    elements.append(Paragraph("Thank you for your business!", footer_style))
    elements.append(Paragraph("This is a system generated invoice", footer_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==================== EXCEL EXPORT ====================

def export_to_excel(dataframes, filename):
    """Export dataframes to Excel"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dataframes.items():
            if not df.empty:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output

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
        ["📊 Dashboard", "📦 Product Master", "🏪 Party Master", "🧾 Sales Billing", 
         "💵 Receipt Entry", "🔄 Sales Return", "📒 Party Statement", 
         "📈 Reports", "⚙️ Settings"]
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
        sales = get_data(service, 'Sales') if service else pd.DataFrame()
        receipts = get_data(service, 'Receipts') if service else pd.DataFrame()
        parties = get_parties(service) if service else pd.DataFrame()
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Today's Sales
        today = datetime.now().strftime("%Y-%m-%d")
        if not sales.empty:
            today_sales = sales[sales['Date'].str.startswith(today)]
            today_sales_amount = today_sales['Total Amount'].astype(float).sum() if not today_sales.empty else 0
        else:
            today_sales_amount = 0
        col1.metric("Today's Sales", f"₹{today_sales_amount:,.2f}")
        
        # Today's Receipts
        if not receipts.empty:
            today_receipts = receipts[receipts['Date'].str.startswith(today)]
            today_receipts_amount = today_receipts['Amount'].astype(float).sum() if not today_receipts.empty else 0
        else:
            today_receipts_amount = 0
        col2.metric("Today's Receipts", f"₹{today_receipts_amount:,.2f}")
        
        # Total Outstanding
        if not sales.empty:
            outstanding = 0
            for _, row in sales.iterrows():
                if 'Status' in row and row['Status'] != 'Paid':
                    outstanding += float(row['Total Amount'])
            col3.metric("Total Outstanding", f"₹{outstanding:,.2f}", delta="Due")
        else:
            col3.metric("Total Outstanding", "₹0.00")
        
        # Total Parties
        col4.metric("Total Parties", len(parties))
        
        st.markdown("---")
        
        # Recent Sales
        st.subheader("📄 Recent Sales")
        if not sales.empty:
            recent = sales.tail(10)[['Invoice No', 'Date', 'Party Name', 'Total Amount', 'Status']]
            st.dataframe(recent, use_container_width=True, hide_index=True)
        else:
            st.info("No sales yet")

    # ==================== PRODUCT MASTER ====================
    elif menu == "📦 Product Master":
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
                    product_names = products['Product Name'].tolist()
                    selected = st.selectbox("Select Product", product_names)
                with col2:
                    change = st.number_input("Quantity Change (+/-)", value=0.0, step=1.0)
                with col3:
                    if st.button("Update Stock"):
                        if change != 0:
                            product = products[products['Product Name'] == selected].iloc[0]
                            if update_stock(service, product['Product ID'], change):
                                st.success(f"Stock updated! {selected}: {change}")
                                st.rerun()
            else:
                st.info("No products available")
        
        with tab2:
            with st.form("add_product"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Product Name *")
                    rate = st.number_input("Rate (₹) *", min_value=0.0, step=1.0)
                    stock = st.number_input("Stock Quantity *", min_value=0.0, step=1.0)
                with col2:
                    brand = st.text_input("Brand")
                    unit = st.selectbox("Unit", ["Pcs", "Kg", "Ltr", "Pack", "Box"])
                
                if st.form_submit_button("Add Product"):
                    if name and rate > 0:
                        product_id = get_next_id(service, 'Products', 'Product ID')
                        new_row = [product_id, name, str(rate), str(stock), brand, unit]
                        add_row(service, 'Products', new_row)
                        st.success(f"Product '{name}' added!")
                        st.rerun()

    # ==================== PARTY MASTER ====================
    elif menu == "🏪 Party Master":
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
                col1, col2 = st.columns(2)
                with col1:
                    party_name = st.text_input("Party Name *")
                    shop_name = st.text_input("Shop Name *")
                    mobile = st.text_input("Mobile Number")
                with col2:
                    address = st.text_area("Address")
                    opening_balance = st.number_input("Opening Balance (₹)", min_value=0.0, step=100.0)
                
                if st.form_submit_button("Add Party"):
                    if party_name and shop_name:
                        add_party(service, party_name, shop_name, mobile, address, opening_balance)
                        st.success(f"Party '{party_name}' added!")
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
            parties = get_parties(service)
            
            if products.empty:
                st.warning("No products available!")
            else:
                product_names = products['Product Name'].tolist()
                selected = st.selectbox("Select Product", product_names)
                
                if selected:
                    product = products[products['Product Name'] == selected].iloc[0]
                    stock = float(product['Stock'])
                    rate = float(product['Rate'])
                    product_id = product['Product ID']
                    st.info(f"📦 Stock: {stock} | Rate: ₹{rate:,.2f}")
                    
                    col_qty, col_add = st.columns([2, 1])
                    with col_qty:
                        qty = st.number_input("Quantity", min_value=0.0, max_value=stock, step=1.0)
                    with col_add:
                        if st.button("➕ Add to Cart"):
                            if qty > 0:
                                st.session_state.cart.append({
                                    'Product ID': product_id,
                                    'Product Name': selected,
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
                st.dataframe(cart_df[['Product Name', 'Qty', 'Rate', 'Amount']], use_container_width=True)
                total = cart_df['Amount'].sum()
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
                party_name = st.selectbox("Party", parties['Party Name'].tolist())
            with col2:
                received = st.number_input("Amount Received (₹)", min_value=0.0, step=100.0)
            with col3:
                if st.button("💳 Generate Invoice", type="primary"):
                    if not st.session_state.cart:
                        st.error("Cart is empty!")
                    else:
                        party = parties[parties['Party Name'] == party_name].iloc[0]
                        party_id = party['Party ID']
                        
                        invoice_no, total = create_invoice(service, party_id, party_name, st.session_state.cart)
                        
                        if invoice_no:
                            balance = total - received
                            
                            # Record receipt if any amount received
                            if received > 0:
                                add_receipt(service, party_id, invoice_no, received, "Cash")
                            
                            st.success(f"Invoice {invoice_no} generated!")
                            
                            # Show invoice preview
                            with st.expander("📄 Invoice Preview"):
                                st.write(f"**Invoice No:** {invoice_no}")
                                st.write(f"**Party:** {party_name}")
                                st.write(f"**Date:** {datetime.now().strftime('%d-%m-%Y %H:%M')}")
                                st.write("---")
                                items_df = pd.DataFrame(st.session_state.cart)
                                st.dataframe(items_df[['Product Name', 'Qty', 'Rate', 'Amount']], 
                                           use_container_width=True)
                                st.write("---")
                                st.write(f"**Total:** ₹{total:,.2f}")
                                st.write(f"**Received:** ₹{received:,.2f}")
                                st.write(f"**Balance:** ₹{balance:,.2f}")
                            
                            # PDF Download
                            pdf_buffer = generate_invoice_pdf(
                                invoice_no, party_name, party.get('Address', ''), 
                                party.get('Mobile', ''), st.session_state.cart, 
                                total, received, balance
                            )
                            st.download_button(
                                "📥 Download PDF Invoice",
                                pdf_buffer,
                                f"{invoice_no}.pdf",
                                "application/pdf"
                            )
                            
                            st.session_state.cart = []

    # ==================== RECEIPT ENTRY ====================
    elif menu == "💵 Receipt Entry":
        st.header("💵 Receipt Entry")
        
        if not service:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        parties = get_parties(service)
        sales = get_data(service, 'Sales')
        
        if parties.empty:
            st.warning("No parties available!")
        else:
            party_name = st.selectbox("Select Party", parties['Party Name'].tolist())
            
            if party_name:
                party = parties[parties['Party Name'] == party_name].iloc[0]
                party_id = party['Party ID']
                
                # Get unpaid invoices for this party
                party_sales = sales[sales['Party ID'] == party_id] if not sales.empty else pd.DataFrame()
                unpaid_invoices = party_sales[party_sales['Status'] != 'Paid'] if not party_sales.empty else pd.DataFrame()
                
                if not unpaid_invoices.empty:
                    st.dataframe(unpaid_invoices[['Invoice No', 'Date', 'Total Amount', 'Status']], 
                               use_container_width=True)
                    
                    invoice_no = st.selectbox("Select Invoice", unpaid_invoices['Invoice No'].tolist())
                    
                    if invoice_no:
                        invoice = unpaid_invoices[unpaid_invoices['Invoice No'] == invoice_no].iloc[0]
                        total = float(invoice['Total Amount'])
                        
                        # Get already received
                        receipts = get_data(service, 'Receipts')
                        received = receipts[receipts['Invoice No'] == invoice_no]['Amount'].astype(float).sum() if not receipts.empty else 0
                        outstanding = total - received
                        
                        st.info(f"Invoice Total: ₹{total:,.2f} | Received: ₹{received:,.2f} | Outstanding: ₹{outstanding:,.2f}")
                        
                        with st.form("receipt_form"):
                            col1, col2 = st.columns(2)
                            with col1:
                                amount = st.number_input("Receipt Amount (₹)", min_value=0.0, 
                                                        max_value=outstanding, step=100.0)
                            with col2:
                                payment_mode = st.selectbox("Payment Mode", ["Cash", "UPI", "Bank Transfer", "Cheque"])
                            remarks = st.text_area("Remarks")
                            
                            if st.form_submit_button("Record Receipt"):
                                if amount > 0:
                                    receipt_no = add_receipt(service, party_id, invoice_no, amount, payment_mode, remarks)
                                    if receipt_no:
                                        st.success(f"Receipt {receipt_no} recorded! Amount: ₹{amount:,.2f}")
                                        st.rerun()
                else:
                    st.info("No outstanding invoices for this party")

    # ==================== SALES RETURN ====================
    elif menu == "🔄 Sales Return":
        st.header("🔄 Sales Return")
        
        if not service:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        sales = get_data(service, 'Sales')
        items = get_data(service, 'Sales_Items')
        
        if sales.empty:
            st.warning("No sales to return!")
        else:
            invoice_no = st.selectbox("Select Invoice for Return", sales['Invoice No'].tolist())
            
            if invoice_no:
                invoice_items = items[items['Invoice No'] == invoice_no] if not items.empty else pd.DataFrame()
                
                if not invoice_items.empty:
                    st.dataframe(invoice_items[['Product Name', 'Qty', 'Rate', 'Amount']], 
                               use_container_width=True)
                    
                    with st.form("return_form"):
                        product_name = st.selectbox("Select Product", invoice_items['Product Name'].tolist())
                        
                        if product_name:
                            product_item = invoice_items[invoice_items['Product Name'] == product_name].iloc[0]
                            max_qty = float(product_item['Qty'])
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                qty_returned = st.number_input("Quantity to Return", min_value=0.0, 
                                                              max_value=max_qty, step=1.0)
                            with col2:
                                reason = st.text_area("Reason for Return")
                            
                            if st.form_submit_button("Process Return"):
                                if qty_returned > 0:
                                    rate = float(product_item['Rate'])
                                    amount = qty_returned * rate
                                    return_no = add_sales_return(service, invoice_no, product_name, qty_returned, amount, reason)
                                    if return_no:
                                        st.success(f"Return {return_no} processed! Amount adjusted: ₹{amount:,.2f}")
                                        st.rerun()

    # ==================== PARTY STATEMENT ====================
    elif menu == "📒 Party Statement":
        st.header("📒 Party Statement of Account")
        
        if not service:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        parties = get_parties(service)
        
        if parties.empty:
            st.warning("No parties available!")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                party_name = st.selectbox("Select Party", parties['Party Name'].tolist())
            with col2:
                from_date = st.date_input("From Date", datetime.now() - timedelta(days=30))
            with col3:
                to_date = st.date_input("To Date", datetime.now())
            
            if party_name:
                party = parties[parties['Party Name'] == party_name].iloc[0]
                party_id = party['Party ID']
                
                statement = get_party_statement(
                    service, party_id, 
                    from_date.strftime("%Y-%m-%d") if from_date else None,
                    to_date.strftime("%Y-%m-%d") if to_date else None
                )
                
                if not statement.empty:
                    st.dataframe(statement, use_container_width=True, hide_index=True)
                    
                    # Summary
                    col1, col2, col3 = st.columns(3)
                    total_sales = statement[statement['Debit'] > 0]['Debit'].sum()
                    total_receipts = statement[statement['Credit'] > 0]['Credit'].sum()
                    closing = float(statement.iloc[-1]['Balance']) if not statement.empty else 0
                    
                    col1.metric("Total Sales", f"₹{total_sales:,.2f}")
                    col2.metric("Total Receipts", f"₹{total_receipts:,.2f}")
                    col3.metric("Closing Balance", f"₹{closing:,.2f}", 
                              delta="Due" if closing > 0 else "Settled")

    # ==================== REPORTS ====================
    elif menu == "📈 Reports":
        st.header("📈 Reports")
        
        if not service:
            st.error("❌ Please connect to Google Sheets first!")
            st.stop()
        
        report_type = st.selectbox(
            "Select Report",
            ["Daily Sales Report", "Monthly Sales Report", "Product-wise Sales Report", 
             "Outstanding Report", "Receipt Against Invoice Report"]
        )
        
        sales = get_data(service, 'Sales')
        sales_items = get_data(service, 'Sales_Items')
        receipts = get_data(service, 'Receipts')
        parties = get_parties(service)
        
        if report_type == "Daily Sales Report":
            date = st.date_input("Select Date", datetime.now())
            date_str = date.strftime("%Y-%m-%d")
            
            daily_sales = sales[sales['Date'].str.startswith(date_str)] if not sales.empty else pd.DataFrame()
            
            if not daily_sales.empty:
                st.dataframe(daily_sales[['Invoice No', 'Party Name', 'Total Amount', 'Status']], 
                           use_container_width=True)
                total = daily_sales['Total Amount'].astype(float).sum()
                st.metric("Total Sales", f"₹{total:,.2f}")
                
                # Export
                if st.button("📥 Export to Excel"):
                    excel_data = {'Daily Sales': daily_sales}
                    excel_file = export_to_excel(excel_data, "daily_sales")
                    st.download_button("Download Excel", excel_file, "daily_sales.xlsx", 
                                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("No sales for this date")
        
        elif report_type == "Monthly Sales Report":
            month = st.selectbox("Select Month", range(1, 13), 
                               format_func=lambda x: datetime(2024, x, 1).strftime("%B"))
            year = st.number_input("Year", min_value=2020, max_value=2030, value=datetime.now().year)
            
            month_str = f"{year}-{month:02d}"
            monthly_sales = sales[sales['Date'].str.startswith(month_str)] if not sales.empty else pd.DataFrame()
            
            if not monthly_sales.empty:
                st.dataframe(monthly_sales[['Invoice No', 'Date', 'Party Name', 'Total Amount', 'Status']], 
                           use_container_width=True)
                total = monthly_sales['Total Amount'].astype(float).sum()
                st.metric("Total Sales", f"₹{total:,.2f}")
            else:
                st.info("No sales for this month")
        
        elif report_type == "Product-wise Sales Report":
            if not sales_items.empty:
                product_sales = sales_items.groupby('Product Name')[['Qty', 'Amount']].sum().reset_index()
                product_sales['Qty'] = product_sales['Qty'].astype(float)
                product_sales['Amount'] = product_sales['Amount'].astype(float)
                st.dataframe(product_sales, use_container_width=True)
                st.metric("Total Sales", f"₹{product_sales['Amount'].sum():,.2f}")
            else:
                st.info("No sales data available")
        
        elif report_type == "Outstanding Report":
            outstanding_data = []
            if not sales.empty:
                for _, row in sales.iterrows():
                    if row['Status'] != 'Paid':
                        total = float(row['Total Amount'])
                        invoice_no = row['Invoice No']
                        received = receipts[receipts['Invoice No'] == invoice_no]['Amount'].astype(float).sum() if not receipts.empty else 0
                        outstanding = total - received
                        outstanding_data.append({
                            'Party': row['Party Name'],
                            'Invoice No': invoice_no,
                            'Outstanding': outstanding
                        })
            
            if outstanding_data:
                df = pd.DataFrame(outstanding_data)
                st.dataframe(df, use_container_width=True)
                st.metric("Total Outstanding", f"₹{df['Outstanding'].sum():,.2f}")
            else:
                st.info("No outstanding dues")
        
        elif report_type == "Receipt Against Invoice Report":
            if not sales.empty and not receipts.empty:
                receipt_data = []
                for _, row in sales.iterrows():
                    invoice_no = row['Invoice No']
                    total = float(row['Total Amount'])
                    received = receipts[receipts['Invoice No'] == invoice_no]['Amount'].astype(float).sum() if not receipts.empty else 0
                    receipt_data.append({
                        'Invoice No': invoice_no,
                        'Invoice Amount': total,
                        'Received': received,
                        'Balance': total - received
                    })
                
                df = pd.DataFrame(receipt_data)
                st.dataframe(df, use_container_width=True)
                st.metric("Total Outstanding", f"₹{df['Balance'].sum():,.2f}")
            else:
                st.info("No data available")

    # ==================== SETTINGS ====================
    elif menu == "⚙️ Settings":
        st.header("⚙️ Settings")
        
        st.subheader("🔐 Connection Status")
        if service:
            st.success("✅ Connected to Google Sheets")
            st.info("📊 Spreadsheet ID: 1jaat8u_k7rQyqhPcdL4zmUkkuG8gpwwk6z-Tvv2SMrQ")
            st.info("🔑 Service Account: detergent-billing@detergent-billing.iam.gserviceaccount.com")
        else:
            st.error("❌ Not connected")
        
        st.subheader("📦 Products")
        products = get_products(service) if service else pd.DataFrame()
        if not products.empty:
            st.dataframe(products, use_container_width=True)
        
        st.subheader("📋 Data Sheets")
        st.write("""
        - **Products** - Product master data
        - **Parties** - Customer/party master data
        - **Sales** - Invoice header data
        - **Sales_Items** - Invoice line items
        - **Receipts** - Payment receipts
        - **Sales_Return** - Sales returns
        """)

# ==================== RUN ====================

if __name__ == "__main__":
    main()
