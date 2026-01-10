# forecast_app/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
import json
import pandas as pd
from .models import OnionPrice, PricePrediction, MarketFactor, UserProfile
from .ml_model.price_predictor import RealTimePredictor
from .utils.mongodb_handler import MongoDBHandler
def home(request):
    """Home page"""
    return render(request, 'forecast_app/home.html')

def dashboard(request):
    """Main dashboard"""
    predictor = RealTimePredictor()
    
    # Get current trends
    trend_data = predictor.get_price_trend()
    
    # Get predictions
    predictions = predictor.predict_next_7_days()
    
    # Get market factors
    factors = MarketFactor.objects.filter(is_active=True)[:5]
    
    context = {
        'trend_data': trend_data,
        'predictions': predictions.to_dict('records') if predictions is not None else [],
        'factors': factors,
        'user_type': request.user.userprofile.user_type if hasattr(request.user, 'userprofile') else None
    }
    
    return render(request, 'forecast_app/dashboard.html', context)

def historical_data(request):
    """View historical price data"""
    mongo = MongoDBHandler()
    
    # Get filter parameters
    market = request.GET.get('market', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Convert dates
    start_date_obj = None
    end_date_obj = None
    
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            start_date_obj = None
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            end_date_obj = None
    
    # Get data
    df = mongo.get_price_data(
        start_date=start_date_obj,
        end_date=end_date_obj,
        market=market
    )
    
    # Get markets list for filter dropdown
    markets = mongo.get_markets_list()
    
    context = {
        'data': df.to_dict('records') if not df.empty else [],
        'markets': markets,
        'selected_market': market,
        'start_date': start_date,
        'end_date': end_date
    }
    
    return render(request, 'forecast_app/historical.html', context)

@login_required
def predict_price(request):
    """Make price predictions"""
    if request.method == 'POST':
        # Get form data
        market = request.POST.get('market')
        days_ahead = int(request.POST.get('days_ahead', 7))
        model_type = request.POST.get('model_type', 'lstm')
        
        # Make prediction
        predictor = RealTimePredictor()
        predictor.load_latest_data()
        
        predictions = predictor.predictor.predict_future(
            model_name=model_type,
            future_days=days_ahead
        )
        
        if predictions is not None:
            # Save prediction to database
            for _, row in predictions.iterrows():
                prediction = PricePrediction.objects.create(
                    prediction_date=timezone.now().date(),
                    forecast_date=row['ds'] if 'ds' in row else timezone.now().date() + timedelta(days=1),
                    market=market or 'All Markets',
                    predicted_modal_price=row['yhat'] if 'yhat' in row else row['predicted_price'],
                    predicted_min_price=row.get('yhat_lower', row['yhat'] * 0.95) if 'yhat_lower' in row else row['predicted_price'] * 0.95,
                    predicted_max_price=row.get('yhat_upper', row['yhat'] * 1.05) if 'yhat_upper' in row else row['predicted_price'] * 1.05,
                    confidence_interval=85.0,
                    model_used_id=1  # Assuming model ID 1 exists
                )
            
            messages.success(request, 'Prediction completed successfully!')
            return redirect('prediction_results')
    
    # GET request - show form
    mongo = MongoDBHandler()
    markets = mongo.get_markets_list()
    
    context = {
        'markets': markets,
        'model_types': [
            ('lstm', 'LSTM Neural Network'),
            ('rf', 'Random Forest'),
            ('xgb', 'XGBoost'),
            ('prophet', 'Facebook Prophet')
        ]
    }
    
    return render(request, 'forecast_app/predict.html', context)

def prediction_results(request):
    """View prediction results"""
    predictions = PricePrediction.objects.all().order_by('-forecast_date')[:50]
    
    context = {
        'predictions': predictions
    }
    
    return render(request, 'forecast_app/prediction_results.html', context)

def api_get_prices(request):
    """API endpoint to get price data"""
    mongo = MongoDBHandler()
    
    # Get parameters
    market = request.GET.get('market', '')
    days = int(request.GET.get('days', 30))
    
    # Calculate dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get data
    df = mongo.get_price_data(
        start_date=start_date,
        end_date=end_date,
        market=market
    )
    
    # Format response
    if df.empty:
        return JsonResponse({'data': [], 'message': 'No data found'})
    
    # Convert to list of dicts
    data = []
    for _, row in df.iterrows():
        data.append({
            'date': row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
            'market': row.get('market', ''),
            'modal_price': row.get('modal_price', 0),
            'min_price': row.get('min_price', 0),
            'max_price': row.get('max_price', 0)
        })
    
    return JsonResponse({'data': data})

def api_get_prediction(request):
    """API endpoint to get predictions"""
    predictor = RealTimePredictor()
    
    market = request.GET.get('market', '')
    days = int(request.GET.get('days', 7))
    
    predictions = predictor.predict_next_7_days(market=market)
    
    if predictions is None:
        return JsonResponse({'error': 'Prediction failed'}, status=500)
    
    data = []
    if 'ds' in predictions.columns:  # Prophet format
        for _, row in predictions.iterrows():
            data.append({
                'date': row['ds'].strftime('%Y-%m-%d'),
                'predicted_price': float(row['yhat']),
                'lower_bound': float(row.get('yhat_lower', row['yhat'] * 0.95)),
                'upper_bound': float(row.get('yhat_upper', row['yhat'] * 1.05))
            })
    else:
        for _, row in predictions.iterrows():
            data.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'predicted_price': float(row['predicted_price'])
            })
    
    return JsonResponse({'predictions': data})

@login_required
def user_recommendations(request):
    """Get personalized recommendations"""
    # Get user type or use default
    user_type = 'GENERAL'  # Default user type
    
    if hasattr(request.user, 'userprofile'):
        user_type = request.user.userprofile.user_type
    else:
        messages.info(request, 'Complete your profile in admin for personalized recommendations.')
    
    predictor = RealTimePredictor()
    
    recommendations = predictor.get_recommendation(user_type)
    trend = predictor.get_price_trend()
    
    context = {
        'user_type': user_type,
        'recommendations': recommendations,
        'trend': trend
    }
    
    return render(request, 'forecast_app/recommendations.html', context)

def about(request):
    """About page"""
    return render(request, 'forecast_app/about.html')

def contact(request):
    """Contact page"""
    return render(request, 'forecast_app/contact.html')