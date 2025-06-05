import calendar
import re
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage

import gspread
import pandas as pd
import streamlit as st
from PIL import Image
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Tumble Cup", page_icon="🥤", layout="centered")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = {
    "type": st.secrets["connections"]["gsheets"]["type"],
    "project_id": st.secrets["connections"]["gsheets"]["project_id"],
    "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
    "private_key": st.secrets["connections"]["gsheets"]["private_key"].replace("\\n", "\n"),
    "client_email": st.secrets["connections"]["gsheets"]["client_email"],
    "client_id": st.secrets["connections"]["gsheets"]["client_id"],
    "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
    "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"]
}


@st.cache_resource(show_spinner="Connecting to Google Sheets...")
def init_gspread_connection():
    """Initialize gspread connection with service account credentials"""
    try:
        # creds = Credentials.from_service_account_file("Credentials.json", scopes=SCOPES)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

        gs_client = gspread.authorize(creds)
        return gs_client
    except Exception as e:
        st.error(f"❌ Failed to initialize Google Sheets connection: {e}")
        return None


# Cached gspread client
gc = init_gspread_connection()


def get_worksheet():
    """Get the worksheet object from the Google Sheet"""
    try:
        if gc is None:
            st.warning("Google Sheets client is not initialized.")
            return None

        SPREADSHEET_ID = st.secrets["connections"]["gsheets"]["spreadsheet"]
        SHEET_NAME = "Tumble_cup"

        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(SHEET_NAME)

        return worksheet

    except Exception as e:
        st.error(f"❌ Failed to access worksheet '{SHEET_NAME}': {e}")
        return None


tumbler_items = {
    "Classic Tumbler": {
        "price": 3999,
        "styles": ["Style 1", "Style 2", "Style 3", "Style 4", "Custom", "Hand Painted"]
    },
    "Can Glass": {
        "price": 1999,
        "styles": ["Style 1", "Style 2", "Style 3", "Style 4", "Custom", "Hand Painted"]
    },
    "Coffee Mug": {
        "price": 2399,
        "styles": ["Style 1", "Style 2", "Style 3", "Style 4", "Custom", "Hand Painted"]
    }
}

CUSTOM_FEE = 250
HANDPAINTED_FEE = 500

month_list = list(calendar.month_name)[1:]
current_month = datetime.today().month
current_month_name = calendar.month_name[current_month]
current_year = datetime.today().year

if 'cart' not in st.session_state:
    st.session_state.cart = {}


def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def format_phone_number(phone):
    phone_digits = re.sub(r'\D', '', phone)

    if phone_digits.startswith('0'):
        phone_digits = '92' + phone_digits[1:]
    elif not phone_digits.startswith('92'):
        phone_digits = '92' + phone_digits

    return '+' + phone_digits


def generate_order_number():
    """Generate a unique order number using gspread"""
    try:
        worksheet = get_worksheet()
        if worksheet is None:
            return "#TC00001"

        raw_data = worksheet.get_all_values()
        if not raw_data or len(raw_data) < 2:
            # No data or only header exists
            return "#TC00001"

        headers = raw_data[0]
        rows = raw_data[1:]
        records = pd.DataFrame(rows, columns=headers)

        # Extract numeric parts from 'Order Number' column
        numeric_parts = []
        if 'Order Number' in records.columns:
            for order_num in records['Order Number']:
                if isinstance(order_num, str) and order_num.startswith('#TC'):
                    try:
                        numeric_parts.append(int(order_num[3:]))
                    except ValueError:
                        continue

        next_id = max(numeric_parts) + 1 if numeric_parts else 1
        return f"#TC{str(next_id).zfill(5)}"

    except Exception as e:
        st.warning(f"Could not determine last order number: {e}")
        return "#TC00001"


def send_email(subject, body, to_email):
    """Send order confirmation email"""
    gmail_user = "teamtumblecup@gmail.com"
    try:
        app_password = st.secrets["Email"]["Password"]

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg.set_content("This is a plain text version of the email")
        msg.add_alternative(body, subtype='html')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(gmail_user, app_password)
            smtp.send_message(msg)
            return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False


