from http import cookies
import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu
from datetime import datetime,timedelta ,date
from streamlit_cookies_manager import EncryptedCookieManager
from Home import check_access 
import json
import time
from collections import defaultdict
import plotly.express as px


cookies = EncryptedCookieManager(prefix="inventory_app_", password="2023")


def check_access(required_role=None):
    """Ensures the user is logged in and has the correct role. Shows a loading spinner while fetching cookies."""

    # Show a spinner while waiting for cookies to be ready
    if not cookies.ready():
        with st.spinner("🔄 Fetching session cookies... Please wait."):
            time.sleep(2)  # Short delay to allow UI to update before rerunning
        st.rerun()  # Restart script after waiting

    # Restore session from cookies if missing
    if "logged_in" not in st.session_state or not st.session_state.get("logged_in", False):
        if cookies.get("logged_in") == "True":
            st.session_state.logged_in = True
            user_data = cookies.get("user")

            if user_data and user_data != "{}":  # Ensure user data is not empty
                try:
                    st.session_state.user = json.loads(user_data)
                    time.sleep(1)  # Small delay to prevent UI flickering
                    st.rerun()  # Force rerun after restoring session
                except json.JSONDecodeError:
                    st.session_state.user = None
                    st.error("⚠️ Corrupted user session. Please log in again.")
                    st.stop()
        else:
            st.warning("⚠️ You must log in to access this page.")
            st.stop()

    # Ensure user session is valid
    if "user" not in st.session_state or not isinstance(st.session_state.user, dict) or not st.session_state.user:
        st.error("🚫 Invalid user session. Please log in again.")
        st.stop()

    # Check role access if required_role is specified
    user_role = st.session_state.user.get("role", None)
    if required_role and user_role != required_role:
        st.error("🚫 Unauthorized Access! You don't have permission to view this page.")
        st.stop()


# Ensure session state is initialized to prevent errors
if "user" not in st.session_state:
    st.session_state.user = {}  # Initialize as an empty dictionary

# 🔹 **Check Access for Inventory Role**
check_access(required_role="Inventory")






# connecting to supabase

from supabase import create_client
# supabase configurations
def get_supabase_client():
    supabase_url = 'https://bpxzfdxxidlfzvgdmwgk.supabase.co' # Your Supabase project URL
    supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJweHpmZHh4aWRsZnp2Z2Rtd2drIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI3NjM0MTQsImV4cCI6MjA1ODMzOTQxNH0.vQq2-VYCJyTQDq3QN2mJprmmBR2w7HMorqBuzz43HRU'
    supabase = create_client(supabase_url, supabase_key)
    return supabase  # Make sure to return the client

# Initialize Supabase client
supabase = get_supabase_client() # use this to call the supabase database


st.subheader("📦 REAL TIME INVENTORY MANAGEMENT SYSTEM")

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()  # ✅ Clear cached data
    st.rerun() # ✅ Force rerun of the app



with st.sidebar:
    selected = option_menu(
        menu_title=('Options'),
        options=["Home","Add", "Delete","Calculations","Filter","Reports"],
        icons=["house", "plus-circle", "trash", "calculator","bar-chart-line"],
        default_index=0
    )


#
# === Define today's date ===
today = date.today()

# Convert today's date to a string (YYYY-MM-DD format)
today_str = today.strftime("%Y-%m-%d")

# fetch restock history data
@st.cache_data(ttl=60*5)
def restock_history_data():
    supabase = get_supabase_client()  # Make sure this is defined
    response = supabase.table("restock_history").select("*").execute()
    return response.data
# Cache inventory data for 5 minutes
@st.cache_data(ttl=60*5)
def fetch_inventory():
    # Fetch inventory data from Supabase
    return supabase.table("inventory_master_log").select("*").execute().data

# Cache requisition data for 5 minutes
@st.cache_data(ttl=60 * 5)
def fetch_inventory():
    return supabase.table("restock_log").select("*").execute().data

@st.cache_data(ttl=60*5)
def fetch_requisitions():
    response = supabase.table('restock_log').select("*").execute()
    if response.data:
        return pd.DataFrame(response.data)  # Convert data to a DataFrame
    return pd.DataFrame() 

# Function to create item dictionary
def create_item_dict(inventory_data):
    item_list = [(item["item_id"], item["item_name"]) for item in inventory_data]
    item_dict = {name: id_ for id_, name in item_list}
    return item_dict

