import calendar
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage

import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Tumble Cup", page_icon="🥤", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

tumbler_items = {
    "Classic Tumbler": {
        "price": 3999,
        "styles": ["Style 1", "Style 2", "Style 3", "Style 4", "Custom", "Hand Painted"]
    },
    "Can Glass": {
        "price": 1999,
        "styles": ["Style 1", "Style 2", "Style 3", "Style 4", "Custom", "Hand Painted"]
    },
    "Coffee Cup": {
        "price": 2399,
        "styles": ["Style 1", "Style 2", "Style 3", "Style 4", "Custom", "Hand Painted"]
    }
}

# Additional fee for custom and hand-painted styles
CUSTOM_FEE = 250
HANDPAINTED_FEE = 500

month_list = list(calendar.month_name)[1:]
current_month = datetime.today().month
current_month_name = calendar.month_name[current_month]
current_year = datetime.today().year

if 'cart' not in st.session_state:
    st.session_state.cart = {}


def generate_order_number():
    """Generate a unique order number"""
    try:
        data = conn.read(worksheet="Tumble_cup", ttl=0)
        if not data.empty and 'Order Number' in data.columns:
            print("hi")
            numeric_parts = []
            for order_num in data['Order Number']:
                if isinstance(order_num, str) and order_num.startswith('#TC'):
                    try:
                        numeric_parts.append(int(order_num[3:]))
                    except ValueError:
                        pass

            if numeric_parts:
                next_id = max(numeric_parts) + 1
            else:
                next_id = 1
        else:
            next_id = 1
    except Exception as e:
        st.warning(f"Could not determine last order number: {e}")
        next_id = 1

    return f"#TC{str(next_id).zfill(5)}"


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
    """Add new orders to Google Sheet with auto-incremented ID"""
    try:
        existing_data = conn.read(worksheet="Tumble_cup", ttl=0)

        new_orders_df = pd.DataFrame(orders_data)
        if not existing_data.empty:
            if 'ID' in existing_data.columns:
                starting_id = int(existing_data['ID'].max()) + 1
            else:
                starting_id = len(existing_data)
        else:
            starting_id = 1

        new_orders_df.insert(0, "ID", range(starting_id, starting_id + len(new_orders_df)))

        if not existing_data.empty:
            for col in new_orders_df.columns:
                if col not in existing_data.columns:
                    existing_data[col] = None

            updated_data = pd.concat([existing_data, new_orders_df], ignore_index=True)
        else:
            updated_data = new_orders_df

        conn.update(worksheet="Tumble_cup", data=updated_data)
        return True
    except Exception as e:
        st.error(f"Failed to add orders to Google Sheet: {e}")
        return False


def get_orders(month=None):
    """Retrieve orders optionally filtered by month"""
    try:
        data = conn.read(worksheet="Tumble_cup", ttl=0)
        if data.empty:
            return pd.DataFrame()

        data["Order Date"] = pd.to_datetime(data["Order Date"], errors="coerce")

        if month:
            filtered_data = data[data["Order Date"].dt.month == month]
        else:
            filtered_data = data[data["Order Date"].dt.month == current_month]

        return filtered_data
    except Exception as e:
        st.error(f"Failed to retrieve orders: {e}")
        return pd.DataFrame()


def count_orders():
    """Count total number of orders"""
    try:
        data = conn.read(worksheet="Tumble_cup", ttl=0)
        if data.empty:
            return 0
        return len(data)
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


