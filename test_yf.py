import yfinance as yf
try:
    ticker = "MSFT"
    stock = yf.Ticker(ticker)
    history = stock.history(period="2y", interval="1mo")
    print(f"Data fetched: {len(history)} rows")
    print(history.head())
except Exception as e:
    print(f"Error: {e}")
