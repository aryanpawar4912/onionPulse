# forecast_app/custom_admin/templatetags/admin_tags.py
from django import template

register = template.Library()

@register.filter
def get_price_class(price):
    """Return CSS class based on price"""
    try:
        price = float(price)
        if price > 50:
            return 'price-high'
        elif price > 30:
            return 'price-medium'
        return 'price-low'
    except:
        return ''

@register.filter
def get_confidence_class(confidence):
    """Return CSS class based on confidence"""
    try:
        confidence = float(confidence)
        if confidence >= 80:
            return 'confidence-high'
        elif confidence >= 60:
            return 'confidence-medium'
        return 'confidence-low'
    except:
        return ''