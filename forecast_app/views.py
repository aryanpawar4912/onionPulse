# forecast_app/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import OnionPrice, PricePrediction, MarketFactor, UserProfile

from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .forms import UserRegisterForm


def login_view(request):
    next_url = request.GET.get('next', 'dashboard')  # Default redirect to dashboard
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                # Redirect to 'next' hidden input value if it exists
                redirect_to = request.POST.get('next', 'dashboard')
                return redirect(redirect_to)
        else:
            # The form.errors will be passed to the template automatically
            return render(request, 'forecast_app/login.html',{'form': form})

    # GET request
    form = AuthenticationForm()
    return render(request, 'forecast_app/login.html', {
        'form': form, 
        'next': next_url
    })


def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            # 1. Save the main User object
            user = form.save()
            
            # 2. Create the linked UserProfile
            UserProfile.objects.create(
                user=user,
                user_type=form.cleaned_data.get('user_type'),
                phone=form.cleaned_data.get('phone'),
                location=form.cleaned_data.get('location')
            )
            
            messages.success(request, f'Account created for {user.username}! You can now login.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'forecast_app/register.html', {'form': form})

def home(request):
    # Pass recent prices, predictions, and market factors to the home page
    recent_prices  = OnionPrice.objects.order_by('-date')[:10]
    market_factors = MarketFactor.objects.filter(is_active=True)[:5]
    predictions    = PricePrediction.objects.order_by('-forecast_date')[:7]

    total_prices      = OnionPrice.objects.count()
    total_factors     = MarketFactor.objects.filter(is_active=True).count()
    total_predictions = PricePrediction.objects.count()

    context = {
        'recent_prices':      recent_prices,
        'market_factors':     market_factors,
        'predictions':        predictions,
        'total_prices':       total_prices,
        'total_factors':      total_factors,
        'total_predictions':  total_predictions,
        'accuracy':           85,
    }
    return render(request, 'forecast_app/home.html', context)


def dashboard(request):
    try:
        from .ml_model.price_predictor import RealTimePredictor
        predictor        = RealTimePredictor()
        trend_data       = predictor.get_price_trend()
        predictions_df   = predictor.predict_next_7_days()
        predictions_list = predictions_df.to_dict('records') if predictions_df is not None else []
    except Exception:
        trend_data       = None
        predictions_list = []

    factors = MarketFactor.objects.filter(is_active=True)[:5]
    context = {
        'trend_data':  trend_data,
        'predictions': predictions_list,
        'factors':     factors,
        'user_type':   request.user.userprofile.user_type if hasattr(request.user, 'userprofile') else None,
    }
    return render(request, 'forecast_app/dashboard.html', context)

@login_required
def historical_data(request):
    market     = request.GET.get('market', '')
    start_date = request.GET.get('start_date', '')
    end_date   = request.GET.get('end_date', '')

    qs = OnionPrice.objects.all().order_by('-date')
    if market:
        qs = qs.filter(market__iexact=market)
    if start_date:
        try:
            qs = qs.filter(date__gte=datetime.strptime(start_date, '%Y-%m-%d').date())
        except ValueError:
            pass
    if end_date:
        try:
            qs = qs.filter(date__lte=datetime.strptime(end_date, '%Y-%m-%d').date())
        except ValueError:
            pass

    markets = list(OnionPrice.objects.values_list('market', flat=True).distinct().order_by('market'))
    context = {
        'data':            list(qs.values()),
        'markets':         markets,
        'selected_market': market,
        'start_date':      start_date,
        'end_date':        end_date,
    }
    return render(request, 'forecast_app/historical.html', context)


@login_required
def predict_price(request):
    """Price prediction page."""
    if request.method == 'POST':
        market     = request.POST.get('market', 'All Markets')
        days_ahead = int(request.POST.get('days_ahead', 7))
        model_type = request.POST.get('model_type', 'lstm')
        saved      = 0
        error_msg  = None

        try:
            from .ml_model.price_predictor import RealTimePredictor
            predictor = RealTimePredictor()
            predictor.load_latest_data()

            predictions_df = None

            if hasattr(predictor, 'predict_future'):
                predictions_df = predictor.predict_future(
                    model_name=model_type, future_days=days_ahead
                )
            elif hasattr(predictor, 'predictor') and hasattr(predictor.predictor, 'predict_future'):
                predictions_df = predictor.predictor.predict_future(
                    model_name=model_type, future_days=days_ahead
                )
            elif hasattr(predictor, 'predict_next_7_days'):
                predictions_df = predictor.predict_next_7_days(market=market)

            if predictions_df is not None and not predictions_df.empty:
                for _, row in predictions_df.iterrows():
                    if 'ds' in row:
                        raw_date      = row['ds']
                        forecast_date = raw_date.date() if hasattr(raw_date, 'date') else datetime.strptime(str(raw_date)[:10], '%Y-%m-%d').date()
                        modal = float(row.get('yhat', 0))
                        lo    = float(row.get('yhat_lower', modal * 0.95))
                        hi    = float(row.get('yhat_upper', modal * 1.05))
                    else:
                        forecast_date = timezone.now().date() + timedelta(days=saved + 1)
                        modal = float(row.get('predicted_price', 0))
                        lo    = modal * 0.95
                        hi    = modal * 1.05

                    PricePrediction.objects.create(
                        prediction_date       = timezone.now().date(),
                        forecast_date         = forecast_date,
                        market                = market,
                        predicted_modal_price = modal,
                        predicted_min_price   = lo,
                        predicted_max_price   = hi,
                        confidence_interval   = 85.0,
                    )
                    saved += 1

                messages.success(request, f'✅ {saved} prediction{"s" if saved != 1 else ""} generated for {market}!')
                return redirect('prediction_results')
            else:
                error_msg = 'The ML model returned no predictions. Make sure enough historical data exists for this market.'

        except Exception as e:
            error_msg = f'Prediction engine error: {e}'

        messages.error(request, error_msg)

    markets            = list(OnionPrice.objects.values_list('market', flat=True).distinct().order_by('market'))
    recent_predictions = PricePrediction.objects.order_by('-prediction_date')[:5]

    context = {
        'markets':            markets,
        'recent_predictions': recent_predictions,
        'model_types': [
            ('lstm',    'LSTM Neural Network'),
            ('rf',      'Random Forest'),
            ('xgb',     'XGBoost'),
            ('prophet', 'Facebook Prophet'),
        ],
    }
    return render(request, 'forecast_app/predict.html', context)


def prediction_results(request):
    """Prediction results page with filtering support."""
    # --- filter params ---
    market_filter = request.GET.get('market', '')
    date_filter   = request.GET.get('date_range', 'all')
    status_filter = request.GET.get('status', 'all')

    qs = PricePrediction.objects.all().order_by('-forecast_date')

    if market_filter:
        qs = qs.filter(market__iexact=market_filter)

    if date_filter == 'week':
        qs = qs.filter(prediction_date__gte=timezone.now().date() - timedelta(days=7))
    elif date_filter == 'month':
        qs = qs.filter(prediction_date__gte=timezone.now().date() - timedelta(days=30))
    elif date_filter == 'quarter':
        qs = qs.filter(prediction_date__gte=timezone.now().date() - timedelta(days=90))

    if status_filter == 'verified':
        qs = qs.filter(actual_price__isnull=False)
    elif status_filter == 'pending':
        qs = qs.filter(actual_price__isnull=True)

    predictions = qs[:100]

    # --- stats ---
    all_predictions       = PricePrediction.objects.all()
    avg_confidence        = all_predictions.aggregate(Avg('confidence_interval'))['confidence_interval__avg'] or 0
    accurate_predictions  = all_predictions.filter(actual_price__isnull=False).count()
    pending_predictions   = all_predictions.filter(actual_price__isnull=True).count()
    total_count           = all_predictions.count()

    # --- distinct markets for filter dropdown ---
    markets = list(
        PricePrediction.objects.values_list('market', flat=True)
        .distinct()
        .order_by('market')
    )

    context = {
        'predictions':           predictions,
        'markets':               markets,
        'avg_confidence':        round(avg_confidence, 1),
        'accurate_predictions':  accurate_predictions,
        'pending_predictions':   pending_predictions,
        'total_count':           total_count,
        # preserve filter state
        'selected_market':       market_filter,
        'selected_date':         date_filter,
        'selected_status':       status_filter,
    }
    return render(request, 'forecast_app/prediction_results.html', context)


def api_get_prices(request):
    """JSON endpoint — historical prices for preview chart."""
    market = request.GET.get('market', '')
    days   = int(request.GET.get('days', 60))

    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=days)

    qs = OnionPrice.objects.filter(
        date__gte=start_dt.date(), date__lte=end_dt.date()
    ).order_by('date')
    if market:
        qs = qs.filter(market__iexact=market)

    data = [
        {
            'date':        obj.date.strftime('%Y-%m-%d'),
            'market':      obj.market,
            'modal_price': float(obj.modal_price or 0),
            'min_price':   float(obj.min_price   or 0),
            'max_price':   float(obj.max_price   or 0),
        }
        for obj in qs
    ]
    return JsonResponse({'data': data})


