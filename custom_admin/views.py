# custom_admin/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg, Sum, Q
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
import pandas as pd
import csv
import io
from django.views.decorators.csrf import csrf_exempt
from forecast_app.models import OnionPrice, PricePrediction, MarketFactor, UserProfile
from forecast_app.ml_model.price_predictor import RealTimePredictor

import openpyxl
from django.http import StreamingHttpResponse
import time

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and (user.is_superuser or user.is_staff):
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions')
    
    return render(request, 'custom_admin/login.html')

@login_required
def admin_logout(request):
    logout(request)
    return redirect('admin_login')

@login_required
def admin_dashboard(request):
    # Check if user is admin
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    # Get statistics
    stats = {
        'total_prices': OnionPrice.objects.count(),
        'total_predictions': PricePrediction.objects.count(),
        'total_users': User.objects.count(),
        'avg_price': OnionPrice.objects.aggregate(Avg('modal_price'))['modal_price__avg'] or 0,
    }
    
    # Get recent data
    recent_prices = OnionPrice.objects.order_by('-date')[:10]
    recent_predictions = PricePrediction.objects.order_by('-forecast_date')[:10]
    
    context = {
        'stats': stats,
        'recent_prices': recent_prices,
        'recent_predictions': recent_predictions,
    }
    
    return render(request, 'custom_admin/dashboard.html', context)

@login_required
def manage_onion_prices(request):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    # Get filter parameters
    market = request.GET.get('market', '')
    state = request.GET.get('state', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Start with all prices
    prices = OnionPrice.objects.all().order_by('-date')
    
    # Apply filters
    if market:
        prices = prices.filter(market__icontains=market)
    if state:
        prices = prices.filter(state__icontains=state)
    if start_date:
        prices = prices.filter(date__gte=start_date)
    if end_date:
        prices = prices.filter(date__lte=end_date)
    
    # Pagination
    paginator = Paginator(prices, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'prices': page_obj,
    }
    return render(request, 'custom_admin/manage_prices.html', context)

# Add these functions to your custom_admin/views.py

@login_required
def export_predictions_csv(request):
    """Export predictions to CSV"""
    if not (request.user.is_superuser or request.user.is_staff):
        return HttpResponse('Access denied', status=403)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="price_predictions_{}.csv"'.format(
        datetime.now().strftime('%Y%m%d_%H%M%S')
    )
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'id', 'prediction_date', 'forecast_date', 'market', 
        'predicted_min_price', 'predicted_modal_price', 'predicted_max_price',
        'confidence_interval', 'actual_price', 'model_used', 'created_at'
    ])
    
    # Apply filters if any
    predictions = PricePrediction.objects.all().order_by('-forecast_date')
    
    market = request.GET.get('market', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    confidence = request.GET.get('confidence', '')
    
    if market:
        predictions = predictions.filter(market__icontains=market)
    if start_date:
        predictions = predictions.filter(forecast_date__gte=start_date)
    if end_date:
        predictions = predictions.filter(forecast_date__lte=end_date)
    if confidence:
        if confidence == 'high':
            predictions = predictions.filter(confidence_interval__gte=80)
        elif confidence == 'medium':
            predictions = predictions.filter(confidence_interval__gte=60, confidence_interval__lt=80)
        elif confidence == 'low':
            predictions = predictions.filter(confidence_interval__lt=60)
    
    # Write data rows
    for prediction in predictions:
        writer.writerow([
            prediction.id,
            prediction.prediction_date,
            prediction.forecast_date,
            prediction.market,
            prediction.predicted_min_price,
            prediction.predicted_modal_price,
            prediction.predicted_max_price,
            prediction.confidence_interval,
            prediction.actual_price or '',
            prediction.model_used.name if prediction.model_used else '',
            prediction.created_at
        ])
    
    return response


@login_required
def export_predictions_excel(request):
    """Export predictions to Excel"""
    if not (request.user.is_superuser or request.user.is_staff):
        return HttpResponse('Access denied', status=403)
    
    # Apply filters if any
    predictions = PricePrediction.objects.all().order_by('-forecast_date')
    
    market = request.GET.get('market', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    confidence = request.GET.get('confidence', '')
    
    if market:
        predictions = predictions.filter(market__icontains=market)
    if start_date:
        predictions = predictions.filter(forecast_date__gte=start_date)
    if end_date:
        predictions = predictions.filter(forecast_date__lte=end_date)
    if confidence:
        if confidence == 'high':
            predictions = predictions.filter(confidence_interval__gte=80)
        elif confidence == 'medium':
            predictions = predictions.filter(confidence_interval__gte=60, confidence_interval__lt=80)
        elif confidence == 'low':
            predictions = predictions.filter(confidence_interval__lt=60)
    
    # Create DataFrame
    data = []
    for prediction in predictions:
        data.append({
            'ID': prediction.id,
            'Prediction Date': prediction.prediction_date,
            'Forecast Date': prediction.forecast_date,
            'Market': prediction.market,
            'Min Price (₹)': prediction.predicted_min_price,
            'Modal Price (₹)': prediction.predicted_modal_price,
            'Max Price (₹)': prediction.predicted_max_price,
            'Confidence (%)': prediction.confidence_interval,
            'Actual Price (₹)': prediction.actual_price or '',
            'Model Used': prediction.model_used.name if prediction.model_used else '',
            'Created At': prediction.created_at,
            'Accuracy': calculate_accuracy_display(prediction)
        })
    
    df = pd.DataFrame(data)
    
    # Create response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="price_predictions_{}.xlsx"'.format(
        datetime.now().strftime('%Y%m%d_%H%M%S')
    )
    
    # Write to Excel
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Price Predictions', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Price Predictions']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 30)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    return response


