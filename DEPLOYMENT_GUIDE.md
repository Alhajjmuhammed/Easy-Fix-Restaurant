# 🚀 Easy Deployment Guide for Beginners

## Your Server Information
- **Server Name**: EasyFix-Restaurant
- **IP Address**: 24.199.116.165
- **Operating System**: Ubuntu 24.04 LTS
- **Memory**: 2 GB
- **Disk**: 50 GB
- **Location**: SFO3 (San Francisco)

---

## 📋 What We'll Do (Simple Steps)

1. **Connect to your server** (like opening a door to your VPS)
2. **Install required software** (Python, database, etc.)
3. **Download your project** from GitHub
4. **Configure the project** for production
5. **Start your website** and make it accessible

**Estimated Time**: 30-45 minutes

---

## 🔧 Step 1: Connect to Your Server

### Option A: Using PowerShell (Windows)

Open PowerShell and type:

```powershell
ssh root@24.199.116.165
```

### Option B: Using PuTTY (Windows)

1. Download PuTTY from: https://www.putty.org/
2. Open PuTTY
3. Enter **24.199.116.165** in "Host Name"
4. Click "Open"
5. Login as: **root**
6. Enter your password (DigitalOcean sent this via email)

**💡 Tip**: When you type your password, you won't see anything on screen - this is normal! Just type and press Enter.

---

## 🎯 Step 2: Automatic Installation Script

Once connected to your server, copy and paste this **ONE COMMAND** to install everything automatically:

```bash
curl -O https://raw.githubusercontent.com/Alhajjmuhammed/Easy-Fix-Restaurant/main/deploy.sh && chmod +x deploy.sh && ./deploy.sh
```

**⏰ This will take 10-15 minutes**. The script will:
- ✅ Update Ubuntu system
- ✅ Install Python 3, PostgreSQL, Nginx, Redis
- ✅ Download your project from GitHub
- ✅ Install all Python packages
- ✅ Set up database
- ✅ Configure firewall
- ✅ Start your website

---

## 📝 Step 3: Manual Installation (If Automatic Fails)

If the automatic script doesn't work, follow these manual steps:

### 3.1 Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 3.2 Install Required Software
```bash
sudo apt install -y python3 python3-pip python3-venv git nginx postgresql postgresql-contrib redis-server
```

### 3.3 Create Project Directory
```bash
mkdir -p /var/www/restaurant
cd /var/www/restaurant
```

### 3.4 Download Your Project
```bash
git clone https://github.com/Alhajjmuhammed/Easy-Fix-Restaurant.git .
```

### 3.5 Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3.6 Install Python Packages
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### 3.7 Set Up PostgreSQL Database
```bash
sudo -u postgres psql -c "CREATE DATABASE restaurant_db;"
sudo -u postgres psql -c "CREATE USER restaurant_user WITH PASSWORD 'YourStrongPassword123!';"
sudo -u postgres psql -c "ALTER ROLE restaurant_user SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE restaurant_user SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE restaurant_user SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE restaurant_db TO restaurant_user;"
```

---

## 🔒 Step 4: Configure Production Settings

### 4.1 Create Environment File
```bash
nano /var/www/restaurant/.env
```

Paste this content (press Ctrl+X, then Y, then Enter to save):

```env
SECRET_KEY=your-very-long-random-secret-key-change-this-in-production
DEBUG=False
ALLOWED_HOSTS=24.199.116.165,yourdomain.com
DATABASE_NAME=restaurant_db
DATABASE_USER=restaurant_user
DATABASE_PASSWORD=YourStrongPassword123!
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

### 4.2 Update Django Settings

The project already has production settings, but verify them:

```bash
nano /var/www/restaurant/restaurant_system/settings.py
```

---

## 🗄️ Step 5: Set Up Database

```bash
cd /var/www/restaurant
source venv/bin/activate
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
```

### Create Admin User
```bash
python manage.py createsuperuser
```

**Follow prompts**:
- Username: admin
- Email: your-email@example.com
- Password: (create a strong password)

---

## 🌐 Step 6: Configure Nginx (Web Server)

### 6.1 Create Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/restaurant
```

Paste this:

```nginx
server {
    listen 80;
    server_name 24.199.116.165;

    client_max_body_size 10M;

    location /static/ {
        alias /var/www/restaurant/staticfiles/;
    }

    location /media/ {
        alias /var/www/restaurant/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 6.2 Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/restaurant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🏃 Step 7: Create Systemd Service (Auto-start)

### 7.1 Create Gunicorn Service
```bash
sudo nano /etc/systemd/system/restaurant.service
```

Paste this:

```ini
[Unit]
Description=Restaurant Ordering System
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/restaurant
Environment="PATH=/var/www/restaurant/venv/bin"
ExecStart=/var/www/restaurant/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 restaurant_system.wsgi:application