def api_get_prediction(request):
    market = request.GET.get('market', '')
    try:
        from .ml_model.price_predictor import RealTimePredictor
        predictor   = RealTimePredictor()
        predictions = predictor.predict_next_7_days(market=market)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    if predictions is None:
        return JsonResponse({'error': 'Prediction failed'}, status=500)

    data = []
    if 'ds' in predictions.columns:
        for _, row in predictions.iterrows():
            data.append({
                'date':            row['ds'].strftime('%Y-%m-%d'),
                'predicted_price': float(row['yhat']),
                'lower_bound':     float(row.get('yhat_lower', row['yhat'] * 0.95)),
                'upper_bound':     float(row.get('yhat_upper', row['yhat'] * 1.05)),
            })
    else:
        for _, row in predictions.iterrows():
            data.append({
                'date':            row['date'].strftime('%Y-%m-%d'),
                'predicted_price': float(row['predicted_price']),
            })
    return JsonResponse({'predictions': data})


@login_required
def user_recommendations(request):
    user_type = 'GENERAL'
    if hasattr(request.user, 'userprofile'):
        user_type = request.user.userprofile.user_type
    else:
        messages.info(request, 'Complete your profile for personalised recommendations.')

    try:
        from .ml_model.price_predictor import RealTimePredictor
        predictor       = RealTimePredictor()
        recommendations = predictor.get_recommendation(user_type)
        trend           = predictor.get_price_trend()
    except Exception:
        recommendations = []
        trend           = None

    context = {'user_type': user_type, 'recommendations': recommendations, 'trend': trend}
    return render(request, 'forecast_app/recommendations.html', context)


def about(request):
    return render(request, 'forecast_app/about.html')


def contact(request):
    return render(request, 'forecast_app/contact.html')