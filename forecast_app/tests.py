from datetime import date

from django.test import TestCase

from forecast_app.models import OnionPrice, PricePrediction
from forecast_app.views import dashboard, home


class DashboardViewTests(TestCase):
    def test_dashboard_uses_database_prices_and_predictions(self):
        OnionPrice.objects.create(
            date=date(2024, 1, 1),
            market='Delhi',
            state='Delhi',
            district='Delhi',
            variety='Red',
            min_price=1000,
            max_price=1200,
            modal_price=1100,
            arrival_quantity=10,
        )
        OnionPrice.objects.create(
            date=date(2024, 1, 2),
            market='Delhi',
            state='Delhi',
            district='Delhi',
            variety='Red',
            min_price=1100,
            max_price=1300,
            modal_price=1200,
            arrival_quantity=10,
        )

        PricePrediction.objects.create(
            prediction_date=date(2024, 1, 2),
            forecast_date=date(2024, 1, 3),
            market='Delhi',
            predicted_min_price=1150,
            predicted_max_price=1250,
            predicted_modal_price=1200,
            confidence_interval=90,
        )
        PricePrediction.objects.create(
            prediction_date=date(2024, 1, 2),
            forecast_date=date(2024, 1, 4),
            market='Delhi',
            predicted_min_price=1180,
            predicted_max_price=1280,
            predicted_modal_price=1230,
            confidence_interval=88,
        )

        response = self.client.get('/dashboard/')

        self.assertEqual(response.context['trend_data']['current_price'], 1200.0)
        self.assertEqual(response.context['trend_data']['avg_30d'], 1150.0)
        self.assertEqual(response.context['predictions'][0]['predicted_price'], 1200.0)
        self.assertEqual(response.context['predictions'][1]['predicted_price'], 1230.0)

    def test_home_page_market_cards_use_latest_database_values(self):
        OnionPrice.objects.create(
            date=date(2024, 2, 1),
            market='Lasalgaon',
            state='Maharashtra',
            district='Nashik',
            variety='Red',
            min_price=2400,
            max_price=2600,
            modal_price=2500,
            arrival_quantity=10,
        )
        OnionPrice.objects.create(
            date=date(2024, 2, 2),
            market='Nashik',
            state='Maharashtra',
            district='Nashik',
            variety='Red',
            min_price=2500,
            max_price=2700,
            modal_price=2600,
            arrival_quantity=10,
        )
        OnionPrice.objects.create(
            date=date(2024, 2, 3),
            market='Lasalgaon',
            state='Maharashtra',
            district='Nashik',
            variety='Red',
            min_price=2300,
            max_price=2500,
            modal_price=2400,
            arrival_quantity=10,
        )

        response = self.client.get('/')

        self.assertEqual(response.context['market_pulse']['price'], 2600.0)
        self.assertEqual(response.context['market_pulse']['change_percent'], 4.0)
        self.assertEqual(response.context['market_cards'][0]['market'], 'Lasalgaon')
        self.assertEqual(response.context['market_cards'][0]['price'], 2400.0)
        self.assertEqual(response.context['market_cards'][1]['market'], 'Nashik')
        self.assertEqual(response.context['market_cards'][1]['price'], 2600.0)
