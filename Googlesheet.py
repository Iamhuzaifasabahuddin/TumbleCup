import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Read existing data
data = conn.read(worksheet="Tumble_cup")

# Display current data (optional)
st.subheader("Current Orders")
st.dataframe(data)

# --- Input Form ---
st.subheader("Add New Order")

with st.form("order_form"):
    order_number = st.text_input("Order Number")
    name = st.text_input("Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone no")
    address = st.text_area("Address")
    city = st.text_input("City")
    post_code = st.text_input("Post Code")
    item = st.text_input("Item")
    item_style = st.text_input("Item Style")
    item_quantity = st.number_input("Item Quantity", min_value=1, step=1)
    price = st.number_input("Price per Item", min_value=0.0)
    total = item_quantity * price
    instructions = st.text_area("Instructions")
    order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payment_method = st.selectbox("Payment Method", ["Card", "Cash", "Bank Transfer", "Other"])
    payment_service = st.text_input("Payment Service (e.g., Stripe, PayPal)")
    transaction_id = st.text_input("Transaction ID")
    payment_status = st.selectbox("Payment Status", ["Pending", "Completed", "Failed"])
    status = st.selectbox("Order Status", ["Processing", "Shipped", "Delivered", "Cancelled"])

    submitted = st.form_submit_button("Submit Order")

# --- Append and Save ---
if submitted:
    # Create a new row as DataFrame
    new_row = pd.DataFrame([{
        "Order Number": order_number,
        "Name": name,
        "Email": email,
        "Phone no": phone,
        "Address": address,
        "City": city,
        "Post Code": post_code,
        "Item": item,
        "Item Style": item_style,
        "Item Quantity": item_quantity,
        "Price": price,
        "Total": total,
        "Instructions": instructions,
        "Order Date": order_date,
        "Payment Method": payment_method,
        "Payment Service": payment_service,
        "Transaction ID": transaction_id,
        "Payment Status": payment_status,
        "Status": status
    }])

    # Append new row to existing data
    updated_data = pd.concat([data, new_row], ignore_index=True)

    # Update the sheet
    conn.update(worksheet="Tumble_cup", data=updated_data)

    st.success("✅ Order submitted successfully!")
