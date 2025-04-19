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
import io
import plotly.express as px

cookies = EncryptedCookieManager(prefix="inventory_app_", password="2018")


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
        options=["Home", "Filter","Reports"],
        icons=["house", "plus-circle","bar-chart-line"],
        default_index=0
    )



# === Helper function to get today's date ===
# === Setup ===
today = str(date.today()) #this is to set up the todays date

# === Fetch data from Supabase ===
@st.cache_data(ttl=60 * 5)
def fetch_inventory():
    return supabase.table("inventory_master_log").select("*").execute().data

@st.cache_data(ttl=60 * 5) # to load requisition table
def fetch_requisitions():
    return supabase.table("requisition").select("*").eq("requisition_date", today).execute().data

@st.cache_data(ttl=60 * 5) # this is to load restock table
def fetch_restocks():
    return supabase.table("restock_log").select("*").eq("restock_date", today).execute().data

# === Load data ===
with st.spinner("Fetching data..."): # this is to show data is loading and not to show error until data loads
    inventory = fetch_inventory()
    requisitions = fetch_requisitions()
    restocks = fetch_restocks()


df_inventory = pd.DataFrame(inventory)

# === Display Inventory ===
if selected == 'Home':
    st.subheader("📋 Current Inventory")
    df_inventory = pd.DataFrame(inventory)
    st.dataframe(df_inventory)
    selected_date = st.date_input("Select Date to Update Inventory", value=date.today())


# Clean and standardize item_name
df_inventory["item_name"] = (
    df_inventory["item_name"]
    .str.strip()
    .str.lower()
    .str.replace(r"\s+", " ", regex=True)  # collapse multiple spaces
    .str.replace(r"\s*\(\s*", "(", regex=True)  # fix spaces before '('
    .str.replace(r"\s*\)\s*", ")", regex=True)  # fix spaces after ')'
    .str.title()
)


# === Function to Move Today's Requisitions to Requisition History ===

def move_requisitions_to_history(selected_date):
    # Fetch today's requisitions
    requisitions_today = supabase.table("requisition").select("*").eq("requisition_date", str(selected_date)).execute().data
    
    if requisitions_today:
        # Get the schema of the requisition_history table
        table_schema = supabase.table("requisition_history").select("*").limit(1).execute().data
        if not table_schema:
            st.error("❌ Failed to retrieve requisition history table schema!")
            return

        # Extract columns from the schema to ensure only valid columns are inserted
        valid_columns = table_schema[0].keys()

        # Filter requisitions_today to only include valid columns
        filtered_requisitions = [
            {key: entry[key] for key in entry if key in valid_columns} 
            for entry in requisitions_today
        ]

        # Loop over requisitions and update or insert as necessary
        for entry in filtered_requisitions:
            requisition_id = entry.get("requisition_id")

            # Try to update existing records
            update_response = supabase.table("requisition_history").upsert(entry).execute()

            # Check if the response is successful
            if update_response.data:
                # If update was successful, delete the requisition from today's list
                delete_response = supabase.table("requisition").delete().eq("requisition_id", requisition_id).execute()
                
                if delete_response.data:  # Check if delete response is successful
                    st.success(f"✅ Requisition ID {requisition_id} moved to requisition history.")
                else:
                    st.error(f"❌ Failed to delete requisition ID {requisition_id}: {delete_response.error}")
            else:
                st.error(f"❌ Failed to update requisition ID {requisition_id}: {update_response.error}")
    else:
        st.info("ℹ️ No requisitions found for today.")

## function to move the retock part

def move_restocks_to_history(selected_date):
    # Fetch today's restocks
    restocks_today = supabase.table("restock_log").select("*").eq("restock_date", str(selected_date)).execute().data
    if restocks_today:
        for restock in restocks_today:
            # Check if restock can be moved to history
            response = supabase.table("restock_history").upsert(restock).execute()
            if response.data:
                # Delete restock from today's list
                delete_response = supabase.table("restock_log").delete().eq("restock_id", restock["restock_id"]).execute()
                if delete_response.data:
                    st.success(f"✅ Restock ID {restock['restock_id']} moved to history.")
                else:
                    st.error("❌ Failed to delete restock from today.")
            else:
                st.error(f"❌ Failed to move restock ID {restock['restock_id']} to history.")
    else:
        st.info("ℹ️ No restocks found for today.")
            


