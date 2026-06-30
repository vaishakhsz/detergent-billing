"""
Test Google Sheets Connection
Run this first to check if everything is working
"""

import streamlit as st
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(page_title="Test Connection", layout="wide")

st.title("🔌 Google Sheets Connection Test")

# Check secrets
st.subheader("1. Checking Secrets")

if 'google_sheets' in st.secrets:
    st.success("✅ Secrets found!")
    st.write("Secrets keys:", list(st.secrets['google_sheets'].keys()))
else:
    st.error("❌ No secrets found!")

# Try to connect
st.subheader("2. Trying to Connect")

try:
    creds_dict = dict(st.secrets['google_sheets'])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    st.success("✅ Connected to Google Sheets API!")
except Exception as e:
    st.error(f"❌ Connection failed: {str(e)}")

# Try to open spreadsheet
st.subheader("3. Trying to Open Spreadsheet")

try:
    sheet_id = "1jaat8u_k7rQyqhPcdL4zmUkkuG8gpwwk6z-Tvv2SMrQ"
    result = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    st.success(f"✅ Spreadsheet found: {result.get('properties', {}).get('title', 'Unknown')}")
except Exception as e:
    st.error(f"❌ Can't open spreadsheet: {str(e)}")
    st.info("💡 Make sure you've shared the sheet with: detergent-billing@detergent-billing.iam.gserviceaccount.com")

# Try to read data
st.subheader("4. Trying to Read Data")

try:
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range="Parties!A:Z"
    ).execute()
    values = result.get('values', [])
    st.success(f"✅ Read {len(values)} rows from Parties sheet")
    if values:
        st.write("Headers:", values[0] if values else "No headers")
    else:
        st.info("Parties sheet is empty")
except Exception as e:
    st.error(f"❌ Can't read data: {str(e)}")

# Try to write data
st.subheader("5. Trying to Write Data (Test)")

try:
    test_data = ['TEST001', 'Test Party', '9999999999', '9999999999', 'Test Address', '0', 'TESTGST']
    body = {'values': [test_data]}
    result = service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range="Parties!A:Z",
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    st.success("✅ Successfully wrote test data to Parties sheet!")
    st.write("Check your Google Sheet - you should see 'Test Party'")
except Exception as e:
    st.error(f"❌ Can't write data: {str(e)}")
    st.info("💡 Make sure the sheet is shared with EDITOR permission")

st.markdown("---")
st.info("If any step failed, check the error message above and fix that issue first.")
