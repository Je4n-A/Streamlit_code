import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import bcrypt
import plotly.express as px
import yfinance as yf
import datetime
import os
import numpy as np

# -----------------------------
# PAGE CONFIGURATION
# -----------------------------
st.set_page_config(page_title="Financial Reporting Portal", layout="wide")

# -----------------------------
# MOCK POSTGRESQL CONNECTION
# -----------------------------
# Initialize database cache
@st.cache_resource
def init_database():
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
            data_to_insert = []
            
            # ---------------------------------------------------------
            # FETCH REAL-WORLD DATA VIA YFINANCE (Test Data API)
            # ---------------------------------------------------------
            # We use Microsoft (MSFT) stock history to simulate financial trends.
            # This acts as our "Test Data API".
            try:
                ticker = "MSFT"
                stock = yf.Ticker(ticker)
                # Fetch 2 years of monthly data
                history = stock.history(period="2y", interval="1mo")
                
                if history.empty:
                    raise ValueError("No data fetched from yfinance API")

                # Process the data to fit our schema
                for date, row in history.iterrows():
                    # Simulate Revenue based on Stock Price * Volume (scaled)
                    # This creates realistic-looking fluctuations
                    if pd.isna(row['Close']) or pd.isna(row['Volume']):
                        continue
                        
                    simulated_revenue = (row['Close'] * row['Volume']) / 1_000_000_000 * 50000 
                    simulated_expenses = simulated_revenue * 0.65  # Assume 65% profit margin
                    
                    month_name = date.strftime('%b')
                    year = date.year
                    
                    # Split into departments
                    data_to_insert.append({
                        "month": month_name, "year": year, 
                        "revenue": simulated_revenue * 0.6, "expenses": simulated_expenses * 0.6, 
                        "department": "Sales"
                    })
                    data_to_insert.append({
                        "month": month_name, "year": year, 
                        "revenue": simulated_revenue * 0.4, "expenses": simulated_expenses * 0.4, 
                        "department": "IT"
                    })
                
                if not data_to_insert:
                    raise ValueError("Data processing resulted in empty dataset")

                # st.toast(f"Successfully loaded real-world test data for {ticker} via yfinance API!", icon="✅")
                
            except Exception as e:
                # st.error(f"Failed to fetch API data: {e}. Using fallback data.")
                # Fallback data if API fails
                data_to_insert = [
                    {'month': 'Jan', 'year': 2024, 'revenue': 150000, 'expenses': 90000, 'department': 'Sales'},
                    {'month': 'Feb', 'year': 2024, 'revenue': 160000, 'expenses': 95000, 'department': 'Sales'},
                    {'month': 'Mar', 'year': 2024, 'revenue': 175000, 'expenses': 92000, 'department': 'Sales'},
                    {'month': 'Jan', 'year': 2024, 'revenue': 80000, 'expenses': 70000, 'department': 'IT'},
                    {'month': 'Feb', 'year': 2024, 'revenue': 82000, 'expenses': 71000, 'department': 'IT'},
                    {'month': 'Mar', 'year': 2024, 'revenue': 85000, 'expenses': 68000, 'department': 'IT'},
                ]

            # Insert data
            for row in data_to_insert:
                conn.execute(text("""
                    INSERT INTO financial_metrics (month, year, revenue, expenses, department) 
                    VALUES (:month, :year, :revenue, :expenses, :department)
                """), row)
            conn.commit()
    return engine

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
# Display credentials for demo purposes
st.info("### Demo Credentials\n* **Admin:** admin / admin123\n* **Analyst:** analyst / analyst123")

# Try/Except block to handle different version signatures of streamlit-authenticator
name, authentication_status, username = None, None, None

try:
    # Try with explicit location keyword
    result = authenticator.login(location="main")
    if result is not None:
        name, authentication_status, username = result
    else:
        name = st.session_state.get('name')
        authentication_status = st.session_state.get('authentication_status')
        username = st.session_state.get('username')