def calculate_accuracy_display(prediction):
    """Helper function to calculate accuracy for display"""
    if prediction.actual_price and prediction.predicted_modal_price:
        try:
            # Use your existing calculate_accuracy filter if available
            # For now, calculate manually
            from django.db.models import F
            diff_percentage = abs(prediction.predicted_modal_price - prediction.actual_price) / prediction.actual_price * 100
            accuracy = 100 - diff_percentage
            return f"{accuracy:.1f}%"
        except:
            return ""
    return ""


@login_required
def bulk_delete_predictions(request):
    """Bulk delete predictions"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('manage_predictions')
    
    if request.method == 'POST':
        try:
            # Get filter parameters
            market = request.POST.get('market', '')
            start_date = request.POST.get('start_date', '')
            end_date = request.POST.get('end_date', '')
            confidence = request.POST.get('confidence', '')
            
            # Start with all predictions
            predictions = PricePrediction.objects.all()
            
            # Apply filters
            if market:
                predictions = predictions.filter(market__icontains=market)
            if start_date:
                predictions = predictions.filter(forecast_date__gte=start_date)
            if end_date:
                predictions = predictions.filter(forecast_date__lte=end_date)
            if confidence:
                if confidence == 'high':
                    predictions = predictions.filter(confidence_interval__gte=80)
                elif confidence == 'medium':
                    predictions = predictions.filter(confidence_interval__gte=60, confidence_interval__lt=80)
                elif confidence == 'low':
                    predictions = predictions.filter(confidence_interval__lt=60)
            
            # Count before deletion
            count_before = predictions.count()
            
            if count_before == 0:
                messages.warning(request, 'No predictions found matching the criteria')
                return redirect('manage_predictions')
            
            # Delete predictions
            predictions.delete()
            
            messages.success(request, f'Successfully deleted {count_before} predictions!')
            
        except Exception as e:
            messages.error(request, f'Error deleting predictions: {str(e)}')
    
    return redirect('manage_predictions')


# Also update the manage_predictions function to pass total_predictions and avg_accuracy
@login_required
def manage_predictions(request):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    # Get filter parameters
    market = request.GET.get('market', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Start with all predictions
    predictions = PricePrediction.objects.all().order_by('-forecast_date')
    
    # Apply filters
    if market:
        predictions = predictions.filter(market__icontains=market)
    if start_date:
        predictions = predictions.filter(forecast_date__gte=start_date)
    if end_date:
        predictions = predictions.filter(forecast_date__lte=end_date)
    
    # Calculate confidence stats
    high_confidence_count = predictions.filter(confidence_interval__gte=80).count()
    medium_confidence_count = predictions.filter(confidence_interval__gte=60, confidence_interval__lt=80).count()
    low_confidence_count = predictions.filter(confidence_interval__lt=60).count()
    
    # Calculate total predictions
    total_predictions = predictions.count()
    
    # Calculate average accuracy (simplified)
    predictions_with_accuracy = predictions.filter(actual_price__isnull=False)
    avg_accuracy = 0
    if predictions_with_accuracy.exists():
        accuracy_sum = 0
        count = 0
        for pred in predictions_with_accuracy:
            if pred.actual_price and pred.predicted_modal_price:
                try:
                    diff_percentage = abs(pred.predicted_modal_price - pred.actual_price) / pred.actual_price * 100
                    accuracy = 100 - diff_percentage
                    accuracy_sum += accuracy
                    count += 1
                except:
                    pass
        if count > 0:
            avg_accuracy = accuracy_sum / count
    
    # Get distinct markets for dropdown
    markets = OnionPrice.objects.values_list('market', flat=True).distinct()
    
    # Pagination
    paginator = Paginator(predictions, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'predictions': page_obj,
        'high_confidence_count': high_confidence_count,
        'medium_confidence_count': medium_confidence_count,
        'low_confidence_count': low_confidence_count,
        'total_predictions': total_predictions,
        'avg_accuracy': round(avg_accuracy, 1),
        'markets': markets,
    }
    return render(request, 'custom_admin/manage_predictions.html', context)

@login_required
def manage_users(request):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    # Get all users
    users = User.objects.all().order_by('-date_joined')
    
    # Apply filters
    search = request.GET.get('search', '')
    user_type = request.GET.get('user_type', '')
    status = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if user_type:
        users = users.filter(userprofile__user_type=user_type)
    
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    elif status == 'staff':
        users = users.filter(is_staff=True)
    elif status == 'superuser':
        users = users.filter(is_superuser=True)
    
    if start_date:
        users = users.filter(date_joined__gte=start_date)
    if end_date:
        users = users.filter(date_joined__lte=end_date)
    
    # Calculate stats
    today = datetime.now().date()
    total_users = users.count()
    active_users = users.filter(last_login__gte=today-timedelta(days=30)).count()
    new_users_today = users.filter(date_joined__date=today).count()
    new_users_week = users.filter(date_joined__gte=today-timedelta(days=7)).count()
    
    # Pagination with 5 users per page
    paginator = Paginator(users, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'total_users': total_users,
        'active_users': active_users,
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
    }
    return render(request, 'custom_admin/manage_users.html', context)

@login_required
def add_user(request):
    """View to add new user - Simplified version"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password1')
            user_type = request.POST.get('user_type', 'FARMER')
            
            # Check if user exists
            if User.objects.filter(username=username).exists():
                messages.error(request, f'Username "{username}" already exists')
                return redirect('manage_users')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, f'Email "{email}" already exists')
                return redirect('manage_users')
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=True  # Make them staff by default
            )
            
            # Create user profile
            UserProfile.objects.create(
                user=user,
                user_type=user_type,
                phone='',
                location=''
            )
            
            messages.success(request, f'User "{username}" created successfully!')
            return redirect('manage_users')
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('manage_users')
    
    # If GET request, redirect to manage users
    return redirect('manage_users')

