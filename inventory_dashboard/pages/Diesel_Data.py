from http import cookies
import streamlit as st
import pandas as pd
import psycopg2
from streamlit_option_menu import option_menu
from datetime import datetime,timedelta ,date 
import numpy as np
from streamlit_cookies_manager import EncryptedCookieManager
import time
import json

cookies = EncryptedCookieManager(prefix="inventory_app_", password="your_secret_key_here")


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


# Add your inventory-related features here









from supabase import create_client
# supabase configurations
def get_supabase_client():
    supabase_url = 'https://bpxzfdxxidlfzvgdmwgk.supabase.co' # Your Supabase project URL
    supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJweHpmZHh4aWRsZnp2Z2Rtd2drIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI3NjM0MTQsImV4cCI6MjA1ODMzOTQxNH0.vQq2-VYCJyTQDq3QN2mJprmmBR2w7HMorqBuzz43HRU'
    supabase = create_client(supabase_url, supabase_key)
    return supabase  # Make sure to return the client

# Initialize Supabase client
supabase = get_supabase_client() # use this to call the supabase database

@st.cache_data(ttl=600)
def fetch_data_from_supabase():
    """Fetch data from Supabase with caching and error handling."""
    try:
        supabase = get_supabase_client()  # Ensure we have a working client
        if not supabase:
            raise ValueError("Supabase client is not initialized!")  # Additional safety check
        
        response = supabase.table("diesel").select("*").execute()
        
        if hasattr(response, "data") and response.data:  
            return pd.DataFrame(response.data)
        else:
            st.warning("❌ No data found in Supabase!")
            return pd.DataFrame()

    except Exception as e:
        st.error(f"🚨 Error fetching data: {str(e)}")
        return pd.DataFrame()


st.subheader("📦 REAL TIME INVENTORY MANAGEMENT SYSTEM")

with st.sidebar:
    selected = option_menu(
        menu_title=('Options'),
        options=["Home page","Add Diesel", "Delete",'Calculations',"Filter","Reports"],
        icons=["house", "plus-circle", "trash", "calculator","bar-chart-line"],
        default_index=0
    )


if selected == "Home page":
    df = fetch_data_from_supabase()
    st.success("✅ Welcome to the Inventory Dashboard!")
    if not df.empty:
        st.write(df) # Display the full dataframe
        st.write('Last ten rows ',df.tail(10)) 
    

# Add diesel

# this function makes the closing stock to be the opening stock of the next entry
# Function to Get the Last Closing Stock
def get_last_closing_stock():
    try:
        response = supabase.table("diesel").select("closing_stock").order("diesel_id", desc=True).limit(1).execute()
        
        # Check if data exists
        data = response.data if hasattr(response, "data") and response.data else []
        return data[0]["closing_stock"] if data else 0

    except Exception as e:
        st.error(f"❌ Error fetching last closing stock: {e}")
        return 0 # Return last closing stock or 0 if no record exists

# Function to Insert Inventory Log
def insert_inventory_log(date, details, open_stock, return_item, supply, stock_out):
    try:
        supabase = get_supabase_client()

        date_str = date.strftime("%Y-%m-%d")  # ✅ Convert date to string
        
        # 🚀 Insert without specifying diesel_id
        response = (
            supabase.table("diesel")
            .insert({
                "date": date_str,
                "details": details,
                "open_stock": open_stock,
                "return_item": return_item,
                "supply": supply,
                "stock_out": stock_out
            })
            .execute()
        )

        if response.data:
            diesel_id = response.data[0]["diesel_id"]
            st.success(f"✅ Diesel log added successfully! ID: {diesel_id} 🎉")

        else:
            st.error("❌ Failed to insert diesel log.")

    except Exception as e:
        st.error(f"❌ Error inserting record: {e}")



# ✅ Streamlit UI for Adding Diesel Usage
if selected == "Add Diesel":
    st.subheader("➕ Add New Diesel Usage")

    # Get last closing stock and use it as the new opening stock
    last_closing_stock = get_last_closing_stock()
    
    # User Inputs
    date = st.date_input("Date", value=datetime.today().date()) 
    details = st.text_input("Input Details")
    open_stock = st.number_input("Opening Stock", value=last_closing_stock, min_value=0, step=1, disabled=True)
    supply = st.number_input("Supply", value=0, min_value=0, step=1)
    return_item = st.number_input("Returned Items", value=0, min_value=0, step=1)
    stock_out = st.number_input("Stock Out", value=0, min_value=0, step=1)

    # Submit Button
    if st.button("➕ Add Diesel"):
        insert_inventory_log(date, details, last_closing_stock, return_item, supply, stock_out)






# Delete Section
    ## to create delete button
