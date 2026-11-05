import argparse
from data.fetch_data import get_stock_data
from analysis.indicators import add_indicators
from analysis.signals import generate_signals
from model.train import train_rf_model
from model.predict import predict_next_trend
from backtest.backtest import run_backtest

def main():
    parser = argparse.ArgumentParser(description="AI Trader Optimizer - Projet Etudiant")
    parser.add_argument('--ticker', type=str, default='AAPL', help='Ticker name (ex: AAPL, BTC-USD)')
    parser.add_argument('--period', type=str, default='1y', help='Data period (ex: 1y, 6mo)')
    args = parser.parse_args()
    
    print(f"--- 🤖 AI Trader Optimizer ---")
    print(f"Analyse pour le ticker: {args.ticker} (période: {args.period})\n")
    
    # 1. Fetch data
    df = get_stock_data(args.ticker, args.period)
    if df is None:
        return
        
    # 2. Indicators & Signals
    df = add_indicators(df)
    df = generate_signals(df)
    
    # 3. ML Model
    model, accuracy = train_rf_model(df)
    print(f"[ML] Random Forest entraîné (Accuracy: {accuracy:.2f})")
    
    # 4. Predict next trend
    prediction = predict_next_trend(model, df)
    print(f"[PREDICT] Tendance prévue pour la prochaine session : {prediction}\n")
    
    # 5. Backtest
    print("Lancement du backtest...")
    stats, plot = run_backtest(df)
    
    print("\n--- 📊 Résultats Backtest ---")
    print(f"Total signaux joués: {stats['total_signals']}")
    print(f"Win rate           : {stats['win_rate']}%")
    print(f"Best trade         : +{stats['best_trade']}%")
    print(f"Worst trade        : {stats['worst_trade']}%\n")
    
    print("Affichage du graphique... (fermez la fenêtre pour quitter)")
    plot.show()

if __name__ == '__main__':
    main()
