import streamlit as st
from datetime import datetime
import pandas as pd
import io
import bcrypt
from streamlit_cookies_manager import EncryptedCookieManager # for making sure you dont get logged out when page is refreshed
import json
import time
# for sending email notification wen request is made
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


cookies = EncryptedCookieManager(prefix="inventory_app_", password="2020")


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

  )


# Ensure session state is initialized to prevent errors
if "user" not in st.session_state:
    st.session_state.user = {}  # Initialize as an empty dictionary

# 🔹 **Check Access for Inventory Role**
check_access(required_role="Employee")
check_access(required_role="Inventory")


# Add your inventory-related features here




# ---- DATABASE CONNECTION ----
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
        
        response = supabase.table("request").select("*").execute()
        
        if hasattr(response, "data") and response.data:  
            return pd.DataFrame(response.data)
        else:
            st.warning("❌ No data found in Supabase!")
            return pd.DataFrame()

    except Exception as e:
        st.error(f"🚨 Error fetching data: {str(e)}")
        return pd.DataFrame()




if st.button("🔄 Refresh Data"):
    st.cache_data.clear()  # ✅ Clear cached data
    st.rerun() # ✅ Force rerun of the app

   


# Function to fetch requests for a specific employee
def get_employee_requests(employee_name):
    try:
        response = supabase.table("requests").select(
            "id, department, location, request_text, request_date, status, md_comment, md_approval_date"
        ).eq("employee_name", employee_name).order("request_date", desc=True).execute()
        
        return response.data if response.data else []
    
    except Exception as e:
        print(f"Error fetching employee requests: {e}")
        return []

# Function to fetch all requests as a DataFrame
def get_requests():
    try:
        response = supabase.table("requests").select(
            "id, employee_name, department, location, request_text, request_date, status, md_comment, md_approval_date"
        ).order("request_date", desc=True).execute()
        
        if response.data:
            return pd.DataFrame(response.data)
        else:
            return pd.DataFrame()  # Return empty DataFrame if no data
        
    except Exception as e:
        print(f"Error fetching all requests: {e}")
        return pd.DataFrame()

# Function to download requests as CSV
def download_requests(df):
    output = io.StringIO()
    df.to_csv(output, index=False)
    processed_data = output.getvalue().encode("utf-8")
    return processed_data





# submity request

def submit_request(employee_name, department, location, request_text):
    request_date = datetime.now().isoformat()  # Convert datetime to ISO string
    
    supabase.table("requests").insert({
        "employee_name": employee_name,
        "department": department,
        "location": location,
        "request_text": request_text,
        "request_date": request_date,  # Now in a serializable format
        "status": "Pending"
    }).execute()


# Function to delete a request
def delete_request(request_id):
    supabase.table("requests").delete().eq("id", request_id).execute()
    st.success(f"Request ID {request_id} has been deleted successfully.")


# accept and reject request
def update_request_status(request_id, status, md_comment, md_username):
    supabase.table("requests").update({
        "status": status,
        "md_comment": md_comment,
        "md_approval_date": datetime.utcnow(),
        "md_username": md_username
    }).eq("id", request_id).execute()


    








# ---- STREAMLIT UI ----
st.title("Employee Request System")

menu = st.sidebar.radio("Menu", ["Submit Request", "View My Requests", "View All Requests"])


if menu == "Submit Request":
    st.header("Submit a New Request")

    employee_name = st.text_input("Employee Name")
    department = st.selectbox("Department", ["HR", "IT", "Finance", "Marketing", "Operations"])
    location = st.text_input("Location")
    request_text = st.text_area("Request Details")

    if st.button("Submit Request"):
        if employee_name and department and location and request_text:
            submit_request(employee_name, department, location, request_text)
            st.success("Your request has been submitted successfully!")

         
        else:
            st.warning("⚠️ Request submitted, but failed to notify MD.")
    else:
        st.error("❌ Please fill in all fields before submitting.")
       

elif menu == "View My Requests":
    st.header("Check Your Request Status")

    employee_name = st.text_input("Enter Your Name to View Requests")

    if st.button("View Requests"):
        if employee_name:
            requests = get_employee_requests(employee_name)
            if requests:
                for req in requests:
                    st.subheader(f"Request ID: {req['id']}")
                    st.write(f"**Department:** {req['department']}")
                    st.write(f"**Location:** {req['location']}")
                    st.write(f"**Request Details:** {req['request_text']}")
                    st.write(f"**Date Submitted:** {req['request_date']}")
                    st.write(f"**Status:** {req['status']}")

                    if req["status"] != "Pending":
                        st.write(f"**Manager's Comment:** {req['md_comment']}")
                        st.write(f"**Approval Date:** {req['md_approval_date']}")

                    
                
        else:
            st.error("Please enter your name to check requests.")

elif menu == "View All Requests":
    st.header("All Requests Table")

    df_requests = get_requests()

    if not df_requests.empty:
        st.dataframe(df_requests)

        csv_data = io.StringIO()
        df_requests.to_csv(csv_data, index=False)
        st.download_button(
            label="Download Requests as CSV",
            data=csv_data.getvalue().encode("utf-8"),
            file_name="requests.csv",
            mime="text/csv"
        )
    else:
        st.warning("No requests found in the database.")


