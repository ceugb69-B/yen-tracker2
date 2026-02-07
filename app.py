import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
st.set_page_config(
    page_title="Yen Tracker",
    page_icon="¥",
    layout="centered", # Better for narrow phone screens
    initial_sidebar_state="collapsed"
)

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
    category = st.selectbox("Category", [
    "Food 🍱", 
    "Transport 🚆", 
    "Shopping 🛍️", 
    "Sightseeing 🏯",
    "Mortgage 🏠", 
    "Car 🚗", 
    "Water 💧", 
    "Electricity ⚡", 
    "Car Insurance 🛡️", 
    "Motorcycle Insurance 🏍️", 
    "Pet stuff 🐾", 
    "Gifts 🎁"
])
    amount = st.number_input("Amount (¥)", min_value=0, step=1, format="%d")
    date = st.date_input("Date")
    
    submit = st.form_submit_button("Save to Google Sheets")
    
# Updated append_row to include the category
if submit:
    if item:
        worksheet.append_row([str(date), item, category, amount])
        st.success(f"Added ¥{amount} for {item}!")
    else:
            st.error("Please enter an item name.")

# --- CALCULATIONS ---
df['Date'] = pd.to_datetime(df['Date'])
df['Month'] = df['Date'].dt.to_period('M')

# Get current month and last month
current_month = pd.Timestamp.now().to_period('M')
last_month = (pd.Timestamp.now() - pd.offsets.MonthBegin(1)).to_period('M')

# Calculate totals
monthly_total = df[df['Month'] == current_month]['Amount'].sum()
last_month_total = df[df['Month'] == last_month]['Amount'].sum()

# SET YOUR BUDGET HERE (e.g., 300,000 Yen)
MONTHLY_BUDGET = 300000 
remaining = MONTHLY_BUDGET - monthly_total

# --- DASHBOARD METRICS ---
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Spent This Month", f"¥{monthly_total:,}")

with col2:
    # This shows the "Month on Month" difference
    delta = monthly_total - last_month_total
    st.metric("vs. Last Month", f"¥{delta:,}", delta_color="inverse")

with col3:
    st.metric("Budget Remaining", f"¥{remaining:,}", delta=f"Budget: ¥{MONTHLY_BUDGET:,}")

# --- MONTHLY BREAKDOWN TABLE ---
st.subheader("Monthly Summary")
monthly_summary = df.groupby('Month')['Amount'].sum().reset_index()
monthly_summary['Month'] = monthly_summary['Month'].astype(str)
st.bar_chart(monthly_summary.set_index('Month'))













