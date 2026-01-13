# train_improved.py
import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onion_forecast.settings')
django.setup()

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from forecast_app.models import OnionPrice
from forecast_app.ml_model.model_training import OnionPricePredictor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import warnings
warnings.filterwarnings('ignore')

def fetch_and_prepare_data():
    """Fetch and prepare data properly"""
    print("Fetching data from database...")
    
    # Get data from last 2 years
    start_date = datetime.now() - timedelta(days=730)
    prices = OnionPrice.objects.filter(date__gte=start_date).order_by('date')
    
    # Convert to pandas DataFrame
    data = []
    for price in prices:
        data.append({
            'date': price.date,
            'market': price.market,
            'state': price.state,
            'district': price.district,
            'variety': price.variety,
            'min_price': price.min_price,
            'max_price': price.max_price,
            'modal_price': price.modal_price,
            'arrival_quantity': price.arrival_quantity
        })
    
    df = pd.DataFrame(data)
    print(f"Total records fetched: {len(df)}")
    
    # Sort by date
    df = df.sort_values('date')
    
    return df

def train_simple_but_effective(df):
    """Train simple models that should work better"""
    print("\n" + "="*60)
    print("TRAINING SIMPLE BUT EFFECTIVE MODELS")
    print("="*60)
    
    # Create simple features
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by date
    df = df.sort_values('date')
    
    # Use only recent data for training
    if len(df) > 365:  # If we have more than 1 year
        df = df.iloc[-365:]  # Use only last year
    
    # Simple feature engineering
    df['day_of_year'] = df['date'].dt.dayofyear
    df['month'] = df['date'].dt.month
    df['year'] = df['date'].dt.year
    
    # Lag features - but careful with train/test split
    df['price_lag_1'] = df['modal_price'].shift(1)
    df['price_lag_7'] = df['modal_price'].shift(7)
    
    # Rolling averages
    df['price_ma_7'] = df['modal_price'].rolling(window=7, min_periods=1).mean()
    df['price_ma_30'] = df['modal_price'].rolling(window=30, min_periods=1).mean()
    
    # Price change
    df['price_change_1'] = df['modal_price'].pct_change(1)
    df['price_change_7'] = df['modal_price'].pct_change(7)
    
    # Drop rows with NaN
    df = df.dropna()
    
    # Encode categorical variables simply (one-hot for small categories)
    categorical_cols = ['market', 'state', 'variety']
    for col in categorical_cols:
        if df[col].nunique() < 20:  # Only if less than 20 unique values
            dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
            df = pd.concat([df, dummies], axis=1)
    
    # Remove the original categorical columns if we created dummies
    df = df.drop(columns=categorical_cols, errors='ignore')
    
    # Define features and target
    feature_cols = [col for col in df.columns 
                   if col not in ['date', 'modal_price', 'min_price', 'max_price', 
                                 'district', 'arrival_quantity']
                   and not col.startswith('Unnamed')]
    
    X = df[feature_cols]
    y = df['modal_price']
    
    print(f"Features used: {feature_cols}")
    print(f"X shape: {X.shape}, y shape: {y.shape}")
    
    # Split data - time series split (no shuffling!)
    split_idx = int(len(X) * 0.8)  # 80% train, 20% test
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"Train size: {len(X_train)}, Test size: {len(X_test)}")
    
    # Train Random Forest (NO scaling for tree models!)
    print("\n1. Training Random Forest (no scaling)...")
    from sklearn.ensemble import RandomForestRegressor
    rf_model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    
    # Train XGBoost (NO scaling)
    print("2. Training XGBoost (no scaling)...")
    from xgboost import XGBRegressor
    xgb_model = XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    xgb_model.fit(X_train, y_train)
    
    # Train Linear Regression (with scaling)
    print("3. Training Linear Regression (with scaling)...")
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    lr_model = LinearRegression()
    lr_model.fit(X_train_scaled, y_train)
    
    # Evaluate models
    print("\n" + "="*60)
    print("MODEL PERFORMANCE")
    print("="*60)
    
    models = {
        'Random Forest': (rf_model, X_test, False),
        'XGBoost': (xgb_model, X_test, False),
        'Linear Regression': (lr_model, X_test_scaled, True)
    }
    
    results = {}
    for name, (model, X_test_data, is_scaled) in models.items():
        y_pred = model.predict(X_test_data)
        
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        results[name] = {
            'mse': mse,
            'mae': mae,
            'r2': r2,
            'predictions': y_pred
        }
        
        print(f"\n{name}:")
        print(f"  MSE:  {mse:,.2f}")
        print(f"  MAE:  {mae:,.2f}")
        print(f"  R²:   {r2:.4f}")
        print(f"  Avg Price: {y_test.mean():,.2f}")
        print(f"  Avg Pred:  {y_pred.mean():,.2f}")
    
    # Save the best model
    best_model_name = max(results.keys(), key=lambda x: results[x]['r2'])
    print(f"\n✅ Best model: {best_model_name} with R² = {results[best_model_name]['r2']:.4f}")
    
    # Save models
    save_path = 'forecast_app/ml_model/saved_models/'
    os.makedirs(save_path, exist_ok=True)
    
    import joblib
    joblib.dump(rf_model, f'{save_path}rf_simple.joblib')
    joblib.dump(xgb_model, f'{save_path}xgb_simple.joblib')
    joblib.dump(lr_model, f'{save_path}lr_simple.joblib')
    joblib.dump(scaler, f'{save_path}scaler_simple.joblib')
    
    # Save feature columns for prediction
    joblib.dump(feature_cols, f'{save_path}feature_cols.joblib')
    
    print(f"\n✅ Simple models saved to {save_path}")
    
    return results