@st.cache_data(ttl=300)
def fetch_inventory_items():
    response = supabase.table("inventory_master_log").select("item_id, item_name").execute()
    items = response.data
    item_dict = {item["item_name"]: item["item_id"] for item in items}
    return item_dict

inventory_data = fetch_inventory() 

# === Create item_dict from inventory data ===
item_dict = fetch_inventory_items()

with st.spinner("Fetching data..."):
    restock = fetch_inventory()
    

# === Display Inventory ===



if selected=='Home':
    st.subheader("📋 Good Receive Data")
    st.write('Temporary Table')
    requisitions = fetch_requisitions()  # Fetch the requisitions
    if not requisitions.empty:
        st.dataframe(requisitions)  # Display requisitions
    else:
        st.info("No requisitions available.")
    st.subheader('Permanent Data')
    restock_history_df = pd.DataFrame(restock_history_data())
    if not restock_history_df.empty:
         st.dataframe(restock_history_df) # Display requisitions
    else:
        st.info("No requisitions available.")
    

if selected == 'Add':
    # 🧱 Inputs
    item_name = st.selectbox("Select Item", list(item_dict.keys()))
    category = st.text_input('Category', placeholder='Enter category')
    supply = st.number_input("Supply", min_value=0, step=1, value=0)
    cost = st.number_input("Cost", min_value=0, step=1, value=0)
    requested_quantity = st.number_input("Quantity Requested", min_value=0, value=0, step=1)
    supplier = st.text_input("Requisited By", placeholder="Enter requisitioned by")
    remark = st.text_area("Remark")
    restock_date = st.date_input("Requisition Date", value=date.today())

    # 🧭 Button
    submit = st.button("📤 Submit")

    if submit:
        # ✅ Validate required fields
        if not category.strip() or not supply or requested_quantity is None:
            st.warning("⚠️ Please fill in all required fields (Category, Supply, Requested Quantity).")
        else:
            data = {
                "item_id": item_dict[item_name],
                'item_name': item_name,
                "category": category,
                "supply": supply,
                "cost": cost,
                "requested_quantity": requested_quantity,
                "supplier": supplier.strip(),
                "remark": remark.strip(),
                "restock_date": restock_date.strftime("%Y-%m-%d")
            }

            st.write("📦 Submitting data:", data)  # Debugging

            # 🚀 Submit to Supabase
            response = supabase.table("restock_log").insert(data).execute()

            if response.data:
                st.success(f"✅ Requisition for '{item_name}' submitted successfully!")
                st.cache_data.clear() 
                 # Clears the data cache used by @st.cache_data
                 # Clears the memo cache
            else:
                st.error(f"❌ Failed to submit requisition. Response: {response}")










# Function to preview restock history record




def preview_restock_history_record(restock_id_to_delete, date_to_delete):
    """Preview the restock history record for the given restock_id and date."""
    try:
        # Fetch the restock history record
        restock_history_response = supabase.table("restock_history")\
            .select("*")\
            .eq("restock_id", restock_id_to_delete)\
            .eq("restock_date", date_to_delete)\
            .execute().data

        if not restock_history_response:
            st.warning(f"No restock history record found for Restock ID {restock_id_to_delete} on {date_to_delete}.")
            return None

        restock_history_record = restock_history_response[0]
        st.write("**Preview of the record to delete:**")
        st.write(f"Item Name: {restock_history_record['item_name']}")
        st.write(f"Item ID: {restock_history_record['item_id']}")
        st.write(f"Restocked Quantity: {restock_history_record['supply']}")
        st.write(f"Restock Date: {restock_history_record['restock_date']}")

        return restock_history_record

    except Exception as e:
        st.error(f"❌ Error while fetching record: {e}")
        return None