@login_required
def generate_prediction(request):
    """View to generate new prediction"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            market = request.POST.get('market')
            days_ahead = int(request.POST.get('days_ahead', 7))
            model_type = request.POST.get('model_type', 'lstm')
            
            # DEBUG: Check how much data we have
            from forecast_app.models import OnionPrice
            total_records = OnionPrice.objects.count()
            market_records = OnionPrice.objects.filter(market__icontains=market).count() if market else 0
            
            print(f"DEBUG: Total records: {total_records}")
            print(f"DEBUG: Market '{market}' records: {market_records}")
            
            # Check if we have enough data
            if total_records < 30:  # Minimum 30 records
                messages.error(request, f'Not enough data. Need at least 30 price records. Currently have: {total_records}')
                return redirect('manage_predictions')
            
            if market and market_records < 15:  # Minimum 15 records for specific market
                messages.warning(request, f'Limited data for {market}. Only {market_records} records found.')
                # Continue anyway with all data
            
            # Initialize predictor
            predictor = RealTimePredictor()
            data_loaded = predictor.load_latest_data()
            
            if data_loaded is None or len(data_loaded) < 30:
                messages.error(request, f'Insufficient data for predictions. Loaded {len(data_loaded) if data_loaded else 0} records. Need at least 30.')
                return redirect('manage_predictions')
            
            # Generate prediction
            predictions = predictor.predict_next_7_days(market=market)
            
            if predictions is not None and not predictions.empty:
                # Save predictions to database
                for index, row in predictions.iterrows():
                    PricePrediction.objects.create(
                        prediction_date=datetime.now().date(),
                        forecast_date=datetime.now().date() + timedelta(days=index + 1),
                        market=market or 'All Markets',
                        predicted_modal_price=float(row.get('yhat', row.get('predicted_price', 1000))),
                        predicted_min_price=float(row.get('yhat_lower', row.get('predicted_price', 1000) * 0.95)),
                        predicted_max_price=float(row.get('yhat_upper', row.get('predicted_price', 1000) * 1.05)),
                        confidence_interval=85.0,
                    )
                
                messages.success(request, f'Successfully generated {len(predictions)} predictions for {market or "All Markets"}!')
            else:
                messages.warning(request, 'Could not generate predictions. Please check data availability.')
            
        except Exception as e:
            messages.error(request, f'Error generating predictions: {str(e)}')
            import traceback
            traceback.print_exc()  # Print full error for debugging
    
    return redirect('manage_predictions')
@login_required
def system_settings(request):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    # Get system settings or defaults
    context = {
        'settings': {
            'total_users': User.objects.count(),
            'total_prices': OnionPrice.objects.count(),
            'total_predictions': PricePrediction.objects.count(),
            'total_models': 4,  # LSTM, RF, XGB, Prophet
        }
    }
    return render(request, 'custom_admin/settings.html', context)

@login_required
def system_analytics(request):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    # Analytics data
    today = datetime.now().date()
    last_month = today - timedelta(days=30)
    
    # Price analytics
    price_stats = {
        'total_records': OnionPrice.objects.count(),
        'avg_price': OnionPrice.objects.aggregate(Avg('modal_price'))['modal_price__avg'] or 0,
        'highest_price': OnionPrice.objects.order_by('-modal_price').first(),
        'lowest_price': OnionPrice.objects.order_by('modal_price').first(),
        'price_change_30d': calculate_price_change(last_month, today),
    }
    
    # Prediction analytics
    prediction_stats = {
        'total_predictions': PricePrediction.objects.count(),
        'avg_confidence': PricePrediction.objects.aggregate(Avg('confidence_interval'))['confidence_interval__avg'] or 0,
        'high_confidence_predictions': PricePrediction.objects.filter(confidence_interval__gte=80).count(),
        'predictions_last_7_days': PricePrediction.objects.filter(forecast_date__gte=today-timedelta(days=7)).count(),
    }
    
    # User analytics
    user_stats = {
        'total_users': User.objects.count(),
        'new_users_today': User.objects.filter(date_joined__date=today).count(),
        'new_users_week': User.objects.filter(date_joined__gte=today-timedelta(days=7)).count(),
        'active_users': User.objects.filter(last_login__gte=today-timedelta(days=30)).count(),
    }
    
    context = {
        'price_stats': price_stats,
        'prediction_stats': prediction_stats,
        'user_stats': user_stats,
        'start_date': last_month,
        'end_date': today,
    }
    
    return render(request, 'custom_admin/analytics.html', context)

def calculate_price_change(start_date, end_date):
    """Calculate price change percentage between two dates"""
    try:
        start_avg = OnionPrice.objects.filter(date__gte=start_date, date__lte=start_date+timedelta(days=1)) \
            .aggregate(Avg('modal_price'))['modal_price__avg'] or 0
        
        end_avg = OnionPrice.objects.filter(date__gte=end_date-timedelta(days=1), date__lte=end_date) \
            .aggregate(Avg('modal_price'))['modal_price__avg'] or 0
        
        if start_avg > 0:
            return round(((end_avg - start_avg) / start_avg) * 100, 2)
        return 0
    except:
        return 0

# Add these new functions to your existing custom_admin/views.py
# DON'T replace your existing functions, just add these new ones:
@login_required
def manage_onion_prices(request):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    market = request.GET.get('market', '')
    state = request.GET.get('state', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    prices = OnionPrice.objects.all().order_by('-date')
    
    if market:
        prices = prices.filter(market__icontains=market)
    if state:
        prices = prices.filter(state__icontains=state)
    if start_date:
        prices = prices.filter(date__gte=start_date)
    if end_date:
        prices = prices.filter(date__lte=end_date)
    
    paginator = Paginator(prices, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    today = datetime.now().date()
    
    context = {
        'prices': page_obj,
        'today': today,
    }
    return render(request, 'custom_admin/manage_prices.html', context)

@login_required
def export_prices_csv(request):
    """Export prices to CSV"""
    if not (request.user.is_superuser or request.user.is_staff):
        return HttpResponse('Access denied', status=403)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="onion_prices_{}.csv"'.format(
        datetime.now().strftime('%Y%m%d_%H%M%S')
    )
    writer = csv.writer(response)
    # Write header
    writer.writerow([
        'date', 'market', 'state', 'district', 'variety',
        'min_price', 'max_price', 'modal_price', 'arrival_quantity'
    ])
    # Apply filters if any
    prices = OnionPrice.objects.all().order_by('-date')
    market = request.GET.get('market', '')
    state = request.GET.get('state', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    if market:
        prices = prices.filter(market__icontains=market)
    if state:
        prices = prices.filter(state__icontains=state)
    if start_date:
        prices = prices.filter(date__gte=start_date)
    if end_date:
        prices = prices.filter(date__lte=end_date)
    
    # Write data rows
    for price in prices:
        writer.writerow([
            price.date,
            price.market,
            price.state,
            price.district,
            price.variety,
            price.min_price,
            price.max_price,
            price.modal_price,
            price.arrival_quantity
        ])
    
    return response

@login_required
def export_prices_excel(request):
    """Export prices to Excel"""
    if not (request.user.is_superuser or request.user.is_staff):
        return HttpResponse('Access denied', status=403)
    
    # Apply filters if any
    prices = OnionPrice.objects.all().order_by('-date')
    
    market = request.GET.get('market', '')
    state = request.GET.get('state', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    if market:
        prices = prices.filter(market__icontains=market)
    if state:
        prices = prices.filter(state__icontains=state)
    if start_date:
        prices = prices.filter(date__gte=start_date)
    if end_date:
        prices = prices.filter(date__lte=end_date)
    
    # Create DataFrame
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
    
    # Create response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="onion_prices_{}.xlsx"'.format(
        datetime.now().strftime('%Y%m%d_%H%M%S')
    )
    
    # Write to Excel
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Onion Prices', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Onion Prices']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 30)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    return response

@login_required
def import_prices_csv(request):
    """Import prices from CSV/Excel"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('manage_onion_prices')
    
    if request.method == 'POST' and request.FILES.get('price_file'):
        try:
            file = request.FILES['price_file']
            
            # Check file extension
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file)
            else:
                messages.error(request, 'Please upload CSV or Excel file (.csv, .xls, .xlsx)')
                return redirect('manage_onion_prices')
            
            # Required columns
            required_columns = ['date', 'market', 'state', 'district', 'variety', 
                               'min_price', 'max_price', 'modal_price']
            
            # Check if required columns exist
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                messages.error(request, f'Missing columns: {", ".join(missing_columns)}')
                return redirect('manage_onion_prices')
            
            # Process each row
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Validate data
                    if pd.isna(row['date']) or pd.isna(row['market']) or pd.isna(row['state']) or pd.isna(row['district']) or pd.isna(row['variety']):
                        error_count += 1
                        errors.append(f"Row {index + 2}: Missing required fields")
                        continue
                    
                    min_price = float(row['min_price'])
                    max_price = float(row['max_price'])
                    modal_price = float(row['modal_price'])
                    
                    if min_price > max_price:
                        error_count += 1
                        errors.append(f"Row {index + 2}: Min price cannot be greater than max price")
                        continue
                    
                    if modal_price < min_price or modal_price > max_price:
                        error_count += 1
                        errors.append(f"Row {index + 2}: Modal price must be between min and max price")
                        continue
                    
                    if min_price <= 0 or max_price <= 0 or modal_price <= 0:
                        error_count += 1
                        errors.append(f"Row {index + 2}: All prices must be greater than 0")
                        continue
                    
                    # Check for duplicate (same market and date)
                    existing_price = OnionPrice.objects.filter(
                        market=row['market'],
                        date=row['date']
                    ).first()
                    
                    if existing_price:
                        # Update existing record
                        existing_price.state = row['state']
                        existing_price.district = row['district']
                        existing_price.variety = row['variety']
                        existing_price.min_price = min_price
                        existing_price.max_price = max_price
                        existing_price.modal_price = modal_price
                        existing_price.arrival_quantity = float(row.get('arrival_quantity', 0))
                        existing_price.save()
                        success_count += 1
                    else:
                        # Create new record
                        OnionPrice.objects.create(
                            date=row['date'],
                            market=row['market'],
                            state=row['state'],
                            district=row['district'],
                            variety=row['variety'],
                            min_price=min_price,
                            max_price=max_price,
                            modal_price=modal_price,
                            arrival_quantity=float(row.get('arrival_quantity', 0))
                        )
                        success_count += 1
                        
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            # Show results
            if success_count > 0:
                messages.success(request, f'Successfully imported/updated {success_count} price records!')
            
            if error_count > 0:
                messages.warning(request, f'{error_count} records had errors')
                # Show first 5 errors
                if errors:
                    error_msg = "<br>".join(errors[:5])
                    if len(errors) > 5:
                        error_msg += f"<br>... and {len(errors) - 5} more errors"
                    messages.error(request, error_msg)
            
        except Exception as e:
            messages.error(request, f'Error importing file: {str(e)}')
    
    return redirect('manage_onion_prices')

