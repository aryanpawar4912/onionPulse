# create_sample_data.py
import os
import django
import random
from datetime import datetime, timedelta

# CORRECTED: Match your project structure
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onion_forecast.settings')
django.setup()

from forecast_app.models import OnionPrice
from django.utils.timezone import now

def create_sample_data():
    """Create sample price data for predictions"""
    
    print("Starting to create sample data...")
    
    markets = ['Lasalgaon', 'Pimpalgaon', 'Nashik', 'Pune', 'Mumbai', 'Delhi', 'Jaipur']
    states = ['Maharashtra', 'Maharashtra', 'Maharashtra', 'Maharashtra', 'Maharashtra', 'Delhi', 'Rajasthan']
    districts = ['Nashik', 'Nashik', 'Nashik', 'Pune', 'Mumbai', 'Delhi', 'Jaipur']
    varieties = ['NASHIK_RED', 'PUNE_WHITE', 'MAHARASHTRA', 'OTHER']
    
    # Clear existing sample data (optional)
    print("Clearing existing sample data...")
    OnionPrice.objects.all().delete()
    
    # Create 180 days of data (6 months)
    start_date = now().date() - timedelta(days=180)
    
    records_created = 0
    
    for i in range(180):
        current_date = start_date + timedelta(days=i)
        
        # Skip weekends occasionally (markets closed)
        if random.random() < 0.3 and current_date.weekday() >= 5:  # 30% chance to skip weekend
            continue
            
        # Create 3-5 records per day
        for j in range(random.randint(3, 5)):
            market_idx = random.randint(0, len(markets)-1)
            variety_idx = random.randint(0, len(varieties)-1)
            
            # Generate realistic onion prices with trends
            base_trend = 1200 + (i * 3)  # Slowly increasing trend
            daily_variation = random.randint(-200, 200)
            base_price = base_trend + daily_variation
            
            # Ensure reasonable prices (₹800-₹3500 range)
            base_price = max(800, min(3500, base_price))
            
            min_price = base_price - random.randint(50, 150)
            max_price = base_price + random.randint(50, 150)
            modal_price = (min_price + max_price) / 2
            arrival = random.randint(300, 2500)
            
            # Create the record
            OnionPrice.objects.create(
                date=current_date,
                market=markets[market_idx],
                state=states[market_idx],
                district=districts[market_idx],
                variety=varieties[variety_idx],
                min_price=min_price,
                max_price=max_price,
                modal_price=modal_price,
                arrival_quantity=arrival
            )
            records_created += 1
            
            if records_created % 100 == 0:
                print(f"Created {records_created} records...")
    
    print(f"\n✅ SUCCESS: Created {records_created} sample price records!")
    print(f"📅 Date range: {start_date} to {now().date()}")
    print(f"🏪 Markets covered: {', '.join(markets)}")
    print(f"🌱 Varieties: {', '.join(varieties)}")
    print("\n🎯 Now try generating predictions in your admin panel!")
    
    # Show sample of created data
    print("\n📊 Sample of created data:")
    recent_prices = OnionPrice.objects.order_by('-date')[:5]
    for price in recent_prices:
        print(f"  {price.date}: {price.market} - ₹{price.modal_price:.2f}")
    
    return records_created

if __name__ == '__main__':
    create_sample_data()