if menu == "MD Approval":
    st.header("MD Approval Panel")
    
    df_pending = get_requests()
    df_pending = df_pending[df_pending["status"] == "Pending"]

    if not df_pending.empty:
        for _, row in df_pending.iterrows():
            with st.expander(f"Request ID: {row['id']} - {row['employee_name']} ({row['department']})"):
                st.write(f"**Employee Name:** {row['employee_name']}")
                st.write(f"**Department:** {row['department']}")
                st.write(f"**Location:** {row['location']}")
                st.write(f"**Request:** {row['request_text']}")
                st.write(f"**Request Date:** {row['request_date']}")

                decision = st.radio(f"Decision for Request {row['id']}", ["Approve", "Reject"], key=row['id'])
                md_comment = st.text_area(f"MD's Comment for Request {row['id']}", key=f"comment_{row['id']}")

                if st.button(f"Submit Decision for {row['id']}"):
                    update_request_status(row["id"], decision, md_comment, "MD User")
                    st.success(f"Request {row['id']} has been {decision}!")
                    st.rerun()
    else:
        st.warning("No pending requests.")





SECRET_CODE = "MD2024Secure"

# this is for enable login for md
response = supabase.table("md_accounts").select("id, password").execute()
users = response.data

for user in users:
    user_id = user["id"]
    old_password = user["password"]

    # Skip already hashed passwords
    if old_password.startswith("$2b$"):
        continue  

    # Hash the plaintext password
    new_hashed_password = bcrypt.hashpw(old_password.encode(), bcrypt.gensalt()).decode()

    # Update the database with the hashed password
    supabase.table("md_accounts").update({"password": new_hashed_password}).eq("id", user_id).execute()

print("✅ All passwords have been rehashed successfully!")



def verify_secret_code(entered_code):
    return entered_code == SECRET_CODE

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def hash_password(password):
    """Hash password before storing in the database."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def md_exists(username):
    response = supabase.table("md_accounts").select("username").eq("username", username).execute()
    return len(response.data) > 0

def register_md(username, password, email):
    if md_exists(username):
        return False  # Username exists
    hashed_pw = hash_password(password)
    supabase.table("md_accounts").insert({"username": username, "password": hashed_pw, "email": email}).execute()
    return True

def check_password(password, hashed):
    """Verify the password against the stored bcrypt hash."""
    if not isinstance(hashed, str) or not hashed.startswith("$2b$"):
        raise ValueError("Invalid password hash format. Please update stored passwords.")

    return bcrypt.checkpw(password.encode(), hashed.encode())



def authenticate_md(username, password):
    response = supabase.table("md_accounts").select("password").eq("username", username).execute()
    if response.data:
        return check_password(password, response.data[0]['password'])
    return False

def fetch_pending_requests():
    return supabase.table("requests").select("id, employee_name, department, location, request_text, request_date").eq("status", "Pending").execute().data

def update_request_status(request_id, decision, comment, md_username):
    supabase.table("requests").update({
        "status": decision,
        "md_comment": comment,
        "md_approval_date": str(datetime.now()),
        "md_username": md_username
    }).eq("id", request_id).execute()

def delete_request(request_id):
    supabase.table("requests").delete().eq("id", request_id).execute()

# Streamlit UI
st.title("MD Request Management System")

if "verified_secret" not in st.session_state:
    st.session_state["verified_secret"] = False

if not st.session_state["verified_secret"]:
    entered_code = st.text_input("Enter Security Code:", type="password")
    if st.button("Submit Code"):
        if verify_secret_code(entered_code):
            st.session_state["verified_secret"] = True
            st.success("Access Granted!")
            st.rerun()
        else:
            st.error("Invalid Code!")

if st.session_state["verified_secret"]:
    menu = st.sidebar.radio("Menu", ["MD Login", "Register MD", "MD Approval", "Delete Request"])
    
    if menu == "Register MD":
        st.header("Register a New MD Account")
        new_username = st.text_input("Username")
        new_email = st.text_input("Email")
        new_password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        if st.button("Register"):
            if new_password == confirm_password:
                if register_md(new_username, new_password, new_email):
                    st.success("Registration successful!")
                else:
                    st.error("Username already exists!")
            else:
                st.error("Passwords do not match.")
    
    if menu == "MD Login":
        st.header("MD Login")
        md_username = st.text_input("Username")
        md_password = st.text_input("Password", type="password")
        if st.button("Login"):
            if authenticate_md(md_username, md_password):
                st.session_state["md_logged_in"] = True
                st.session_state["md_username"] = md_username
                st.success("Login successful!")
            else:
                st.error("Invalid credentials!")
    
    if menu == "MD Approval":
        if "md_logged_in" not in st.session_state:
            st.warning("Please log in first.")
        else:
            st.header("Pending Requests")
            pending_requests = fetch_pending_requests()
            if pending_requests:
                for req in pending_requests:
                    with st.expander(f"Request {req['id']} - {req['employee_name']}"):
                        st.write(f"**Department:** {req['department']}")
                        st.write(f"**Location:** {req['location']}")
                        st.write(f"**Request:** {req['request_text']}")
                        st.write(f"**Date:** {req['request_date']}")
                        decision = st.radio(f"Decision for {req['id']}", ["Approve", "Reject"], key=req['id'])
                        comment = st.text_area(f"Comment for {req['id']}", key=f"comment_{req['id']}")
                        if st.button(f"Submit {req['id']}"):
                            update_request_status(req['id'], decision, comment, st.session_state["md_username"])
                            st.success(f"Request {req['id']} {decision}!")
                            st.rerun()
            else:
                st.warning("No pending requests.")
    
    if menu == "Delete Request":
        request_id_to_delete = st.text_input("Enter Request ID")
        if st.button("Delete Request"):
            if request_id_to_delete:
                delete_request(request_id_to_delete)
                st.success("Request deleted!")
                st.rerun()
            else:
                st.error("Enter a valid Request ID.")