def add_orders_to_gsheet(orders_data):
    """Add new orders to Google Sheet using gspread"""
    try:
        worksheet = get_worksheet()
        if worksheet is None:
            st.error("Google Sheet not found.")
            return False

        # Get existing data
        existing_records_raw = worksheet.get_all_values()
        if not existing_records_raw:
            existing_records = pd.DataFrame()
            headers = list(orders_data[0].keys())
        else:
            headers = existing_records_raw[0]
            rows = existing_records_raw[1:]
            existing_records = pd.DataFrame(rows, columns=headers)

        # Determine starting ID
        if not existing_records.empty and 'ID' in existing_records.columns:
            try:
                existing_ids = existing_records['ID'].apply(lambda x: int(str(x).strip().replace('#', ''))).tolist()
                starting_id = max(existing_ids) + 1
            except Exception:
                starting_id = len(existing_records) + 1
        else:
            starting_id = 1

        # Prepare new rows for batch insert
        new_rows = []
        for i, order_data in enumerate(orders_data):
            order_data['ID'] = starting_id + i

            # Determine row values in order of headers
            row = [order_data.get(h, '') for h in headers]
            new_rows.append(row)

        # Write headers if sheet is empty
        if not existing_records_raw:
            worksheet.append_row(headers)

        # Batch insert new rows
        if new_rows:
            worksheet.append_rows(new_rows)

        # Optional: Clear function cache (if using @lru_cache)
        if hasattr(get_worksheet, "cache_clear"):
            get_worksheet.cache_clear()

        return True

    except Exception as e:
        st.error(f"Failed to add orders to Google Sheet: {e}")
        return False


def get_orders(month=None):
    """Retrieve orders optionally filtered by month using gspread"""
    try:
        worksheet = get_worksheet()
        if worksheet is None:
            return pd.DataFrame()

        # Get all records
        records = worksheet.get_all_values()

        if not records:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(records)

        # Convert Order Date to datetime
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")

        # Filter by month if specified
        if month:
            filtered_data = df[df["Order Date"].dt.month == month]
        else:
            filtered_data = df[df["Order Date"].dt.month == current_month]

        return filtered_data

    except Exception as e:
        st.error(f"Failed to retrieve orders: {e}")
        return pd.DataFrame()


def count_orders():
    """Count total number of orders using gspread"""
    try:
        worksheet = get_worksheet()
        if worksheet is None:
            return 0

        # Get the number of rows (minus header)
        row_count = len(worksheet.get_all_values())
        return max(0, row_count - 1)  # Subtract 1 for header row

    except Exception as e:
        st.error(f"Failed to count orders: {e}")
        return 0


def has_custom_or_hand_painted_items():
    """Check if cart contains any custom or hand-painted items"""
    for item in st.session_state.cart.values():
        if item['style'] in ["Custom", "Hand Painted"]:
            return True
    return False


def get_item_price(base_price, style):
    """Calculate item price including any extra fees for custom/hand-painted styles"""
    if style == "Custom":
        return base_price + CUSTOM_FEE
    elif style == "Hand Painted":
        return base_price + HANDPAINTED_FEE
    return base_price


def get_style_fee(style):
    """Return the additional fee for a specific style"""
    if style == "Custom":
        return CUSTOM_FEE
    elif style == "Hand Painted":
        return HANDPAINTED_FEE
    return 0