if selected == 'Delete':
    st.header("🗑️ Delete Restock Record by ID")

    # 1. Input the Restock ID and Date to delete
    restock_id_to_delete = st.text_input("Enter Restock ID to Delete", "")
    date_to_delete = st.date_input("Enter Restock Date to Delete")

    # Check if the necessary inputs are provided
    if restock_id_to_delete and date_to_delete:
        # 2. Fetch restock records from both tables
        restock_history_data = supabase.table("restock_history")\
            .select("*")\
            .eq("restock_id", restock_id_to_delete)\
            .eq("restock_date", date_to_delete)\
            .execute().data

        restock_log_data = supabase.table("restock_log")\
            .select("*")\
            .eq("restock_id", restock_id_to_delete)\
            .eq("restock_date", date_to_delete)\
            .execute().data

        # Combine data from both tables
        if restock_history_data:
            selected_restock = restock_history_data[0]
        elif restock_log_data:
            selected_restock = restock_log_data[0]
        else:
            selected_restock = None

        # Check if a restock record is found
        if selected_restock:
            # Display the restock details for confirmation
            st.subheader("Restock Details to Delete")
            st.write(f"**Restock ID:** {selected_restock['restock_id']}")
            st.write(f"**Item ID:** {selected_restock['item_id']}")
            st.write(f"**Supply Added:** {selected_restock['supply']}")
            st.write(f"**Restock Date:** {selected_restock['restock_date']}")

            # 3. Confirm deletion
            if st.button("🗑️ Delete This Restock"):
                try:
                    # 4. Delete from restock_history if the record exists
                    if restock_history_data:
                        supabase.table("restock_history").delete()\
                            .eq("restock_id", selected_restock["restock_id"])\
                            .eq("restock_date", selected_restock["restock_date"]).execute()

                    # 5. Delete from restock_log if the record exists
                    if restock_log_data:
                        supabase.table("restock_log").delete()\
                            .eq("restock_id", selected_restock["restock_id"])\
                            .eq("restock_date", selected_restock["restock_date"]).execute()

                    # 6. Optionally, update inventory if the record exists
                    item_id = selected_restock.get("item_id")
                    supply_added = selected_restock.get("supply")

                    if item_id and supply_added:
                        # Fetch current inventory data
                        inventory_item = supabase.table("inventory_master_log")\
                            .select("supply")\
                            .eq("item_id", item_id)\
                            .single().execute().data
                        
                        if inventory_item:
                            # Deduct the added supply from inventory (since we are deleting the restock)
                            new_supply = inventory_item["supply"] - supply_added
                            supabase.table("inventory_master_log").update({"supply": new_supply})\
                                .eq("item_id", item_id).execute()

                    # Success message after deletion from both tables and inventory update
                    st.success("✅ Restock record deleted and inventory updated successfully.")
                    

                except Exception as e:
                    st.error(f"❌ Failed to delete: {e}")
        else:
            st.error("❌ No restock record found with the given Restock ID and Date.")
    else:
        st.info("Please enter a Restock ID and Restock Date to delete.")






def get_item_aggregation(item, start_date, end_date, aggregation, field):
    try:
        supabase = get_supabase_client()

        # Fetch relevant data from the 'restock_history' table
        response = supabase.table("restock_history")\
            .select("restock_date, item_name, " + field)\
            .eq("item_name", item)\
            .gte("restock_date", start_date.strftime("%Y-%m-%d"))\
            .lte("restock_date", end_date.strftime("%Y-%m-%d"))\
            .execute()

        data = response.data

        if not data:
            return f"No data found for '{item_name}' between {start_date} and {end_date}.", None

        df = pd.DataFrame(data)

        # Numeric fields
        numeric_fields = ["supply", "cost", "requested_quantity"]
        if field in numeric_fields:
            df[field] = pd.to_numeric(df[field], errors="coerce")

            if aggregation == "SUM":
                result = df[field].sum()
            elif aggregation == "AVG":
                result = df[field].mean()
            elif aggregation == "MIN":
                result = df[field].min()
            elif aggregation == "MAX":
                result = df[field].max()
            elif aggregation == "COUNT":
                result = df[field].count()
            else:
                return "❌ Invalid aggregation type selected.", None

        # Non-numeric fields
        else:
            if aggregation == "COUNT":
                result = df[field].value_counts().to_dict()
            elif aggregation == "MODE":
                result = df[field].mode().iloc[0] if not df[field].mode().empty else "No mode"
            else:
                return f"❌ Aggregation '{aggregation}' not supported for non-numeric fields.", None

        return None, result

    except Exception as e:
        return f"❌ An error occurred: {e}", None


