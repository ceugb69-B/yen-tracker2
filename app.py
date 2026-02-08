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

# 4. Initialize AI Variables
suggested_item = ""
suggested_amount = 0
suggested_cat = "Food 🍱"

# 5. Get Salary from Settings Tab
try:
    budget_val = settings_ws.acell('B1').value
    monthly_budget = int(str(budget_val).replace(',', '')) if budget_val else 300000
except:
    monthly_budget = 300000

st.title("Bond Finances")

# --- SECTION 1: AI SCANNER ---
with st.expander("📸 Scan Receipt with AI"):
    uploaded_file = st.camera_input("Take a photo")
    if uploaded_file:
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# We use the 'gemini-pro-vision' name as a fallback 
# OR the strictly formatted string below:
    try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    model = genai.GenerativeModel('gemini-pro-vision')
            
            # SURGERY: Open and resize the image to reduce data load
            img = Image.open(uploaded_file)
            max_size = (800, 800)
            img.thumbnail(max_size) # Shrinks image if it's huge
            
            with st.spinner("AI analyzing..."):
                # Simplified prompt to reduce processing time
                prompt = "Return JSON only: {'item': str, 'amount': int, 'category': str}. Categories: Food 🍱, Transport 🚆, Shopping 🛍️, Sightseeing 🏯, Mortgage 🏠, Car 🚗, Water 💧, Electricity ⚡, Car Insurance 🛡️, Motorcycle Insurance 🏍️, Pet stuff 🐾, Gifts 🎁"
                
                # The actual API call
                response = model.generate_content([prompt, img])
                
                # Clean and parse
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                ai_data = json.loads(clean_json)
                
                suggested_item = ai_data.get('item', "")
                suggested_amount = ai_data.get('amount', 0)
                suggested_cat = ai_data.get('category', "Food 🍱")
                
                st.success(f"Found: {suggested_item} (¥{suggested_amount})")
        except Exception as e:
            st.warning("Scanner connection busy. Please try manual entry or take the photo again.")
            # This prints the actual error to your Streamlit logs so you can see it later
            print(f"DEBUG AI ERROR: {e}")

# --- SECTION 2: ADD EXPENSE FORM ---
with st.form("expense_form", clear_on_submit=True):
    st.subheader("Add New Expense")
    col_a, col_b = st.columns(2)
    with col_a:
        item = st.text_input("Item Name", value=suggested_item)
        amount = st.number_input("Amount (¥)", min_value=0, value=int(suggested_amount), step=1)
        description = st.text_input("Description (Optional)", placeholder="e.g. Weekly groceries")
    with col_b:
        categories = ["Food 🍱", "Transport 🚆", "Shopping 🛍️", "Sightseeing 🏯",
                      "Mortgage 🏠", "Car 🚗", "Water 💧", "Electricity ⚡", 
                      "Car Insurance 🛡️", "Motorcycle Insurance 🏍️", "Pet stuff 🐾", "Gifts 🎁"]
        # Match AI category if found
        idx = categories.index(suggested_cat) if suggested_cat in categories else 0
        category = st.selectbox("Category", categories, index=idx)
        date = st.date_input("Date")
    
    submit = st.form_submit_button("Save to Google Sheets")
    
    if submit:
        if item and amount > 0:
            # SAVING ORDER: Date, Item, Amount, Category, Description
            expense_ws.append_row([str(date), item, amount, category, description])
            st.success(f"Saved: {item}")
            st.rerun()

# --- SECTION 3: DASHBOARD & GRAPHS ---
# Fetch all data from Sheet
raw_data = expense_ws.get_all_records()

if raw_data:
    df = pd.DataFrame(raw_data)
    # Clean up column names (removes hidden spaces)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Force correct data types
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    
    # Drop rows that are missing core data
    df = df.dropna(subset=['Date', 'Amount'])

    if not df.empty:
        # Sort for proper chronological graphing
        df = df.sort_values('Date')
        
        # Calculate Monthly Metrics
        current_month = pd.Timestamp.now().to_period('M')
        df['MonthYear'] = df['Date'].dt.to_period('M')
        curr_month_df = df[df['MonthYear'] == current_month]
        
        monthly_total = curr_month_df['Amount'].sum()
        remaining = monthly_budget - monthly_total
        percent_spent = min(max(monthly_total / monthly_budget, 0.0), 1.0)

        # Display Metrics
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Spent This Month", f"¥{int(monthly_total):,}")
        m2.metric("Remaining Salary", f"¥{int(remaining):,}", 
                  delta=f"{(remaining/monthly_budget)*100:.1f}% budget used", delta_color="inverse")
        st.progress(percent_spent)

        # --- CHARTS ---
        st.write("### Spending Analysis")
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            # Bar Chart: Historical spending per month
            trend_df = df.groupby(df['Date'].dt.strftime('%Y-%m'))['Amount'].sum().reset_index()
            trend_df.columns = ['Month', 'Total Amount']
            fig_bar = px.bar(trend_df, x='Month', y='Total Amount', 
                             title="Monthly Spending History", 
                             color_discrete_sequence=['#ff4b4b'])
            # Add the Salary Line
            fig_bar.add_hline(y=monthly_budget, line_dash="dot", line_color="green", annotation_text="Budget Limit")
            st.plotly_chart(fig_bar, use_container_width=True)

        with chart_col2:
            # Pie Chart: Current month categories
            if not curr_month_df.empty:
                cat_df = curr_month_df.groupby('Category')['Amount'].sum().reset_index()
                fig_pie = px.pie(cat_df, values='Amount', names='Category', 
                                 title=f"Category Breakdown ({current_month})", 
                                 hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No data for the current month yet.")

        # --- HISTORY TABLE ---
        with st.expander("View Recent History"):
            # Show the full 5 columns in reverse order
            history_view = df[['Date', 'Item', 'Amount', 'Category', 'Description']].iloc[::-1].copy()
            history_view['Date'] = history_view['Date'].dt.strftime('%Y-%m-%d')
            st.dataframe(history_view.head(15), hide_index=True, use_container_width=True)
else:
    st.info("No data found. Add your first expense above!")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    new_budget = st.number_input("Monthly Salary (¥)", value=int(monthly_budget), step=10000)
    if st.button("Update Salary"):
        settings_ws.update_acell('B1', new_budget)
        st.success("Salary updated!")
        st.rerun()
if st.button("Test AI Connection"):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Say 'System Online'")
        st.write(response.text)
    except Exception as e:
        st.error(f"Test Failed: {e}")



















