## function to update and move the requisition and restock
def update_inventory_balances(selected_date):
    # Fetch today's requisitions and restocks
    requisitions_today = supabase.table("requisition").select("*").eq("requisition_date", str(selected_date)).execute().data
    restocks_today = supabase.table("goods_bought").select("*").eq("purchase_date", str(selected_date)).execute().data

   

    # If both are empty, show a warning and stop
    if not requisitions_today and not restocks_today:
        st.warning("⚠️ No restocks or requisitions to update today.")
        return

    # Process restocks
    restock_dict = defaultdict(int)
    for entry in restocks_today:
        restock_dict[entry["item_id"]] += entry.get("supply", 0)

    # Process requisitions
    requisition_dict = defaultdict(int)
    return_dict = defaultdict(int)
    for entry in requisitions_today:
        requisition_dict[entry["item_id"]] += entry.get("stock_out", 0)
        return_dict[entry["item_id"]] += entry.get("return_quantity", 0)

    # Fetch existing inventory
    inventory_response = supabase.table("inventory_master_log").select("*").execute().data
    inventory = pd.DataFrame(inventory_response)

    # Track updated items
    updated_count = 0
    failed_items = []

    for item in inventory.itertuples():
        item_id = item.item_id
        item_name = item.item_name
        prev_closing = 0 if pd.isna(item.closing_balance) else item.closing_balance

        supply = restock_dict.get(item_id, 0)
        stock_out = requisition_dict.get(item_id, 0)
        return_quantity = return_dict.get(item_id, 0)

        # Ensure integers
        try:
            stock_out = int(stock_out or 0)
            supply = int(supply or 0)
            return_quantity = int(return_quantity or 0)
            open_balance = int(prev_closing or 0)
            closing_balance = open_balance + supply + return_quantity - stock_out
            closing_balance = int(closing_balance)

            daily_log = {
                "item_id": item_id,
                "item_name": item_name,
                "open_balance": open_balance,
                "supply": supply,
                "stock_out": stock_out,
                "return_quantity": return_quantity,
              
                "log_date":selected_date.isoformat(),
                "last_updated": selected_date.isoformat()
            }

            response = supabase.table("inventory_master_log").upsert(daily_log, on_conflict=["item_id", "log_date"]).execute()


            if response.data:
                updated_count += 1
            else:
                failed_items.append(item_name)

        except Exception as e:
            failed_items.append(f"{item_name} (Error: {e})")

    # Display results once
    if updated_count:
        st.success(f"✅ Inventory log updated for {updated_count} items.")
    if failed_items:
        st.error(f"❌ Failed to update: {', '.join(failed_items)}")

    st.cache_data.clear()

# Trigger Inventory Update and Move to History
if selected == 'Home':
    if st.button("🔄 Update Inventory Balances"):
        update_inventory_balances(selected_date)
        move_requisitions_to_history(selected_date)  # Move today's requisitions after updating the inventory
        move_restocks_to_history(selected_date)  # Move today's restocks to history

# Display Today's Logs
    with st.expander("📤 Today's Requisitions"):
        requisitions_today = supabase.table("requisition").select("*").eq("requisition_date", str(selected_date)).execute().data
        st.dataframe(pd.DataFrame(requisitions_today))

    with st.expander("📥 Today's Restocks"):
        restocks_today = supabase.table("restock_log").select("*").eq("restock_date", str(selected_date)).execute().data
        st.dataframe(pd.DataFrame(restocks_today))

# Display Daily Inventory Log by Date
    st.subheader("📆 Daily Inventory Log History")
    selected_log_date = st.date_input("Select a date", value=date.today())
    daily_history = supabase.table("inventory_master_log").select("*").eq("log_date", str(selected_log_date)).execute().data


    if daily_history:
        st.dataframe(pd.DataFrame(daily_history))
    else:
        st.info("ℹ️ No inventory log found for this date.")




## filter sections
# Fetch all inventory master logs
all_logs = supabase.table("inventory_master_log").select("*").execute().data
df_logs = pd.DataFrame(all_logs)

