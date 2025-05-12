import calendar
import os
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv("creds.env")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Tumble_Cup"

month_list = list(calendar.month_name)[1:]
current_month = datetime.today().month
current_month_name = calendar.month_name[current_month]
current_year = datetime.today().year


def clean_data(url: str) -> pd.DataFrame:
    data = pd.read_csv(url)
    columns = list(data.columns)
    end_col_index = columns.index("Status")
    data = data.iloc[:, :end_col_index + 1]
    return data


def count_rows(url) -> int:
    data = clean_data(url)
    return len(data)


def Add_data(row: int, data: list):
    creds = None
    token_path = r'C:\Users\Huzaifa Sabah Uddin\PycharmProjects\TumbleCup\Token.json'
    credentials_path = r"C:\Users\Huzaifa Sabah Uddin\PycharmProjects\TumbleCup\Credentials.json"

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()

        update_range = f"Tumble_cup!A{row}:L{row}"
        response = sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=update_range,
            valueInputOption="USER_ENTERED",
            body={"values": [data]}
        ).execute()

    except HttpError as err:
        st.error(f"An error occurred: {err}")


# Define items with their prices
tumbler_items = {
    "Classic Tumbler": 1500,
    "Insulated Tumbler": 2000,
    "Travel Mug": 1800,
    "Water Bottle": 1200,
    "Coffee Cup": 1000,
    "Thermos Flask": 2500
}

# Initialize session state for cart if it doesn't exist
if 'cart' not in st.session_state:
    st.session_state.cart = {}

# Center the title using markdown with HTML
st.markdown("<h1 style='text-align: center; color: orange;'>Tumble Cup</h1>", unsafe_allow_html=True)

# Create tabs for Shopping and Checkout
tab1, tab2 = st.tabs(["Shop Items", "Checkout"])

with tab1:
    st.header("Add Items to Cart")

    # Display each item with an "Add to Cart" button
    for item_name, item_price in tumbler_items.items():
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.write(f"**{item_name}**")
            st.write(f"Price: Rs. {item_price}")

        with col2:
            quantity = st.number_input(f"Qty", min_value=1, value=1, key=f"qty_{item_name}")

        with col3:
            if st.button(f"Add to Cart", key=f"add_{item_name}"):
                # Add or update item in cart
                if item_name in st.session_state.cart:
                    st.session_state.cart[item_name]['quantity'] += quantity
                else:
                    st.session_state.cart[item_name] = {
                        'price': item_price,
                        'quantity': quantity
                    }
                st.success(f"Added {quantity} {item_name}(s) to cart!")

        st.divider()

    # Display current cart contents
    if st.session_state.cart:
        st.subheader("Current Cart")

        total_cart_price = 0
        for item_name, item_data in st.session_state.cart.items():
            item_total = item_data['price'] * item_data['quantity']
            total_cart_price += item_total

            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{item_name}**")
            with col2:
                st.write(f"Qty: {item_data['quantity']}")
            with col3:
                st.write(f"Rs. {item_total}")
            with col4:
                if st.button("Remove", key=f"remove_{item_name}"):
                    del st.session_state.cart[item_name]
                    st.rerun()

        st.write(f"**Total: Rs. {total_cart_price}**")

        if st.button("Clear Cart"):
            st.session_state.cart = {}
            st.rerun()
    else:
        st.info("Your cart is empty. Add some items!")

# Add required indicator style
st.markdown("""
<style>
.required:after {
    content: " *";
    color: red;
}
</style>
""", unsafe_allow_html=True)