except (TypeError, ValueError):
    try:
        # Older versions
        result = authenticator.login("Login", "main")
        if result is not None:
            name, authentication_status, username = result
        else:
            name = st.session_state.get('name')
            authentication_status = st.session_state.get('authentication_status')
            username = st.session_state.get('username')
    except (TypeError, ValueError):
        # Fallback
        result = authenticator.login()
        if result is not None:
            name, authentication_status, username = result
        else:
            name = st.session_state.get('name')
            authentication_status = st.session_state.get('authentication_status')
            username = st.session_state.get('username')

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
    # Initialize database connection
    engine = init_database()

    # Get year options from database
    with engine.connect() as conn:
        years_result = conn.execute(text("SELECT DISTINCT year FROM financial_metrics ORDER BY year DESC"))
        available_years = [row[0] for row in years_result.fetchall()]
        
        # Get departments for filter
        dept_result = conn.execute(text("SELECT DISTINCT department FROM financial_metrics"))
        available_depts = [row[0] for row in dept_result.fetchall()]
    
    # Sidebar for navigation and logout
    with st.sidebar:
        st.title(f"Welcome, {name}")
        st.divider()
        authenticator.logout("Logout", "sidebar")
        
        st.header("Filters")
        if available_years:
            selected_year = st.selectbox("Select Fiscal Year", available_years)
        else:
            st.error("No data available in database")
            st.stop()
            
        selected_depts = st.multiselect("Select Departments", available_depts, default=available_depts)

    st.title("📊 Executive Financial Dashboard")
    st.markdown("Automated reporting for leadership review.")

    # -----------------------------
    # DATA ANALYSIS
    # -----------------------------
    # Base query
    query_str = f"SELECT * FROM financial_metrics WHERE year = {selected_year}"
    if selected_depts:
        depts_str = "', '".join(selected_depts)
        query_str += f" AND department IN ('{depts_str}')"
    
    query = text(query_str)
    df = pd.read_sql(query, engine)
    
    if df.empty:
        st.warning("No data available for the selected filters.")
        st.stop()
    
    # Calculate Profit & Margin
    df['profit'] = df['revenue'] - df['expenses']
    df['margin'] = (df['profit'] / df['revenue']) * 100

    # Create Tabs
    tab1, tab2, tab3 = st.tabs(["📈 Dashboard", "🔮 Forecasting", "💾 Data & Export"])

    with tab1:
        # KPI Metrics with Deltas (Simulated vs Target/Prev Year)
        total_revenue = df['revenue'].sum()
        total_profit = df['profit'].sum()
        avg_margin = df['margin'].mean()
        
        # Simulate targets for demo purposes (e.g., 5% growth target)
        target_revenue = total_revenue * 0.95
        target_profit = total_profit * 0.90
        target_margin = avg_margin * 0.95

        col1, col2, col3 = st.columns(3)
        col1.metric(
            "Total Revenue", 
            f"${total_revenue:,.0f}", 
            f"{((total_revenue - target_revenue) / target_revenue * 100):.1f}% vs Target"
        )
        col2.metric(
            "Total Profit", 
            f"${total_profit:,.0f}", 
            f"{((total_profit - target_profit) / target_profit * 100):.1f}% vs Target"
        )
        col3.metric(
            "Avg Margin", 
            f"{avg_margin:.1f}%", 
            f"{(avg_margin - target_margin):.1f}% vs Target"
        )

        st.divider()

        # VISUALIZATIONS
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.subheader("Revenue vs Expenses by Month")
            # Aggregate by month
            monthly_data = df.groupby('month')[['revenue', 'expenses']].sum().reset_index()
            # Sort months correctly
            month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            monthly_data['month'] = pd.Categorical(monthly_data['month'], categories=month_order, ordered=True)
            monthly_data = monthly_data.sort_values('month')
            
            fig_bar = px.bar(
                monthly_data, 
                x='month', 
                y=['revenue', 'expenses'], 
                barmode='group',
                color_discrete_map={'revenue': '#00CC96', 'expenses': '#EF553B'}
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_chart2:
            st.subheader("Profit Distribution by Department")
            dept_data = df.groupby('department')['profit'].sum().reset_index()
            fig_pie = px.pie(dept_data, values='profit', names='department', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

    with tab2:
        st.subheader("Revenue Forecast (Next 3 Months)")
        st.info("Simple linear regression forecast based on current year's monthly data.")
        
        # Prepare data for forecasting
        forecast_df = df.groupby(['year', 'month'])['revenue'].sum().reset_index()
        
        # Create a proper datetime column for sorting and plotting
        forecast_df['date_str'] = forecast_df['year'].astype(str) + '-' + forecast_df['month']
        forecast_df['date'] = pd.to_datetime(forecast_df['date_str'], format='%Y-%b')
        forecast_df = forecast_df.sort_values('date')
        
        if len(forecast_df) > 1:
            # Linear Regression using ordinal dates
            forecast_df['ordinal_date'] = forecast_df['date'].apply(lambda x: x.toordinal())
            
            x = forecast_df['ordinal_date'].values
            y = forecast_df['revenue'].values
            
            # Fit polynomial (degree 1 = linear)
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            
            # Predict next 3 months
            last_date = forecast_df['date'].iloc[-1]
            future_dates = [last_date + pd.DateOffset(months=i) for i in range(1, 4)]
            future_ordinals = [d.toordinal() for d in future_dates]
            future_revenue = p(future_ordinals)
            
            future_df = pd.DataFrame({
                'date': future_dates,
                'revenue': future_revenue,
                'type': 'Forecast'
            })
            
            forecast_df['type'] = 'Historical'
            
            # Combine
            combined_df = pd.concat([forecast_df[['date', 'revenue', 'type']], future_df])
            
            # Plot
            fig_forecast = px.line(
                combined_df, 
                x='date', 
                y='revenue', 
                color='type', 
                markers=True,
                line_shape='spline',
                title=f"Revenue Forecast: {selected_year} - Next Quarter"
            )
            fig_forecast.update_xaxes(dtick="M1", tickformat="%b %Y")
            fig_forecast.add_vline(x=last_date, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_forecast, use_container_width=True)
        else:
            st.warning("Not enough data points to generate a forecast.")

    with tab3:
        st.subheader("Detailed Financial Records")
        
        # Download Button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name=f'financial_data_{selected_year}.csv',
            mime='text/csv',
        )
        
        st.dataframe(df, use_container_width=True)