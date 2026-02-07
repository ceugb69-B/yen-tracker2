import streamlit as st
import pandas as pd

st.title("¥ Yen Tracker Pro")

# 1. Your Google Sheet URL
# Make sure the URL ends in /export?format=csv
sheet_id = "YOUR_SHEET_ID_HEREhttps://docs.google.com/spreadsheets/d/1L_0iJOrN-nMxjX5zjNm2yUnUyck9RlUqeg2rnXvpAlU/edit?usp=sharing" 
url = f"https://docs.google.com/spreadsheets/d/1L_0iJOrN-nMxjX5zjNm2yUnUyck9RlUqeg2rnXvpAlU/edit?pli=1&gid=0#gid=0export?format=csv"

# 2. Read the data
try:
    df = pd.read_csv(url)
    st.write("### Current Expenses")
    st.dataframe(df)
    
    # 3. Quick Total
    if 'Amount' in df.columns:
        total = df['Amount'].sum()
        st.metric("Total Spent", f"¥{total:,.0f}")

except Exception as e:
    st.error("The app can't see the sheet. Did you set 'Anyone with the link' to Viewer?")

