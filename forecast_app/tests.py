from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import OnionPrice, PricePrediction


class MarketDataViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='tester', password='secret123')

        self.latest_price = OnionPrice.objects.create(
            date=date.today(),
            market='Lasalgaon',
            state='Maharashtra',
            district='Nashik',
            variety='Red',
            min_price=1800,
            max_price=2400,
            modal_price=2100,
            arrival_quantity=125,
        )
        OnionPrice.objects.create(
            date=date.today() - timedelta(days=1),
            market='Lasalgaon',
            state='Maharashtra',
            district='Nashik',
            variety='Red',
            min_price=1700,
            max_price=2300,
            modal_price=2000,
            arrival_quantity=120,
        )
        OnionPrice.objects.create(
            date=date.today() - timedelta(days=2),
            market='Pune',
            state='Maharashtra',
            district='Pune',
            variety='Red',
            min_price=1600,
            max_price=2200,
            modal_price=1950,
            arrival_quantity=110,
        )

        PricePrediction.objects.create(
            prediction_date=date.today(),
            forecast_date=date.today() + timedelta(days=1),
            market='Lasalgaon',
            predicted_min_price=1900,
            predicted_max_price=2200,
            predicted_modal_price=2100,
            confidence_interval=88.0,
        )
        PricePrediction.objects.create(
            prediction_date=date.today(),
            forecast_date=date.today() + timedelta(days=2),
            market='Lasalgaon',
            predicted_min_price=1950,
            predicted_max_price=2250,
            predicted_modal_price=2150,
            confidence_interval=84.0,
        )

    def test_home_page_uses_saved_market_data(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lasalgaon')
        self.assertContains(response, '₹2100')
        self.assertContains(response, 'Increase')

    def test_dashboard_uses_saved_metrics_and_predictions(self):
        self.client.login(username='tester', password='secret123')
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Current Price')
        self.assertContains(response, '30-Day Avg')
        self.assertContains(response, 'Price Range')
        self.assertContains(response, '7-Day Price Forecast')
        self.assertContains(response, '₹2100')
        self.assertContains(response, '₹2000')

    def test_historical_page_uses_saved_summary_stats(self):
        self.client.login(username='tester', password='secret123')
        response = self.client.get(reverse('historical'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Avg Min Price')
        self.assertContains(response, 'Avg Max Price')
        self.assertContains(response, '₹1700')
        self.assertContains(response, '₹2300')
