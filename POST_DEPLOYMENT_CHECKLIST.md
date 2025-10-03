# 🔧 Post-Deployment Checklist

After running the deployment script, follow these steps:

---

## ✅ Immediate Tasks (Must Do)

### 1. Create Admin User
```bash
cd /var/www/restaurant
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=restaurant_system.production_settings
python manage.py createsuperuser
```

### 2. Create Default Roles
```bash
python manage.py shell
```

Then paste this:
```python
from accounts.models import Role

roles = [
    ('administrator', 'System Administrator'),
    ('owner', 'Restaurant Owner'),
    ('customer_care', 'Customer Care'),
    ('kitchen', 'Kitchen Staff'),
    ('cashier', 'Cashier'),
    ('customer', 'Customer'),
]

for name, description in roles:
    Role.objects.get_or_create(name=name, defaults={'description': description})
    print(f"✓ Created role: {name}")

print("\nAll roles created successfully!")
exit()
```

### 3. Verify Services are Running
```bash
sudo systemctl status restaurant
sudo systemctl status restaurant-daphne
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis-server
```

All should show **"active (running)"** in green.

---

## 🔒 Security Tasks (Recommended)

### 1. Change Database Password
```bash
sudo -u postgres psql
\password restaurant_user
# Enter new password
# Update .env file with new password
\q
```

### 2. Set Up SSH Key Authentication
```bash
# On your local computer (Windows PowerShell):
ssh-keygen -t ed25519

# Copy public key to server:
ssh-copy-id root@24.199.116.165
```

### 3. Disable Root Password Login (After SSH key works)
```bash
nano /etc/ssh/sshd_config
# Change: PermitRootLogin yes → PermitRootLogin prohibit-password
sudo systemctl restart sshd
```

---

## 📊 Testing Tasks

### 1. Test Website Access
- Open: http://24.199.116.165
- Should see login page

### 2. Test Admin Login
- Go to: http://24.199.116.165/accounts/login/
- Login with admin credentials

### 3. Test Creating a Restaurant Owner
As admin:
1. Go to System Admin dashboard
2. Create a restaurant owner
3. Generate QR code for the restaurant

### 4. Test WebSocket Connection
- Open browser console (F12)
- Go to kitchen dashboard
- Should see WebSocket connection in Network tab

---

## 📁 Directory Structure Check

Verify these directories exist:

```bash
ls -la /var/www/restaurant/
ls -la /var/www/restaurant/staticfiles/
ls -la /var/www/restaurant/media/
ls -la /var/www/restaurant/logs/
```

---

## 🔍 Log Monitoring

### View Application Logs
```bash
# Real-time logs
sudo journalctl -u restaurant -f

# Last 100 lines
sudo journalctl -u restaurant -n 100

# Errors only
sudo journalctl -u restaurant -p err
```

### View Nginx Logs
```bash
# Error log
sudo tail -f /var/log/nginx/restaurant_error.log

# Access log
sudo tail -f /var/log/nginx/restaurant_access.log
```

### View Gunicorn Logs
```bash
sudo tail -f /var/log/gunicorn/error.log
sudo tail -f /var/log/gunicorn/access.log
```

---

## 🔄 Common Maintenance Commands

### Restart All Services
```bash
sudo systemctl restart restaurant
sudo systemctl restart restaurant-daphne
sudo systemctl restart nginx
sudo systemctl restart redis-server
```

### Update from GitHub
```bash
cd /var/www/restaurant
git pull origin main
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=restaurant_system.production_settings
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart restaurant
sudo systemctl restart restaurant-daphne
```

### Database Backup
```bash
# Create backup
sudo -u postgres pg_dump restaurant_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
sudo -u postgres psql restaurant_db < backup_20241003_120000.sql
```

### Clear Django Cache
```bash
cd /var/www/restaurant
source venv/bin/activate
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
>>> exit()
```

---

## 🌐 Setting Up Domain Name (Optional)

If you have a domain (e.g., myrestaurant.com):

### 1. Point Domain to Server
In your domain registrar (GoDaddy, Namecheap, etc.):
- Add A Record: `@` → `24.199.116.165`
- Add A Record: `www` → `24.199.116.165`

### 2. Update Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/restaurant
```

Change:
```nginx
server_name 24.199.116.165;
```
To:
```nginx
server_name myrestaurant.com www.myrestaurant.com;
```

### 3. Update Django Settings
```bash
nano /var/www/restaurant/.env
```

Update:
```env
ALLOWED_HOSTS=24.199.116.165,myrestaurant.com,www.myrestaurant.com
```

### 4. Install SSL Certificate (HTTPS)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d myrestaurant.com -d www.myrestaurant.com
```

