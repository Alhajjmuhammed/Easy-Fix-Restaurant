#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_system.settings')

# Configure Django settings without Redis for testing
import logging
logging.disable(logging.CRITICAL)

try:
    django.setup()
    from accounts.models import User
    
    print("=== QR CODE TESTING ===")
    
    # Test each QR code
    qr_codes = [
        'REST-E0C81579F359',
        'REST-B3899BEE25C0', 
        'REST-615C7BFFA57C',
        'REST-AC4369AEE2C8',
        'REST-6140FF391DFF'
    ]
    
    for qr in qr_codes:
        try:
            restaurant = User.objects.get(
                restaurant_qr_code=qr, 
                role__name='owner', 
                is_active=True
            )
            print(f"✅ QR: {qr} -> {restaurant.restaurant_name}")
        except User.DoesNotExist:
            print(f"❌ QR: {qr} -> NOT FOUND")
        except Exception as e:
            print(f"⚠️  QR: {qr} -> ERROR: {e}")
    
    print("\n=== TESTING QR_CODE_ACCESS VIEW LOGIC ===")
    # Test the exact same query used in the view
    test_qr = 'REST-E0C81579F359'
    try:
        restaurant = User.objects.get(
            restaurant_qr_code=test_qr, 
            role__name='owner', 
            is_active=True
        )
        print(f"✅ View logic test passed: {restaurant.restaurant_name}")
        print(f"   QR URL: {restaurant.get_qr_url()}")
    except User.DoesNotExist:
        print(f"❌ View logic test failed: Restaurant not found for QR {test_qr}")
    
except Exception as e:
    print(f"Setup error: {e}")