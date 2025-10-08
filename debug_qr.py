"""
Debug script to check QR codes in database
Run with: python manage.py shell < debug_qr.py
"""

from accounts.models import User

print("\n" + "="*60)
print("QR CODE DEBUG - Checking all owner accounts")
print("="*60 + "\n")

owners = User.objects.filter(role__name='owner', is_active=True)

if not owners.exists():
    print("❌ No active owner accounts found!")
else:
    print(f"✅ Found {owners.count()} owner account(s):\n")
    
    for idx, owner in enumerate(owners, 1):
        print(f"Owner #{idx}:")
        print(f"  Username: {owner.username}")
        print(f"  Email: {owner.email}")
        print(f"  Restaurant: {owner.restaurant_name}")
        print(f"  QR Code: {owner.restaurant_qr_code}")
        print(f"  Expected URL: https://easyfixsoft.com/r/{owner.restaurant_qr_code}/")
        print(f"  Is Active: {owner.is_active}")
        print()

print("="*60)
print("INSTRUCTIONS:")
print("="*60)
print("1. Compare the QR Code above with your working URL")
print("2. Working URL: REST-8F453B5D369D")
print("3. Scanned QR: REST-2C65409B3843")
print("4. If they don't match, you need to regenerate the QR image")
print("="*60 + "\n")
