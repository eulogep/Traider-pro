import numpy as np

def predict_next_trend(model, latest_data):
    """
    Prédit la tendance de la prochaine session avec le modèle entraîné.
    """
    # On prend juste la dernière ligne
    features = ['RSI', 'MACD', 'MACD_signal', 'Volume']
    last_row = latest_data[features].iloc[-1:]
    
    prediction = model.predict(last_row)[0]
    
    # 1 -> UP, 0 -> DOWN
    if prediction == 1:
        return "HAUSSIER (UP)"
    else:
        return "BAISSIER (DOWN)"
