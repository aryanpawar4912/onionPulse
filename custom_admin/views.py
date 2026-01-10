# custom_admin/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg, Sum, Q
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from forecast_app.models import OnionPrice, PricePrediction, MarketFactor, UserProfile
from forecast_app.ml_model.price_predictor import RealTimePredictor
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
    paginator = Paginator(prices, 50)  # 50 per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'prices': page_obj,
    }
    return render(request, 'custom_admin/manage_prices.html', context)

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
    
    # Get distinct markets for dropdown
    markets = OnionPrice.objects.values_list('market', flat=True).distinct()
    
    # Pagination
    paginator = Paginator(predictions, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'predictions': page_obj,
        'high_confidence_count': high_confidence_count,
        'medium_confidence_count': medium_confidence_count,
        'low_confidence_count': low_confidence_count,
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
    
    # Calculate stats
    today = datetime.now().date()
    total_users = users.count()
    active_users = users.filter(last_login__gte=today-timedelta(days=30)).count()
    new_users_today = users.filter(date_joined__date=today).count()
    new_users_week = users.filter(date_joined__gte=today-timedelta(days=7)).count()
    
    # Pagination
    paginator = Paginator(users, 50)
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
            
            # Initialize predictor
            predictor = RealTimePredictor()
            predictor.load_latest_data()
            
            # Generate prediction
            predictions = predictor.predict_next_7_days(market=market)
            
            if predictions is not None:
                # Save predictions to database
                for index, row in predictions.iterrows():
                    PricePrediction.objects.create(
                        prediction_date=datetime.now().date(),
                        forecast_date=datetime.now().date() + timedelta(days=index + 1),
                        market=market or 'All Markets',
                        predicted_modal_price=float(row.get('yhat', 1000)),
                        predicted_min_price=float(row.get('yhat_lower', 950)),
                        predicted_max_price=float(row.get('yhat_upper', 1050)),
                        confidence_interval=85.0,
                    )
                
                messages.success(request, f'Predictions generated successfully for {market}!')
            else:
                messages.warning(request, 'Could not generate predictions. Please check data availability.')
            
        except Exception as e:
            messages.error(request, f'Error generating predictions: {str(e)}')
    
    return redirect('manage_predictions')

@login_required
def manage_factors(request):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'Access denied')
        return redirect('admin_login')
    
    # Get all market factors
    factors = MarketFactor.objects.all().order_by('-impact_score')
    
    context = {
        'factors': factors,
    }
    return render(request, 'custom_admin/manage_factors.html', context)

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
def add_onion_price(request):
    """Add new onion price record - NEW FUNCTION"""
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
    """Delete onion price record - NEW FUNCTION"""
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