# 📝 Command Cheat Sheet

Quick reference for managing your deployed Restaurant Ordering System.

---

## 🔌 Connecting to Server

```bash
# Connect via SSH
ssh root@24.199.116.165

# If using a domain
ssh root@yourdomain.com

# Exit SSH session
exit
```

---

## 🔄 Service Management

```bash
# Check service status
sudo systemctl status restaurant
sudo systemctl status restaurant-daphne
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis-server

# Start a service
sudo systemctl start restaurant

# Stop a service
sudo systemctl stop restaurant

# Restart a service
sudo systemctl restart restaurant

# Restart all services
sudo systemctl restart restaurant restaurant-daphne nginx

# Enable service to start on boot
sudo systemctl enable restaurant

# View service logs
sudo journalctl -u restaurant -f
```

---

## 📊 Checking Logs

```bash
# Application logs (real-time)
sudo journalctl -u restaurant -f

# Last 100 lines
sudo journalctl -u restaurant -n 100

# Errors only
sudo journalctl -u restaurant -p err

# Nginx error log
sudo tail -f /var/log/nginx/restaurant_error.log

# Nginx access log
sudo tail -f /var/log/nginx/restaurant_access.log

# Gunicorn logs
sudo tail -f /var/log/gunicorn/error.log
```

---

## 🗄️ Database Commands

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Connect to specific database
sudo -u postgres psql restaurant_db

# List databases
sudo -u postgres psql -c "\l"

# List tables in database
sudo -u postgres psql restaurant_db -c "\dt"

# Backup database
sudo -u postgres pg_dump restaurant_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore database
sudo -u postgres psql restaurant_db < backup_20241003_120000.sql

# Check database size
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('restaurant_db'));"
```

---

## 🔄 Updating from GitHub

```bash
# Navigate to project
cd /var/www/restaurant

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install new packages (if requirements changed)
pip install -r requirements.txt

# Run migrations
export DJANGO_SETTINGS_MODULE=restaurant_system.production_settings
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart application
sudo systemctl restart restaurant restaurant-daphne

# Deactivate virtual environment
deactivate
```

---

## 🛠️ Django Management Commands

```bash
# Navigate to project
cd /var/www/restaurant
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=restaurant_system.production_settings

# Create superuser
python manage.py createsuperuser

# Run migrations
python manage.py migrate

# Make migrations (after model changes)
python manage.py makemigrations

# Collect static files
python manage.py collectstatic

# Open Django shell
python manage.py shell

# Check for system issues
python manage.py check

# Clear sessions
python manage.py clearsessions

# Create new app
python manage.py startapp appname
```

---

## 🔥 Firewall Commands

```bash
# Check firewall status
sudo ufw status

# Allow port
sudo ufw allow 80/tcp

# Allow specific IP
sudo ufw allow from 192.168.1.100

# Deny port
sudo ufw deny 8080/tcp

# Enable firewall
sudo ufw enable

# Disable firewall
sudo ufw disable

# Show firewall rules
sudo ufw status numbered

# Delete rule
sudo ufw delete 3
```

---

## 🌐 Nginx Commands

```bash
# Test configuration
sudo nginx -t

# Reload configuration
sudo nginx -s reload

# Restart Nginx
sudo systemctl restart nginx

# Stop Nginx
sudo systemctl stop nginx

# View configuration
sudo nano /etc/nginx/sites-available/restaurant

# Check which sites are enabled
ls -la /etc/nginx/sites-enabled/
```

---

## 💾 Backup Commands

```bash
# Backup database
sudo -u postgres pg_dump restaurant_db | gzip > /tmp/db_backup_$(date +%Y%m%d).sql.gz

# Backup media files
tar -czf /tmp/media_backup_$(date +%Y%m%d).tar.gz /var/www/restaurant/media/

# Backup entire project
tar -czf /tmp/project_backup_$(date +%Y%m%d).tar.gz /var/www/restaurant/

# Download backup to local machine (from local computer)
scp root@24.199.116.165:/tmp/db_backup_*.sql.gz ~/Downloads/
```

---

## 📁 File Management

```bash
# List files
ls -la /var/www/restaurant/

# View file content
cat /var/www/restaurant/.env

# Edit file
nano /var/www/restaurant/.env

# Copy file
cp /var/www/restaurant/.env /var/www/restaurant/.env.backup

# Delete file
rm /var/www/restaurant/somefile.txt

# Create directory
mkdir -p /var/www/restaurant/newdir

# Change permissions
sudo chown -R www-data:www-data /var/www/restaurant/
sudo chmod -R 755 /var/www/restaurant/

# Check disk space
df -h

# Check directory size
du -sh /var/www/restaurant/
```

---

## 🔍 Monitoring Commands

```bash
# Check CPU and memory usage
top

# Check running processes
ps aux | grep python