st.markdown("""
    <style>
        .title {
            text-align: center;
            color: orange;
            font-size: 48px;
            font-weight: bold;
        }
        .quote {
            text-align: center;
            font-size: 24px;
            font-style: italic;
            color: #6c757d;
            margin-top: 10px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='title'>Order Tumble Cup</div>", unsafe_allow_html=True)

image = Image.open("Tumblecup.jpeg")
left_co, cent_co, right_co = st.columns([1, 2, 1])
with cent_co:
    st.image(image, width=1000)

# Motivational Quote
st.markdown("<div class='quote'>“Hydrate and glow – your body will thank you.”</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Shop Items", "Cart", "Checkout"])

# Shop Items Tab
with tab1:
    st.header("Add Items to Cart")

    for item_name, item_info in tumbler_items.items():
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

        with col1:
            st.write(f"**{item_name}**")
            st.write(
                f"Price: Rs. {item_info['price']} (+ Rs. {CUSTOM_FEE} for Custom, + Rs. {HANDPAINTED_FEE} for Hand Painted)")

        with col2:
            style = st.selectbox(
                f"Select Style",
                item_info['styles'],
                key=f"style_{item_name}"
            )

        with col3:
            quantity = st.number_input(f"Qty", min_value=1, value=1, key=f"qty_{item_name}", step=1)

        with col4:
            if st.button("Add to Cart", key=f"add_{item_name}"):
                item_price = get_item_price(item_info['price'], style)
                item_key = f"{item_name} ({style})"

                if item_key in st.session_state.cart:
                    st.session_state.cart[item_key]['quantity'] += quantity
                else:
                    st.session_state.cart[item_key] = {
                        'name': item_name,
                        'style': style,
                        'price': item_price,
                        'base_price': item_info['price'],
                        'style_fee': get_style_fee(style),
                        'has_custom_fee': style == "Custom",
                        'has_handpainted_fee': style == "Hand Painted",
                        'quantity': quantity
                    }
                st.success(f"Added {quantity} {item_name} ({style}) to cart!")

    st.divider()
    total_items = sum(item['quantity'] for item in st.session_state.cart.values())
    st.markdown(f"🛒 **Total Items in Cart: {total_items}**")

    if st.session_state.cart:
        st.subheader("Current Cart")

        total_cart_price = 0
        for item_key, item_data in st.session_state.cart.items():
            item_total = item_data['price'] * item_data['quantity']
            total_cart_price += item_total

            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                display_name = f"{item_key}"
                if item_data['has_custom_fee']:
                    display_name += f" (Includes Rs. {CUSTOM_FEE} custom fee)"
                elif item_data['has_handpainted_fee']:
                    display_name += f" (Includes Rs. {HANDPAINTED_FEE} hand-painted fee)"
                st.write(f"**{display_name}**")
            with col2:
                st.write(f"Qty: {item_data['quantity']}")
            with col3:
                st.write(f"Rs. {item_total}")
            with col4:
                if st.button("Remove", key=f"remove_{item_key}"):
                    del st.session_state.cart[item_key]
                    time.sleep(0.5)
                    st.rerun()

        st.write(f"**Total: Rs. {total_cart_price}**")

        if st.button("Clear Cart"):
            st.session_state.cart = {}
            st.info("Emptying your cart.....")
            time.sleep(2)
            st.rerun("app")
    else:
        st.info("Your cart is empty. Add some items!")

# Custom CSS
st.markdown("""
<style>
.required:after {
    content: " *";
    color: red;
}
# .st-emotion-cache-1weic72 {
# display: none;
# }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Cart Tab
with tab2:
    st.header("Cart")
    if st.session_state.cart:
        st.subheader("Current Cart")

        total_cart_price = 0
        for item_key, item_data in st.session_state.cart.items():
            item_total = item_data['price'] * item_data['quantity']
            total_cart_price += item_total

            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                display_name = f"{item_key}"
                if item_data['has_custom_fee']:
                    display_name += f" (Includes Rs. {CUSTOM_FEE} custom fee)"
                elif item_data['has_handpainted_fee']:
                    display_name += f" (Includes Rs. {HANDPAINTED_FEE} hand-painted fee)"
                st.write(f"**{display_name}**")
            with col2:
                st.write(f"Qty: {item_data['quantity']}")
            with col3:
                st.write(f"Rs. {item_total}")
            with col4:
                if st.button("Remove", key=f"tab2_remove_{item_key}"):
                    del st.session_state.cart[item_key]
                    st.rerun()

        st.write(f"**Total: Rs. {total_cart_price}**")

        if st.button("Clear Cart", key="tab2_clear"):
            st.session_state.cart = {}
            st.info("Your Cart has been Cleared!")
            time.sleep(0.5)
            st.rerun()
    else:
        st.info("Your cart is empty. Add some items!")

with tab3:
    if not st.session_state.cart:
        st.warning("Your cart is empty. Please add items before proceeding to checkout.")
    else:
        st.header("Checkout")

        cart_total = sum(item['price'] * item['quantity'] for item in st.session_state.cart.values())
        st.subheader("Cart Summary")

        has_custom_items = has_custom_or_hand_painted_items()

        for item_key, item_data in st.session_state.cart.items():
            item_total = item_data['quantity'] * item_data['price']

            price_display = f"{item_key} × {item_data['quantity']} = Rs. {item_total}"
            if item_data['has_custom_fee']:
                price_display += f" (Includes Rs. {CUSTOM_FEE} custom fee per item)"
            elif item_data['has_handpainted_fee']:
                price_display += f" (Includes Rs. {HANDPAINTED_FEE} hand-painted fee per item)"
            st.write(price_display)

            if item_data['style'] in ["Custom", "Hand Painted"]:
                st.info(f"Note: '{item_data['style']}' items require detailed instructions")

        st.write(f"**Total: Rs. {cart_total}**")

        st.subheader("Contact Information")
        st.markdown('<p class="required">Name</p>', unsafe_allow_html=True)
        name = st.text_input("Name", placeholder="Enter your name", key="name_input")

        st.markdown('<p class="required">Email</p>', unsafe_allow_html=True)
        email = st.text_input("Email", placeholder="Enter your email", key="email_input")

        st.markdown('<p class="required">Phone</p>', unsafe_allow_html=True)
        phone = st.text_input("Phone", placeholder="Enter your phone (e.g., 03001234567)", key="phone_input",
                              help="Phone number will be automatically formatted with +92 country code")

        st.subheader("Delivery Address")
        st.markdown('<p class="required">Street Address</p>', unsafe_allow_html=True)
        address_street = st.text_input("Address", placeholder="Enter your street address", key="address_street_input")

        st.markdown('<p class="required">City</p>', unsafe_allow_html=True)
        address_city = st.text_input("City", placeholder="Enter your city", key="address_city_input")

        st.markdown('<p class="required">Postal Code</p>', unsafe_allow_html=True)
        postal_code = st.text_input("Posst Code", placeholder="Enter your postal code", key="postal_code_input")

        if has_custom_items:
            st.markdown('<p class="required">Instructions</p>', unsafe_allow_html=True)
            instructions = st.text_area("Instructions",
                                        placeholder="Please provide detailed instructions for your custom/hand-painted items",
                                        key="instructions_input")
        else:
            st.markdown('<p class="">Instructions</p>', unsafe_allow_html=True)
            instructions = st.text_area("Instructions", placeholder="Enter any special delivery instructions",
                                        key="instructions_input")

        order_date = datetime.today().strftime("%d-%B-%Y")

        mobile_money_accounts = {
            "JazzCash": f"{st.secrets['Banking']['Phone']}",
            "EasyPaisa": f"{st.secrets['Banking']['Phone']}",
            "Raast": f"{st.secrets['Banking']['Phone']}"
        }

        bank_transfer_details = {
            "Bank Name": "HBL",
            "Account Title": "TOOBA",
            "Account Number": f"{st.secrets['Banking']['Account']}",
            "IBAN": f"{st.secrets['Banking']['IBAN']}"
        }

        st.markdown('<p class="required">Payment Method</p>', unsafe_allow_html=True)
        payment_method = st.selectbox(
            "",
            ["Cash on Delivery", "Mobile Money (Jazzcash etc)", "Bank Transfer"],
            index=0,
            key="payment_method"
        )

        payment_service = None
        transaction_id = None

        if payment_method == "Mobile Money (Jazzcash etc)":
            st.subheader("Mobile Money Account Details")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info("JazzCash: " + mobile_money_accounts["JazzCash"])
            with col2:
                st.info("EasyPaisa: " + mobile_money_accounts["EasyPaisa"])
            with col3:
                st.info("Raast: " + mobile_money_accounts["Raast"])

            st.markdown('<p class="required">Select Mobile Money Service Used:</p>', unsafe_allow_html=True)
            mobile_service = st.radio("Mobile Service", ["JazzCash", "EasyPaisa", "Raast", "Other"], key="mobile_service")
            if mobile_service == "Other":
                st.markdown('<p class="required">Specify Service:</p>', unsafe_allow_html=True)
                other_service = st.text_input("", placeholder="Enter mobile money service name", key="other_service")
                payment_service = other_service
            else:
                payment_service = mobile_service

            st.markdown('<p class="required">Transaction ID:</p>', unsafe_allow_html=True)
            transaction_id = st.text_input("Transaction ID", placeholder="Enter transaction ID", key="transaction_id")

        elif payment_method == "Bank Transfer":
            st.subheader("Bank Transfer Details")
            st.info(f"""
            **Bank Name:** {bank_transfer_details['Bank Name']}  
            **Account Title:** {bank_transfer_details['Account Title']}  
            **Account Number:** {bank_transfer_details['Account Number']}  
            **IBAN:** {bank_transfer_details['IBAN']}
            """)
            st.markdown('<p class="required">Transaction Reference:</p>', unsafe_allow_html=True)
            transaction_id = st.text_input("", placeholder="Enter bank transfer reference", key="transaction_ref")
            payment_service = "Bank Transfer"

        submit_button = st.button("Place Order")

        if submit_button:
            with st.spinner("Placing Your Order..."):
                missing_fields = []
                validation_errors = []

                # Basic field validation
                if not name:
                    missing_fields.append("Name")
                if not email:
                    missing_fields.append("Email")
                elif not is_valid_email(email):
                    validation_errors.append("Please enter a valid email address")
                if not phone:
                    missing_fields.append("Phone")
                if not address_street:
                    missing_fields.append("Street Address")
                if not address_city:
                    missing_fields.append("City")
                if not postal_code:
                    missing_fields.append("Postal Code")

                # Custom items validation
                if has_custom_items and not instructions:
                    missing_fields.append("Instructions (required for custom/hand-painted items)")

                # Payment method validation
                if payment_method == "Mobile Money (Jazzcash etc)":
                    if mobile_service == "Other" and not payment_service:
                        missing_fields.append("Mobile Money Service")
                    if not transaction_id:
                        missing_fields.append("Transaction ID")
                elif payment_method == "Bank Transfer":
                    if not transaction_id:
                        missing_fields.append("Transaction Reference")

                # Display errors
                if missing_fields:
                    st.error(f"Please fill in all required fields: {', '.join(missing_fields)}")
                elif validation_errors:
                    for error in validation_errors:
                        st.error(error)
                else:
                    formatted_phone = format_phone_number(phone)
                    order_number = generate_order_number()
                    order_rows = ""
                    total_amount = 0
                    all_order_data = []

                    for item_key, item_data in st.session_state.cart.items():
                        item_total = item_data['quantity'] * item_data['price']
                        total_amount += item_total

                        price_display = f"Rs. {item_data['price']}"
                        if item_data['has_custom_fee']:
                            price_display = f"Rs. {item_data['base_price']} + Rs. {CUSTOM_FEE} (custom)"
                        elif item_data['has_handpainted_fee']:
                            price_display = f"Rs. {item_data['base_price']} + Rs. {HANDPAINTED_FEE} (hand-painted)"

                        order_rows += f"""
                            <tr>
                                <td>{item_data['name']}</td>
                                <td>{item_data['style']}</td>
                                <td>{item_data['quantity']}</td>
                                <td>{price_display}</td>
                                <td>Rs. {item_total}</td>
                            </tr>
                        """
                        style_fee = 0
                        fee_type = ""
                        if item_data['has_custom_fee']:
                            style_fee = CUSTOM_FEE
                            fee_type = "Custom Fee"
                        elif item_data['has_handpainted_fee']:
                            style_fee = HANDPAINTED_FEE
                            fee_type = "Hand-Painted Fee"

                        order_data = {
                            "Order Number": order_number,
                            "Name": name,
                            "Email": email,
                            "Phone no": formatted_phone,
                            "Address": address_street,
                            "City": address_city,
                            "Post Code": postal_code,
                            "Item Name": item_data['name'],
                            "Item Style": item_data['style'],
                            "Item Quantity": item_data['quantity'],
                            "Base Price": item_data['base_price'],
                            "Style Fee Type": fee_type,
                            "Style Fee": style_fee,
                            "Price": item_data['price'],
                            "Total": item_data['price'] * item_data['quantity'],
                            "Instructions": instructions,
                            "Order Date": order_date,
                            "Payment Method": payment_method,
                            "Payment Service": payment_service,
                            "Transaction ID": transaction_id,
                            "Payment Status": "Pending",
                            "Status": "Pending",
                            "Tracking ID": "",
                            "Tracking Partner": ""
                        }

                        all_order_data.append(order_data)

                    try:
                        if add_orders_to_gsheet(all_order_data):
                            successful_items = len(all_order_data)
                        else:
                            successful_items = 0
                    except Exception as e:
                        st.error(f"Failed to submit orders: {str(e)}")
                        successful_items = 0

                    if successful_items > 0:
                        html_body = f"""
                        <html>
      <body style="margin: 0; padding: 0; background-color: #fef9f6; font-family: 'Segoe UI', sans-serif;">
    
        <div style="max-width: 600px; margin: 0 auto; padding: 40px 30px; background-color: #ffffff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
    
          <h1 style="color: #ff7b00; text-align: center; font-size: 28px;">Thank You for Your Order! 🧡</h1>
          <p style="text-align: center; font-size: 16px; color: #555;">
            Your order has been received and is being processed.
          </p>
    
          <div style="margin-top: 30px; font-size: 15px; color: #333;">
            <p><strong>Order Number:</strong> {order_number}</p>
            <p>
              <strong>Name:</strong> {name}<br>
              <strong>Email:</strong> {email}<br>
              <strong>Phone:</strong> {phone}<br>
              <strong>Address:</strong> {address_street}, {address_city}, {postal_code}
            </p>
          </div>
    
    
          <h3 style="color: #ff7b00; border-bottom: 1px solid #eee; padding-bottom: 5px;">🧾 Order Summary</h3>
          <table cellpadding="10" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 20px;">
            <thead style="background-color: #ffecd9; color: #333;">
              <tr>
                <th align="left">Item</th>
                <th align="left">Style</th>
                <th align="center">Qty</th>
                <th align="right">Unit Price</th>
                <th align="right">Total</th>
              </tr>
            </thead>
            <tbody>
              {order_rows}
              <tr style="border-top: 1px solid #eee;">
                <td colspan="4" align="right"><strong>Total Amount</strong></td>
                <td align="right"><strong>Rs. {total_amount}</strong></td>
              </tr>
            </tbody>
          </table>
          <p style="font-size: 14px; color: #444;">
            <strong>Payment Method:</strong> {payment_method}<br>
            <strong>Transaction Reference:</strong> {transaction_id or "N/A"}<br>
            <strong>Special Instructions:</strong> {instructions or "N/A"}
          </p>
    
          <p style="font-size: 15px; color: #333; margin-top: 30px;">
            We'll begin preparing your order right away.  
            Thank you for choosing <strong>Tumble Cup</strong>! 🥤
          </p>
    
        </div>
        <div style="text-align: center; padding: 15px 0; font-size: 12px; color: #888;">
          &copy; 2025 Tumble Cup. All rights reserved. <br>
          hello
        </div>
    
      </body>
    </html>
    
                        """
                        st.success(
                            f"Order submitted successfully! {successful_items} item(s) added to your order. \nEmail has been sent to {email}. Please check your spam or junk folder if you don't see it!")
                        st.toast(f"Order {order_number} has been placed successfully!")
                        send_email(f"Tumble Cup Order {order_number} has been placed successfully!", html_body, email)

                        st.subheader("Order Summary")
                        summary_cols = st.columns(2)
                        with summary_cols[0]:
                            for item_key, item_data in st.session_state.cart.items():
                                price_display = f"**{item_key}:** {item_data['quantity']} × Rs. {item_data['price']}"
                                if item_data['has_custom_fee']:
                                    price_display += f" (includes Rs. {CUSTOM_FEE} custom fee per item)"
                                elif item_data['has_handpainted_fee']:
                                    price_display += f" (includes Rs. {HANDPAINTED_FEE} hand-painted fee per item)"
                                price_display += f" = Rs. {item_data['price'] * item_data['quantity']}"
                                st.write(price_display)
                            st.write(f"**Total:** Rs. {cart_total}")
                        with summary_cols[1]:
                            st.write(f"**Order Number:** {order_number}")
                            st.write(f"**Order Date:** {order_date}")
                            st.write(f"**Payment Method:** {payment_method}")
                            st.write(f"**Delivery Address:** {address_street}, {address_city}, {postal_code}")
                            st.write(f"**Instructions:** {instructions or 'None provided'}")
                            st.write(f"**Status:** Pending")
                        st.session_state.cart = {}
                        time.sleep(5)
                        st.rerun(scope="app")
                    else:
                        st.error("Failed to submit any items in your order. Please try again.")
                        time.sleep(5)
                        st.rerun(scope="app")
