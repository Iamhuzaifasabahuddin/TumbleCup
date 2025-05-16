import base64
import calendar
import os
import smtplib
import sqlite3
from datetime import datetime
from email.message import EmailMessage

import pandas as pd
import streamlit as st
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# from dotenv import load_dotenv
#
# load_dotenv("creds.env")
DB_PATH = "tumble_cup.db"
# DB_PATH = "tumble_cup_test.db"


# Encryption setup
# Encryption setup
def get_encryption_key():
    """Generate or retrieve the encryption key from Streamlit secrets"""
    if "ENCRYPTION_KEY" in st.secrets:
        key = st.secrets["ENCRYPTION_KEY"]
    else:
        salt = f'{st.secrets["Encrypt"]["Salt"]}'.encode('utf-8')
        password = (st.secrets["Encrypt"]["Password"]).encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))

    return key


def get_cipher():
    return Fernet(get_encryption_key())


def encrypt_data(data):
    if data is None:
        return None
    cipher = get_cipher()
    return cipher.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data):
    if encrypted_data is None:
        return None
    cipher = get_cipher()
    return cipher.decrypt(encrypted_data.encode()).decode()


def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute('''
                  CREATE TABLE IF NOT EXISTS orders
                  (
                      id
                      INTEGER
                      PRIMARY
                      KEY
                      AUTOINCREMENT,
                      order_number
                      TEXT
                      NOT
                      NULL,
                      customer_name
                      TEXT
                      NOT
                      NULL,
                      email
                      TEXT
                      NOT
                      NULL,
                      phone
                      TEXT
                      NOT
                      NULL,
                      address
                      TEXT,
                      city
                      TEXT,
                      postal_code
                      TEXT,
                      item_name
                      TEXT
                      NOT
                      NULL,
                      item_style
                      TEXT
                      NOT
                      NULL,
                      quantity
                      INTEGER
                      NOT
                      NULL,
                      price
                      REAL
                      NOT
                      NULL,
                      total_price
                      REAL
                      NOT
                      NULL,
                      instructions
                      TEXT,
                      order_date
                      TEXT
                      NOT
                      NULL,
                      payment_method
                      TEXT
                      NOT
                      NULL,
                      payment_service
                      TEXT,
                      transaction_id
                      TEXT,
                      payment_status
                      TEXT
                      DEFAULT
                      'Pending',
                      status
                      TEXT
                      DEFAULT
                      'Pending'
                  )
                  ''')

        conn.commit()
        print("Database and table created.")
    else:
        conn = sqlite3.connect(DB_PATH)
        print("Database already exists.")

    return conn


def add_data(order_number, data):
    conn = init_db()
    c = conn.cursor()

    encrypted_data = list(data)

    encrypted_data[0] = encrypt_data(encrypted_data[0])
    encrypted_data[1] = encrypt_data(encrypted_data[1])
    encrypted_data[2] = encrypt_data(encrypted_data[2])
    encrypted_data[3] = encrypt_data(encrypted_data[3])

    c.execute('''
              INSERT INTO orders (order_number, customer_name, email, phone, address, city, postal_code, item_name,
                                  item_style,
                                  quantity,
                                  price, total_price, instructions, order_date,
                                  payment_method, payment_service, transaction_id, payment_status, status)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
              ''', (order_number, *encrypted_data))

    conn.commit()
    conn.close()
    return True


def send_email(subject, body, to_email):
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


def count_orders():
    conn = init_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM orders')
    count = c.fetchone()[0]
    conn.close()
    return count


def get_orders(month):
    conn = init_db()
    df = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()

    if not df.empty:
        df["customer_name"] = df["customer_name"].apply(lambda x: decrypt_data(x) if x else None)
        df["email"] = df["email"].apply(lambda x: decrypt_data(x) if x else None)
        df["phone"] = df["phone"].apply(lambda x: decrypt_data(x) if x else None)
        df["address"] = df["address"].apply(lambda x: decrypt_data(x) if x else None)

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    if month:
        data = df[df["order_date"].dt.month == month]
    else:
        data = df[df["order_date"].dt.month == current_month]
    return data


def generate_order_number():
    conn = init_db()
    c = conn.cursor()
    c.execute('SELECT MAX(id) FROM orders')
    last_id = c.fetchone()[0]
    conn.close()
    next_id = (last_id or 0) + 1
    return f"#TC{str(next_id).zfill(5)}"


