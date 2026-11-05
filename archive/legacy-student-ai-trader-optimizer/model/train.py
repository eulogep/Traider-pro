import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def train_rf_model(df):
    """
    Entraîne un RandomForest basique pour prédire si ça va monter ou descendre
    le lendemain.
    """
    # Features (on utilise nos indicateurs)
    features = ['RSI', 'MACD', 'MACD_signal', 'Volume']
    
    # Target: 1 si Close(j+1) > Close(j) sinon 0
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    
    # On enlève la dernière ligne qui a un Target NaN
    df_clean = df.dropna()
    
    X = df_clean[features]
    y = df_clean['Target']
    
    # Split train/test (80/20)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    # Model init
    # Petit modèle, pas besoin de trop d'arbres
    model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
    model.fit(X_train, y_train)
    
    # Petite éval rapide
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    # print(f"Model Accuracy: {accuracy:.2f}")
    
    # return trained model and basic score
    return model, accuracy