Follow prompts and choose option 2 (redirect HTTP to HTTPS).

### 5. Update Production Settings for HTTPS
```bash
nano /var/www/restaurant/.env
```

Add:
```env
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

Restart services:
```bash
sudo systemctl restart restaurant
sudo systemctl restart nginx
```

---

## 📱 Testing from Mobile Device

1. Connect mobile to same network or use 4G/5G
2. Open browser on mobile
3. Go to: http://24.199.116.165
4. Test QR code scanning feature
5. Test order placement
6. Test real-time updates

---

## 🐛 Troubleshooting Common Issues

### Issue: 502 Bad Gateway

**Solution 1**: Check if Gunicorn is running
```bash
sudo systemctl status restaurant
sudo systemctl restart restaurant
```

**Solution 2**: Check Gunicorn logs
```bash
sudo journalctl -u restaurant -n 50
```

### Issue: Static files not loading (no CSS)

**Solution**:
```bash
cd /var/www/restaurant
source venv/bin/activate
python manage.py collectstatic --noinput
sudo systemctl restart nginx
```

### Issue: Database connection errors

**Solution**: Check PostgreSQL
```bash
sudo systemctl status postgresql
sudo -u postgres psql -c "\l"  # List databases
```

### Issue: WebSocket not connecting

**Solution**: Check Daphne service
```bash
sudo systemctl status restaurant-daphne
sudo systemctl restart restaurant-daphne
sudo journalctl -u restaurant-daphne -f
```

### Issue: Permission denied errors

**Solution**: Fix file permissions
```bash
sudo chown -R www-data:www-data /var/www/restaurant
sudo chmod -R 755 /var/www/restaurant
```

---

## 📊 Performance Optimization

### 1. Enable Gzip Compression in Nginx
```bash
sudo nano /etc/nginx/nginx.conf
```

Add inside `http` block:
```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
gzip_min_length 1000;
```

### 2. Increase Gunicorn Workers
```bash
sudo nano /etc/systemd/system/restaurant.service
```

Change:
```
--workers 3
```
To (rule of thumb: 2-4 x CPU cores):
```
--workers 5
```

Reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart restaurant
```

### 3. Set Up Redis for Caching
Already installed! Add to production_settings.py:
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

---

## 🔐 Security Hardening

### 1. Set Up Fail2Ban (Prevent brute force)
```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 2. Configure Automatic Security Updates
```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### 3. Set Up Database Backups (Daily)
```bash
# Create backup script
sudo nano /usr/local/bin/backup-restaurant-db.sh
```

Paste:
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/restaurant"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
sudo -u postgres pg_dump restaurant_db | gzip > $BACKUP_DIR/backup_$DATE.sql.gz
# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
```

Make executable:
```bash
sudo chmod +x /usr/local/bin/backup-restaurant-db.sh
```

Add to crontab (daily at 2 AM):
```bash
sudo crontab -e
```

Add:
```
0 2 * * * /usr/local/bin/backup-restaurant-db.sh
```

---

## 📧 Monitoring and Alerts

### Set Up Email Notifications for Errors
Configure in production_settings.py:
```python
ADMINS = [('Your Name', 'your-email@example.com')]
SERVER_EMAIL = 'server@myrestaurant.com'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

---

## ✅ Final Verification Checklist

- [ ] Website accessible at http://24.199.116.165
- [ ] Admin can login
- [ ] All services running (restaurant, daphne, nginx, postgresql, redis)
- [ ] Static files loading correctly
- [ ] Media uploads working
- [ ] Database connected
- [ ] WebSocket connections working
- [ ] Can create restaurant owner
- [ ] Can generate QR codes
- [ ] Can place orders
- [ ] Kitchen receives orders
- [ ] Cashier can process payments
- [ ] Reports generating correctly
- [ ] Logs being written
- [ ] Firewall configured
- [ ] SSL certificate installed (if using domain)
- [ ] Backups configured
- [ ] Mobile testing completed

---

## 🎉 Success!

Your restaurant ordering system is now fully deployed and ready for production use!

**Client Demo URL**: http://24.199.116.165

**Next Steps**:
1. Show your client the system
2. Create their restaurant owner account
3. Set up their menu and products
4. Generate QR codes for tables
5. Train their staff

**Support**: Keep this checklist for reference when issues arise.

Good luck! 🚀
