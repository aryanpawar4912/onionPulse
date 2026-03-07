# 🧅 Onion Price Forecasting System

A Django-based web application for predicting onion prices using machine learning models. The system includes a custom admin panel for managing price data, predictions, users, and market analytics.

##  Features

### **Admin Panel**
- **Dashboard**: Overview with statistics and recent data
- **Price Management**: CRUD operations for onion price records
- **Prediction Management**: Generate and view price predictions
- **User Management**: Manage system users and profiles
- **Market Factors**: Configure market influencing factors
- **System Analytics**: View comprehensive analytics and trends
- **System Settings**: Configure application settings

### **Prediction Models**
- LSTM Neural Networks
- Random Forest
- XGBoost
- Facebook Prophet

### **User Roles**
- Admin/Superuser
- Staff Members
- Farmers
- Traders
- Consumers
- Government Officials
- Researchers

##  Quick Start

### **Prerequisites**
- Python 3.8+
- Django 3.2+
- SQLite3 (default database)
- Required Python packages (see requirements.txt)

### **Installation**

1. **Clone the repository**
```bash
git clone <your-repository-url>
cd onion-price-forecast
```

2. **Create virtual environment**
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Mac/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Apply migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Create superuser**
```bash
python manage.py createsuperuser
```

6. **Run the development server**
```bash
python manage.py runserver
```

7. **Access the application**
- Main application: http://127.0.0.1:8000/
- Admin panel: http://127.0.0.1:8000/admin-panel/
- Django admin: http://127.0.0.1:8000/admin/

##  Project Structure

```
onion-price-forecast/
├── custom_admin/              # Custom admin panel
│   ├── templates/
│   │   └── custom_admin/     # Admin templates
│   ├── templatetags/         # Custom template filters
│   ├── views.py             # Admin views
│   └── urls.py              # Admin URLs
├── forecast_app/             # Main application
│   ├── models.py            # Database models
│   ├── views.py             # Main views
│   ├── ml_model/            # ML models
│   │   ├── model_training.py
│   │   └── price_predictor.py
│   └── templates/           # User-facing templates
├── static/                  # Static files
├── media/                   # Uploaded files
├── manage.py               # Django management
└── requirements.txt        # Python dependencies
```

##  Configuration

### **Settings**
The main configuration is in `settings.py`:

```python
# Database (SQLite by default)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Authentication
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'
```

### **URL Configuration**
```python
# onion_forecast/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),           # Django admin
    path('admin-panel/', include('custom_admin.urls')),  # Custom admin
    path('', include('forecast_app.urls')),    # Main app
]
```

##  Data Models

### **OnionPrice**
- Stores historical onion price data
- Fields: date, market, state, district, variety, min/max/modal prices, arrival quantity

### **PricePrediction**
- Stores price predictions
- Fields: forecast date, market, predicted prices, confidence interval

### **MarketFactor**
- Market influencing factors
- Fields: name, factor type, impact score, description

### **UserProfile**
- Extended user information
- Fields: user type, phone, location, preferences

##  Admin Panel Features

### **Price Management**
- Add/Edit/Delete price records
- Bulk import from CSV/Excel
- Filter and search functionality
- Export data to CSV

### **Prediction Management**
- Generate predictions using different models
- View prediction history
- Filter predictions by market and date
- View confidence scores and accuracy

### **User Management**
- Add new users with profiles
- View user statistics
- Filter and search users
- Set user roles and permissions

### **Analytics Dashboard**
- Price trends visualization
- Prediction statistics
- User activity metrics
- System performance monitoring

##  Machine Learning Models

### **Model Training**
The system supports multiple ML models:
1. **LSTM Neural Networks**: For time series forecasting
2. **Random Forest**: Ensemble learning method
3. **XGBoost**: Gradient boosting framework
4. **Facebook Prophet**: Additive regression model

### **Features Used**
- Historical price data
- Seasonal patterns
- Market factors
- Date features (month, day, season)
- Lag features and rolling statistics

##  Security Features