@login_required
def download_sample_csv(request):
    """Download sample CSV template"""
    if not (request.user.is_superuser or request.user.is_staff):
        return HttpResponse('Access denied', status=403)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_onion_prices_template.csv"'
    
    writer = csv.writer(response)
    
    # Write header with sample data
    writer.writerow([
        'date', 'market', 'state', 'district', 'variety',
        'min_price', 'max_price', 'modal_price', 'arrival_quantity'
    ])
    
    # Write sample rows
    sample_data = [
        ['2024-01-15', 'Lasalgaon', 'Maharashtra', 'Nashik', 'NASHIK_RED', '1800', '2200', '2000', '1500'],
        ['2024-01-15', 'Pimpalgaon', 'Maharashtra', 'Nashik', 'PUNE_WHITE', '1700', '2100', '1900', '1200'],
        ['2024-01-16', 'Kotputli', 'Rajasthan', 'Jaipur', 'MAHARASHTRA', '1600', '2000', '1800', '800'],
        ['2024-01-16', 'Chittoor', 'Andhra Pradesh', 'Chittoor', 'OTHER', '1400', '1800', '1600', '600']
    ]
    
    for row in sample_data:
        writer.writerow(row)
    
    return response

@login_required
def bulk_delete_prices(request):
    """Bulk delete prices"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        try:
            # Get selected IDs from request
            price_ids = request.POST.getlist('price_ids[]')
            
            if not price_ids:
                return JsonResponse({'error': 'No prices selected'}, status=400)
            
            # Delete prices
            deleted_count = OnionPrice.objects.filter(id__in=price_ids).delete()[0]
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully deleted {deleted_count} price records'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)
@login_required
def add_onion_price(request):
    """Add new onion price record"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            # Get form data
            date = request.POST.get('date')
            market = request.POST.get('market')
            state = request.POST.get('state')
            district = request.POST.get('district')
            variety = request.POST.get('variety')
            min_price = float(request.POST.get('min_price', 0))
            max_price = float(request.POST.get('max_price', 0))
            modal_price = float(request.POST.get('modal_price', 0))
            arrival_quantity = float(request.POST.get('arrival_quantity', 0))
            
            # Validate data
            if not all([date, market, state, district, variety]):
                messages.error(request, 'Please fill in all required fields')
                return redirect('manage_onion_prices')
            
            if min_price > max_price:
                messages.error(request, 'Min price cannot be greater than max price')
                return redirect('manage_onion_prices')
            
            if modal_price < min_price or modal_price > max_price:
                messages.error(request, 'Modal price must be between min and max price')
                return redirect('manage_onion_prices')
            
            if min_price <= 0 or max_price <= 0 or modal_price <= 0:
                messages.error(request, 'All prices must be greater than 0')
                return redirect('manage_onion_prices')
            
            # Create price record
            price = OnionPrice.objects.create(
                date=date,
                market=market,
                state=state,
                district=district,
                variety=variety,
                min_price=min_price,
                max_price=max_price,
                modal_price=modal_price,
                arrival_quantity=arrival_quantity
            )
            
            messages.success(request, f'Price record for {market} on {date} added successfully!')
            return redirect('manage_onion_prices')
            
        except Exception as e:
            messages.error(request, f'Error adding price record: {str(e)}')
            return redirect('manage_onion_prices')
    
    # If GET request, redirect to manage prices
    return redirect('manage_onion_prices')