with tab2:
    if not st.session_state.cart:
        st.warning("Your cart is empty. Please add items before proceeding to checkout.")
    else:
        st.header("Checkout")

        # Calculate cart total
        cart_total = sum(item['price'] * item['quantity'] for item in st.session_state.cart.values())

        # Display cart summary
        st.subheader("Cart Summary")
        for item_name, item_data in st.session_state.cart.items():
            item_total = item_data['price'] * item_data['quantity']
            st.write(f"{item_name} × {item_data['quantity']} = Rs. {item_total}")

        st.write(f"**Total: Rs. {cart_total}**")

        # Required input fields with indicator
        st.markdown('<p class="required">Name</p>', unsafe_allow_html=True)
        name = st.text_input("", placeholder="Enter your name", key="name_input")

        st.markdown('<p class="required">Email</p>', unsafe_allow_html=True)
        email = st.text_input("", placeholder="Enter your email", key="email_input")

        st.markdown('<p class="required">Phone</p>', unsafe_allow_html=True)
        phone = st.text_input("", placeholder="Enter your phone", key="phone_input")

        st.markdown('<p class="">Instructions</p>', unsafe_allow_html=True)
        instructions = st.text_area("", placeholder="Enter your instructions", key="instructions_input")
        order_date = datetime.today().strftime("%d-%B-%Y")

        # Define account details for different payment methods
        mobile_money_accounts = {
            "JazzCash": "0300-1234567",
            "EasyPaisa": "0333-7654321"
        }

        bank_transfer_details = {
            "Bank Name": "ABC Bank",
            "Account Title": "Tumble Cup",
            "Account Number": "12345678901234",
            "IBAN": "PK12ABCD1234567890123456"
        }

        # Payment method selection
        st.markdown('<p class="required">Payment Method</p>', unsafe_allow_html=True)
        payment_method = st.selectbox(
            "",
            ["Cash on Delivery", "Mobile Money (Jazzcash etc)", "Bank Transfer"],
            index=0,
            key="payment_method"
        )

        # Display relevant account details based on payment method
        if payment_method == "Mobile Money (Jazzcash etc)":
            st.subheader("Mobile Money Account Details")
            col1, col2 = st.columns(2)
            with col1:
                st.info("JazzCash: " + mobile_money_accounts["JazzCash"])
            with col2:
                st.info("EasyPaisa: " + mobile_money_accounts["EasyPaisa"])

            # Required fields for mobile money payments
            st.markdown('<p class="required">Select Mobile Money Service Used:</p>', unsafe_allow_html=True)
            mobile_service = st.radio("", ["JazzCash", "EasyPaisa", "Other"], key="mobile_service")
            if mobile_service == "Other":
                st.markdown('<p class="required">Specify Service:</p>', unsafe_allow_html=True)
                other_service = st.text_input("", placeholder="Enter mobile money service name", key="other_service")

            st.markdown('<p class="required">Transaction ID:</p>', unsafe_allow_html=True)
            transaction_id = st.text_input("", placeholder="Enter transaction ID", key="transaction_id")

        elif payment_method == "Bank Transfer":
            st.subheader("Bank Transfer Details")
            st.info(f"""
            **Bank Name:** {bank_transfer_details['Bank Name']}  
            **Account Title:** {bank_transfer_details['Account Title']}  
            **Account Number:** {bank_transfer_details['Account Number']}  
            **IBAN:** {bank_transfer_details['IBAN']}
            """)

            # Required field for bank transfer
            st.markdown('<p class="required">Transaction Reference:</p>', unsafe_allow_html=True)
            transaction_ref = st.text_input("", placeholder="Enter bank transfer reference", key="transaction_ref")

        # Submit button
        submit_button = st.button("Place Order")

        if submit_button:
            # Validate all required fields
            missing_fields = []

            if not name:
                missing_fields.append("Name")
            if not email:
                missing_fields.append("Email")
            if not phone:
                missing_fields.append("Phone")
            # Validate payment-specific required fields
            if payment_method == "Mobile Money (Jazzcash etc)":
                if 'mobile_service' in locals() and mobile_service == "Other" and not (
                        'other_service' in locals() and other_service):
                    missing_fields.append("Mobile Money Service")
                if 'transaction_id' not in locals() or not transaction_id:
                    missing_fields.append("Transaction ID")
            elif payment_method == "Bank Transfer":
                if 'transaction_ref' not in locals() or not transaction_ref:
                    missing_fields.append("Transaction Reference")

            if missing_fields:
                st.error(f"Please fill in all required fields: {', '.join(missing_fields)}")
            else:
                # Get current row count once
                current_row_count = count_rows(url)

                # Counter for successful item submissions
                successful_items = 0

                # Process each item in the cart as a separate order row
                for item_index, (item_name, item_data) in enumerate(st.session_state.cart.items()):
                    # Prepare data for submission
                    order_data = [
                        name,
                        email,
                        phone,
                        item_name,
                        item_data['quantity'],
                        item_data['price'],
                        item_data['price'] * item_data['quantity'],
                        instructions,
                        order_date,
                        payment_method,
                    ]

                    # Add payment-specific details
                    if payment_method == "Mobile Money (Jazzcash etc)":
                        payment_service = mobile_service if mobile_service != "Other" else other_service
                        order_data.append(payment_service)
                        order_data.append(transaction_id)
                    elif payment_method == "Bank Transfer":
                        order_data.append("Bank Transfer")
                        order_data.append(transaction_ref)
                    else:
                        order_data.append("NO")
                    order_data.append("Pending")
                    next_row = current_row_count + 2 + item_index

                    try:
                        Add_data(next_row, order_data)
                        successful_items += 1
                    except Exception as e:
                        st.error(f"Failed to submit order for {item_name}: {str(e)}")
                        continue  # Try to continue with other items instead of breaking

                if successful_items > 0:
                    st.success(f"Order submitted successfully! {successful_items} item(s) added to your order.")

                    # Show order summary
                    st.subheader("Order Summary")
                    summary_cols = st.columns(2)
                    with summary_cols[0]:
                        for item_name, item_data in st.session_state.cart.items():
                            st.write(
                                f"**{item_name}:** {item_data['quantity']} × Rs. {item_data['price']} = Rs. {item_data['price'] * item_data['quantity']}")
                        st.write(f"**Total:** Rs. {cart_total}")
                    with summary_cols[1]:
                        st.write(f"**Order Date:** {order_date}")
                        st.write(f"**Payment Method:** {payment_method}")
                        st.write(f"**Status:** Pending")

                    # Clear the cart after successful order
                    st.session_state.cart = {}
                else:
                    st.error("Failed to submit any items in your order. Please try again.")