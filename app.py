import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# -----------------------------
# CONFIGURATION FOR AUTHENTICATION
# -----------------------------
# Inline configuration (you can also load this from a YAML file if preferred)
config = {
    "credentials": {
        "usernames": {
            "user1": {
                "name": "User One",
                "password": "password1"  # In production, store and use hashed passwords!
            },
            "user2": {
                "name": "User Two",
                "password": "password2"
            }
        }
    },
    "cookie": {
        "expiry_days": 30,
        "key": "some_signature_key",  # Replace with a secure key
        "name": "some_cookie_name"
    },
    "preauthorized": {
        "emails": []
    }
}

# Initialize the authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Display the login widget
name, authentication_status, username = authenticator.login('Login', 'main')

# -----------------------------
# MAIN APPLICATION LOGIC
# -----------------------------
if authentication_status:
    st.write(f"Welcome {name}!")

    # -----------------------------
    # SET UP A TEMPORARY DATABASE
    # -----------------------------
    # We use an in-memory SQLite database for demonstration purposes.
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Create a temporary table and insert some sample data.
    # Note: The data will be lost when the app stops.
    with engine.connect() as conn:
        # Create the table if it doesn't exist
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS your_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                age INTEGER
            )
        """))
        # Insert sample data
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
        # Load data from the temporary database into a pandas DataFrame
        df = pd.read_sql(query, engine)
        
        st.subheader("Data from the Temporary Database")
        st.dataframe(df)
        
        # Optional: Show a summary of the DataFrame
        if st.checkbox("Show DataFrame Summary"):
            st.write(df.describe())
    except Exception as e:
        st.error(f"Error loading data: {e}")
    
    # -----------------------------
    # LOGOUT BUTTON
    # -----------------------------
    authenticator.logout("Logout", "main")

elif authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")