@login_required
def delete_onion_price(request, price_id):
    """Delete onion price record"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    try:
        price = OnionPrice.objects.get(id=price_id)
        market = price.market
        date = price.date
        price.delete()
        messages.success(request, f'Price record for {market} on {date} deleted successfully!')
    except OnionPrice.DoesNotExist:
        messages.error(request, 'Price record not found')
    except Exception as e:
        messages.error(request, f'Error deleting price record: {str(e)}')
    
    return redirect('manage_onion_prices')

@login_required
def edit_onion_price(request, price_id):
    """Edit existing onion price record"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            # Get the price record
            price = get_object_or_404(OnionPrice, id=price_id)
            
            # Get form data
            date = request.POST.get('date')
            market = request.POST.get('market')
            state = request.POST.get('state')
            district = request.POST.get('district')
            variety = request.POST.get('variety')
            min_price = float(request.POST.get('min_price', 0))
            max_price = float(request.POST.get('max_price', 0))
            modal_price = float(request.POST.get('modal_price', 0))
            arrival_quantity = float(request.POST.get('arrival_quantity', 0))
            
            # Validate data
            if not all([date, market, state, district, variety]):
                messages.error(request, 'Please fill in all required fields')
                return redirect('manage_onion_prices')
            
            if min_price > max_price:
                messages.error(request, 'Min price cannot be greater than max price')
                return redirect('manage_onion_prices')
            
            if modal_price < min_price or modal_price > max_price:
                messages.error(request, 'Modal price must be between min and max price')
                return redirect('manage_onion_prices')
            
            if min_price <= 0 or max_price <= 0 or modal_price <= 0:
                messages.error(request, 'All prices must be greater than 0')
                return redirect('manage_onion_prices')
            
            # Update price record
            price.date = date
            price.market = market
            price.state = state
            price.district = district
            price.variety = variety
            price.min_price = min_price
            price.max_price = max_price
            price.modal_price = modal_price
            price.arrival_quantity = arrival_quantity
            price.save()
            
            messages.success(request, f'Price record for {market} on {date} updated successfully!')
            return redirect('manage_onion_prices')
            
        except OnionPrice.DoesNotExist:
            messages.error(request, 'Price record not found')
        except Exception as e:
            messages.error(request, f'Error updating price record: {str(e)}')
    
    return redirect('manage_onion_prices')


