#!/bin/bash

# 🔧 Restaurant System - Health Check & Troubleshooting Script
# Run this script to diagnose issues with your deployment

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🏥 Restaurant System Health Check 🏥                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Please run as root: sudo ./health-check.sh${NC}"
    exit 1
fi

# Function to check service
check_service() {
    local service=$1
    local name=$2
    
    if systemctl is-active --quiet $service; then
        echo -e "${GREEN}✓ $name is running${NC}"
        return 0
    else
        echo -e "${RED}✗ $name is NOT running${NC}"
        echo -e "  ${YELLOW}Fix: sudo systemctl start $service${NC}"
        return 1
    fi
}

# Function to check port
check_port() {
    local port=$1
    local name=$2
    
    if netstat -tuln | grep -q ":$port "; then
        echo -e "${GREEN}✓ $name (port $port) is listening${NC}"
        return 0
    else
        echo -e "${RED}✗ $name (port $port) is NOT listening${NC}"
        return 1
    fi
}

# Function to check file
check_file() {
    local file=$1
    local name=$2
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ $name exists${NC}"
        return 0
    else
        echo -e "${RED}✗ $name does NOT exist${NC}"
        return 1
    fi
}

# Function to check directory
check_directory() {
    local dir=$1
    local name=$2
    
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓ $name exists${NC}"
        return 0
    else
        echo -e "${RED}✗ $name does NOT exist${NC}"
        return 1
    fi
}

echo -e "${BLUE}[1/8] Checking System Services...${NC}"
check_service restaurant "Restaurant Application"
check_service restaurant-daphne "WebSocket Server (Daphne)"
check_service nginx "Nginx Web Server"
check_service postgresql "PostgreSQL Database"
check_service redis-server "Redis Cache"
echo ""

echo -e "${BLUE}[2/8] Checking Network Ports...${NC}"
apt-get install -y net-tools >/dev/null 2>&1
check_port 80 "HTTP (Nginx)"
check_port 8000 "Gunicorn"
check_port 8001 "Daphne"
check_port 5432 "PostgreSQL"
check_port 6379 "Redis"
echo ""

echo -e "${BLUE}[3/8] Checking Project Files...${NC}"
check_directory "/var/www/restaurant" "Project Directory"
check_file "/var/www/restaurant/manage.py" "Django manage.py"
check_file "/var/www/restaurant/.env" "Environment File"
check_directory "/var/www/restaurant/venv" "Virtual Environment"
check_directory "/var/www/restaurant/staticfiles" "Static Files"
check_directory "/var/www/restaurant/media" "Media Files"
echo ""

echo -e "${BLUE}[4/8] Checking Nginx Configuration...${NC}"
if nginx -t 2>&1 | grep -q "successful"; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo -e "${RED}✗ Nginx configuration has errors${NC}"
    nginx -t
fi
echo ""

echo -e "${BLUE}[5/8] Checking Database Connection...${NC}"
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw restaurant_db; then
    echo -e "${GREEN}✓ Database 'restaurant_db' exists${NC}"
else
    echo -e "${RED}✗ Database 'restaurant_db' does NOT exist${NC}"
    echo -e "  ${YELLOW}Fix: Run deployment script again${NC}"
fi
echo ""

echo -e "${BLUE}[6/8] Checking Disk Space...${NC}"
disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $disk_usage -lt 80 ]; then
    echo -e "${GREEN}✓ Disk space: ${disk_usage}% used (OK)${NC}"
else
    echo -e "${YELLOW}⚠ Disk space: ${disk_usage}% used (Getting full!)${NC}"
fi
echo ""

echo -e "${BLUE}[7/8] Checking Memory Usage...${NC}"
mem_usage=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
if [ $mem_usage -lt 90 ]; then
    echo -e "${GREEN}✓ Memory usage: ${mem_usage}% (OK)${NC}"
else
    echo -e "${YELLOW}⚠ Memory usage: ${mem_usage}% (High!)${NC}"
fi
echo ""

echo -e "${BLUE}[8/8] Checking Recent Logs...${NC}"
echo -e "${YELLOW}Last 5 application errors:${NC}"
journalctl -u restaurant --since "1 hour ago" -p err -n 5 --no-pager || echo "No recent errors"
echo ""

# Summary
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    📊 Summary                            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"

# Count issues
issues=0

# Check services
for service in restaurant restaurant-daphne nginx postgresql redis-server; do
    if ! systemctl is-active --quiet $service; then
        ((issues++))
    fi
done

if [ $issues -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! System is healthy! 🎉${NC}"
else
    echo -e "${RED}✗ Found $issues issue(s). See above for fixes.${NC}"
fi

echo ""
echo -e "${BLUE}🔧 Common Fixes:${NC}"
echo ""
echo "1. Restart all services:"
echo -e "   ${YELLOW}sudo systemctl restart restaurant restaurant-daphne nginx${NC}"
echo ""
echo "2. Check detailed logs:"
echo -e "   ${YELLOW}sudo journalctl -u restaurant -f${NC}"
echo ""
echo "3. Test website:"
echo -e "   ${YELLOW}curl -I http://localhost${NC}"
echo ""
echo "4. Update from GitHub:"
echo -e "   ${YELLOW}cd /var/www/restaurant && git pull && sudo systemctl restart restaurant${NC}"
echo ""
echo "5. Collect static files:"
echo -e "   ${YELLOW}cd /var/www/restaurant && source venv/bin/activate && python manage.py collectstatic --noinput${NC}"
echo ""

# Offer to restart services
if [ $issues -gt 0 ]; then
    read -p "Do you want to restart all services now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Restarting services...${NC}"
        systemctl restart restaurant
        systemctl restart restaurant-daphne
        systemctl restart nginx
        echo -e "${GREEN}✓ Services restarted!${NC}"
        echo "Wait 10 seconds and try accessing your website again."
    fi
fi

echo ""
echo -e "${BLUE}For more help, check: DEPLOYMENT_GUIDE.md${NC}"
