# forecast_app/ml_model/model_training.py
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor
from prophet import Prophet
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
import joblib
import warnings
warnings.filterwarnings('ignore')
import os

class OnionPricePredictor:
    def __init__(self, data=None):
        self.data = data
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.models = {}
        
    def prepare_features(self, df):
        """Prepare features for ML model"""
        df = df.copy()
        
        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Extract date features
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['day'] = df['date'].dt.day
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_of_year'] = df['date'].dt.dayofyear
        df['week_of_year'] = df['date'].dt.isocalendar().week
        df['quarter'] = df['date'].dt.quarter
        
        # Seasonal features for onion (rabi and kharif seasons)
        def get_season(month):
            if month in [3, 4, 5]:  # March-May: Summer harvest
                return 0  # Summer
            elif month in [6, 7, 8, 9]:  # June-Sept: Kharif
                return 1  # Kharif
            elif month in [10, 11]:  # Oct-Nov: Late Kharif
                return 2  # Late Kharif
            else:  # Dec-Feb: Winter
                return 3  # Winter
        
        df['season'] = df['month'].apply(get_season)
        
        # Lag features (previous prices)
        for lag in [1, 7, 30, 90]:  # 1 day, 1 week, 1 month, 3 months
            df[f'price_lag_{lag}'] = df['modal_price'].shift(lag)
        
        # Rolling statistics
        df['price_rolling_mean_7'] = df['modal_price'].rolling(window=7).mean()
        df['price_rolling_std_7'] = df['modal_price'].rolling(window=7).std()
        df['price_rolling_mean_30'] = df['modal_price'].rolling(window=30).mean()
        
        # Encode categorical variables
        categorical_cols = ['market', 'state', 'district', 'variety']
        for col in categorical_cols:
            if col in df.columns:
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
        
        # Drop rows with NaN values from lag features
        df = df.dropna()
        
        return df
    
    def train_random_forest(self, X_train, y_train):
        """Train Random Forest model"""
        print("Training Random Forest model...")
        rf_model = RandomForestRegressor(
            n_estimators=200,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X_train, y_train)
        return rf_model
    
    def train_xgboost(self, X_train, y_train):
        """Train XGBoost model"""
        print("Training XGBoost model...")
        xgb_model = XGBRegressor(
            n_estimators=200,
            max_depth=10,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        xgb_model.fit(X_train, y_train)
        return xgb_model
    
    def train_lstm(self, X_train, y_train):
        """Train LSTM neural network"""
        print("Training LSTM model...")
        
        # Reshape data for LSTM [samples, time steps, features]
        if hasattr(X_train, 'values'):  # Check if it's a DataFrame
            X_train_reshaped = X_train.values.reshape((X_train.shape[0], 1, X_train.shape[1]))
        else:  # It's already a numpy array
            X_train_reshaped = X_train.reshape((X_train.shape[0], 1, X_train.shape[1]))
        
        # Build LSTM model
        model = Sequential([
            LSTM(100, return_sequences=True, input_shape=(X_train_reshaped.shape[1], X_train_reshaped.shape[2])),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25, activation='relu'),
            Dense(1)
        ])
        
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        
        # Callbacks
        early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
        
        # Train model
        history = model.fit(
            X_train_reshaped, y_train,
            epochs=50,
            batch_size=32,
            validation_split=0.2,
            callbacks=[early_stop],
            verbose=0
        )
        
        return model
    
    def train_prophet(self, df):
        """Train Facebook Prophet model"""
        print("Training Prophet model...")
        
        # Prepare data for Prophet
        prophet_df = df[['date', 'modal_price']].copy()
        prophet_df.columns = ['ds', 'y']
        
        # Create and fit model
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            seasonality_mode='multiplicative'
        )
        
        # Add Indian festival holidays (approximate dates)
        indian_holidays = pd.DataFrame({
            'holiday': 'festival',
            'ds': pd.to_datetime([
                '2023-01-26', '2023-03-08', '2023-04-14', '2023-08-15',  # National holidays
                '2023-10-02', '2023-12-25',  # Gandhi Jayanti, Christmas
            ]),
            'lower_window': -2,
            'upper_window': 2,
        })
        
        model.add_country_holidays(country_name='IN')
        model.fit(prophet_df)
        
        return model
    
    def train_all_models(self, df, target_col='modal_price'):
        """Train multiple models and compare performance"""
        
        # Prepare features
        df_processed = self.prepare_features(df)
        
        # Define features and target
        feature_cols = [col for col in df_processed.columns 
                       if col not in ['date', target_col, 'min_price', 'max_price'] 
                       and not col.startswith('Unnamed')]
        
        X = df_processed[feature_cols]
        y = df_processed[target_col]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train models
        models = {}
        
        # Random Forest
        rf_model = self.train_random_forest(X_train_scaled, y_train)
        models['rf'] = {
            'model': rf_model,
            'type': 'RF'
        }
        
        # XGBoost
        xgb_model = self.train_xgboost(X_train_scaled, y_train)
        models['xgb'] = {
            'model': xgb_model,
            'type': 'XGB'
        }
        
        # LSTM
        lstm_model = self.train_lstm(X_train_scaled, y_train)
        models['lstm'] = {
            'model': lstm_model,
            'type': 'LSTM'
        }
        
        # Prophet
        prophet_model = self.train_prophet(df)
        models['prophet'] = {
            'model': prophet_model,
            'type': 'PROPHET'
        }
        
        # Evaluate models
        evaluation_results = {}
        for name, model_info in models.items():
            if model_info['type'] != 'PROPHET':
                if model_info['type'] == 'LSTM':
                    X_test_reshaped = X_test_scaled.reshape((X_test_scaled.shape[0], 1, X_test_scaled.shape[1]))
                    y_pred = model_info['model'].predict(X_test_reshaped).flatten()
                else:
                    y_pred = model_info['model'].predict(X_test_scaled)
                
                mse = mean_squared_error(y_test, y_pred)
                mae = mean_absolute_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                
                evaluation_results[name] = {
                    'mse': mse,
                    'mae': mae,
                    'r2': r2,
                    'type': model_info['type']
                }
        
        self.models = models
        return models, evaluation_results
    
    def save_models(self, path='forecast_app/ml_model/saved_models/'):
        """Save trained models"""
        os.makedirs(path, exist_ok=True)
        
        for name, model_info in self.models.items():
            model = model_info['model']
            model_type = model_info['type']
            
            try:
                if model_type == 'LSTM':
                    model.save(f'{path}{name}_model.h5')
                elif model_type == 'PROPHET':
                    joblib.dump(model, f'{path}{name}_model.pkl')
                else:
                    joblib.dump(model, f'{path}{name}_model.joblib')
                print(f"Saved {name} model")
            except Exception as e:
                print(f"Error saving {name} model: {e}")
        
        # Save scaler and encoders
        joblib.dump(self.scaler, f'{path}scaler.joblib')
        joblib.dump(self.label_encoders, f'{path}label_encoders.joblib')
        
        print(f"All models saved to {path}")
    
    def load_models(self, path='forecast_app/ml_model/saved_models/'):
        """Load trained models"""
        models = {}
        
        model_files = {
            'rf': 'rf_model.joblib',
            'xgb': 'xgb_model.joblib',
            'lstm': 'lstm_model.h5',
            'prophet': 'prophet_model.pkl'
        }
        
        for name, filename in model_files.items():
            filepath = f'{path}{filename}'
            if os.path.exists(filepath):
                try:
                    if name == 'lstm':
                        models[name] = load_model(filepath)
                    else:
                        models[name] = joblib.load(filepath)
                    print(f"Loaded {name} model")
                except Exception as e:
                    print(f"Error loading {name} model: {e}")
        
        # Load scaler and encoders
        scaler_path = f'{path}scaler.joblib'
        encoders_path = f'{path}label_encoders.joblib'
        
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
        if os.path.exists(encoders_path):
            self.label_encoders = joblib.load(encoders_path)
        
        return models
    
    def predict_future(self, model_name, future_days=30, last_data=None):
        """Predict future prices"""
        if model_name not in self.models:
            print(f"Model {model_name} not found!")
            return None
        
        model = self.models[model_name]['model']
        model_type = self.models[model_name]['type']
        
        if model_type == 'PROPHET':
            # Create future dataframe
            future = model.make_future_dataframe(periods=future_days)
            forecast = model.predict(future)
            return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(future_days)
        
        elif model_type in ['RF', 'XGB']:
            # For tree-based models, we need to prepare future data
            predictions = []
            current_features = last_data.copy() if last_data is not None else self.data.iloc[-1].copy()
            
            for i in range(future_days):
                # Prepare features for prediction
                features = self.prepare_features_for_prediction(current_features, i)
                pred = model.predict([features])[0]
                predictions.append(pred)
                
                # Update for next prediction
                current_features = self.update_features_after_prediction(current_features, pred)
            
            return pd.DataFrame({
                'date': pd.date_range(start=pd.Timestamp.today(), periods=future_days),
                'predicted_price': predictions
            })
        
        return None