@login_required
def bulk_import_prices(request):
    """Bulk import prices from CSV/Excel - NEW FUNCTION"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    if request.method == 'POST' and request.FILES.get('price_file'):
        try:
            import pandas as pd
            import io
            
            file = request.FILES['price_file']
            
            # Check file extension
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file)
            else:
                messages.error(request, 'Please upload CSV or Excel file')
                return redirect('manage_onion_prices')
            
            # Required columns
            required_columns = ['date', 'market', 'state', 'district', 'variety', 
                               'min_price', 'max_price', 'modal_price']
            
            # Check if required columns exist
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                messages.error(request, f'Missing columns: {", ".join(missing_columns)}')
                return redirect('manage_onion_prices')
            
            # Process each row
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Convert date if needed
                    date_str = str(row['date'])
                    
                    OnionPrice.objects.create(
                        date=date_str,
                        market=row['market'],
                        state=row['state'],
                        district=row['district'],
                        variety=row['variety'],
                        min_price=float(row['min_price']),
                        max_price=float(row['max_price']),
                        modal_price=float(row['modal_price']),
                        arrival_quantity=float(row.get('arrival_quantity', 0))
                    )
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            if success_count > 0:
                messages.success(request, f'Successfully imported {success_count} records')
            if error_count > 0:
                messages.warning(request, f'{error_count} records failed to import')
                if errors:
                    error_msg = "<br>".join(errors[:5])  # Show first 5 errors
                    if len(errors) > 5:
                        error_msg += f"<br>... and {len(errors) - 5} more errors"
                    messages.error(request, error_msg)
            
        except Exception as e:
            messages.error(request, f'Error importing file: {str(e)}')
    
    return redirect('manage_onion_prices')


@login_required
def edit_onion_price(request, price_id):
    """Edit existing onion price record - NEW FUNCTION"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            # Get the price record
            price = OnionPrice.objects.get(id=price_id)
            
            # Get form data
            date = request.POST.get('date')
            market = request.POST.get('market')
            state = request.POST.get('state')
            district = request.POST.get('district')
            variety = request.POST.get('variety')
            min_price = float(request.POST.get('min_price', 0))
            max_price = float(request.POST.get('max_price', 0))
            modal_price = float(request.POST.get('modal_price', 0))
            arrival_quantity = float(request.POST.get('arrival_quantity', 0))
            
            # Validate data
            if not all([date, market, state, district, variety]):
                messages.error(request, 'Please fill in all required fields')
                return redirect('manage_onion_prices')
            
            if min_price > max_price:
                messages.error(request, 'Min price cannot be greater than max price')
                return redirect('manage_onion_prices')
            
            if modal_price < min_price or modal_price > max_price:
                messages.error(request, 'Modal price must be between min and max price')
                return redirect('manage_onion_prices')
            
            # Update price record
            price.date = date
            price.market = market
            price.state = state
            price.district = district
            price.variety = variety
            price.min_price = min_price
            price.max_price = max_price
            price.modal_price = modal_price
            price.arrival_quantity = arrival_quantity
            price.save()
            
            messages.success(request, f'Price record for {market} on {date} updated successfully!')
            return redirect('manage_onion_prices')
            
        except OnionPrice.DoesNotExist:
            messages.error(request, 'Price record not found')
        except Exception as e:
            messages.error(request, f'Error updating price record: {str(e)}')
    
    return redirect('manage_onion_prices')

