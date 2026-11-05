import pandas as pd
import numpy as np

def generate_signals(df):
    """
    Génère des signaux simples : 1 (Buy), -1 (Sell), 0 (Hold)
    Basé sur le RSI et les bandes de Bollinger.
    """
    df_signals = df.copy()
    signals = []
    
    for i in range(len(df_signals)):
        rsi = df_signals['RSI'].iloc[i]
        close = df_signals['Close'].iloc[i]
        bb_low = df_signals['BB_low'].iloc[i]
        bb_high = df_signals['BB_high'].iloc[i]
        
        # Simple strategy: RSI < 30 and price near lower BB -> BUY
        if rsi < 30 and close <= bb_low * 1.02:
            signals.append(1)
            # print("Buy signal detected!")
        # RSI > 70 and price near upper BB -> SELL
        elif rsi > 70 and close >= bb_high * 0.98:
            signals.append(-1)
        else:
            signals.append(0)
            
    df_signals['Signal'] = signals
    return df_signals
