import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# 1. Setup Connection
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds_dict = st.secrets["connections"]["gsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# 2. Open the Sheet (Use your Sheet ID here)
SHEET_ID = "1L_0iJOrN-nMxjX5zjNm2yUnUyck9RlUqeg2rnXvpAlU"
sh = client.open_by_key(SHEET_ID)
worksheet = sh.get_worksheet(0)

st.title("Bond Finance Tracker")

# --- ADD EXPENSE FORM ---
with st.form("expense_form"):
    st.subheader("Add New Expense")
    item = st.text_input("Item Name")
    amount = st.number_input("Amount (¥)", min_value=0, step=1)
    date = st.date_input("Date")
    
    submit = st.form_submit_button("Save to Google Sheets")
    
    if submit:
        if item:
            # Add the row to the bottom of the sheet
            worksheet.append_row([str(date), item, amount])
            st.success(f"Added ¥{amount} for {item}!")
        else:
            st.error("Please enter an item name.")

# --- VIEW DATA ---
st.divider()
st.subheader("Recent Expenses")
data = worksheet.get_all_records()
df = pd.DataFrame(data)
st.dataframe(df)