[Install]
WantedBy=multi-user.target
```

### 7.2 Create Daphne Service (WebSocket)
```bash
sudo nano /etc/systemd/system/restaurant-daphne.service
```

Paste this:

```ini
[Unit]
Description=Restaurant WebSocket Server
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/restaurant
Environment="PATH=/var/www/restaurant/venv/bin"
ExecStart=/var/www/restaurant/venv/bin/daphne -b 0.0.0.0 -p 8001 restaurant_system.asgi:application

[Install]
WantedBy=multi-user.target
```

### 7.3 Start Services
```bash
sudo systemctl daemon-reload
sudo systemctl start restaurant
sudo systemctl start restaurant-daphne
sudo systemctl enable restaurant
sudo systemctl enable restaurant-daphne
```

---

## 🔥 Step 8: Configure Firewall

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

---

## ✅ Step 9: Verify Installation

Check if services are running:

```bash
sudo systemctl status restaurant
sudo systemctl status restaurant-daphne
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis-server
```

All should show **"active (running)"** in green.

---

## 🎉 Step 10: Access Your Website!

Open your browser and go to:

**http://24.199.116.165**

You should see your restaurant ordering system! 🎊

### First Login:
- Go to: **http://24.199.116.165/accounts/login/**
- Use the admin credentials you created

---

## 🔧 Troubleshooting

### Problem: Can't access the website

**Solution 1**: Check if services are running
```bash
sudo systemctl status restaurant
sudo systemctl status nginx
```

**Solution 2**: Check Nginx error logs
```bash
sudo tail -f /var/log/nginx/error.log
```

**Solution 3**: Check application logs
```bash
sudo journalctl -u restaurant -f
```

### Problem: Static files (CSS/JS) not loading

**Solution**: Collect static files again
```bash
cd /var/www/restaurant
source venv/bin/activate
python manage.py collectstatic --noinput
sudo systemctl restart restaurant
```

### Problem: Database errors

**Solution**: Check PostgreSQL is running
```bash
sudo systemctl status postgresql
sudo -u postgres psql -c "\l"  # List databases
```

---

## 🔄 How to Update Your Project

When you make changes on GitHub:

```bash
cd /var/www/restaurant
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart restaurant
sudo systemctl restart restaurant-daphne
```

---

## 📱 Using a Custom Domain (Optional)

If you have a domain (like www.myrestaurant.com):

1. **Point domain to your server**:
   - Go to your domain registrar
   - Add an A record pointing to: 24.199.116.165

2. **Update settings**:
   ```bash
   nano /var/www/restaurant/.env
   ```
   Change: `ALLOWED_HOSTS=24.199.116.165,yourdomain.com`

3. **Install SSL (HTTPS)**:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com
   ```

---

## 🆘 Need Help?

### Check Logs:
```bash
# Application logs
sudo journalctl -u restaurant -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log

# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-16-main.log
```

### Restart Everything:
```bash
sudo systemctl restart restaurant
sudo systemctl restart restaurant-daphne
sudo systemctl restart nginx
sudo systemctl restart redis-server
```

---

## 📞 Important Commands Cheat Sheet

| Task | Command |
|------|---------|
| Connect to server | `ssh root@24.199.116.165` |
| Check website status | `sudo systemctl status restaurant` |
| Restart website | `sudo systemctl restart restaurant` |
| View logs | `sudo journalctl -u restaurant -f` |
| Update from GitHub | `cd /var/www/restaurant && git pull` |
| Enter Python env | `source /var/www/restaurant/venv/bin/activate` |
| Run Django commands | `cd /var/www/restaurant && python manage.py <command>` |

---

## 🎯 Success Checklist

- [ ] Connected to server successfully
- [ ] All software installed (Python, PostgreSQL, Nginx, Redis)
- [ ] Project downloaded from GitHub
- [ ] Database created and migrated
- [ ] Admin user created
- [ ] Services running (restaurant, daphne, nginx)
- [ ] Firewall configured
- [ ] Website accessible from browser
- [ ] Can login with admin credentials

---

**🎉 Congratulations!** Your restaurant ordering system is now live!

Show it to your client: **http://24.199.116.165**

---

## 📧 Support

If you encounter any issues during deployment:
1. Check the troubleshooting section above
2. Review the logs for error messages
3. Ensure all services are running
4. Verify firewall settings

**Remember**: Take it slow, read each step carefully, and don't rush! 🚀