def delete_requisition(req_id):
    try:
        supabase = get_supabase_client()  # Get Supabase connection
        
        # Check if the record exists
        check_response = supabase.table("diesel").select("diesel_id").eq("diesel_id", req_id).execute()
        if not check_response.data:
            st.sidebar.warning(f"⚠️ No requisition found with ID {req_id}. Deletion aborted.")
            return
        
        # Delete the record
        response = supabase.table("diesel").delete().eq("diesel_id", req_id).execute()
        
        if response.data:
            st.success(f"✅ diesel {req_id} deleted successfully!")
        else:
            st.error("❌ Deletion failed. The record may not exist or deletion is restricted.")

    except Exception as e:
        st.error(f"❌ Error deleting requisition: {e}")

# Streamlit UI for deletion
if selected == "Delete":
    st.sidebar.subheader("🗑️ Delete a Requisition")

    req_id = st.number_input("Enter the serial number", format="%d", step=1)

    if st.button("Delete Requisition"):
        if req_id > 0:
            delete_requisition(req_id)
        else:
            st.sidebar.warning("⚠️ Please enter a valid requisition ID.")

## calculations
# Your goal is to retrieve aggregate values for columns like open_stock, return_item, supply, stock_out, and closing_stock from the diesel table while applying a date range filter.

# Steps to Achieve This:
# Allow users to select which column they want to aggregate.

# Provide an option to choose the aggregation type (SUM, MAX, MIN, etc.).

# Apply the date range filter to ensure only relevant data is used.

# Execute the SQL query dynamically based on user input.




# Function to aggregate column values within a date range
# Function to perform column aggregation
def get_column_aggregation(column, start_date, end_date, aggregation):
    try:
        supabase = get_supabase_client()

        # ✅ Validate input to prevent SQL injection
        valid_columns = ["open_stock", "return_item", "supply", "stock_out", "closing_stock"]
        valid_aggregations = ["SUM", "MAX", "MIN", "AVG", "COUNT"]

        if aggregation == "COUNT":
            column = "id"  # Use the primary key to count rows
        
        if column not in valid_columns and aggregation != "COUNT":
            st.error("❌ Invalid column or aggregation type!")
            return None

        # ✅ Fetch filtered records
        response = supabase.table("diesel") \
            .select(column if aggregation != "COUNT" else "diesel_id") \
            .gte("date", str(start_date)) \
            .lte("date", str(end_date)) \
            .execute()

        # ✅ Extract values
        if aggregation == "COUNT":
            return len(response.data)  # ✅ Count the number of rows

        data = [record[column] for record in response.data if record[column] is not None]

        # ✅ Perform aggregation in Python
        if not data:
            return 0  # Return 0 if no data

        if aggregation == "SUM":
            return sum(data)
        elif aggregation == "MAX":
            return max(data)
        elif aggregation == "MIN":
            return min(data)
        elif aggregation == "AVG":
            return round(np.mean(data), 2)

    except Exception as e:
        st.error(f"❌ Error fetching data: {e}")
        return None

# ✅ Streamlit UI for Aggregations
if selected == "Calculations":
    st.subheader("📊 Diesel Stock Aggregations")

    # Select column to aggregate (COUNT does not require a column)
    column = st.selectbox("📌 Select Column", ["open_stock", "return_item", "supply", "stock_out", "closing_stock", "COUNT"])

    # Select aggregation type
    aggregation = st.selectbox("📈 Select Aggregation Type", ["SUM", "MAX", "MIN", "AVG", "COUNT"])

    # Date range input
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("📅 Start Date", datetime.today().replace(day=1))
    with col2:
        end_date = st.date_input("📅 End Date", datetime.today())

    # Button to fetch results
    if st.button("🔍 Get Aggregated Data"):
        if start_date > end_date:
            st.error("❌ Start date cannot be after end date!")
        else:
            result = get_column_aggregation(column if column != "COUNT" else "id", start_date, end_date, aggregation)

            if result is not None:
                st.success(f"✅ {aggregation} of '{column}' from {start_date} to {end_date}: {result}")
            else:
                st.warning("⚠️ No data found for the selected date range.")







## Filters section





# Function to filter the entire table based on date range
# Function to filter data by date
def filter_by_date(start_date, end_date):
    try:
        supabase = get_supabase_client()

        # ✅ Query to fetch all records within the date range
        response = supabase.table("diesel") \
            .select("*") \
            .gte("date", str(start_date)) \
            .lte("date", str(end_date)) \
            .execute()

        # ✅ Extract data
        if response.data:
            df = pd.DataFrame(response.data)
            return df
        else:
            return pd.DataFrame()  # Return empty DataFrame if no results

    except Exception as e:
        st.error(f"❌ Error fetching data: {e}")
        return pd.DataFrame()

# Function to filter data by item and date
def filter_by_details_and_date(details, start_date, end_date):
    try:
        supabase = get_supabase_client()

        # ✅ Query to fetch records based on details and date range
        response = supabase.table("diesel") \
            .select("*") \
            .ilike_any_of("details", f"%{details}%")  \
            .gte("date", str(start_date)) \
            .lte("date", str(end_date)) \
            .execute()

        # ✅ Extract data
        if response.data:
            df = pd.DataFrame(response.data)
            return df
        else:
            return pd.DataFrame()  # Return empty DataFrame if no results

    except Exception as e:
        st.error(f"❌ Error fetching data: {e}")
        return pd.DataFrame()

