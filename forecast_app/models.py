

# forecast_app/models.py - FIXED VERSION for SQLite
from django.db import models
from django.contrib.auth.models import User
import json

class OnionPrice(models.Model):
    # REMOVED: _id = models.ObjectIdField()  # Not needed for SQLite
    date = models.DateField()
    market = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    variety = models.CharField(max_length=50)
    min_price = models.FloatField()  # in rupees
    max_price = models.FloatField()  # in rupees
    modal_price = models.FloatField()  # in rupees (most common price)
    arrival_quantity = models.FloatField()  # in quintals
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['market']),
            models.Index(fields=['state']),
        ]
    
    def __str__(self):
        return f"{self.date} - {self.market} - ₹{self.modal_price}"

class WeatherData(models.Model):
    # REMOVED: _id = models.ObjectIdField()  # Not needed for SQLite
    date = models.DateField()
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    rainfall = models.FloatField()  # in mm
    temperature = models.FloatField()  # in °C
    humidity = models.FloatField()  # in %
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.date} - {self.district}"

class PredictionModel(models.Model):
    MODEL_TYPES = [
        ('LSTM', 'LSTM Neural Network'),
        ('RF', 'Random Forest'),
        ('XGB', 'XGBoost'),
        ('PROPHET', 'Facebook Prophet'),
    ]
    
    # REMOVED: _id = models.ObjectIdField()  # Not needed for SQLite
    name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=50, choices=MODEL_TYPES)
    accuracy = models.FloatField(null=True, blank=True)
    mse = models.FloatField(null=True, blank=True)
    mae = models.FloatField(null=True, blank=True)
    file_path = models.CharField(max_length=200)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.model_type})"

class PricePrediction(models.Model):
    # REMOVED: _id = models.ObjectIdField()  # Not needed for SQLite
    prediction_date = models.DateField()
    forecast_date = models.DateField()
    market = models.CharField(max_length=100)
    predicted_min_price = models.FloatField()  # in rupees
    predicted_max_price = models.FloatField()  # in rupees
    predicted_modal_price = models.FloatField()  # in rupees
    confidence_interval = models.FloatField()  # confidence percentage
    model_used = models.ForeignKey(PredictionModel, on_delete=models.CASCADE, null=True, blank=True)
    actual_price = models.FloatField(null=True, blank=True)  # for validation
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Prediction for {self.forecast_date}: ₹{self.predicted_modal_price}"

class MarketFactor(models.Model):
    FACTOR_TYPES = [
        ('SEASONAL', 'Seasonal'),
        ('WEATHER', 'Weather'),
        ('ECONOMIC', 'Economic'),
        ('POLICY', 'Government Policy'),
        ('TRANSPORT', 'Transportation'),
    ]
    
    # REMOVED: _id = models.ObjectIdField()  # Not needed for SQLite
    name = models.CharField(max_length=100)
    factor_type = models.CharField(max_length=50, choices=FACTOR_TYPES)
    description = models.TextField()
    impact_score = models.FloatField()  # -1 to +1, negative/positive impact
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.factor_type})"

class UserProfile(models.Model):
    USER_TYPES = [
        ('FARMER', 'Farmer'),
        ('TRADER', 'Trader'),
        ('CONSUMER', 'Consumer'),
        ('GOVERNMENT', 'Government Official'),
        ('RESEARCHER', 'Researcher'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    phone = models.CharField(max_length=15)
    location = models.CharField(max_length=100)
    # For SQLite, use TextField with JSON string instead of JSONField
    preferences = models.TextField(default='{}')  # Store JSON as string
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_preferences(self):
        """Get preferences as dictionary"""
        return json.loads(self.preferences)
    
    def set_preferences(self, data):
        """Set preferences from dictionary"""
        self.preferences = json.dumps(data)
    
    def __str__(self):
        return f"{self.user.username} - {self.user_type}"