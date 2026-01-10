# custom_admin/templatetags/custom_filters.py
from django import template
import math
register = template.Library()
@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value
@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value
@register.filter
def divide(value, arg):
    """Divide value by arg"""
    try:
        arg = float(arg)
        if arg != 0:
            return float(value) / arg
        return 0
    except (ValueError, TypeError):
        return 0
@register.filter
def abs_value(value):
    """Get absolute value"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value
@register.filter
def calculate_accuracy(predicted, actual):
    """Calculate prediction accuracy"""
    try:
        predicted = float(predicted)
        actual = float(actual)
        if actual != 0:
            error = abs(predicted - actual) / actual
            accuracy = (1 - error) * 100
            return round(accuracy, 2)
        return 0
    except (ValueError, TypeError):
        return 0
@register.filter
def get_accuracy_badge_class(accuracy):
    """Get badge class for accuracy"""
    try:
        accuracy = float(accuracy)
        if accuracy > 90:
            return 'bg-success'
        elif accuracy > 80:
            return 'bg-success'
        elif accuracy > 70:
            return 'bg-warning'
        else:
            return 'bg-danger'
    except (ValueError, TypeError):
        return 'bg-secondary'
@register.filter
def get_accuracy_text(accuracy):
    """Get text for accuracy"""
    try:
        accuracy = float(accuracy)
        if accuracy > 90:
            return 'Excellent'
        elif accuracy > 80:
            return 'Good'
        elif accuracy > 70:
            return 'Fair'
        else:
            return 'Poor'
    except (ValueError, TypeError):
        return 'Pending'
@register.filter
def format_price(value):
    """Format price with ₹ symbol"""
    try:
        return f"₹{float(value):.2f}"
    except (ValueError, TypeError):
        return f"₹{value}"