# ---- Streamlit UI ----
if selected == "Calculations":
    st.subheader("📊 Item Aggregation")

    item_name = st.selectbox("Select Item", list(item_dict.keys()))

    # Select field to aggregate
    available_fields = ["supply", "cost", "requested_quantity", "category", "supplier", "remark"]
    field = st.selectbox("Select Field to Aggregate", available_fields)

    # Aggregation options
    if field in ["supply", "cost", "requested_quantity"]:
        aggregation = st.selectbox("Select Aggregation Function", ["SUM", "AVG", "MIN", "MAX", "COUNT"])
    else:
        aggregation = st.selectbox("Select Aggregation Function", ["COUNT", "MODE"])

    # Date range
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")

    if st.button("Calculate"):
        if item_name and field and aggregation and start_date and end_date:
            msg, result = get_item_aggregation(item_name, start_date, end_date, aggregation, field)
            if msg:
                st.warning(msg)
            else:
                if isinstance(result, dict):
                    st.write(f"### {aggregation} of `{field}` for '{item_name}':")
                    st.dataframe(pd.DataFrame(list(result.items()), columns=[field, "Count"]))
                else:
                    st.success(f"✅ {aggregation} of `{field}` for '{item_name}' from {start_date} to {end_date}: **{result}**")
        else:
            st.warning("⚠️ Please complete all fields.")







## filter section
def filter_inventory_log(filter_column, filter_value):
    try:
        # Query Supabase
        response = supabase.table("restock_history").select("*").eq(filter_column, filter_value).execute()

        # Convert response to DataFrame
        if response.data:
            return pd.DataFrame(response.data)
        else:
            return pd.DataFrame()  # Return empty DataFrame if no results

    except Exception as e:
        st.error(f"❌ Error fetching filtered data: {e}")
        return pd.DataFrame()


# function to filter by date
def filter_by_date(start_date, end_date):
    try:
        response = (
            supabase.table("restock_history")
            .select("*")
            .gte("restock_date", str(start_date))
            .lte("restock_date", str(end_date))
            .execute()
        )

        if response.data:
            return pd.DataFrame(response.data)
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"❌ Error fetching data: {e}")
        return pd.DataFrame()



# function to filter by date and item

def filter_by_item_and_date(item, start_date, end_date):
    try:
        response = (
            supabase.table("restock_history")
            .select("*")
            .eq("item_name", item_name)
            .gte("restock_date", str(start_date))
            .lte("restock_date", str(end_date))
            .execute()
        )

        if response.data:
            return pd.DataFrame(response.data)
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"❌ Error fetching data: {e}")
        return pd.DataFrame()


# streamlit code
# Streamlit App
# Streamlit App
if selected == "Filter":
    st.subheader("🔍 Filter log")

    # Select Filter Type
    filter_option = st.selectbox("Select Filter Type", ["Filter by Column", "Filter by Date", "Filter by Item & Date"])

    if filter_option == "Filter by Column":
        filter_column = st.selectbox("📌 Select Column to Filter By", 
                                     ["item_name", "category", "supply","cost", "requested_quantity","supplier","remark"])
        filter_value = st.text_input(f"Enter {filter_column} Value:")

        if st.button("🔎 Apply Filter"):
            if filter_value:
                filtered_df = filter_inventory_log(filter_column, filter_value)

                if not filtered_df.empty:
                    st.success(f"✅ Filter Applied Successfully!")
                    st.dataframe(filtered_df)
                else:
                    st.warning(f"⚠️ No records found for {filter_column} = {filter_value}")
            else:
                st.warning("⚠️ Please enter a filter value.")

    elif filter_option == "Filter by Date":
        st.subheader("Filter by Date")
        start_date = st.date_input("Start Date", date.today() - timedelta(days=30))  # Fixed
        end_date = st.date_input("End Date", date.today())  # Fixed

        if st.button("Apply Date Filter"):
            if start_date and end_date:
                filtered_df = filter_by_date(start_date, end_date)

                if not filtered_df.empty:
                    st.success("✅ Date Filter Applied Successfully!")
                    st.dataframe(filtered_df)
                else:
                    st.warning("⚠️ No results found for the selected date range.")

    elif filter_option == "Filter by Item & Date":
        st.subheader("Filter by Item & Date")
        item_name = st.selectbox("Select Item", list(item_dict.keys()))
        
        # Correct way to get today's date and subtract 30 days
        start_date = st.date_input("Start Date", date.today() - timedelta(days=30))  # Fixed
        end_date = st.date_input("End Date", date.today())  # Fixed

        if st.button("Apply Item & Date Filter"):
            if item_name and start_date and end_date:
                filtered_df = filter_by_item_and_date(item_name, start_date, end_date)

                if not filtered_df.empty:
                    st.success(f"✅ Filter Applied for '{item_name}' from {start_date} to {end_date}")
                    st.dataframe(filtered_df)
                else:
                    st.warning(f"⚠️ No results found for '{item_name}' in the selected date range.")




