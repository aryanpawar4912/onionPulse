# import_data.py

import os
import django
import pandas as pd
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onion_forecast.settings')
django.setup()

from forecast_app.models import OnionPrice, MarketFactor
from forecast_app.utils.mongodb_handler import MongoDBHandler

def import_sample_data():
    """Import sample onion price data"""
    
    # Sample data (you can replace with real CSV file)
    sample_data = [
        {
            'date': '2024-01-01',
            'market': 'Azadpur Mandi, Delhi',
            'state': 'Delhi',
            'district': 'North Delhi',
            'variety': 'Nasik Red',
            'min_price': 1800.0,
            'max_price': 2200.0,
            'modal_price': 2000.0,
            'arrival_quantity': 15000.0
        },
        {
            'date': '2024-01-02',
            'market': 'Lasalgaon, Maharashtra',
            'state': 'Maharashtra',
            'district': 'Nashik',
            'variety': 'Nasik Red',
            'min_price': 1700.0,
            'max_price': 2100.0,
            'modal_price': 1900.0,
            'arrival_quantity': 12000.0
        },
        {
             'date': '2024-01-02',
            'market': 'Lasalgaon, Maharashtra',
            'state': 'Maharashtra',
            'district': 'Nashik',
            'variety': 'Nasik Red',
            'min_price': 1500.0,
            'max_price': 2000.0,
            'modal_price': 2900.0,
            'arrival_quantity': 12000.0
        }
        # Add more sample data...
    ]
    
    for data in sample_data:
        OnionPrice.objects.create(**data)
    
    print(f"Imported {len(sample_data)} records")

def create_market_factors():
    """Create sample market factors"""
    
    factors = [
        {
            'name': 'Monsoon Rainfall',
            'factor_type': 'WEATHER',
            'description': 'Adequate rainfall during monsoon season improves yield',
            'impact_score': -0.3  # Good rainfall reduces prices
        },
        {
            'name': 'Transportation Costs',
            'factor_type': 'TRANSPORT',
            'description': 'Increase in fuel prices raises transportation costs',
            'impact_score': 0.4  # Increases prices
        },
        {
            'name': 'Government Export Ban',
            'factor_type': 'POLICY',
            'description': 'Ban on onion exports reduces supply in international market',
            'impact_score': -0.5  # Reduces domestic prices
        },
        {
            'name': 'Rabi Season Harvest',
            'factor_type': 'SEASONAL',
            'description': 'Harvest season increases supply in market',
            'impact_score': -0.6  # Significantly reduces prices
        },
        {
            'name': 'Festival Demand',
            'factor_type': 'SEASONAL',
            'description': 'Increased demand during festivals',
            'impact_score': 0.5  # Increases prices
        },
    ]
    
    for factor in factors:
        MarketFactor.objects.create(**factor)
    
    print("Created market factors")

def import_from_csv(csv_path):
    """Import data from CSV file"""
    mongo = MongoDBHandler()
    success = mongo.import_csv_data(csv_path)
    
    if success:
        print("Data imported successfully from CSV")
    else:
        print("Failed to import data from CSV")

if __name__ == '__main__':
    print("Starting data import...")
    
    # Uncomment based on what you want to do
    # import_sample_data()
    # create_market_factors()
    
    # For CSV import
    # csv_path = 'data/onion_prices.csv'
    # import_from_csv(csv_path)
    
    print("Data import completed!")