# 🚀 One-Command Deployment to DigitalOcean

## Deploy Your Restaurant System in 5 Minutes!

This repository contains everything you need to deploy the Restaurant Ordering System to your DigitalOcean VPS.

---

## 📋 Prerequisites

- ✅ DigitalOcean VPS running Ubuntu 24.04 LTS
- ✅ Root access to your server
- ✅ Server IP address (e.g., 24.199.116.165)

---

## 🎯 Quick Deployment

### Step 1: Connect to Your Server

```bash
ssh root@YOUR_SERVER_IP
```

### Step 2: Run Deployment Script

```bash
curl -sL https://raw.githubusercontent.com/Alhajjmuhammed/Easy-Fix-Restaurant/main/deploy.sh -o deploy.sh && chmod +x deploy.sh && ./deploy.sh
```

### Step 3: Create Admin User

```bash
cd /var/www/restaurant
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=restaurant_system.production_settings
python manage.py createsuperuser
```

### Step 4: Access Your Website

Open browser: `http://YOUR_SERVER_IP`

---

## 📖 Documentation

- **[Quick Start Guide](QUICKSTART.md)** - 5-minute deployment
- **[Visual Guide](VISUAL_GUIDE.md)** - Step-by-step with explanations
- **[Full Deployment Guide](DEPLOYMENT_GUIDE.md)** - Complete instructions
- **[Post-Deployment Checklist](POST_DEPLOYMENT_CHECKLIST.md)** - After installation

---

## 🔧 What Gets Installed

The deployment script automatically installs and configures:

- ✅ **Python 3** - Application runtime
- ✅ **PostgreSQL** - Production database
- ✅ **Nginx** - Web server
- ✅ **Redis** - WebSocket support
- ✅ **Gunicorn** - WSGI server
- ✅ **Daphne** - ASGI server for WebSocket
- ✅ **Systemd Services** - Auto-start on boot
- ✅ **Firewall** - Security configuration

---

## 🌟 Features

- 🍽️ **Multi-Restaurant Support** - Host multiple restaurants
- 📱 **QR Code Ordering** - Customers scan & order
- ⚡ **Real-Time Updates** - WebSocket order tracking
- 💳 **Payment Processing** - Cash, card, digital payments
- 📊 **Sales Reports** - Comprehensive analytics
- 🗑️ **Waste Management** - Track food waste
- ⏰ **Happy Hour** - Automated time-based discounts
- 👥 **Role-Based Access** - 6 user roles

---

## 🔐 Security

- ✅ CSRF protection enabled
- ✅ PostgreSQL with strong passwords
- ✅ Firewall configured
- ✅ Rate limiting
- ✅ XSS protection
- ✅ Secure headers

---

## 📊 System Requirements

**Minimum** (for testing):
- 1 GB RAM
- 25 GB Disk
- 1 CPU Core

**Recommended** (for production):
- 2 GB RAM
- 50 GB Disk
- 2 CPU Cores

---

## 🔄 Updating Your Deployment

When you push changes to GitHub:

```bash
ssh root@YOUR_SERVER_IP
cd /var/www/restaurant
git pull origin main
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart restaurant
```

---

## 🆘 Troubleshooting

### Website not accessible?

```bash
# Check services
sudo systemctl status restaurant
sudo systemctl status nginx

# Restart if needed
sudo systemctl restart restaurant
sudo systemctl restart nginx
```

### Database errors?

```bash
sudo systemctl status postgresql
sudo -u postgres psql -c "\l"
```

### View logs?

```bash
# Application logs
sudo journalctl -u restaurant -f

# Nginx logs
sudo tail -f /var/log/nginx/restaurant_error.log
```

---

## 🌐 Using a Custom Domain

1. Point your domain A record to your server IP
2. Update `/var/www/restaurant/.env`:
   ```
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   ```
3. Install SSL certificate:
   ```bash
   sudo certbot --nginx -d yourdomain.com
   ```

---

## 📱 Client Demo Flow

1. **Admin creates restaurant owner**
2. **Owner adds menu items**
3. **Owner creates tables & QR codes**
4. **Customers scan QR code**
5. **Customers place orders**
6. **Kitchen receives orders in real-time**
7. **Cashier processes payments**
8. **Owner views reports**

---

## 🎯 User Roles

1. **Administrator** - Full system access
2. **Owner** - Restaurant management
3. **Kitchen Staff** - Order preparation
4. **Customer Care** - Customer support
5. **Cashier** - Payment processing
6. **Customer** - Place orders

---

## 📞 Support

- **Issues**: Open a GitHub issue
- **Documentation**: Check the guides folder
- **Logs**: Use troubleshooting commands above

---

## 📄 License

This project is open source and available for use.

---

## 🙏 Acknowledgments

Built with Django, PostgreSQL, Nginx, and Redis.

---

## ⭐ Quick Links

- **Login**: `http://YOUR_IP/accounts/login/`
- **Admin Panel**: `http://YOUR_IP/admin-panel/`
- **System Admin**: `http://YOUR_IP/system-admin/`
- **Kitchen**: `http://YOUR_IP/orders/kitchen/`
- **Cashier**: `http://YOUR_IP/cashier/`

---

## 🚀 Get Started Now!

```bash
ssh root@YOUR_SERVER_IP
curl -sL https://raw.githubusercontent.com/Alhajjmuhammed/Easy-Fix-Restaurant/main/deploy.sh -o deploy.sh
chmod +x deploy.sh
./deploy.sh
```

**That's it!** Your restaurant system will be live in 15 minutes! 🎉

---

Made with ❤️ for Restaurant Owners
