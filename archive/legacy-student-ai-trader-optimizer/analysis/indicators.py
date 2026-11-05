import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands

def add_indicators(df):
    """
    Ajoute RSI, MACD et Bollinger Bands au dataframe.
    """
    df_copy = df.copy()
    
    # RSI
    indicator_rsi = RSIIndicator(close=df_copy['Close'], window=14)
    df_copy['RSI'] = indicator_rsi.rsi()
    
    # MACD
    indicator_macd = MACD(close=df_copy['Close'], window_slow=26, window_fast=12, window_sign=9)
    df_copy['MACD'] = indicator_macd.macd()
    df_copy['MACD_signal'] = indicator_macd.macd_signal()
    
    # Bollinger Bands
    indicator_bb = BollingerBands(close=df_copy['Close'], window=20, window_dev=2)
    df_copy['BB_high'] = indicator_bb.bollinger_hband()
    df_copy['BB_low'] = indicator_bb.bollinger_lband()
    
    # Drop rows avec NaN créés par les indicateurs
    df_copy = df_copy.dropna()
    
    return df_copy
