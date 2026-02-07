import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# 1. Page Config for iPhone
st.set_page_config(page_title="Bond's Finance Tracker", page_icon="¥", layout="centered")

# 2. Setup Connection
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds_dict = st.secrets["connections"]["gsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# 3. Open the Sheet (Make sure your ID is correct below)
SHEET_ID = "1L_0iJOrN-nMxjX5zjNm2yUnUyck9RlUqeg2rnXvpAlU" 
sh = client.open_by_key(SHEET_ID)
expense_ws = sh.get_worksheet(0) # Targets the first tab (Sheet1)
settings_ws = sh.worksheet("Settings") # Targets the Settings tab

# 4. Get Budget from Settings Tab (Cell B1)
try:
    budget_val = settings_ws.acell('B1').value
    monthly_budget = int(budget_val.replace(',', '')) if budget_val else 300000
except:
    monthly_budget = 300000

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("Budget Settings")
    new_budget = st.number_input("Monthly Limit (¥)", value=monthly_budget, step=10000)
    if st.button("Save New Budget"):
        settings_ws.update_acell('B1', new_budget)
        st.success("Budget Saved!")
        st.rerun()

st.title("¥ Bond Finances ¥")

# --- ADD EXPENSE FORM ---
with st.form("expense_form", clear_on_submit=True):
    st.subheader("Add New Expense")
    item = st.text_input("Item Name")
    amount = st.number_input("Amount (¥)", min_value=0, step=1, format="%d")
    category = st.selectbox("Category", [
        "Food 🍱", "Transport 🚆", "Shopping 🛍️", "Sightseeing 🏯",
        "Mortgage 🏠", "Car 🚗", "Water 💧", "Electricity ⚡", 
        "Car Insurance 🛡️", "Motorcycle Insurance 🏍️", "Pet stuff 🐾", "Gifts 🎁"
    ])
    date = st.date_input("Date")
    
    submit = st.form_submit_button("Save to Google Sheets")
    
    if submit:
        if item and amount > 0:
            # Append row to Sheet1: Date, Item, Category, Amount
            expense_ws.append_row([str(date), item, category, amount])
            st.success(f"Saved: {item} for ¥{amount:,}")
            st.rerun()
        else:
            st.error("Please enter both an item and an amount.")

# --- DATA PROCESSING & DASHBOARD ---
data = expense_ws.get_all_records()

if data:
    df = pd.DataFrame(data)
    # Clean up any messy data
    df.columns = df.columns.str.strip()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    df = df.dropna(subset=['Date', 'Amount'])

    if not df.empty:
        # Calculate Current Month Spending
        current_month = pd.Timestamp.now().to_period('M')
        df['MonthYear'] = df['Date'].dt.to_period('M')
        
        monthly_total = df[df['MonthYear'] == current_month]['Amount'].sum()
        remaining = new_budget - monthly_total

        # --- DISPLAY METRICS ---
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Spent (This Month)", f"¥{int(monthly_total):,}")
        
        # Calculate Delta and Color
        remaining_pct = (remaining / new_budget) * 100 if new_budget > 0 else 0
        m2.metric(
            "Remaining", 
            f"¥{int(remaining):,}", 
            delta=f"{remaining_pct:.1f}% left",
            delta_color="normal" if remaining > 0 else "inverse"
        )
        
        # Progress Bar visual
        st.progress(min(max(monthly_total / new_budget, 0.0), 1.0) if new_budget > 0 else 0.0)

        # Show History
        st.subheader("Recent Expenses")
        st.dataframe(
            df[['Date', 'Item', 'Category', 'Amount']].iloc[::-1].head(15), 
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No data found. Start by adding an expense above!")






















