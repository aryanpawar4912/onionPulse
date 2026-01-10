# forecast_app/ml_model/price_predictor.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
import os
from .model_training import OnionPricePredictor
class RealTimePredictor:
    def __init__(self):
        self.predictor = OnionPricePredictor()
        self.models = self.predictor.load_models()
        self.current_data = None
    def load_latest_data(self):
        """Load latest data from MongoDB"""
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
        return self.current_data
    def predict_next_7_days(self, market=None, variety=None):
        """Predict prices for next 7 days"""
        if self.current_data is None:
            self.load_latest_data()
        
        # Filter data if market or variety specified
        df = self.current_data.copy()
        if market:
            df = df[df['market'] == market]
        if variety:
            df = df[df['variety'] == variety]
        
        # Use the best performing model (you can select based on validation)
        if 'lstm' in self.models:
            predictions = self.predictor.predict_future('lstm', future_days=7)
        elif 'rf' in self.models:
            predictions = self.predictor.predict_future('rf', future_days=7)
        else:
            predictions = self.predictor.predict_future('prophet', future_days=7)
        
        return predictions
    
    def get_price_trend(self, days=30):
        """Get price trend for specified days"""
        if self.current_data is None:
            self.load_latest_data()
        
        df = self.current_data.copy()
        df = df.sort_values('date')
        
        # Calculate moving averages
        df['ma_7'] = df['modal_price'].rolling(window=7).mean()
        df['ma_30'] = df['modal_price'].rolling(window=30).mean()
        
        # Get trend direction
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
        
        return {
            'current_price': df['modal_price'].iloc[-1] if len(df) > 0 else None,
            'trend': recent_trend,
            'min_30d': df['modal_price'].tail(30).min() if len(df) >= 30 else None,
            'max_30d': df['modal_price'].tail(30).max() if len(df) >= 30 else None,
            'avg_30d': df['modal_price'].tail(30).mean() if len(df) >= 30 else None,
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
                    'message': 'Prices are increasing. Consider selling now.',
                    'confidence': 'High'
                })
            elif trend['trend'] in ['Decreasing', 'Decreasing Rapidly']:
                recommendations.append({
                    'type': 'HOLD',
                    'message': 'Prices are decreasing. Consider storing for better prices.',
                    'confidence': 'Medium'
                })
            else:
                recommendations.append({
                    'type': 'MONITOR',
                    'message': 'Prices are stable. Monitor market for 2-3 days.',
                    'confidence': 'Low'
                })
        
        elif user_type == 'TRADER':
            # Trader recommendations
            pass
        
        elif user_type == 'CONSUMER':
            # Consumer recommendations
            pass
        
        return recommendations