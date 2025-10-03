# 🍽️ Restaurant Ordering System

[![Django](https://img.shields.io/badge/Django-4.2.7-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-Open%20Source-green.svg)](LICENSE)

A comprehensive **multi-tenant restaurant management and ordering system** with real-time order tracking, QR code ordering, payment processing, waste management, and advanced reporting.

---

## 🚀 Quick Deploy to DigitalOcean

**Deploy in 5 minutes with ONE command!**

```bash
ssh root@YOUR_SERVER_IP
curl -sL https://raw.githubusercontent.com/Alhajjmuhammed/Easy-Fix-Restaurant/main/deploy.sh -o deploy.sh && chmod +x deploy.sh && ./deploy.sh
```

### 📚 Deployment Documentation

- 🎯 **[QUICKSTART.md](QUICKSTART.md)** - Deploy in 5 minutes (for beginners)
- 🎨 **[VISUAL_GUIDE.md](VISUAL_GUIDE.md)** - Step-by-step visual guide
- 📘 **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment instructions
- ✅ **[POST_DEPLOYMENT_CHECKLIST.md](POST_DEPLOYMENT_CHECKLIST.md)** - After deployment tasks
- 📝 **[COMMANDS_CHEATSHEET.md](COMMANDS_CHEATSHEET.md)** - Quick command reference
- 📖 **[DEPLOYMENT_INDEX.md](DEPLOYMENT_INDEX.md)** - Documentation overview

---

## ✨ Features

### 🏢 Multi-Tenant Architecture
- Multiple restaurants on one system
- Isolated data per restaurant
- QR code-based restaurant access
- Custom branding per restaurant

### 📱 Customer Experience
- **QR Code Ordering** - Scan table QR code to access menu
- **Real-time Order Tracking** - WebSocket-powered live updates
- **Shopping Cart** - Add/remove items, special instructions
- **Order History** - View past orders
- **Mobile-Friendly** - PWA (Progressive Web App) ready

### 👨‍🍳 Kitchen Management
- **Real-time Order Display** - New orders appear instantly
- **Order Status Management** - Update status (pending → preparing → ready → served)
- **WebSocket Notifications** - Audio/visual alerts for new orders
- **Preparation Time** - Estimated cooking time per item

### 💰 Payment Processing
- **Multiple Payment Methods** - Cash, card, digital, voucher
- **Split Bill** - Pay for specific items
- **Void/Refund** - Transaction reversal with audit trail
- **Payment History** - Complete transaction log

### 📊 Reports & Analytics
- **Sales Reports** - Daily, weekly, monthly, custom ranges
- **Product Performance** - Best sellers, revenue by product
- **Category Analysis** - Performance by category
- **Payment Method Breakdown** - Cash vs card vs digital
- **Export Options** - CSV, PDF, Excel

### 🗑️ Waste Management
- **Comprehensive Tracking** - Record all food waste
- **Cost Breakdown** - Ingredient, labor, overhead costs
- **Waste Reasons** - Customer refused, quality issues, kitchen errors
- **Disposal Methods** - Track how waste is handled
- **Reports** - Waste trends and cost analysis

### ⏰ Happy Hour Promotions
- **Time-Based Discounts** - Automatic price adjustments
- **Day-Specific** - Configure for specific weekdays
- **Flexible Targeting** - Apply to products, categories, or subcategories
- **Dynamic Pricing** - Real-time price calculation

### 👥 Role-Based Access Control
- **Administrator** - Full system access, all restaurants
- **Owner** - Restaurant management, staff creation
- **Kitchen Staff** - Order preparation and status updates
- **Customer Care** - Customer support and order assistance
- **Cashier** - Payment processing and waste recording
- **Customer** - Browse menu and place orders

---

## 🛠️ Technology Stack

### Backend
- **Django 4.2.7** - Web framework
- **PostgreSQL** - Production database
- **Channels 4.0.0** - WebSocket support
- **Redis** - Caching and channel layer
- **Gunicorn** - WSGI server
- **Daphne** - ASGI server for WebSocket

### Frontend
- **Bootstrap 5.3.2** - UI framework
- **JavaScript** - Real-time features
- **PWA** - Progressive Web App capabilities

### Infrastructure
- **Nginx** - Web server & reverse proxy
- **Systemd** - Service management
- **Ubuntu 24.04 LTS** - Operating system

### Additional Libraries
- **Pillow** - Image processing
- **QRCode** - QR code generation
- **ReportLab** - PDF generation
- **Pandas** - Data analysis
- **OpenPyXL** - Excel export

---

## 📋 System Requirements

### Minimum (Testing)
- 1 GB RAM
- 25 GB Disk
- 1 CPU Core

### Recommended (Production)
- 2 GB RAM
- 50 GB Disk
- 2 CPU Cores

---

## 🎯 Quick Start

### For Complete Beginners

1. **Connect to your server**:
   ```bash
   ssh root@24.199.116.165
   ```

2. **Run deployment script**:
   ```bash
   curl -sL https://raw.githubusercontent.com/Alhajjmuhammed/Easy-Fix-Restaurant/main/deploy.sh -o deploy.sh
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Create admin user**:
   ```bash
   cd /var/www/restaurant
   source venv/bin/activate
   python manage.py createsuperuser
   ```

4. **Access your website**:
   ```
   http://YOUR_SERVER_IP
   ```

**📖 For detailed instructions, see [QUICKSTART.md](QUICKSTART.md)**

---

## 📊 Project Structure

```
restaurant-ordering-system/
├── accounts/              # User authentication & roles
├── admin_panel/          # Owner/admin management
├── cashier/              # Payment processing
├── orders/               # Order management & WebSocket
├── reports/              # Analytics & reporting
├── restaurant/           # Menu & product management
├── system_admin/         # System administrator functions
├── waste_management/     # Food waste tracking
├── restaurant_system/    # Django project settings
├── templates/            # HTML templates
├── static/              # CSS, JS, images
├── media/               # Uploaded files
└── deploy.sh            # Automated deployment script
```

---

## 🔐 Security Features

- ✅ CSRF protection
- ✅ XSS protection
- ✅ SQL injection prevention (Django ORM)
- ✅ Secure password hashing
- ✅ Role-based access control
- ✅ Firewall configuration
- ✅ SSL/HTTPS ready

---

## 🌐 Access Points

After deployment:

| Service | URL |
|---------|-----|
| Main Website | `http://YOUR_IP/` |
| Login | `http://YOUR_IP/accounts/login/` |
| Admin Panel | `http://YOUR_IP/admin-panel/` |
| System Admin | `http://YOUR_IP/system-admin/` |
| Kitchen | `http://YOUR_IP/orders/kitchen/` |
| Cashier | `http://YOUR_IP/cashier/` |
| Reports | `http://YOUR_IP/reports/` |

---

## 🔄 Updating

When you push changes to GitHub:

```bash
ssh root@YOUR_SERVER_IP
cd /var/www/restaurant
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart restaurant restaurant-daphne
```

---

## 🆘 Troubleshooting

### Website not loading?
```bash
sudo systemctl restart restaurant nginx
curl -I http://localhost
```

### View logs
```bash
sudo journalctl -u restaurant -f
sudo tail -f /var/log/nginx/restaurant_error.log
```

### Run health check
```bash
cd /var/www/restaurant
sudo ./health-check.sh
```

**📖 For more help, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**

---

## 📱 Demo Flow

1. **Admin** creates restaurant owner
2. **Owner** adds menu items with photos
3. **Owner** creates tables and generates QR codes
4. **Customer** scans QR code with phone
5. **Customer** browses menu and places order
6. **Kitchen** receives order in real-time
7. **Kitchen** updates status as they cook
8. **Customer** sees live status updates
9. **Cashier** processes payment
10. **Owner** views sales reports

---

## 🎓 Documentation

- **[ACCESS_GUIDE.md](ACCESS_GUIDE.md)** - User roles and access
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Full deployment instructions
- **[COMMANDS_CHEATSHEET.md](COMMANDS_CHEATSHEET.md)** - Quick reference

---

## 🤝 Contributing

This project is open for contributions. Feel free to:
- Report bugs
- Suggest features
- Submit pull requests
- Improve documentation

---

## 📄 License

Open Source - Free to use and modify

---

## 🙏 Acknowledgments

Built with Django, PostgreSQL, Nginx, Redis, and Channels.

---

## 📧 Support

- **Documentation**: Check the guides folder
- **Issues**: Open a GitHub issue
- **Logs**: Use `sudo journalctl -u restaurant -f`

---

## ⭐ Quick Links

- [Deploy in 5 Minutes](QUICKSTART.md)
- [Visual Step-by-Step Guide](VISUAL_GUIDE.md)
- [Complete Documentation](DEPLOYMENT_INDEX.md)
- [Command Reference](COMMANDS_CHEATSHEET.md)
- [Health Check Script](health-check.sh)

---

**🎉 Ready to deploy? Start with [QUICKSTART.md](QUICKSTART.md)!**

---

*Made with ❤️ for Restaurant Owners*