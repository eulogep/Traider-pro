import yfinance as yf
import pandas as pd

def get_stock_data(ticker, period="1y"):
    """
    Récupère les données historiques via yfinance.
    """
    # print(f"Fetching data for {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        
        if df.empty:
            print(f"Erreur : Aucune donnée trouvée pour {ticker}")
            return None
            
        # On garde juste les colonnes importantes
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # TODO: gérer les NaN de façon plus propre si on a des trous dans les datas
        df = df.dropna()
        
        return df
    except Exception as e:
        print(f"Erreur lors du fetch des données : {e}")
        return None