# Load data
# Function to fetch restock history data
def restock_history_data():
    supabase = get_supabase_client()  # Make sure this is defined
    response = supabase.table("restock_history").select("*").execute()
    return response.data

# Now when you use the variable, make sure it’s not overwriting the function name
restock_data = restock_history_data()  # Call the function and store its result in a different variable

# Check if the data is valid before creating the DataFrame
if restock_data and isinstance(restock_data, list):
    restock_history_df = pd.DataFrame(restock_data)
    
else:
    st.error("❌ Invalid or empty data returned from the database.")


if selected == "Reports":

    st.title("📦 Restock History Report")

    # --- Ensure 'restock_date' exists and is in datetime format ---
    if 'restock_date' in restock_history_df.columns:
        restock_history_df['restock_date'] = pd.to_datetime(restock_history_df['restock_date'], errors='coerce')
    else:
        st.error("❌ 'restock_date' column not found in the data.")
        st.stop()

    # --- Date Filter ---
    st.markdown("### 📅 Date Filter")
    min_date = restock_history_df['restock_date'].min().date()
    max_date = restock_history_df['restock_date'].max().date()

    start_date = st.date_input("Start Date", min_value=min_date, value=min_date)
    end_date = st.date_input("End Date", min_value=min_date, value=max_date)

    # --- Dropdown Filters ---
    categories = restock_history_df['category'].dropna().unique().tolist()
    suppliers = restock_history_df['supplier'].dropna().unique().tolist()
    
    if 'item_name' not in restock_history_df.columns:
        st.error("❌ 'item_name' column not found in the data.")
        st.stop()

    item_names = st.selectbox("Select Item", list(item_dict.keys()))

    category_filter = st.multiselect("Filter by Category", categories)
    supplier_filter = st.multiselect("Filter by Supplier", suppliers)
    item_filter = st.multiselect("Filter by Item Name", item_names)

    # --- Apply Filters ---
    filtered_df = restock_history_df[
        (restock_history_df['restock_date'].dt.date >= start_date) &
        (restock_history_df['restock_date'].dt.date <= end_date)
    ]
    if item_filter:
        filtered_df = filtered_df[filtered_df['item_name'].isin(item_filter)]
    if category_filter:
        filtered_df = filtered_df[filtered_df['category'].isin(category_filter)]
    if supplier_filter:
        filtered_df = filtered_df[filtered_df['supplier'].isin(supplier_filter)]

    # --- Summary Statistics ---
    st.markdown("### 📊 Summary Statistics")
    total_items = filtered_df['item_name'].nunique()
    total_quantity = filtered_df['supply'].sum()
    total_cost = filtered_df['cost'].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("🛒 Unique Items", total_items)
    col2.metric("📦 Total Quantity Supplied", total_quantity)
    col3.metric("💰 Total Cost", f"₦{total_cost:,.2f}")

    # --- Top 5 Supplied Items ---
    st.markdown("#### 🏆 Top 5 Supplied Items")
    top_items = filtered_df.groupby('item_name')['supply'].sum().sort_values(ascending=False).head(5)
    st.dataframe(top_items.reset_index())

    # --- Top 5 Suppliers ---
    st.markdown("#### 🏆 Top 5 Suppliers by Cost")
    top_suppliers = filtered_df.groupby('supplier')['cost'].sum().sort_values(ascending=False).head(5)
    st.dataframe(top_suppliers.reset_index())

    # --- Charts ---
    st.markdown("### 📈 Visual Insights")

    fig1 = px.bar(top_items.reset_index(), x='item_name', y='supply', title='Top 5 Supplied Items')
    st.plotly_chart(fig1)

    fig2 = px.pie(top_suppliers.reset_index(), names='supplier', values='cost', title='Cost by Supplier')
    st.plotly_chart(fig2)

    # --- Full Table View ---
    st.markdown("### 📄 Full Restock History (Filtered)")
    st.dataframe(filtered_df[['restock_date', 'item_name', 'category', 'supply', 'cost', 'supplier', 'remark']])
     

    st.markdown("### 💾 Download Filtered Data")

@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

if selected == 'Reports':
    csv_data = convert_df_to_csv(filtered_df)

    st.download_button(
    label="⬇️ Download CSV",
    data=csv_data,
    file_name='filtered_restock_history.csv',
    mime='text/csv' )