def analyze_data(df):
    """Analyze the data to understand patterns"""
    print("\n" + "="*60)
    print("DATA ANALYSIS")
    print("="*60)
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Total days: {(df['date'].max() - df['date'].min()).days}")
    print(f"Unique markets: {df['market'].nunique()}")
    print(f"Unique states: {df['state'].nunique()}")
    
    # Price statistics
    print(f"\nPrice Statistics:")
    print(f"Min price: ₹{df['modal_price'].min():,.2f}")
    print(f"Max price: ₹{df['modal_price'].max():,.2f}")
    print(f"Mean price: ₹{df['modal_price'].mean():,.2f}")
    print(f"Median price: ₹{df['modal_price'].median():,.2f}")
    print(f"Std price: ₹{df['modal_price'].std():,.2f}")
    
    # Check for missing values
    print(f"\nMissing values:")
    for col in df.columns:
        missing = df[col].isnull().sum()
        if missing > 0:
            print(f"  {col}: {missing} missing")
    
    # Check price distribution by market
    if df['market'].nunique() < 10:
        print(f"\nAverage price by market:")
        for market, group in df.groupby('market'):
            print(f"  {market}: ₹{group['modal_price'].mean():,.2f} (n={len(group)})")

def main():
    print("=== IMPROVED MODEL TRAINING ===")
    
    # Fetch data
    df = fetch_and_prepare_data()
    
    if len(df) < 100:
        print(f"Need at least 100 records. Found: {len(df)}")
        return
    
    # Analyze data
    analyze_data(df)
    
    # Train simple models
    results = train_simple_but_effective(df)
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("="*60)
    
    if all(r['r2'] < 0 for r in results.values()):
        print("⚠️  All models have negative R². This suggests:")
        print("   1. The features don't predict the target well")
        print("   2. There might be data leakage issues")
        print("   3. Consider simpler approaches:")
        print("      - Predict tomorrow's price = today's price")
        print("      - Use moving average as prediction")
        print("      - Focus on specific markets separately")
    else:
        best_model = max(results.keys(), key=lambda x: results[x]['r2'])
        if results[best_model]['r2'] > 0.5:
            print(f"✅ Good! {best_model} has R² > 0.5")
        elif results[best_model]['r2'] > 0:
            print(f"⚠️  OK. {best_model} has positive R² but < 0.5")
            print("   Consider adding more features or getting more data")
    
    # Simple baseline: predict tomorrow = today
    df_sorted = df.sort_values('date')
    baseline_pred = df_sorted['modal_price'].shift(1).iloc[-len(y_test):].values
    baseline_r2 = r2_score(y_test, baseline_pred) if 'y_test' in locals() else None
    
    if baseline_r2 is not None:
        print(f"\nBaseline (tomorrow = today): R² = {baseline_r2:.4f}")

if __name__ == "__main__":
    main()