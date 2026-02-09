import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from PIL import Image
import json
import plotly.express as px

# 1. Page Config
st.set_page_config(page_title="Yen Tracker Pro", page_icon="¥", layout="wide")

# 2. Connections Setup
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds_dict = st.secrets["connections"]["gsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# 3. Open Sheets (REPLACE SHEET_ID WITH YOURS)
SHEET_ID = "1L_0iJOrN-nMxjX5zjNm2yUnUyck9RlUqeg2rnXvpAlU" 
sh = client.open_by_key(SHEET_ID)
expense_ws = sh.get_worksheet(0)
settings_ws = sh.worksheet("Settings")

# 4. Initialize Variables & Budget
try:
    budget_val = settings_ws.acell('B1').value
    monthly_budget = int(str(budget_val).replace(',', '')) if budget_val else 300000
except:
    monthly_budget = 300000

# --- DATA FETCHING (Done early for filters) ---
raw_data = expense_ws.get_all_records()
df = pd.DataFrame(raw_data)

if not df.empty:
    df.columns = [str(c).strip() for c in df.columns]
    # Use 'mixed' to handle the apostrophe-text vs date objects
    df['Date'] = pd.to_datetime(df['Date'], format='mixed', errors='coerce')
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    df = df.dropna(subset=['Date'])
    df = df.sort_values('Date')

# --- SIDEBAR (Filters & Maintenance) ---
with st.sidebar:
    st.header("Settings & Filters")
    
    # Salary Update
    new_budget = st.number_input("Monthly Salary (¥)", value=int(monthly_budget), step=10000)
    if st.button("Update Salary"):
        settings_ws.update_acell('B1', new_budget)
        st.success("Salary updated!")
        st.rerun()

    st.divider()

    # Advanced Filters
    if not df.empty:
        st.subheader("Chart Filters")
        min_date = df['Date'].min().date()
        max_date = df['Date'].max().date()
        selected_range = st.date_input("Select Date Range", value=(min_date, max_date))
        
        all_cats = sorted(df['Category'].unique().tolist())
        selected_cats = st.multiselect("Filter by Category", options=all_cats, default=all_cats)
        
        # Apply Filters to the main DF used by charts
        if len(selected_range) == 2:
            start, end = selected_range
            df = df[(df['Date'].dt.date >= start) & (df['Date'].dt.date <= end)]
        df = df[df['Category'].isin(selected_cats)]
    
    st.divider()

    # Maintenance Button (The Apostrophe Killer)
    if st.button("🧹 Clean & Standardize Sheet"):
        with st.spinner("Standardizing dates and removing apostrophes..."):
            all_data = expense_ws.get_all_records()
            if all_data:
                clean_df = pd.DataFrame(all_data)
                clean_df['Date'] = pd.to_datetime(clean_df['Date'], format='mixed', errors='coerce')
                clean_df = clean_df.dropna(subset=['Date'])
                clean_df['Date'] = clean_df['Date'].dt.strftime('%Y-%m-%d')
                clean_df['Amount'] = pd.to_numeric(clean_df['Amount'], errors='coerce').fillna(0).astype(int)
                
                updated_rows = [clean_df.columns.values.tolist()] + clean_df.values.tolist()
                expense_ws.clear()
                # value_input_option='USER_ENTERED' removes the ' marks in the formula bar
                expense_ws.update(range_name='A1', values=updated_rows, value_input_option='USER_ENTERED')
                st.success("Sheet cleaned!")
                st.rerun()

st.title("Bond Finances")

# --- SECTION 1: AI SCANNER ---
suggested_item, suggested_amount, suggested_cat = "", 0, "Food 🍱"

with st.expander("📸 Scan Receipt with AI"):
    uploaded_file = st.camera_input("Take a photo")
    if uploaded_file:
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            img = Image.open(uploaded_file)
            img.thumbnail((800, 800))
            
            with st.spinner("AI reading..."):
                prompt = "Return JSON: {'item': str, 'amount': int, 'category': str}"
                response = model.generate_content([prompt, img])
                raw_json = response.text.replace('```json', '').replace('```', '').strip()
                ai_data = json.loads(raw_json)
                suggested_item = ai_data.get('item', "")
                suggested_amount = ai_data.get('amount', 0)
                suggested_cat = ai_data.get('category', "Food 🍱")
                st.success(f"AI Found: {suggested_item}")
        except Exception as e:
            st.warning("Scanner connection busy.")

# --- SECTION 2: ADD EXPENSE FORM ---
with st.form("expense_form", clear_on_submit=True):
    st.subheader("Add New Expense")
    col_a, col_b = st.columns(2)
    with col_a:
        item = st.text_input("Item Name", value=suggested_item)
        amount = st.number_input("Amount (¥)", min_value=0, value=int(suggested_amount), step=1)
        description = st.text_input("Description (Optional)")
    with col_b:
        categories = ["Food 🍱", "Transport 🚆", "Shopping 🛍️", "Sightseeing 🏯", "Mortgage 🏠", "Car 🚗", "Water 💧", "Electricity ⚡", "Pet stuff 🐾", "Gifts 🎁"]
        idx = categories.index(suggested_cat) if suggested_cat in categories else 0
        category = st.selectbox("Category", categories, index=idx)
        date = st.date_input("Date")
    
    if st.form_submit_button("Save to Google Sheets"):
        if item and amount > 0:
            # Format date as string to prevent Sheets formatting issues
            expense_ws.append_row([date.strftime("%Y-%m-%d"), item, amount, category, description])
            st.success(f"Saved: {item}")
            st.rerun()

# --- SECTION 3: DASHBOARD & GRAPHS ---
if not df.empty:
    # Metrics
    current_month = pd.Timestamp.now().to_period('M')
    df['MonthYear'] = df['Date'].dt.to_period('M')
    curr_month_df = df[df['MonthYear'] == current_month]
    
    monthly_total = curr_month_df['Amount'].sum()
    remaining = monthly_budget - monthly_total
    percent_spent = min(max(monthly_total / monthly_budget, 0.0), 1.0)

    st.divider()
    m1, m2 = st.columns(2)
    m1.metric("Spent This Month", f"¥{int(monthly_total):,}")
    m2.metric("Remaining Salary", f"¥{int(remaining):,}", delta=f"{(remaining/monthly_budget)*100:.1f}% budget used", delta_color="inverse")
    st.progress(percent_spent)
import calendar
from datetime import datetime
    
    now = datetime.now()
    # Get last day of current month (e.g., 28 for Feb 2026)
    last_day = calendar.monthrange(now.year, now.month)[1]
    days_left = last_day - now.day + 1
    
    st.divider()
    m1, m2, m3 = st.columns(3) # Changed to 3 columns
    m1.metric("Spent This Month", f"¥{int(monthly_total):,}")
    m2.metric("Remaining Salary", f"¥{int(remaining):,}")
    
    if remaining > 0:
        daily_allowance = remaining / days_left
        m3.metric("Daily Allowance", f"¥{int(daily_allowance):,}")
        st.write(f"💡 *You have **{days_left}** days left this month.*")
    else:
        m3.metric("Daily Allowance", "¥0", delta="- Over Budget", delta_color="inverse")
    
    st.progress(percent_spent)
    # --------------------------
    # Charts
    st.write("### Spending Analysis")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        trend_df = df.groupby(df['Date'].dt.strftime('%Y-%m'))['Amount'].sum().reset_index()
        trend_df.columns = ['Month', 'Total Amount']
        fig_bar = px.bar(trend_df, x='Month', y='Total Amount', title="Monthly Spending History", color_discrete_sequence=['#ff4b4b'])
        fig_bar.add_hline(y=monthly_budget, line_dash="dot", line_color="green", annotation_text="Budget Limit")
        st.plotly_chart(fig_bar, use_container_width=True)

    with chart_col2:
        if not curr_month_df.empty:
            cat_df = curr_month_df.groupby('Category')['Amount'].sum().reset_index()
            fig_pie = px.pie(cat_df, values='Amount', names='Category', title=f"Category Breakdown ({current_month})", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No data for the current month matches the filters.")

    with st.expander("View Recent History"):
        history_view = df[['Date', 'Item', 'Amount', 'Category', 'Description']].iloc[::-1].copy()
        history_view['Date'] = history_view['Date'].dt.strftime('%Y-%m-%d')
        st.dataframe(history_view.head(15), hide_index=True, use_container_width=True)
else:
    st.info("No data found. Ensure your Sheet has headers: Date, Item, Amount, Category, Description")





































































