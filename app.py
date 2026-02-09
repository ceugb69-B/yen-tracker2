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
# --- 1. AI SCANNER (Self-Contained) ---
with st.expander("📸 Scan Receipt with AI"):
    uploaded_file = st.camera_input("Take a photo")
    if uploaded_file:
        ai_success = False
        try: # THIS TRY...
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
                ai_success = True
                st.success(f"AI Found: {suggested_item}")
        except Exception as e: # ...MUST BE CLOSED BY THIS EXCEPT IMMEDIATELY
            st.warning("Scanner connection busy.")
            print(f"AI Error: {e}")

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
    
    # 1. Clean up column names (removes hidden spaces/case sensitivity)
    df.columns = [str(c).strip() for c in df.columns]
    
    # 2. Safety Check: Ensure 'Amount' exists before processing
    if 'Amount' in df.columns:
        # Force correct data types
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce', infer_datetime_format=True)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        
        # Drop rows that are missing core data (like empty rows at the bottom)
        df = df.dropna(subset=['Date', 'Amount'])

        if not df.empty:
            # Sort for proper chronological graphing
            df = df.sort_values('Date')
            
            # ... [The rest of your chart logic remains the same] ...
            
            # --- HISTORY TABLE ---
            with st.expander("View Recent History"):
                # Dynamically select columns that actually exist to avoid KeyErrors
                cols_to_show = [c for c in ['Date', 'Item', 'Amount', 'Category', 'Description'] if c in df.columns]
                history_view = df[cols_to_show].iloc[::-1].copy()
                history_view['Date'] = history_view['Date'].dt.strftime('%Y-%m-%d')
                st.dataframe(history_view.head(15), hide_index=True, use_container_width=True)
    else:
        st.error("Column 'Amount' not found. Please check your Google Sheet headers.")
else:
    st.info("No data found. Add your first expense above!")





























