def prepare_features_for_prediction(self, current_features, day_offset):
    """Prepare features for future prediction"""
    # This is a simplified version - you should expand based on your feature engineering
    features = []
    
    # Extract date features from current date + offset
    current_date = pd.Timestamp.today() + timedelta(days=day_offset)
    
    features.append(current_date.month)
    features.append(current_date.day)
    features.append(current_date.dayofweek)
    
    # Add price features from current_features
    if isinstance(current_features, dict):
        features.extend([
            current_features.get('modal_price', 1500),
            current_features.get('price_lag_1', 1500),
            current_features.get('price_lag_7', 1500),
        ])
    elif isinstance(current_features, pd.Series):
        features.extend([
            current_features.get('modal_price', 1500),
            current_features.get('price_lag_1', 1500) if 'price_lag_1' in current_features else 1500,
            current_features.get('price_lag_7', 1500) if 'price_lag_7' in current_features else 1500,
        ])
    else:
        # Default values
        features.extend([1500, 1500, 1500])
    
    return features

def update_features_after_prediction(self, current_features, new_price):
    """Update features after making a prediction"""
    # Simplified update - you should expand this
    if isinstance(current_features, dict):
        current_features['modal_price'] = new_price
        current_features['price_lag_1'] = new_price
        # Shift other lag features if they exist
    elif isinstance(current_features, pd.Series):
        current_features['modal_price'] = new_price
        if 'price_lag_1' in current_features:
            current_features['price_lag_1'] = new_price
    
    return current_features