month_list = list(calendar.month_name)[1:]
current_month = datetime.today().month
current_month_name = calendar.month_name[current_month]
current_year = datetime.today().year

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

if 'cart' not in st.session_state:
    st.session_state.cart = {}


def has_custom_or_hand_painted_items():
    for item in st.session_state.cart.values():
        if item['style'] in ["Custom", "Hand Painted"]:
            return True
    return False


st.markdown("<h1 style='text-align: center; color: orange;'>Tumble Cup</h1>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Shop Items", "Cart", "Checkout", "Admin Panel"])

with tab1:
    st.header("Add Items to Cart")

    for item_name, item_info in tumbler_items.items():
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

        with col1:
            st.write(f"**{item_name}**")
            st.write(f"Price: Rs. {item_info['price']}")

        with col2:
            style = st.selectbox(
                f"Select Style",
                item_info['styles'],
                key=f"style_{item_name}"
            )

        with col3:
            quantity = st.number_input(f"Qty", min_value=1, value=1, key=f"qty_{item_name}")

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
                st.write(f"**{item_key}**")
            with col2:
                st.write(f"Qty: {item_data['quantity']}")
            with col3:
                st.write(f"Rs. {item_total}")
            with col4:
                if st.button("Remove", key=f"remove_{item_key}"):
                    del st.session_state.cart[item_key]
                    st.rerun()

        st.write(f"**Total: Rs. {total_cart_price}**")

        if st.button("Clear Cart"):
            st.session_state.cart = {}
            st.rerun()
    else:
        st.info("Your cart is empty. Add some items!")