@login_required
def deactivate_user(request, user_id):
    """Deactivate a user"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('manage_users')
    
    try:
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            messages.error(request, 'You cannot deactivate yourself')
        else:
            user.is_active = False
            user.save()
            messages.success(request, f'User "{user.username}" has been deactivated')
    except Exception as e:
        messages.error(request, f'Error deactivating user: {str(e)}')
    
    return redirect('manage_users')

@login_required
def activate_user(request, user_id):
    """Activate a user"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('manage_users')
    
    try:
        user = get_object_or_404(User, id=user_id)
        user.is_active = True
        user.save()
        messages.success(request, f'User "{user.username}" has been activated')
    except Exception as e:
        messages.error(request, f'Error activating user: {str(e)}')
    
    return redirect('manage_users')

@login_required
def toggle_user_status(request, user_id):
    """Toggle user active/inactive status"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            return JsonResponse({'error': 'You cannot change your own status'}, status=400)
        
        user.is_active = not user.is_active
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
            'is_active': user.is_active
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@login_required
def prediction_details(request, prediction_id):
    """Get prediction details for AJAX request"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        prediction = get_object_or_404(PricePrediction, id=prediction_id)
        
        # Calculate accuracy
        accuracy = 0
        difference = 0
        if prediction.actual_price and prediction.predicted_modal_price:
            try:
                diff_percentage = abs(prediction.predicted_modal_price - prediction.actual_price) / prediction.actual_price * 100
                accuracy = 100 - diff_percentage
                difference = abs(prediction.predicted_modal_price - prediction.actual_price)
            except:
                pass
        
        data = {
            'success': True,
            'prediction': {
                'id': prediction.id,
                'market': prediction.market or '-',
                'forecast_date': prediction.forecast_date.isoformat() if prediction.forecast_date else None,
                'predicted_min_price': float(prediction.predicted_min_price or 0),
                'predicted_modal_price': float(prediction.predicted_modal_price or 0),
                'predicted_max_price': float(prediction.predicted_max_price or 0),
                'confidence_interval': float(prediction.confidence_interval or 0),
                'actual_price': float(prediction.actual_price) if prediction.actual_price else None,
                'model_used': {
                    'name': prediction.model_used.name if prediction.model_used else 'N/A'
                },
                'created_at': prediction.created_at.isoformat() if prediction.created_at else None,
                'accuracy': accuracy,
                'difference': difference
            }
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
@login_required
def manage_factors(request):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    # Get all market factors
    factors = MarketFactor.objects.all().order_by('-impact_score')
    
    # Apply filters
    search = request.GET.get('search', '')
    factor_type = request.GET.get('factor_type', '')
    status = request.GET.get('status', '')
    
    if search:
        factors = factors.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    if factor_type:
        factors = factors.filter(factor_type=factor_type)
    
    if status == 'active':
        factors = factors.filter(is_active=True)
    elif status == 'inactive':
        factors = factors.filter(is_active=False)
    
    # Calculate statistics
    total_factors = factors.count()
    active_count = factors.filter(is_active=True).count()
    active_percentage = round((active_count / total_factors * 100) if total_factors > 0 else 0, 1)
    avg_impact_score = factors.aggregate(avg=Avg('impact_score'))['avg'] or 0
    high_impact_count = factors.filter(impact_score__gte=70).count()
    
    # Get unique factor types
    factor_types = MarketFactor.objects.values_list('factor_type', flat=True).distinct()
    factor_types = [ft for ft in factor_types if ft]  # Remove empty values
    
    # Pagination
    paginator = Paginator(factors, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'factors': page_obj,
        'active_count': active_count,
        'active_percentage': active_percentage,
        'avg_impact_score': round(avg_impact_score, 1),
        'high_impact_count': high_impact_count,
        'factor_types': factor_types,
    }
    return render(request, 'custom_admin/manage_factors.html', context)

@login_required
def add_factor(request):
    """Add new market factor"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            factor_type = request.POST.get('factor_type', '')
            impact_score = float(request.POST.get('impact_score', 50))
            is_active = request.POST.get('is_active') == 'on'
            
            # Validate
            if not name:
                messages.error(request, 'Factor name is required')
                return redirect('manage_factors')
            
            if impact_score < 0 or impact_score > 100:
                messages.error(request, 'Impact score must be between 0 and 100')
                return redirect('manage_factors')
            
            # Create factor
            factor = MarketFactor.objects.create(
                name=name,
                description=description,
                factor_type=factor_type if factor_type else None,
                impact_score=impact_score,
                is_active=is_active,
                created_by=request.user
            )
            
            messages.success(request, f'Market factor "{name}" added successfully!')
            return redirect('manage_factors')
            
        except Exception as e:
            messages.error(request, f'Error adding market factor: {str(e)}')
            return redirect('manage_factors')
    
    return redirect('manage_factors')

@login_required
def edit_factor(request, factor_id):
    """Edit existing market factor"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            factor = get_object_or_404(MarketFactor, id=factor_id)
            
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            factor_type = request.POST.get('factor_type', '')
            impact_score = float(request.POST.get('impact_score', 50))
            is_active = request.POST.get('is_active') == 'on'
            
            # Validate
            if not name:
                messages.error(request, 'Factor name is required')
                return redirect('manage_factors')
            
            if impact_score < 0 or impact_score > 100:
                messages.error(request, 'Impact score must be between 0 and 100')
                return redirect('manage_factors')
            
            # Update factor
            factor.name = name
            factor.description = description
            factor.factor_type = factor_type if factor_type else None
            factor.impact_score = impact_score
            factor.is_active = is_active
            factor.updated_at = now()
            factor.save()
            
            messages.success(request, f'Market factor "{name}" updated successfully!')
            return redirect('manage_factors')
            
        except Exception as e:
            messages.error(request, f'Error updating market factor: {str(e)}')
    
    return redirect('manage_factors')

@login_required
def delete_factor(request, factor_id):
    """Delete market factor"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    try:
        factor = get_object_or_404(MarketFactor, id=factor_id)
        name = factor.name
        factor.delete()
        messages.success(request, f'Market factor "{name}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting market factor: {str(e)}')
    
    return redirect('manage_factors')