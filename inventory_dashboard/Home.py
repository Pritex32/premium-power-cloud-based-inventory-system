import streamlit as st
st.set_page_config(
    page_title='INVENTORY MANAGEMENT SYSTEM',
    page_icon='👋 ',

)


import bcrypt
import pandas as pd
from streamlit_option_menu import option_menu
from datetime import datetime
import json
import time
from streamlit_cookies_manager import EncryptedCookieManager
from PIL import Image



from streamlit_cookies_manager import EncryptedCookieManager

# Initialize Cookie Manager

cookies = EncryptedCookieManager(prefix="inventory_app_", password="your_secret_key_here")

if not cookies.ready():
    st.stop()





from supabase import create_client
# supabase configurations
def get_supabase_client():
    supabase_url = 'https://bpxzfdxxidlfzvgdmwgk.supabase.co' # Your Supabase project URL
    supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJweHpmZHh4aWRsZnp2Z2Rtd2drIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI3NjM0MTQsImV4cCI6MjA1ODMzOTQxNH0.vQq2-VYCJyTQDq3QN2mJprmmBR2w7HMorqBuzz43HRU'
    supabase = create_client(supabase_url, supabase_key)
    return supabase  # Make sure to return the client

# Initialize Supabase client
supabase = get_supabase_client() # use this to call the supabase database


# Load the image
image_path = "inventory_dashboard/pages/Daily_Requisitions and 8 more pages - Profile 1 - Microsoft​ Edge 3_23_2025 1_29_17 PM (2).png"
image = Image.open(image_path)

# Resize the image (set new width & height)
resized_image = image.resize((200,100) ) # Adjust size as needed

# Display in Streamlit
st.image(resized_image)


# contact developer
st.sidebar.markdown("---")  # Adds a separator
if st.sidebar.button("📩 Contact Developer"):
    st.sidebar.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/in/prisca-ukanwa-800a1117a/)")


# Secret Key for Employee Registration


# Secret Keys for Role-Based Registration
SECRET_KEYS = {
    "Inventory": "INV-9x2T$Lm@pZ8",
    "Employee": "EMP-7vY&KwQ#6Bts"
}





def register_user(name, email, password, role, secret_code):
    SECRET_KEYS = {"Inventory": "INV-9x2T$Lm@pZ8", "Employee": "EMP-7vY&KwQ#6Bts"}
    
    if secret_code != SECRET_KEYS.get(role, ""):
        return "❌ Invalid Secret Code! Contact Admin."
    
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    try:
        response = supabase.table("employees").insert({
            "name": name,
            "email": email,
            "password": hashed_password,
            "role": role
        }).execute()
        return "✅ Account created successfully!"
    except Exception as e:
        return f"⚠️ Error: {e}"

# Function to Authenticate Login
def login_user(email, password):
    try:
        response = supabase.table("employees").select("*").eq("email", email).execute()
        user_data = response.data

        if user_data and bcrypt.checkpw(password.encode(), user_data[0]['password'].encode()):
            return user_data[0]  # Return user details
        
        return None
    except Exception:
        return None

# Function to Maintain Login Session
def check_login_status():
    if "logged_in" not in st.session_state:
        if cookies.get("logged_in") == "True":
            st.session_state.logged_in = True
            st.session_state.user = json.loads(cookies.get("user"))
        else:
            st.session_state.logged_in = False
            st.session_state.user = None

# Check if User is Already Logged In via Cookies
if "logged_in" not in st.session_state:
    st.session_state.logged_in = cookies.get("logged_in") == "True"
    st.session_state.user = cookies.get("user")





# Sidebar Menu
# this is to ensure that when you register, it autoamtically takes yoy to login page
if "menu" not in st.session_state:
    st.session_state.menu = "Login"
if "redirect_to_login" not in st.session_state:
    st.session_state.redirect_to_login = False

if st.session_state.redirect_to_login:
    st.session_state.menu = "Login"
    st.session_state.redirect_to_login = False
    st.rerun()

# Sidebar Menu (bind to session state)
menu = st.sidebar.selectbox("Menu", ["Login", "Register", "Delete Account"], key="menu")




# Registration Page
if menu == "Register":
    st.subheader("📝 Create an Account")
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Select Role", ["Inventory", "Employee"])
    secret_code = st.text_input(f"Enter Secret Code for {role}", type="password")

     
    if st.button("Register"):
        if name and email and password and secret_code:
            result = register_user(name, email, password, role, secret_code)
            if "successfully" in result:
                st.success(result)

