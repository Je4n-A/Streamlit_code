import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import bcrypt
import plotly.express as px  # You might need to pip install plotly

# -----------------------------
# PAGE CONFIGURATION
# -----------------------------
st.set_page_config(page_title="Financial Reporting Portal", layout="wide")

# -----------------------------
# MANUALLY HASH PASSWORDS
# -----------------------------
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

# Hash the passwords (In production, load these from a secure env file)
hashed_passwords = [hash_password("admin123"), hash_password("analyst123")]

# -----------------------------
# CONFIGURATION FOR AUTHENTICATION
# -----------------------------
config = {
    "credentials": {
        "usernames": {
            "admin": {
                "name": "Senior Finance Manager",
                "password": hashed_passwords[0]
            },
            "analyst": {
                "name": "Financial Analyst",
                "password": hashed_passwords[1]
            }
        }
    },
    "cookie": {
        "expiry_days": 30,
        "key": "random_signature_key_123", 
        "name": "finance_portal_cookie"
    },
    "preauthorized": {
        "emails": []
    }
}

# -----------------------------
# INITIALIZE AUTHENTICATOR
# -----------------------------
authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"]
)

# -----------------------------
# LOGIN SECTION
# -----------------------------
# Try/Except block to handle different version signatures of streamlit-authenticator
try:
    # Newer versions
    name, authentication_status, username = authenticator.login("main")
except TypeError:
    # Older versions
    name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status is False:
    st.error("Username/password is incorrect")
    st.stop()
elif authentication_status is None:
    st.warning("Please enter your username and password")
    st.stop()

# -----------------------------
# MAIN APPLICATION LOGIC
# -----------------------------
if authentication_status:
    # Sidebar for navigation and logout
    with st.sidebar:
        st.title(f"Welcome, {name}")
        st.divider()
        authenticator.logout("Logout", "sidebar")
        
        st.header("Filters")
        selected_year = st.selectbox("Select Fiscal Year", [2023, 2024, 2025])

    st.title("📊 Executive Financial Dashboard")
    st.markdown("Automated reporting for leadership review.")

    # -----------------------------
    # MOCK POSTGRESQL CONNECTION
    # -----------------------------
    # In a real work scenario, you would use: 
    # engine = create_engine("postgresql+psycopg2://user:password@host:port/dbname")
    
    # For this demo, we use SQLite in-memory to simulate the DB
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Seed the database with financial data
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS financial_metrics (
                id INTEGER PRIMARY KEY,
                month TEXT,
                year INTEGER,
                revenue DECIMAL(10,2),
                expenses DECIMAL(10,2),
                department TEXT
            )
        """))
        
        # Check if empty to avoid duplicate inserts on rerun
        result = conn.execute(text("SELECT count(*) FROM financial_metrics"))
        if result.scalar() == 0:
            conn.execute(text("""
                INSERT INTO financial_metrics (month, year, revenue, expenses, department) VALUES
                    ('Jan', 2024, 150000, 90000, 'Sales'),
                    ('Feb', 2024, 160000, 95000, 'Sales'),
                    ('Mar', 2024, 175000, 92000, 'Sales'),
                    ('Jan', 2024, 80000, 70000, 'IT'),
                    ('Feb', 2024, 82000, 71000, 'IT'),
                    ('Mar', 2024, 85000, 68000, 'IT'),
                    ('Jan', 2023, 120000, 85000, 'Sales'),
                    ('Feb', 2023, 130000, 88000, 'Sales')
            """))
    
    # -----------------------------
    # DATA ANALYSIS
    # -----------------------------
    query = text(f"SELECT * FROM financial_metrics WHERE year = {selected_year}")
    df = pd.read_sql(query, engine)
    
    # Calculate Profit
    df['profit'] = df['revenue'] - df['expenses']
    df['margin'] = (df['profit'] / df['revenue']) * 100

    # KPI Metrics
    total_revenue = df['revenue'].sum()
    total_profit = df['profit'].sum()
    avg_margin = df['margin'].mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"${total_revenue:,.0f}")
    col2.metric("Total Profit", f"${total_profit:,.0f}")
    col3.metric("Avg Margin", f"{avg_margin:.1f}%")

    st.divider()

    # -----------------------------
    # VISUALIZATIONS
    # -----------------------------
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Revenue vs Expenses by Month")
        # Aggregate by month
        monthly_data = df.groupby('month')[['revenue', 'expenses']].sum().reset_index()
        # Sort months correctly
        month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        monthly_data['month'] = pd.Categorical(monthly_data['month'], categories=month_order, ordered=True)
        monthly_data = monthly_data.sort_values('month')
        
        fig_bar = px.bar(monthly_data, x='month', y=['revenue', 'expenses'], barmode='group')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_chart2:
        st.subheader("Profit Distribution by Department")
        dept_data = df.groupby('department')['profit'].sum().reset_index()
        fig_pie = px.pie(dept_data, values='profit', names='department', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    # Detailed Data View
    with st.expander("View Detailed Financial Records"):
        st.dataframe(df, use_container_width=True)