- Admin authentication required for sensitive operations
- CSRF protection
- SQL injection prevention
- Input validation and sanitization
- Session-based authentication
- Permission-based access control

##  Responsive Design

- Bootstrap 5 for responsive layout
- Mobile-friendly interface
- Dark/light mode compatible
- Interactive charts and tables
- Intuitive navigation

##  Testing

Run tests with:
```bash
python manage.py test
```

Test coverage includes:
- Model creation and validation
- View responses
- URL routing
- Form submissions
- Authentication

##  Deployment

### **Production Deployment Steps**

1. **Update settings for production**
```python
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']

# Use PostgreSQL for production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'onion_forecast',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Static files configuration
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

2. **Collect static files**
```bash
python manage.py collectstatic
```

3. **Configure Gunicorn/WSGI**
```bash
pip install gunicorn
```

4. **Set up Nginx/Apache**
- Configure web server as reverse proxy
- Set up SSL certificates
- Configure static/media file serving

##  Data Import/Export

### **Supported Formats**
- CSV files
- Excel files (.xlsx, .xls)

### **Import Template**
Create CSV files with these columns:
```
date,market,state,district,variety,min_price,max_price,modal_price,arrival_quantity
2024-01-01,Lasalgaon APMC,Maharashtra,Nashik,Red Onion,1500,2000,1750,1000
```

### **Export Features**
- Export filtered data to CSV
- Download prediction reports
- Generate analytics reports

##  API Endpoints

### **Available APIs**
- `GET /api/prices/` - Get price data
- `GET /api/predict/` - Get predictions
- `POST /api/train/` - Train ML models (admin only)

### **API Examples**
```bash
# Get last 30 days of price data
curl http://127.0.0.1:8000/api/prices/?days=30

# Get predictions for specific market
curl http://127.0.0.1:8000/api/predict/?market=Lasalgaon&days=7
```

##  Troubleshooting

### **Common Issues**

1. **"NoReverseMatch" errors**
   - Check URL patterns in urls.py
   - Ensure view names match in templates
   - Restart development server after URL changes

2. **Template filter errors**
   - Ensure custom_filters.py exists in templatetags
   - Add `{% load custom_filters %}` at template top
   - Restart server after adding new filters

3. **Database issues**
   - Run migrations: `python manage.py migrate`
   - Create superuser if missing
   - Check database file permissions

4. **Static files not loading**
   - Run: `python manage.py collectstatic`
   - Check STATIC_URL in settings
   - Ensure static files directory exists

### **Debug Mode**
Enable debug mode in development:
```python
# settings.py
DEBUG = True
```

##  Future Enhancements

1. **Real-time Data Integration**
   - Live market data feeds
   - Automated data collection
   - Real-time price updates

2. **Advanced Analytics**
   - Sentiment analysis of news
   - Weather impact analysis
   - Supply chain analytics

3. **Mobile Application**
   - React Native mobile app
   - Push notifications
   - Offline capabilities

4. **Advanced ML Features**
   - Ensemble model predictions
   - Hyperparameter optimization
   - Automated model retraining

5. **Additional Features**
   - SMS/Email alerts
   - Multi-language support
   - API rate limiting
   - Advanced reporting

##  Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests for new features
5. Submit a pull request

### **Code Style**
- Follow PEP 8 guidelines
- Use meaningful variable names
- Add comments for complex logic
- Write docstrings for functions

##  Acknowledgments

- Django framework and community
- Bootstrap for responsive design
- Chart.js for data visualization
- All contributors and testers

##  Support

For support, please:
1. Check the troubleshooting section
2. Review the documentation
3. Open an issue on GitHub
4. Contact the development team

---

**Happy Forecasting!** 🧅
```

## **Quick Start Commands Summary**

```bash
# Installation
git clone <repo-url>
cd onion-price-forecast
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## **Key URLs**
- **Home**: http://127.0.0.1:8000/
- **Admin Panel**: http://127.0.0.1:8000/admin-panel/
- **Django Admin**: http://127.0.0.1:8000/admin/

--------------------------------------** Changes **-----------------------------------------------
1.login page redirection
2.change logo name
