# forecast_app/ml_model/price_predictor.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
import os

class RealTimePredictor:
    def __init__(self):
        self.models = {}
        self.feature_cols = None
        self.scaler = None
        self.load_models()
        self.current_data = None
    
    def load_models(self):
        """Load trained models"""
        model_path = 'forecast_app/ml_model/saved_models/'
        
        try:
            # Load Linear Regression (best model!)
            lr_path = os.path.join(model_path, 'lr_simple.joblib')
            if os.path.exists(lr_path):
                self.models['lr'] = joblib.load(lr_path)
                print("✅ Loaded Linear Regression model (R²=0.97)")
            
            # Load scaler
            scaler_path = os.path.join(model_path, 'scaler_simple.joblib')
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
            
            # Load feature columns
            feature_cols_path = os.path.join(model_path, 'feature_cols.joblib')
            if os.path.exists(feature_cols_path):
                self.feature_cols = joblib.load(feature_cols_path)
                print(f"✅ Loaded {len(self.feature_cols)} feature columns")
            
            # Load other models as backups
            rf_path = os.path.join(model_path, 'rf_simple.joblib')
            if os.path.exists(rf_path):
                self.models['rf'] = joblib.load(rf_path)
                print("✅ Loaded Random Forest model")
            
            xgb_path = os.path.join(model_path, 'xgb_simple.joblib')
            if os.path.exists(xgb_path):
                self.models['xgb'] = joblib.load(xgb_path)
                print("✅ Loaded XGBoost model")
                
        except Exception as e:
            print(f"Error loading models: {e}")
        
        print(f"Total models loaded: {len(self.models)}")
    
    def load_latest_data(self):
        """Load latest data from database"""
        from forecast_app.models import OnionPrice
        from django.utils import timezone
        
        # Get data from last 2 years
        start_date = timezone.now() - timedelta(days=730)
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
        
        self.current_data = pd.DataFrame(data)
        if not self.current_data.empty:
            self.current_data['date'] = pd.to_datetime(self.current_data['date'])
            self.current_data = self.current_data.sort_values('date')
        
        print(f"Loaded {len(self.current_data)} records")
        return self.current_data
    
    def prepare_features(self, df, market=None):
        """Prepare features for prediction"""
        if len(df) < 7:
            return None
        
        # Use the latest data
        df = df.copy()
        df = df.sort_values('date')
        
        # Get the last row
        latest = df.iloc[-1:].copy()
        
        # Basic features
        latest['day_of_year'] = latest['date'].dt.dayofyear
        latest['month'] = latest['date'].dt.month
        latest['year'] = latest['date'].dt.year
        
        # Price features
        if len(df) >= 2:
            latest['price_lag_1'] = df['modal_price'].iloc[-2]
        else:
            latest['price_lag_1'] = latest['modal_price'].iloc[0]
        
        if len(df) >= 8:
            latest['price_lag_7'] = df['modal_price'].iloc[-8]
        else:
            latest['price_lag_7'] = latest['modal_price'].iloc[0]
        
        if len(df) >= 7:
            latest['price_ma_7'] = df['modal_price'].tail(7).mean()
        else:
            latest['price_ma_7'] = df['modal_price'].mean()
        
        if len(df) >= 30:
            latest['price_ma_30'] = df['modal_price'].tail(30).mean()
        else:
            latest['price_ma_30'] = df['modal_price'].mean()
        
        # Price changes
        if len(df) >= 2:
            latest['price_change_1'] = (df['modal_price'].iloc[-1] - df['modal_price'].iloc[-2]) / df['modal_price'].iloc[-2]
        else:
            latest['price_change_1'] = 0
        
        if len(df) >= 8:
            latest['price_change_7'] = (df['modal_price'].iloc[-1] - df['modal_price'].iloc[-8]) / df['modal_price'].iloc[-8]
        else:
            latest['price_change_7'] = 0
        
        # Create one-hot encoding for categorical features
        if self.feature_cols:
            # Initialize all feature columns to 0
            for col in self.feature_cols:
                if col not in latest.columns:
                    latest[col] = 0
            
            # Get categorical values
            market_val = latest['market'].iloc[0] if 'market' in latest.columns else ''
            state_val = latest['state'].iloc[0] if 'state' in latest.columns else ''
            variety_val = latest['variety'].iloc[0] if 'variety' in latest.columns else ''
            
            # Set the correct one-hot values
            if market_val and f'market_{market_val}' in self.feature_cols:
                latest[f'market_{market_val}'] = 1
            
            if state_val and f'state_{state_val}' in self.feature_cols:
                latest[f'state_{state_val}'] = 1
            
            if variety_val and f'variety_{variety_val}' in self.feature_cols:
                latest[f'variety_{variety_val}'] = 1
            
            # Select only the feature columns used in training
            latest = latest[self.feature_cols]
        
        return latest
    
    def predict_with_model(self, model_name, df):
        """Predict using specified model"""
        if model_name not in self.models or self.scaler is None:
            return None
        
        # Prepare features
        features_df = self.prepare_features(df)
        if features_df is None or len(features_df) == 0:
            return None
        
        try:
            # Scale features
            scaled_features = self.scaler.transform(features_df)
            
            # Make prediction
            prediction = self.models[model_name].predict(scaled_features)[0]
            return float(prediction)
        except Exception as e:
            print(f"Error predicting with {model_name}: {e}")
            return None
    
    def predict_next_7_days(self, market=None, variety=None):
        """Predict prices for next 7 days"""
        if self.current_data is None:
            self.load_latest_data()
        
        if self.current_data is None or len(self.current_data) == 0:
            print("No data available")
            return None
        
        # Filter data if market specified
        df = self.current_data.copy()
        if market:
            df = df[df['market'] == market]
        if variety:
            df = df[df['variety'] == variety]
        
        if len(df) < 7:
            print(f"Not enough data. Only {len(df)} records.")
            return None
        
        # Try Linear Regression first (best model)
        if 'lr' in self.models:
            print("Using Linear Regression model...")
            initial_pred = self.predict_with_model('lr', df)
        elif 'rf' in self.models:
            print("Using Random Forest model...")
            initial_pred = self.predict_with_model('rf', df)
        elif 'xgb' in self.models:
            print("Using XGBoost model...")
            initial_pred = self.predict_with_model('xgb', df)
        else:
            print("No models available")
            return None
        
        if initial_pred is None:
            # Fallback to moving average
            print("Model prediction failed, using moving average...")
            initial_pred = df['modal_price'].tail(7).mean()
        
        # Generate predictions for next 7 days
        predictions = []
        current_price = float(df['modal_price'].iloc[-1])
        
        # Calculate recent trend
        if len(df) >= 7:
            recent_trend = (df['modal_price'].iloc[-1] - df['modal_price'].iloc[-7]) / df['modal_price'].iloc[-7]
        else:
            recent_trend = 0
        
        # First day prediction
        predictions.append(round(initial_pred, 2))
        
        # Next 6 days: continue trend
        for i in range(1, 7):
            daily_trend = recent_trend * (0.8 ** i)  # Diminishing trend
            random_factor = np.random.uniform(-0.01, 0.01)  # Small randomness
            next_price = predictions[-1] * (1 + daily_trend + random_factor)
            
            # Apply reasonable bounds
            avg_price = df['modal_price'].mean()
            min_bound = max(avg_price * 0.7, 500)
            max_bound = avg_price * 1.3
            next_price = np.clip(next_price, min_bound, max_bound)
            
            predictions.append(round(next_price, 2))
        
        # Create result DataFrame
        dates = pd.date_range(start=datetime.now().date(), periods=7)
        result = pd.DataFrame({
            'date': dates,
            'predicted_price': predictions,
            'min_price': [round(p * 0.95, 2) for p in predictions],  # 5% lower
            'max_price': [round(p * 1.05, 2) for p in predictions],  # 5% higher
            'confidence': [0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55]  # Decreasing
        })
        
        return result
    
    def get_price_trend(self, days=30):
        """Get price trend for specified days"""
        if self.current_data is None:
            self.load_latest_data()
        
        if self.current_data is None or len(self.current_data) == 0:
            return {
                'current_price': None,
                'trend': "No data",
                'min_30d': None,
                'max_30d': None,
                'avg_30d': None,
            }
        
        df = self.current_data.copy()
        df = df.sort_values('date')
        
        # Calculate trend
        recent_trend = "Stable"
        if len(df) >= 2:
            last_price = df['modal_price'].iloc[-1]
            prev_price = df['modal_price'].iloc[-2]
            change = ((last_price - prev_price) / prev_price) * 100
            
            if change > 5:
                recent_trend = "Increasing Rapidly"
            elif change > 2:
                recent_trend = "Increasing"
            elif change < -5:
                recent_trend = "Decreasing Rapidly"
            elif change < -2:
                recent_trend = "Decreasing"
        
        # Get recent statistics
        recent_data = df.tail(min(days, len(df)))
        
        return {
            'current_price': float(df['modal_price'].iloc[-1]) if len(df) > 0 else None,
            'trend': recent_trend,
            'min_30d': float(recent_data['modal_price'].min()) if len(recent_data) > 0 else None,
            'max_30d': float(recent_data['modal_price'].max()) if len(recent_data) > 0 else None,
            'avg_30d': float(recent_data['modal_price'].mean()) if len(recent_data) > 0 else None,
            'daily_change': round(change, 2) if 'change' in locals() else 0,
        }
    
    def get_recommendation(self, user_type='FARMER'):
        """Get recommendations based on user type"""
        predictions = self.predict_next_7_days()
        trend = self.get_price_trend()
        
        recommendations = []
        
        if user_type == 'FARMER':
            if trend['trend'] in ['Increasing', 'Increasing Rapidly']:
                recommendations.append({
                    'type': 'SELL',
                    'message': 'Prices are increasing. Consider selling now to maximize profits.',
                    'confidence': 'High',
                    'action': 'Sell within 1-2 days'
                })
            elif trend['trend'] in ['Decreasing', 'Decreasing Rapidly']:
                recommendations.append({
                    'type': 'HOLD',
                    'message': 'Prices are decreasing. Consider storing for better prices.',
                    'confidence': 'Medium',
                    'action': 'Wait 5-7 days and monitor'
                })
            else:
                recommendations.append({
                    'type': 'MONITOR',
                    'message': 'Prices are stable. Monitor market for 2-3 days.',
                    'confidence': 'Low',
                    'action': 'Check again in 2-3 days'
                })
            
            # Add prediction-based recommendation
            if predictions is not None and len(predictions) > 0:
                avg_predicted = predictions['predicted_price'].mean()
                if avg_predicted > trend['current_price'] * 1.05:
                    recommendations.append({
                        'type': 'DELAY_SELL',
                        'message': f'Prices expected to rise to ₹{avg_predicted:.2f} in next week',
                        'confidence': 'Medium',
                        'action': 'Consider waiting 3-4 days'
                    })
        
        elif user_type == 'TRADER':
            if trend['trend'] in ['Increasing', 'Increasing Rapidly']:
                recommendations.append({
                    'type': 'BUY',
                    'message': 'Prices trending up. Good time to buy for short-term trade.',
                    'confidence': 'High'
                })
            elif trend['trend'] in ['Decreasing', 'Decreasing Rapidly']:
                recommendations.append({
                    'type': 'SELL',
                    'message': 'Prices trending down. Sell existing stock.',
                    'confidence': 'Medium'
                })
            else:
                recommendations.append({
                    'type': 'HOLD',
                    'message': 'Market stable. Maintain current position.',
                    'confidence': 'Low'
                })
        
        elif user_type == 'CONSUMER':
            if trend['trend'] in ['Decreasing', 'Decreasing Rapidly']:
                recommendations.append({
                    'type': 'DELAY_BUY',
                    'message': 'Prices decreasing. Wait for better prices.',
                    'confidence': 'High',
                    'action': 'Wait 3-4 days before buying'
                })
            elif trend['trend'] in ['Increasing', 'Increasing Rapidly']:
                recommendations.append({
                    'type': 'BUY_NOW',
                    'message': 'Prices increasing. Buy now to avoid higher prices.',
                    'confidence': 'High',
                    'action': 'Purchase within 1-2 days'
                })
            else:
                recommendations.append({
                    'type': 'NORMAL_BUY',
                    'message': 'Prices stable. Normal buying recommended.',
                    'confidence': 'Medium',
                    'action': 'Buy as needed'
                })
        
        return recommendations
    
    def get_market_analysis(self, market_name):
        """Get detailed analysis for a specific market"""
        if self.current_data is None:
            self.load_latest_data()
        
        if market_name not in self.current_data['market'].unique():
            return {"error": f"Market '{market_name}' not found in data"}
        
        market_data = self.current_data[self.current_data['market'] == market_name].copy()
        market_data = market_data.sort_values('date')
        
        if len(market_data) < 7:
            return {"error": f"Insufficient data for {market_name}"}
        
        # Calculate metrics
        latest = market_data.iloc[-1]
        week_ago = market_data.iloc[-7] if len(market_data) >= 7 else None
        
        analysis = {
            'market': market_name,
            'current_price': float(latest['modal_price']),
            'current_date': latest['date'].strftime('%Y-%m-%d'),
            'state': latest['state'],
            'district': latest['district'],
            'variety': latest['variety'],
            'price_stats': {
                'min_7d': float(market_data['modal_price'].tail(7).min()),
                'max_7d': float(market_data['modal_price'].tail(7).max()),
                'avg_7d': float(market_data['modal_price'].tail(7).mean()),
            }
        }
        
        # Calculate weekly change
        if week_ago is not None:
            week_change = ((latest['modal_price'] - week_ago['modal_price']) / week_ago['modal_price']) * 100
            analysis['weekly_change'] = round(float(week_change), 2)
        
        # Get predictions
        predictions = self.predict_next_7_days(market=market_name)
        if predictions is not None:
            analysis['predictions'] = predictions.to_dict('records')
        
        # Get trend
        analysis['trend'] = self.get_price_trend()
        
        return analysis