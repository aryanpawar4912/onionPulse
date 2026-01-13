# debug_predictor.py
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onion_forecast.settings')
import django
django.setup()

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib

class DebugPredictor:
    def __init__(self):
        self.models = {}
        self.feature_cols = None
        self.scaler = None
        self.load_models()
    
    def load_models(self):
        """Load models and debug"""
        model_path = 'forecast_app/ml_model/saved_models/'
        
        print("DEBUG: Loading models...")
        
        # Load Linear Regression
        lr_path = os.path.join(model_path, 'lr_simple.joblib')
        if os.path.exists(lr_path):
            self.models['lr'] = joblib.load(lr_path)
            print("DEBUG: ✅ Linear Regression loaded")
        
        # Load scaler
        scaler_path = os.path.join(model_path, 'scaler_simple.joblib')
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            print("DEBUG: ✅ Scaler loaded")
        
        # Load feature columns
        feature_cols_path = os.path.join(model_path, 'feature_cols.joblib')
        if os.path.exists(feature_cols_path):
            self.feature_cols = joblib.load(feature_cols_path)
            print(f"DEBUG: ✅ Feature columns loaded: {len(self.feature_cols)} features")
            print(f"DEBUG: First 10 features: {self.feature_cols[:10]}")
    
    def load_test_data(self):
        """Load some test data"""
        from forecast_app.models import OnionPrice
        
        prices = OnionPrice.objects.all().order_by('-date')[:50]
        
        data = []
        for price in prices:
            data.append({
                'date': price.date,
                'market': price.market,
                'state': price.state,
                'district': price.district,
                'variety': price.variety,
                'modal_price': price.modal_price,
            })
        
        return pd.DataFrame(data)
    
    def debug_feature_preparation(self, df):
        """Debug feature preparation"""
        print("\nDEBUG: Feature Preparation")
        print("=" * 50)
        
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        print(f"Original data shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        
        # Get the last row
        latest = df.iloc[-1:].copy()
        print(f"\nLatest row:")
        print(f"  Date: {latest['date'].iloc[0]}")
        print(f"  Market: {latest['market'].iloc[0]}")
        print(f"  State: {latest['state'].iloc[0]}")
        print(f"  Variety: {latest['variety'].iloc[0]}")
        print(f"  Price: {latest['modal_price'].iloc[0]}")
        
        # Prepare features
        latest['day_of_year'] = latest['date'].dt.dayofyear
        latest['month'] = latest['date'].dt.month
        latest['year'] = latest['date'].dt.year
        
        # Calculate lag features
        if len(df) >= 2:
            latest['price_lag_1'] = df['modal_price'].iloc[-2]
            print(f"  price_lag_1: {latest['price_lag_1'].iloc[0]}")
        
        if len(df) >= 8:
            latest['price_lag_7'] = df['modal_price'].iloc[-8]
        
        # Calculate rolling averages
        if len(df) >= 7:
            latest['price_ma_7'] = df['modal_price'].tail(7).mean()
            print(f"  price_ma_7: {latest['price_ma_7'].iloc[0]}")
        
        if len(df) >= 30:
            latest['price_ma_30'] = df['modal_price'].tail(30).mean()
        
        # Calculate price changes
        if len(df) >= 2:
            latest['price_change_1'] = (df['modal_price'].iloc[-1] - df['modal_price'].iloc[-2]) / df['modal_price'].iloc[-2]
        
        if len(df) >= 8:
            latest['price_change_7'] = (df['modal_price'].iloc[-1] - df['modal_price'].iloc[-8]) / df['modal_price'].iloc[-8]
        
        # Check what features we have vs what the model expects
        print(f"\nDEBUG: Features created:")
        for col in latest.columns:
            print(f"  {col}: {latest[col].iloc[0]}")
        
        # Check against expected features
        if self.feature_cols:
            print(f"\nDEBUG: Expected features ({len(self.feature_cols)}):")
            missing = []
            for col in self.feature_cols:
                if col in latest.columns:
                    print(f"  ✓ {col}: {latest[col].iloc[0]}")
                else:
                    missing.append(col)
                    print(f"  ✗ {col}: MISSING")
            
            print(f"\nDEBUG: Missing features: {missing}")
            
            # Try to create missing features
            for col in missing:
                if col.startswith('market_'):
                    market_name = col.replace('market_', '')
                    latest[col] = 1 if latest['market'].iloc[0] == market_name else 0
                    print(f"  Created {col} = {latest[col].iloc[0]}")
                elif col.startswith('state_'):
                    state_name = col.replace('state_', '')
                    latest[col] = 1 if latest['state'].iloc[0] == state_name else 0
                    print(f"  Created {col} = {latest[col].iloc[0]}")
                elif col.startswith('variety_'):
                    variety_name = col.replace('variety_', '')
                    latest[col] = 1 if latest['variety'].iloc[0] == variety_name else 0
                    print(f"  Created {col} = {latest[col].iloc[0]}")
                else:
                    latest[col] = 0
                    print(f"  Created {col} = 0")
        
        # Scale features
        if self.scaler is not None and self.feature_cols is not None:
            try:
                # Ensure we have all features in correct order
                prepared_features = latest[self.feature_cols]
                print(f"\nDEBUG: Prepared features shape: {prepared_features.shape}")
                
                scaled_features = self.scaler.transform(prepared_features)
                print(f"DEBUG: Scaled features shape: {scaled_features.shape}")
                print(f"DEBUG: First 5 scaled values: {scaled_features[0][:5]}")
                
                return scaled_features
            except Exception as e:
                print(f"DEBUG: Error scaling features: {e}")
                return None
        
        return None
    
    def test_prediction(self, df):
        """Test prediction"""
        print("\nDEBUG: Testing Prediction")
        print("=" * 50)
        
        # Prepare and scale features
        scaled_features = self.debug_feature_preparation(df)
        
        if scaled_features is not None and 'lr' in self.models:
            try:
                prediction = self.models['lr'].predict(scaled_features)
                print(f"\nDEBUG: Prediction successful!")
                print(f"DEBUG: Predicted price: {prediction[0]}")
                return prediction[0]
            except Exception as e:
                print(f"DEBUG: Prediction error: {e}")
                return None
        
        return None

def main():
    print("DEBUG PREDICTOR")
    print("=" * 50)
    
    # Create predictor
    predictor = DebugPredictor()
    
    # Load test data
    test_data = predictor.load_test_data()
    print(f"\nLoaded {len(test_data)} test records")
    
    # Test feature preparation and prediction
    prediction = predictor.test_prediction(test_data)
    
    if prediction is not None:
        print(f"\n✅ Final predicted price: ₹{prediction:.2f}")
    else:
        print("\n❌ Prediction failed")

if __name__ == "__main__":
    main()