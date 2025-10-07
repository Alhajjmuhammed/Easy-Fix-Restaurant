#!/usr/bin/env python3
"""
Script to test security headers and CORS configuration
"""
import requests
import sys

def test_security_headers():
    """Test that security headers are properly set"""
    url = "http://localhost:8000"
    
    try:
        print("🔍 Testing security headers...")
        response = requests.get(url, timeout=10)
        
        headers_to_check = {
            'Cross-Origin-Opener-Policy': 'same-origin',
            'Cross-Origin-Embedder-Policy': 'require-corp',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
        }
        
        print(f"✅ Server responded with status: {response.status_code}")
        print("\n📋 Security Headers Check:")
        
        all_good = True
        for header, expected in headers_to_check.items():
            actual = response.headers.get(header)
            if actual:
                if actual.lower() == expected.lower():
                    print(f"  ✅ {header}: {actual}")
                else:
                    print(f"  ⚠️  {header}: {actual} (expected: {expected})")
                    all_good = False
            else:
                print(f"  ❌ {header}: Missing")
                all_good = False
        
        print(f"\n🔒 CSRF Token Check:")
        csrf_cookie = response.cookies.get('csrftoken')
        if csrf_cookie:
            print(f"  ✅ CSRF token present: {csrf_cookie[:20]}...")
        else:
            print(f"  ⚠️  CSRF token not found in cookies")
        
        if all_good:
            print(f"\n🎉 All security headers configured correctly!")
        else:
            print(f"\n⚠️  Some security headers need attention")
            
        return all_good
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error testing headers: {e}")
        return False

if __name__ == "__main__":
    success = test_security_headers()
    sys.exit(0 if success else 1)