if selected == 'Filter':
    st.subheader('Filter inventory')

    if not df_logs.empty:
        with st.expander("🔍 Filter Inventory Log", expanded=True):
            df_logs["log_date"] = pd.to_datetime(df_logs["log_date"], errors="coerce")  # convert with error handling

            # Drop rows with invalid dates
            df_logs = df_logs.dropna(subset=["log_date"])

            # Get unique values for filters
            item_options = df_logs["item_name"].dropna().unique()

            if not df_logs.empty:
                min_date = df_logs["log_date"].min().date()
                max_date = df_logs["log_date"].max().date()
                min_supply = int(df_logs["supply"].min())
                max_supply = int(df_logs["supply"].max())

                # Sidebar filters
                selected_item = st.selectbox("Select an Item", options=item_options)
                date_range = st.date_input("Select Date Range", [min_date, max_date])

                # Handle slider safely
                if min_supply == max_supply:
                    st.warning("⚠️ All supply values are the same, slider is disabled.")
                    supply_range = (min_supply, max_supply)
                else:
                    supply_range = st.slider(
                        "Supply Range",
                        min_value=min_supply,
                        max_value=max_supply,
                        value=(min_supply, max_supply)
                    )

                # Apply filters
                filtered_df = df_logs[
                    (df_logs["item_name"] == selected_item) &
                    (df_logs["log_date"] >= pd.to_datetime(date_range[0])) &
                    (df_logs["log_date"] <= pd.to_datetime(date_range[1])) &
                    (df_logs["supply"] >= supply_range[0]) &
                    (df_logs["supply"] <= supply_range[1])
                ]

                # Show filtered table
                st.dataframe(filtered_df)
            else:
                st.warning("⚠️ No valid log dates available.")
    else:
        st.warning("⚠️ Inventory log table is empty.")


## report section

def get_summary_report(time_period, start_date, end_date):
    try:
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        response = supabase.table("inventory_master_log") \
            .select("log_date", "item_name", "open_balance", "supply", "return_quantity", "stock_out", "closing_balance") \
            .gte("log_date", start_date_str) \
            .lte("log_date", end_date_str) \
            .execute()

        if hasattr(response, "error") and response.error:
            st.error(f"❌ Supabase Error: {response.error}")
            return pd.DataFrame()

        if not hasattr(response, "data") or not response.data:
            st.warning("⚠️ No data returned from Supabase.")
            return pd.DataFrame()

        df = pd.DataFrame(response.data)
        df["log_date"] = pd.to_datetime(df["log_date"])  # Ensure datetime format

        time_trunc_map = {
            "Weekly": "W",
            "Monthly": "M",
            "Yearly": "Y"
        }

        if time_period not in time_trunc_map:
            st.error("❌ Invalid time period selected!")
            return pd.DataFrame()

        df_summary = (
            df.groupby([pd.Grouper(key="log_date", freq=time_trunc_map[time_period]), "item_name"])
            .agg(
                total_open_stock=('open_balance', 'sum'),
                total_stock_in=("supply", "sum"),
                total_returned=("return_quantity", "sum"),
                total_stock_out=("stock_out", "sum")
            )
            .reset_index()
        )

        df_summary['total_closing_stock'] = (
            df_summary['total_open_stock'] + df_summary['total_returned'] +
            df_summary['total_stock_in'] - df_summary['total_stock_out']
        )

        df_summary.rename(columns={"log_date": "period"}, inplace=True)
        return df_summary

    except Exception as e:
        st.error(f"❌ Error fetching summary report: {e}")
        return pd.DataFrame()

# 🔹 Streamlit UI

if selected == 'Reports':
    st.title("📦 Inventory Summary Reports")

# Select Report Type
    report_type = st.selectbox("📆 Select Report Type", ["Weekly", "Monthly", "Yearly"])

# Select Date Range
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("📅 Start Date", datetime.today().replace(day=1))
    with col2:
        end_date = st.date_input("📅 End Date", datetime.today())

# Generate Button
    if st.button("📈 Generate Report"):
        if start_date > end_date:
            st.error("❌ Start date cannot be after end date!")
        else:
            summary_df = get_summary_report(report_type, start_date, end_date)

        if not summary_df.empty:
            st.success(f"✅ {report_type} Report Generated Successfully!")
            st.dataframe(summary_df, use_container_width=True)

            # Download Excel
            buffer = io.BytesIO()
            summary_df.to_excel(buffer, index=False, sheet_name="Summary Report")
            buffer.seek(0)

            st.download_button(
                label="⬇️ Download Report as Excel",
                data=buffer,
                file_name=f"{report_type.lower()}_inventory_summary.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            
        else:
            st.warning("⚠️ No data found for the selected date range.")