st.markdown("""
<style>
.required:after {
    content: " *";
    color: red;
}
.st-emotion-cache-1weic72 {
display: none;
}
</style>
""", unsafe_allow_html=True)

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
                st.write(f"**{item_key}**")
            with col2:
                st.write(f"Qty: {item_data['quantity']}")
            with col3:
                st.write(f"Rs. {item_total}")
            with col4:
                if st.button("Remove", key=f"remove_{item_key}"):
                    del st.session_state.cart[item_key]
                    st.rerun()

        st.write(f"**Total: Rs. {total_cart_price}**")

        if st.button("Clear Cart"):
            st.session_state.cart = {}
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

        # Flag to check if any custom/hand-painted items are in the cart
        has_custom_items = has_custom_or_hand_painted_items()

        for item_key, item_data in st.session_state.cart.items():
            item_total = item_data['price'] * item_data['quantity']
            st.write(f"{item_key} × {item_data['quantity']} = Rs. {item_total}")

            # Highlight custom/hand-painted items that will need instructions
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
            "JazzCash": f"{st.secrets["Banking"]["Phone"]}",
            "EasyPaisa": f"{st.secrets["Banking"]["Phone"]}",
            "Raast": f"{st.secrets["Banking"]["Phone"]}"
        }

        bank_transfer_details = {
            "Bank Name": "HBL",
            "Account Title": "TOOBA",
            "Account Number": f"{st.secrets["Banking"]["Account"]}",
            "IBAN": f"{st.secrets["Banking"]["IBAN"]}"
        }

        st.markdown('<p class="required">Payment Method</p>', unsafe_allow_html=True)
        payment_method = st.selectbox(
            "",
            ["Cash on Delivery", "Mobile Money (Jazzcash etc)", "Bank Transfer"],
            index=0,
            key="payment_method"
        )

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
            transaction_ref = st.text_input("", placeholder="Enter bank transfer reference", key="transaction_ref")

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
            # Make instructions required for custom/hand-painted items
            if has_custom_items and not instructions:
                missing_fields.append("Instructions (required for custom/hand-painted items)")
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
                successful_items = 0
                order_number = generate_order_number()
                order_rows = ""
                total_amount = 0
                for item_key, item_data in st.session_state.cart.items():
                    item_total = item_data['quantity'] * item_data['price']
                    total_amount += item_total
                    order_rows += f"""
                        <tr>
                            <td>{item_data['name']}</td>
                            <td>{item_data['style']}</td>
                            <td>{item_data['quantity']}</td>
                            <td>Rs. {item_data['price']}</td>
                            <td>Rs. {item_total}</td>
                        </tr>
                    """
                    payment_service = None
                    transaction_reference = None

                    if payment_method == "Mobile Money (Jazzcash etc)":
                        payment_service = mobile_service if mobile_service != "Other" else other_service
                        transaction_reference = transaction_id
                    elif payment_method == "Bank Transfer":
                        payment_service = "Bank Transfer"
                        transaction_reference = transaction_ref

                    order_data = [
                        name,
                        email,
                        phone,
                        address_street,
                        address_city,
                        postal_code,
                        item_data['name'],
                        item_data['style'],
                        item_data['quantity'],
                        item_data['price'],
                        item_data['price'] * item_data['quantity'],
                        instructions,
                        order_date,
                        payment_method,
                        payment_service,
                        transaction_reference,
                        "Pending",
                        "Pending"
                    ]

                    try:
                        add_data(order_number, order_data)
                        successful_items += 1
                    except Exception as e:
                        st.error(f"Failed to submit order for {item_key}: {str(e)}")
                        continue

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
                           <strong>Transaction Reference:</strong> {transaction_reference or "N/A"}</p>

                        <p><strong>Special Instructions:</strong> {instructions or "N/A"}</p>

                        <p>We will process your order shortly. Thank you for shopping with Tumble Cup!</p>
                    </body>
                    </html>
                    """
                    st.success(
                        f"Order submitted successfully! {successful_items} item(s) added to your order. \n Email has been sent to {email} Please check your spam or junk!")
                    st.toast(f"Order {order_number} has been placed successfully!")
                    send_email(f"{order_number} has been placed successfully!", f"{html_body}", str(email))
                    st.subheader("Order Summary")
                    summary_cols = st.columns(2)
                    with summary_cols[0]:
                        for item_key, item_data in st.session_state.cart.items():
                            st.write(
                                f"**{item_key}:** {item_data['quantity']} × Rs. {item_data['price']} = Rs. {item_data['price'] * item_data['quantity']}")
                        st.write(f"**Total:** Rs. {cart_total}")
                    with summary_cols[1]:
                        st.write(f"**Order Date:** {order_date}")
                        st.write(f"**Payment Method:** {payment_method}")
                        st.write(f"**Delivery Address:** {address_street}, {address_city}, {postal_code}")
                        st.write(f"**Instructions:** {instructions}")
                        st.write(f"**Status:** Pending")

                    st.session_state.cart = {}
                else:
                    st.error("Failed to submit any items in your order. Please try again.")

with tab4:
    st.header("Admin Panel")
    admin_password = st.text_input("Enter Admin Password", type="password")
    pwd = st.secrets["Password"]["Password"]
    if admin_password == str(pwd):
        st.success("Admin authenticated!")
        selected_month = st.selectbox(
            "Select Month",
            month_list,
            index=current_month - 1,
            placeholder="Select Month"
        )
        selected_month_number = month_list.index(selected_month) + 1 if selected_month else None
        orders_df = get_orders(selected_month_number)
        orders_df["order_date"] = pd.to_datetime(orders_df["order_date"], errors="coerce").dt.strftime("%d-%B-%Y")
        if not orders_df.empty:
            search_term = st.text_input("Search by Name or Order Number", placeholder="Enter Search Term",
                                        key="search_term")
            if search_term:
                orders_df = orders_df[orders_df['customer_name'].str.contains(search_term, case=False) |
                                      orders_df['order_number'].str.contains(search_term, case=False)]

                if orders_df.empty:
                    st.warning("No such orders found!")
                else:

                    status_filter = st.multiselect("Filter by Status", options=orders_df['status'].unique().tolist(),
                                                   default=orders_df['status'].unique().tolist())
                    payment_filter = st.multiselect("Filter by Payment Status",
                                                    options=orders_df['payment_status'].unique().tolist(),
                                                    default=orders_df['payment_status'].unique().tolist())

                    filtered_df = orders_df[orders_df['status'].isin(status_filter) &
                                            orders_df['payment_status'].isin(payment_filter)]

                    st.dataframe(filtered_df)

                    st.subheader("Update Order Status")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        order_id = st.number_input("Order ID", min_value=1, max_value=int(orders_df['id'].max()),
                                                   step=1)
                    with col2:
                        new_status = st.selectbox("New Status",
                                                  ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"])
                    with col3:
                        if st.button("Update Status"):
                            conn = init_db()
                            c = conn.cursor()
                            c.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
                            conn.commit()
                            conn.close()
                            st.success(f"Order #{order_id} status updated to {new_status}")
                            st.rerun()
                    if st.button("Export Orders to CSV"):
                        csv = filtered_df.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"tumble_cup_orders_{datetime.today().strftime('%Y-%m-%d')}.csv",
                            mime="text/csv"
                        )
            else:

                status_filter = st.multiselect("Filter by Status", options=orders_df['status'].unique().tolist(),
                                               default=orders_df['status'].unique().tolist())
                payment_filter = st.multiselect("Filter by Payment Status",
                                                options=orders_df['payment_status'].unique().tolist(),
                                                default=orders_df['payment_status'].unique().tolist())

                filtered_df = orders_df[orders_df['status'].isin(status_filter) &
                                        orders_df['payment_status'].isin(payment_filter)]
                st.dataframe(filtered_df)

                st.subheader("Update Order & Payment Status")
                col1, col2, col3 = st.columns(3)
                with col1:
                    order_id = st.number_input("Order ID", min_value=1,
                                               max_value=int(orders_df['id'].max()) if not orders_df.empty else 1,
                                               step=1)
                    payment_order_id = st.number_input("Payment Order ID", min_value=1,
                                                       max_value=int(
                                                           orders_df['id'].max()) if not orders_df.empty else 1,
                                                       step=1)
                    delete_order_id = st.number_input("Delete Order ID", min_value=1,
                                                      max_value=int(
                                                          orders_df['id'].max()) if not orders_df.empty else 1,
                                                      step=1)
                with col2:
                    new_status = st.selectbox("New Status",
                                              ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"])
                    payment_new_status = st.selectbox("Payment New Status",
                                                      ["Pending", "Processing", "Confirmed", "Cancelled"])
                with col3:
                    if st.button("Update Status"):
                        conn = init_db()
                        c = conn.cursor()
                        c.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
                        conn.commit()
                        conn.close()
                        st.success(f"Order #{order_id} status updated to {new_status}")
                        st.rerun()

                    if st.button("Update Payment Status"):
                        conn = init_db()
                        c = conn.cursor()
                        c.execute("UPDATE orders SET payment_status = ? WHERE id = ?",
                                  (payment_new_status, payment_order_id))
                        conn.commit()
                        conn.close()
                        st.success(f"Order #{payment_order_id} payment status updated to {payment_new_status}")
                        st.rerun()

                    if st.button("Delete Order"):
                        conn = init_db()
                        c = conn.cursor()
                        c.execute("DELETE FROM orders WHERE id = ?",
                                  (delete_order_id,))
                        conn.commit()
                        conn.close()
                        st.success(f"Order #{delete_order_id} has been deleted")
                        st.rerun()

                if st.button("Export Orders to CSV"):
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"tumble_cup_orders_{datetime.today().strftime('%Y-%m-%d')}.csv",
                        mime="text/csv"
                    )
                st.subheader("Database Security Tools")
                if st.button("Check Encryption Status"):
                    try:

                        conn = init_db()
                        c = conn.cursor()
                        c.execute("SELECT customer_name FROM orders LIMIT 1")
                        sample = c.fetchone()
                        conn.close()

                        if sample and sample[0]:
                            try:
                                decrypt_data(sample[0])
                                st.success("✅ Database encryption is active and working correctly!")
                            except:
                                st.warning("⚠️ Some records may not be encrypted. Consider upgrading all records.")
                        else:
                            st.info("No records found to check encryption status.")
                    except Exception as e:
                        st.error(f"Error checking encryption: {str(e)}")

                if st.button("Backup Database"):
                    try:
                        import shutil

                        backup_file = f"tumblecup_backup_{datetime.today().strftime('%Y%m%d_%H%M%S')}.db"
                        shutil.copy2(DB_PATH, backup_file)

                        with open(backup_file, "rb") as f:
                            bytes_data = f.read()

                        st.download_button(
                            label="Download Database Backup",
                            data=bytes_data,
                            file_name=backup_file,
                            mime="application/octet-stream"
                        )
                        st.success(f"Database backed up successfully as {backup_file}")
                    except Exception as e:
                        st.error(f"Backup failed: {str(e)}")
        else:
            st.info("No orders found in the database.")
    elif admin_password:
        st.error("Incorrect password")

if __name__ == '__main__':
    init_db()