# this help to redirect you to login page after registering
                st.session_state.redirect_to_login = True 
                st.rerun()
               
            else:
                st.error(result)
    
        else:
            st.error("⚠️ All fields are required!")







# Restrict Access to Pages if Not Logged In
elif menu == "Login":
    st.subheader("🔑 User Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = login_user(email, password)

        if user:
            st.session_state.logged_in = True
            st.session_state.user = user  # Store user info in session

            # Store login session in cookies
            cookies["logged_in"] = "True"
            cookies["user"] = json.dumps(user)  # Save user details properly
            cookies.save()  # Save persistently

            st.sidebar.success(f"✅ Welcome {user['name']}! 🎉")
            st.rerun()  # Refresh UI after login

    else:
        st.error("⚠️ Invalid email or password!")



elif menu == "Delete Account":
    st.subheader("❌ Delete Your Account")
    st.warning("⚠️ This action is irreversible!")

    if st.session_state.get("user"):
        user = st.session_state["user"]
        st.write(f"Logged in as: `{user['email']}`")
        password = st.text_input("Confirm your password to delete account", type="password")

        if st.button("Delete My Account"):
            # Re-authenticate
            valid_user = login_user(user["email"], password)
            if valid_user:
                # Delete from database
                delete_result = supabase.table("employees").delete().eq("email", user["email"]).execute()

                if not hasattr(delete_result, "error") or not delete_result.error:
                    # Clear session and cookies
                    st.session_state.logged_in = False
                    st.session_state.user = None
                    cookies["logged_in"] = "False"
                    cookies["user"] = ""
                    cookies.save()

                    st.success("✅ Your account has been deleted.")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to delete account: {delete_result.error}")
            else:
                st.error("❌ Password incorrect!")
else:
    st.sidebar.write('Choose options above')




def check_access(required_role=None):
    if not cookies.ready():
        st.warning("Cookies are not enabled. Login state may not persist.")
        return  # Avoid stopping execution prematurely

    # Restore session from cookies if missing
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        if cookies.get("logged_in") == "True":
            st.session_state.logged_in = True
            user_data = cookies.get("user")

            if user_data and user_data != "{}":  # Ensure user data is not empty
                try:
                    st.session_state.user = json.loads(user_data)
                    st.rerun()  # Force rerun after restoring session
                except json.JSONDecodeError:
                    st.session_state.user = None
                    st.warning("⚠️ Corrupted user session, please log in again.")
                    st.stop()
        else:
            st.warning("⚠️ You must log in to access this page.")
            st.stop()

    if "user" not in st.session_state or not isinstance(st.session_state.user, dict) or not st.session_state.user:
        st.error("🚫 Invalid user session. Please log in again.")
        st.stop()

    user_role = st.session_state.user.get("role", None)
    if required_role and user_role != required_role:
        st.error("🚫 Unauthorized Access! You don't have permission to view this page.")
        st.stop()






# Check If User is Logged In
if st.session_state.get("logged_in", False):  # Ensure logged_in exists
    # Ensure user data is a dictionary, not a string
    if isinstance(st.session_state.get("user"), str):  
        try:
            st.session_state.user = json.loads(st.session_state.user)
        except json.JSONDecodeError:
            st.error("⚠️ Corrupted user session. Please log in again.")
            st.stop()

   
    # ✅ Prevent KeyError by using .get()
    user_role = st.session_state.user.get("role", "No Role")
    user_name = st.session_state.user.get("name", "Unknown User")

    st.sidebar.success(f"✅ Logged in as {user_name} ({user_role})")

    # 🔹 Logout Button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user = None

        # Clear cookies properly
        cookies.update({"logged_in": "False", "user": json.dumps({})})
        cookies.save()
        st.rerun()

    # 🔹 **Role-Based Navigation**
    st.subheader("🏠 Welcome to the Inventory System")

    if user_role == "Inventory":
        st.write("📦 Inventory Dashboard")
        # Add inventory-related features here

    elif user_role == "Employee":
        st.write("👨‍💼 Employee Dashboard")
        # Add employee-related features here

else:
    st.sidebar.warning("⚠️ You must log in to access the system.")
