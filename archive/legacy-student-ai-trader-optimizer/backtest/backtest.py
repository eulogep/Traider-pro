import pandas as pd
import matplotlib.pyplot as plt

def run_backtest(df):
    """
    Simule la strat sur les datas historiques.
    Calcule le win rate et affiche un petit graphe.
    """
    initial_capital = 1000
    capital = initial_capital
    position = 0 # 0 = pas de position, 1 = on a acheté
    buy_price = 0
    
    trades = []
    
    for i in range(len(df)):
        signal = df['Signal'].iloc[i]
        price = df['Close'].iloc[i]
        
        # Acheter
        if signal == 1 and position == 0:
            position = 1
            buy_price = price
            # print(f"Achat à {price}")
            
        # Vendre
        elif signal == -1 and position == 1:
            position = 0
            profit = (price - buy_price) / buy_price * 100
            trades.append(profit)
            capital = capital * (1 + profit/100)
            # print(f"Vente à {price}, Profit: {profit:.2f}%")
            
    # Stats
    win_trades = [t for t in trades if t > 0]
    win_rate = (len(win_trades) / len(trades) * 100) if len(trades) > 0 else 0
    best_trade = max(trades) if trades else 0
    worst_trade = min(trades) if trades else 0
    
    # TODO: Refaire un plus beau plot si le temps
    plt.figure(figsize=(10, 5))
    plt.plot(df.index, df['Close'], label='Prix', alpha=0.5)
    
    # Les points d'achat/vente
    buys = df[df['Signal'] == 1]
    sells = df[df['Signal'] == -1]
    
    plt.scatter(buys.index, buys['Close'], marker='^', color='green', label='Buy', s=100)
    plt.scatter(sells.index, sells['Close'], marker='v', color='red', label='Sell', s=100)
    
    plt.title("Backtest Result")
    plt.legend()
    # On ne fait pas show() tout de suite
    
    return {
        'total_signals': len(trades) * 2, # (Achat + vente)
        'win_rate': round(win_rate, 2),
        'best_trade': round(best_trade, 2),
        'worst_trade': round(worst_trade, 2)
    }, plt
