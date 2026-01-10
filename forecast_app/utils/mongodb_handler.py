# forecast_app/utils/mongodb_handler.py

from pymongo import MongoClient
import pandas as pd
from datetime import datetime, timedelta
import os
from django.conf import settings

class MongoDBHandler:
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()
    
    def connect(self):
        """Connect to MongoDB"""
        try:
            # Get connection details from settings
            from django.conf import settings
            db_settings = settings.DATABASES['default']
            
            self.client = MongoClient(db_settings['CLIENT']['host'])
            self.db = self.client[db_settings['NAME']]
            print(f"Connected to MongoDB: {db_settings['NAME']}")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
    
    def import_csv_data(self, csv_path):
        """Import data from CSV to MongoDB"""
        try:
            df = pd.read_csv(csv_path)
            
            # Convert date strings to datetime
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            
            # Convert DataFrame to dictionary
            data = df.to_dict('records')
            
            # Insert into MongoDB
            collection = self.db['forecast_app_onionprice']
            result = collection.insert_many(data)
            
            print(f"Imported {len(result.inserted_ids)} records")
            return True
            
        except Exception as e:
            print(f"Error importing data: {e}")
            return False
    
    def get_price_data(self, start_date=None, end_date=None, market=None):
        """Get price data with filters"""
        try:
            collection = self.db['forecast_app_onionprice']
            
            # Build query
            query = {}
            
            if start_date or end_date:
                query['date'] = {}
                if start_date:
                    query['date']['$gte'] = start_date
                if end_date:
                    query['date']['$lte'] = end_date
            
            if market:
                query['market'] = market
            
            # Execute query
            cursor = collection.find(query).sort('date', 1)
            
            # Convert to DataFrame
            data = list(cursor)
            df = pd.DataFrame(data)
            
            # Remove MongoDB _id field
            if '_id' in df.columns:
                df.drop('_id', axis=1, inplace=True)
            
            return df
            
        except Exception as e:
            print(f"Error getting data: {e}")
            return pd.DataFrame()
    
    def get_markets_list(self):
        """Get list of unique markets"""
        try:
            collection = self.db['forecast_app_onionprice']
            markets = collection.distinct('market')
            return markets
        except Exception as e:
            print(f"Error getting markets: {e}")
            return []
    
    def get_recent_prices(self, days=30, limit=100):
        """Get recent prices"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            collection = self.db['forecast_app_onionprice']
            
            query = {
                'date': {
                    '$gte': start_date,
                    '$lte': end_date
                }
            }
            
            cursor = collection.find(query).sort('date', -1).limit(limit)
            data = list(cursor)
            
            return data
            
        except Exception as e:
            print(f"Error getting recent prices: {e}")
            return []
    
    def save_prediction(self, prediction_data):
        """Save prediction to database"""
        try:
            collection = self.db['forecast_app_priceprediction']
            result = collection.insert_one(prediction_data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error saving prediction: {e}")
            return None
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()