st.markdown("<h1 style='text-align: center; color: orange;'>Tumble Cup</h1>", unsafe_allow_html=True)

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
            quantity = st.number_input(f"Qty", min_value=1, value=1, key=f"qty_{item_name}")

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
.st-emotion-cache-1weic72 {
display: none;
}
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
        name = st.text_input("", placeholder="Enter your name", key="name_input")

        st.markdown('<p class="required">Email</p>', unsafe_allow_html=True)
        email = st.text_input("", placeholder="Enter your email", key="email_input")

        st.markdown('<p class="required">Phone</p>', unsafe_allow_html=True)
        phone = st.text_input("", placeholder="Enter your phone", key="phone_input")

        st.subheader("Delivery Address")
        st.markdown('<p class="required">Street Address</p>', unsafe_allow_html=True)
        address_street = st.text_input("", placeholder="Enter your street address", key="address_street_input")

        st.markdown('<p class="required">City</p>', unsafe_allow_html=True)
        address_city = st.text_input("", placeholder="Enter your city", key="address_city_input")

        st.markdown('<p class="required">Postal Code</p>', unsafe_allow_html=True)
        postal_code = st.text_input("", placeholder="Enter your postal code", key="postal_code_input")

        if has_custom_items:
            st.markdown('<p class="required">Instructions</p>', unsafe_allow_html=True)
            instructions = st.text_area("",
                                        placeholder="Please provide detailed instructions for your custom/hand-painted items",
                                        key="instructions_input")
        else:
            st.markdown('<p class="">Instructions</p>', unsafe_allow_html=True)
            instructions = st.text_area("", placeholder="Enter any special delivery instructions",
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
            mobile_service = st.radio("", ["JazzCash", "EasyPaisa", "Raast", "Other"], key="mobile_service")
            if mobile_service == "Other":
                st.markdown('<p class="required">Specify Service:</p>', unsafe_allow_html=True)
                other_service = st.text_input("", placeholder="Enter mobile money service name", key="other_service")
                payment_service = other_service
            else:
                payment_service = mobile_service

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
            st.markdown('<p class="required">Transaction Reference:</p>', unsafe_allow_html=True)
            transaction_id = st.text_input("", placeholder="Enter bank transfer reference", key="transaction_ref")
            payment_service = "Bank Transfer"

        submit_button = st.button("Place Order")

        if submit_button:
            missing_fields = []

            if not name:
                missing_fields.append("Name")
            if not email:
                missing_fields.append("Email")
            if not phone:
                missing_fields.append("Phone")
            if not address_street:
                missing_fields.append("Street Address")
            if not address_city:
                missing_fields.append("City")
            if not postal_code:
                missing_fields.append("Postal Code")

            if has_custom_items and not instructions:
                missing_fields.append("Instructions (required for custom/hand-painted items)")
            if payment_method == "Mobile Money (Jazzcash etc)":
                if mobile_service == "Other" and not payment_service:
                    missing_fields.append("Mobile Money Service")
                if not transaction_id:
                    missing_fields.append("Transaction ID")
            elif payment_method == "Bank Transfer":
                if not transaction_id:
                    missing_fields.append("Transaction Reference")

            if missing_fields:
                st.error(f"Please fill in all required fields: {', '.join(missing_fields)}")
            else:
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
                        "Phone no": phone,
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
                        "Status": "Pending"
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
                    <body>
                        <h2 style="color: orange;">Thank you for your order!</h2>
                        <p><strong>Order Number:</strong> {order_number}</p>
                        <p><strong>Name:</strong> {name}<br>
                           <strong>Email:</strong> {email}<br>
                           <strong>Phone:</strong> {phone}<br>
                           <strong>Address:</strong> {address_street}, {address_city}, {postal_code}</p>

                        <h3>Order Summary</h3>
                        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
                            <thead style="background-color: #f2f2f2;">
                                <tr>
                                    <th>Item</th>
                                    <th>Style</th>
                                    <th>Qty</th>
                                    <th>Unit Price</th>
                                    <th>Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {order_rows}
                                <tr>
                                    <td colspan="4"><strong>Total Amount</strong></td>
                                    <td><strong>Rs. {total_amount}</strong></td>
                                </tr>
                            </tbody>
                        </table>

                        <p><strong>Payment Method:</strong> {payment_method}<br>
                           <strong>Transaction Reference:</strong> {transaction_id or "N/A"}</p>

                        <p><strong>Special Instructions:</strong> {instructions or "N/A"}</p>

                        <p>We will process your order shortly. Thank you for shopping with Tumble Cup!</p>
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
