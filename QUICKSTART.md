# 🚀 Quick Start - Deploy in 5 Minutes!

## For Complete Beginners 👋

This is the **EASIEST** way to deploy your restaurant system. Just follow these 3 steps:

---

## 📝 Step 1: Connect to Your Server

### Windows Users (PowerShell):
```powershell
ssh root@24.199.116.165
```

### Windows Users (PuTTY):
1. Download PuTTY: https://www.putty.org/
2. Open PuTTY
3. Enter: **24.199.116.165**
4. Click "Open"
5. Login as: **root**

**💡 When typing password, you won't see anything - this is normal!**

---

## 🎯 Step 2: Run Automatic Installation

Copy and paste this **ONE COMMAND**:

```bash
curl -sL https://raw.githubusercontent.com/Alhajjmuhammed/Easy-Fix-Restaurant/main/deploy.sh -o deploy.sh && chmod +x deploy.sh && ./deploy.sh
```

**⏰ Wait 10-15 minutes** while it installs everything automatically.

---

## ✅ Step 3: Create Admin Account

After installation completes, create your admin account:

```bash
cd /var/www/restaurant
source venv/bin/activate
python manage.py createsuperuser
```

**Answer the prompts**:
- Username: `admin` (or your choice)
- Email: your-email@example.com
- Password: (create a strong password)
- Password (again): (repeat your password)

---

## 🎉 Done! Access Your Website

Open your browser and go to:

**http://24.199.116.165**

Login at:

**http://24.199.116.165/accounts/login/**

---

## ❌ If Something Goes Wrong

### Problem: Can't connect to server
**Solution**: Check your email from DigitalOcean for the root password

### Problem: Script fails
**Solution**: Run these commands one by one:

```bash
sudo apt update
sudo apt install -y curl git
curl -sL https://raw.githubusercontent.com/Alhajjmuhammed/Easy-Fix-Restaurant/main/deploy.sh -o deploy.sh
chmod +x deploy.sh
./deploy.sh
```

### Problem: Website not loading
**Solution**: Check if services are running:

```bash
sudo systemctl status restaurant
sudo systemctl status nginx
```

If they show **"failed"**, restart them:

```bash
sudo systemctl restart restaurant
sudo systemctl restart nginx
```

---

## 🔄 How to Update Your Website

When you push changes to GitHub:

```bash
cd /var/www/restaurant
git pull origin main
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart restaurant
```

---

## 📞 Important Commands

| What you want to do | Command |
|---------------------|---------|
| Check if website is running | `sudo systemctl status restaurant` |
| Restart website | `sudo systemctl restart restaurant` |
| See error messages | `sudo journalctl -u restaurant -f` |
| Update from GitHub | `cd /var/www/restaurant && git pull` |

---

## 🆘 Emergency Reset

If everything breaks, run the deployment script again:

```bash
cd /var/www/restaurant
git pull origin main
./deploy.sh
```

---

## 📋 What the Script Does

✅ Installs Python, PostgreSQL, Nginx, Redis  
✅ Downloads your project from GitHub  
✅ Creates database  
✅ Installs all packages  
✅ Sets up web server  
✅ Configures firewall  
✅ Starts your website  

---

## ✨ Features Your Client Can Use

1. **QR Code Menu**: Customers scan QR code to order
2. **Real-time Orders**: Kitchen sees orders instantly
3. **Payment System**: Cashier processes payments
4. **Reports**: Owner sees sales reports
5. **Waste Tracking**: Track food waste
6. **Happy Hour**: Automatic discounts at specific times

---

## 🎯 Success! Your website is live at:

### **http://24.199.116.165**

Show this to your client! 🎊

---

## 📧 Need More Help?

Read the full guide: `DEPLOYMENT_GUIDE.md`

Or check specific issues in the troubleshooting section.

**Remember**: Take your time, read each step, and don't panic! 😊