# ✅ Streamlit UI for Filtering
if selected == "Filter":
    st.title("🔍 Filter Options")

    # Select filtering option
    filter_option = st.selectbox("📌 Select Filter Type", ["Filter by Date", "Filter by Details & Date"])

    if filter_option == "Filter by Date":
        st.subheader("📅 Filter by Date")

        start_date = st.date_input("📅 Start Date", datetime.today().replace(day=1))
        end_date = st.date_input("📅 End Date", datetime.today())

        if st.button("🔍 Apply Date Filter"):
            if start_date > end_date:
                st.error("❌ Start date cannot be after end date!")
            else:
                filtered_df = filter_by_date(start_date, end_date)

                if not filtered_df.empty:
                    st.write("### ✅ Filtered Data")
                    st.dataframe(filtered_df)
                else:
                    st.warning("⚠️ No results found for the selected date range.")

    elif filter_option == "Filter by Details & Date":
        st.subheader("🛢️ Filter Diesel Records by Details & Date")

        details = st.text_input("🔍 Enter Details (e.g., diesel, fuel, paper)")
        start_date = st.date_input("📅 Start Date", datetime.today().replace(day=1))
        end_date = st.date_input("📅 End Date", datetime.today())

        if st.button("🔍 Apply Details & Date Filter"):
            if not details:
                st.error("❌ Please enter details!")
            elif start_date > end_date:
                st.error("❌ Start date cannot be after end date!")
            else:
                filtered_df = filter_by_details_and_date(details, start_date, end_date)

                if not filtered_df.empty:
                    st.write(f"### ✅ Filtered Data for '{details}' from {start_date} to {end_date}")
                    st.dataframe(filtered_df)
                else:
                    st.warning(f"⚠️ No results found for '{details}' in the selected date range.")





















# Reports


# Function to generate summary report
def get_summary_report(time_period, start_date, end_date):
    try:
        supabase = get_supabase_client()

        # ✅ Fetch data from Supabase table
        response = supabase.table("diesel") \
            .select("date, details, open_stock, return_item, supply, stock_out, closing_stock") \
            .gte("date", str(start_date)) \
            .lte("date", str(end_date)) \
            .execute()

        # ✅ Convert response data to DataFrame
        if response.data:
            df = pd.DataFrame(response.data)
        else:
            return pd.DataFrame()  # Return empty DataFrame if no data found

        # ✅ Convert date to datetime type for grouping
        df["date"] = pd.to_datetime(df["date"])

        # ✅ Time truncation logic in Python (since Supabase lacks DATE_TRUNC)
        if time_period == "Weekly":
            df["period"] = df["date"].dt.to_period("W").apply(lambda r: r.start_time)
        elif time_period == "Monthly":
            df["period"] = df["date"].dt.to_period("M").apply(lambda r: r.start_time)
        elif time_period == "Yearly":
            df["period"] = df["date"].dt.to_period("Y").apply(lambda r: r.start_time)
        else:
            st.error("❌ Invalid time period selected!")
            return pd.DataFrame()

        # ✅ Perform aggregation
        summary_df = df.groupby(["period", "details"]).agg({
            "open_stock": "sum",
            "return_item": "sum",
            "supply": "sum",
            "stock_out": "sum",
            "closing_stock": "sum"
        }).reset_index()

        # ✅ Rename columns for clarity
        summary_df.columns = ["period", "details", "total_stock_in", "total_returned", "total_supplied", "total_stock_out", "total_closing_stock"]

        return summary_df

    except Exception as e:
        st.error(f"❌ Error fetching summary report: {e}")
        return pd.DataFrame()


# Streamlit UI for Reports
# ✅ Streamlit UI for Reports
if selected == "Reports":
    st.subheader("📊 Diesel Summary Reports")

    # ✅ Select Report Type
    report_type = st.selectbox("📆 Select Report Type", ["Weekly", "Monthly", "Yearly"])

    # ✅ Select Date Range
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("📅 Start Date", datetime.today().replace(day=1))
    with col2:
        end_date = st.date_input("📅 End Date", datetime.today())

    # ✅ Generate Report Button
    if st.button("📈 Generate Report"):
        if start_date > end_date:
            st.error("❌ Start date cannot be after end date!")
        else:
            summary_df = get_summary_report(report_type, start_date, end_date)

            if not summary_df.empty:
                st.success(f"✅ {report_type} Report Generated Successfully!")

                # ✅ Convert numeric columns properly
                numeric_cols = ["total_stock_in", "total_returned", "total_supplied", "total_stock_out", "total_closing_stock"]
                summary_df[numeric_cols] = summary_df[numeric_cols].apply(pd.to_numeric, errors="coerce")

                # ✅ Display formatted DataFrame
                st.dataframe(summary_df.style.format({col: "{:.2f}" for col in numeric_cols}))

            else:
                st.warning("⚠️ No data found for the selected date range.")
