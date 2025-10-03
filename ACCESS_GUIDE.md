# Restaurant System Access Guide

## How to Access the System

### 🌐 **System URLs**
- **Main Site**: http://127.0.0.1:8000/ or http://localhost:8000/
- **Login Page**: http://127.0.0.1:8000/accounts/login/
- **Admin Panel**: http://127.0.0.1:8000/admin-panel/

---

## 👥 **User Role Access**

### 🔑 **Login Process**
1. Visit the main site (http://localhost:8000/)
2. You'll be redirected to the login page
3. Enter your username and password
4. After login, you'll be automatically redirected to your role-specific dashboard

---

### 👨‍💼 **Administrator**
- **Login Redirect**: Admin Panel Dashboard
- **Access**: Full system control
- **URL**: `/admin-panel/`
- **Permissions**: 
  - Manage all users and roles
  - Full CRUD on products, categories, tables, orders
  - View all system statistics

### 👑 **Owner**
- **Login Redirect**: Admin Panel Dashboard (same as admin but with restrictions)
- **Access**: Restaurant management with limited user management
- **URL**: `/admin-panel/`
- **Permissions**: 
  - Manage products, categories, tables, orders
  - Create/manage Kitchen Staff and Customer Care only
  - Cannot manage administrators or other owners

### 👨‍🍳 **Kitchen Staff**
- **Login Redirect**: Kitchen Dashboard
- **Access**: Order management and kitchen operations
- **URL**: `/orders/kitchen/`
- **Permissions**: 
  - View pending orders
  - Update order status (confirmed → preparing → ready → served)
  - Manage cooking workflow

### 👥 **Customer Care**
- **Login Redirect**: Customer Care Dashboard  
- **Access**: Customer service and order support
- **URL**: `/orders/customer-care/`
- **Permissions**: 
  - View customer orders
  - Handle customer inquiries
  - Assist with order issues

### 🛒 **Customer**
- **Login Redirect**: Restaurant Menu
- **Access**: Browse menu and place orders
- **URL**: `/restaurant/menu/`
- **Permissions**: 
  - Browse restaurant menu
  - Place orders
  - View order history

---

## 🚀 **Quick Start for Different Roles**

### For Kitchen Staff:
1. Go to http://localhost:8000/
2. Login with your kitchen staff credentials
3. You'll see the Kitchen Dashboard with pending orders
4. Update order statuses as you cook

### For Customer Care:
1. Go to http://localhost:8000/
2. Login with your customer care credentials  
3. Access the Customer Care Dashboard
4. Help customers with their orders and inquiries

### For Owners/Administrators:
1. Go to http://localhost:8000/
2. Login with your credentials
3. Access the comprehensive Admin Panel
4. Manage all restaurant operations

---

## 🔐 **Security Notes**

- All areas require login authentication
- Role-based access control enforces proper permissions
- Users can only access features appropriate to their role
- Admin panel has additional security for sensitive operations

---

## 🆘 **Troubleshooting**

### "Page not found (404)" Error:
- **Solution**: The root URL now properly redirects to login
- Make sure to use http://localhost:8000/ or http://127.0.0.1:8000/

### "Access Denied" Messages:
- **Solution**: Check that you're logged in with the correct role
- Kitchen staff should access kitchen dashboard
- Customer care should access customer care dashboard
- Contact administrator if role assignment is incorrect

### Can't Access Admin Panel:
- **Solution**: Only administrators and owners can access `/admin-panel/`
- Kitchen staff and customer care have their own dedicated dashboards