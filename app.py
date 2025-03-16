import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# -----------------------------
# CONFIGURATION FOR AUTHENTICATION
# -----------------------------
config = {
    "credentials": {
        "usernames": {
            "user1": {
                "name": "User One",
                "password": "password1"  # In production, use hashed passwords!
            },
            "user2": {
                "name": "User Two",
                "password": "password2"
            }
        }
    },
    "cookie": {
        "expiry_days": 30,
        "key": "some_signature_key",  # Change to a secure key
        "name": "some_cookie_name"
    },
    "preauthorized": {
        "emails": []
    }
}

# Initialize the authenticator
authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"]
)

# Optionally, display version info for debugging (if available)
if hasattr(stauth, "__version__"):
    st.write(f"streamlit_authenticator version: {stauth.__version__}")
else:
    st.write("streamlit_authenticator version: unknown")

# -----------------------------
# LOGIN SECTION
# -----------------------------
st.title("Login")
login_result = authenticator.login(location="main")
if login_result is None:
    st.stop()
name, authentication_status, username = login_result

# -----------------------------
# MAIN APPLICATION LOGIC
# -----------------------------
if authentication_status:
    st.write(f"Welcome {name}!")

    # -----------------------------
    # SET UP A TEMPORARY DATABASE
    # -----------------------------
    # Configure the engine to use StaticPool to persist the in-memory DB across connections.
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create a temporary table and insert sample data.
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS your_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                age INTEGER
            )
        """))
        conn.execute(text("""
            INSERT INTO your_table (name, age) VALUES
                ('Alice', 30),
                ('Bob', 25),
                ('Charlie', 35)
        """))
    
    # -----------------------------
    # QUERY AND DISPLAY DATA
    # -----------------------------
    query = "SELECT * FROM your_table"
    try:
        df = pd.read_sql(query, engine)
        st.subheader("Data from the Temporary Database")
        st.dataframe(df)
        
        if st.checkbox("Show DataFrame Summary"):
            st.write(df.describe())
    except Exception as e:
        st.error(f"Error loading data: {e}")
    
    # -----------------------------
    # LOGOUT BUTTON
    # -----------------------------
    try:
        authenticator.logout(location="main")
    except Exception as e:
        st.write("Logout button could not be displayed.")
        
elif authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")
