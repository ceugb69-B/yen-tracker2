import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from PIL import Image
import json

# 1. Page Config
st.set_page_config(page_title="Yen Tracker Pro", page_icon="¥", layout="centered")

# 2. Connections
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds_dict = st.secrets["connections"]["gsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# 3. Open Sheets
SHEET_ID = "1L_0iJOrN-nMxjX5zjNm2yUnUyck9RlUqeg2rnXvpAlU" # <--- RE-PASTE YOUR SHEET ID HERE
sh = client.open_by_key(SHEET_ID)
expense_ws = sh.get_worksheet(0)
settings_ws = sh.worksheet("Settings")

# 4. Get Budget
try:
    budget_val = settings_ws.acell('B1').value
    monthly_budget = int(budget_val.replace(',', '')) if budget_val else 300000
except:
    monthly_budget = 300000
# ... setup code ...

## --- INITIALIZE VARIABLES ---
suggested_item = ""
suggested_amount = 0
suggested_cat = "Food 🍱"

st.title("Bond Finances")

# --- AI SCANNER ---
with st.expander("📸 Scan Receipt with AI"):
    uploaded_file = st.camera_input("Take a photo")
    if uploaded_file:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        img = Image.open(uploaded_file)
        
        with st.spinner("AI reading receipt..."):
            prompt = "Analyze this receipt. Return ONLY JSON: {'item': 'name', 'amount': int, 'category': 'match'}"
            response = model.generate_content([prompt, img])
            try:
                raw_text = response.text.strip().replace('```json', '').replace('```', '')
                ai_data = json.loads(raw_text)
                suggested_item = ai_data.get('item', "")
                suggested_amount = ai_data.get('amount', 0)
                suggested_cat = ai_data.get('category', "Food 🍱")
            except:
                st.error("AI parse error.")

# --- ADD EXPENSE FORM (Aligned to the left wall!) ---
with st.form("expense_form", clear_on_submit=True):
    st.subheader("Add New Expense")
    item = st.text_input("Item Name", value=suggested_item)
    amount = st.number_input("Amount (¥)", min_value=0, value=int(suggested_amount))
    
    categories = ["Food 🍱", "Transport 🚆", "Shopping 🛍️", "Sightseeing 🏯",
                  "Mortgage 🏠", "Car 🚗", "Water 💧", "Electricity ⚡", 
                  "Car Insurance 🛡️", "Motorcycle Insurance 🏍️", "Pet stuff 🐾", "Gifts 🎁"]
    
    # Use the 'key' to avoid the duplicate ID error we saw earlier
    idx = categories.index(suggested_cat) if suggested_cat in categories else 0
    category = st.selectbox("Category", categories, index=idx, key="main_cat_select")
    
    submit = st.form_submit_button("Save to Google Sheets")
    
    if submit:
        if item and amount > 0:
            expense_ws.append_row([str(st.date_input("Date")), item, category, amount])
            st.success("Saved!")
            st.rerun()





































