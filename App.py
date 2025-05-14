import calendar
import os
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st
DB_PATH = "tumble_cup.db"


def init_db():

    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                total_price REAL NOT NULL,
                instructions TEXT,
                order_date TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                payment_service TEXT,
                transaction_id TEXT,
                status TEXT DEFAULT 'Pending'
            )
        ''')

        conn.commit()
        print("Database and table created.")
    else:
        conn = sqlite3.connect(DB_PATH)
        print("Database already exists.")

    # Return the connection to be used later
    return conn


# Add data to SQLite
def add_data(data):
    conn = init_db()
    c = conn.cursor()

    c.execute('''
              INSERT INTO orders (customer_name, email, phone, item_name, quantity,
                                  price, total_price, instructions, order_date,
                                  payment_method, payment_service, transaction_id, status)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
              ''', data)

    conn.commit()
    conn.close()
    return True


# Get order count
def count_orders():
    conn = init_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM orders')
    count = c.fetchone()[0]
    conn.close()
    return count


# Get all orders as DataFrame
def get_orders():
    conn = init_db()
    df = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()
    return df


# Current date information
month_list = list(calendar.month_name)[1:]
current_month = datetime.today().month
current_month_name = calendar.month_name[current_month]
current_year = datetime.today().year

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

# Create tabs for Shopping, Checkout, and Admin
tab1, tab2, tab3 = st.tabs(["Shop Items", "Checkout", "Admin Panel"])

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
                # Counter for successful item submissions
                successful_items = 0

                # Process each item in the cart as a separate order row
                for item_name, item_data in st.session_state.cart.items():
                    # Prepare data for submission
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
                        item_name,
                        item_data['quantity'],
                        item_data['price'],
                        item_data['price'] * item_data['quantity'],
                        instructions,
                        order_date,
                        payment_method,
                        payment_service,
                        transaction_reference,
                        "Pending"
                    ]

                    try:
                        add_data(order_data)
                        successful_items += 1
                    except Exception as e:
                        st.error(f"Failed to submit order for {item_name}: {str(e)}")
                        continue

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

# Admin Panel Tab
with tab3:
    st.header("Admin Panel")

    # Simple password protection
    admin_password = st.text_input("Enter Admin Password", type="password")
    if admin_password == "admin123":
        st.success("Admin authenticated!")

        st.subheader("All Orders")
        orders_df = get_orders()

        if not orders_df.empty:
            # Add filter options
            status_filter = st.multiselect("Filter by Status", options=orders_df['status'].unique().tolist(),
                                           default=orders_df['status'].unique().tolist())

            # Apply filters
            filtered_df = orders_df[orders_df['status'].isin(status_filter)] if status_filter else orders_df

            # Display orders
            st.dataframe(filtered_df)

            # Allow status updates
            st.subheader("Update Order Status")

            col1, col2, col3 = st.columns(3)
            with col1:
                order_id = st.number_input("Order ID", min_value=1,
                                           max_value=int(orders_df['id'].max()) if not orders_df.empty else 1, step=1)
            with col2:
                new_status = st.selectbox("New Status", ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"])
            with col3:
                if st.button("Update Status"):
                    conn = init_db()
                    c = conn.cursor()
                    c.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
                    conn.commit()
                    conn.close()
                    st.success(f"Order #{order_id} status updated to {new_status}")
                    st.rerun()

            # Export to CSV
            if st.button("Export Orders to CSV"):
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"tumble_cup_orders_{datetime.today().strftime('%Y-%m-%d')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("No orders found in the database.")
    elif admin_password:
        st.error("Incorrect password")

if __name__ == '__main__':

    init_db()