# Check open ports
sudo netstat -tulpn

# Check disk I/O
sudo iotop

# Check system resources
htop  # (may need to install: sudo apt install htop)

# Check who's logged in
who

# Check system uptime
uptime

# Check free memory
free -h
```

---

## 🛑 Emergency Commands

```bash
# Kill stuck process
sudo pkill -f gunicorn
sudo systemctl start restaurant

# Restart server (LAST RESORT!)
sudo reboot

# Check if website responds
curl -I http://localhost

# Test internal connections
curl http://127.0.0.1:8000

# Check if port is in use
sudo lsof -i :8000
```

---

## 🔐 Security Commands

```bash
# Change password for user
passwd username

# List users
cat /etc/passwd | grep /bin/bash

# Check failed login attempts
sudo grep "Failed password" /var/log/auth.log

# Check last logins
last

# Update system
sudo apt update && sudo apt upgrade -y

# Install security updates
sudo apt install unattended-upgrades
```

---

## 🧹 Cleanup Commands

```bash
# Clear apt cache
sudo apt clean
sudo apt autoclean
sudo apt autoremove

# Clear logs older than 3 days
sudo journalctl --vacuum-time=3d

# Clear old systemd journal
sudo journalctl --vacuum-size=100M

# Find large files
find /var/www/restaurant -type f -size +100M

# Remove Python cache
find /var/www/restaurant -type d -name __pycache__ -exec rm -r {} +
find /var/www/restaurant -type f -name "*.pyc" -delete
```

---

## 🎯 Quick Troubleshooting

```bash
# Website not loading
sudo systemctl restart restaurant nginx
curl -I http://localhost

# Database issues
sudo systemctl status postgresql
sudo -u postgres psql restaurant_db -c "SELECT 1;"

# Static files not loading
cd /var/www/restaurant && source venv/bin/activate
python manage.py collectstatic --noinput
sudo systemctl restart restaurant

# WebSocket not working
sudo systemctl restart restaurant-daphne
sudo journalctl -u restaurant-daphne -n 50

# Permission errors
sudo chown -R www-data:www-data /var/www/restaurant
sudo systemctl restart restaurant

# Memory issues
free -h
sudo systemctl restart restaurant
```

---

## 📦 Package Management

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install package
sudo apt install package-name

# Remove package
sudo apt remove package-name

# Search for package
apt search package-name

# List installed packages
dpkg -l

# Python packages (in virtual environment)
cd /var/www/restaurant && source venv/bin/activate
pip list
pip install package-name
pip uninstall package-name
pip freeze > requirements.txt
```

---

## 🔧 Environment Variables

```bash
# View environment file
cat /var/www/restaurant/.env

# Edit environment file
sudo nano /var/www/restaurant/.env

# After changing .env, restart services
sudo systemctl restart restaurant restaurant-daphne
```

---

## 📞 Health Check

```bash
# Run health check script
cd /var/www/restaurant
sudo ./health-check.sh

# Or manually check everything
sudo systemctl status restaurant restaurant-daphne nginx postgresql redis-server
curl -I http://localhost
sudo journalctl -u restaurant -n 20
```

---

## 💡 Tips

1. **Always activate virtual environment** before running Django commands:
   ```bash
   cd /var/www/restaurant && source venv/bin/activate
   ```

2. **Set Django settings** for production:
   ```bash
   export DJANGO_SETTINGS_MODULE=restaurant_system.production_settings
   ```

3. **Restart services** after changes:
   ```bash
   sudo systemctl restart restaurant restaurant-daphne
   ```

4. **Check logs** when something doesn't work:
   ```bash
   sudo journalctl -u restaurant -f
   ```

5. **Backup regularly**:
   ```bash
   sudo -u postgres pg_dump restaurant_db > backup.sql
   ```

---

## 🆘 Get Help

If stuck, check:
1. Application logs: `sudo journalctl -u restaurant -f`
2. Nginx logs: `sudo tail -f /var/log/nginx/restaurant_error.log`
3. Service status: `sudo systemctl status restaurant`
4. Full guides in `DEPLOYMENT_GUIDE.md`

---

## ⚡ One-Liners

```bash
# Complete restart
sudo systemctl restart restaurant restaurant-daphne nginx && echo "✓ All services restarted"

# Quick update
cd /var/www/restaurant && git pull && sudo systemctl restart restaurant && echo "✓ Updated"

# View recent errors
sudo journalctl -u restaurant --since "1 hour ago" -p err

# Check if website is accessible
curl -I http://localhost && echo "✓ Website is up"

# Quick backup
sudo -u postgres pg_dump restaurant_db | gzip > ~/backup_$(date +%Y%m%d_%H%M%S).sql.gz && echo "✓ Backup created"
```

---

**📌 Bookmark this page for quick reference!**
