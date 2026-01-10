# forecast_app/custom_admin/permissions.py
from django.contrib.auth.models import Group

def is_admin_user(user):
    """Check if user is an admin"""
    # You can define your own logic here
    # For example, check if user is superuser or belongs to admin group
    return user.is_superuser or user.is_staff

def create_admin_group():
    """Create admin group with permissions"""
    admin_group, created = Group.objects.get_or_create(name='Admin')
    
    # Add permissions to admin group
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    
    # Get all model permissions
    models = [
        'onionprice', 'weatherdata', 'predictionmodel',
        'priceprediction', 'marketfactor', 'userprofile'
    ]
    
    for model_name in models:
        try:
            content_type = ContentType.objects.get(app_label='forecast_app', model=model_name)
            permissions = Permission.objects.filter(content_type=content_type)
            admin_group.permissions.add(*permissions)
        except:
            continue
    
    return admin_group