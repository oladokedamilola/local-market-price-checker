# 🔎 **MarketLens — Market Price Comparison System**

**MarketLens** is a comprehensive web-based platform designed to help residents of Alimosho Local Government access transparent and up-to-date market prices while enabling verified vendors to manage and publish their product prices independently — fairly, securely, and in complete isolation.

---

## 📌 Overview

Market shoppers in the Alimosho area often face difficulties in determining fair prices for essential goods due to inconsistent pricing and limited visibility into market information. **MarketLens** solves that problem by:

* Allowing authenticated users to browse and compare prices of products across markets with real-time data
* Providing vendors a dedicated dashboard where they can independently list and manage product prices
* Ensuring complete privacy and isolation so vendors cannot access competitor pricing information
* Implementing a robust KYC verification process to maintain marketplace integrity and trust
* Delivering role-specific experiences for Consumers, Vendors, and Administrators

---

## ✨ Key Features

### 🌍 For Consumers (Shoppers)

* **Advanced Product Search** 🔍 - Search and filter products by name, category, market, and price range
* **Price Comparison** ⚖️ - Compare up to 4 products side-by-side with detailed price analysis
* **Market Explorer** 📌 - Browse products by market location across Alimosho LGA
* **Price Alerts** 🔔 - Set target prices and receive instant notifications when prices drop
* **Favorites & Vendor Following** ⭐ - Save favorite products and follow vendors for updates
* **Saved Comparisons** 📊 - Save and share product comparisons with unique links
* **Category Browsing** 🏷️ - Explore products by category with filtering options
* **Price History** 📈 - View price trends over time to make informed decisions

### 🏪 For Vendors

* **KYC Verification** ✅ - Upload NIN/BVN/ID for admin verification
* **Product Management** 📦 - Add, update, and delete product listings with image uploads
* **Bulk Operations** 🔄 - Bulk update prices and export product data to CSV
* **Private Pricing** 🔒 - Complete isolation from competitor pricing data
* **Dashboard Analytics** 📊 - Track product performance and price updates
* **Category Requests** 🆕 - Request new product categories from admin
* **Stale Product Alerts** ⏰ - Identify products not updated in 30+ days
* **Mobile-Optimized Interface** 📱 - Manage your shop on the go

### 👩‍💼 For Admin

* **Vendor Verification** 🛂 - Review and approve KYC submissions with rejection reasons
* **User Management** 👥 - Manage all consumers and vendors with profile pictures
* **Market Management** 🏪 - Create and manage markets with cover images
* **Category Management** 🏷️ - Full CRUD operations for product categories
* **Category Requests** 📨 - Review and approve vendor category requests
* **Product Oversight** 📦 - Monitor all vendor products and listings
* **System Reports** 📊 - Generate reports on platform activity and growth
* **Notification Center** 🔔 - Receive real-time alerts for vendor activities

---

## 🔐 User Roles & Access Control

| Role     | Price Search | Compare Prices | Manage Products | Follow Vendors | Access Competitor Data | KYC Required |
|----------|:------------:|:--------------:|:---------------:|:--------------:|:----------------------:|:------------:|
| Consumer |      ✔️      |       ✔️       |        ❌       |       ✔️       |           ❌           |      ❌      |
| Vendor   |      ❌      |       ❌       |        ✔️       |       ❌       |           ❌           |      ✔️      |
| Admin    |    ✔️ Full   |     ✔️ Full    |      ✔️ Full    |       ❌       |           ✔️           |      ❌      |

📌 **All users must verify their email address before accessing the platform.**

---

## 🧠 System Logic (How It Works)

1. **Registration & Verification**
   * Users register as either **Consumer** or **Vendor**
   * Email verification is mandatory for all accounts
   * Vendors proceed to KYC submission after registration

2. **Vendor Onboarding**
   * Vendors upload identification documents (NIN/BVN/ID)
   * Admin reviews and verifies vendor identity
   * Verified vendors gain access to vendor dashboard

3. **Product Management**
   * Vendors add products with prices, categories, and images
   * Products are automatically visible to consumers
   * Vendors can update prices in real-time
   * Followers get notifications when vendors add/update products

4. **Consumer Experience**
   * Consumers log in and search for products
   * Filter by market, category, or price range
   * Compare products side-by-side
   * Set price alerts for favorite items
   * Follow vendors to get updates on new products

5. **Data Isolation**
   * Consumers see all verified vendor prices
   * Vendors see ONLY their own listings
   * Complete competitor privacy protection

---

## 📱 Core Features in Detail

### 🔍 Smart Search & Filtering
- Full-text search across product names and descriptions
- Filter by market location, category, and price range
- Sort by price (low to high / high to low), newest, or recently updated
- Real-time result counts and pagination (12 per page)

### ⚖️ Price Comparison Tool
- Select up to 4 products for comparison
- Side-by-side view of prices, vendors, and markets
- Highlighted best price with savings calculation
- Save comparisons for later or share via unique links
- Public shareable links (no login required)

### 🔔 Notification System
- **Real-time in-app notifications** for all user roles
- **Email notifications** for critical events:
  * Admin: New vendor registrations and KYC submissions
  * Vendor: KYC approval/rejection, category request decisions
  * Consumer: Price alerts, favorite product updates, vendor activity
- Customizable notification preferences
- Unread count badges and notification center

### 👥 Vendor Following
- Consumers can follow/unfollow vendors with one click
- Followers receive notifications when vendors:
  * Add new products
  * Update product prices
- One-way relationship (vendors don't know they're being followed)

### 🏪 Market Management
- Admin-created markets with cover images
- Market details including location, hours, and contact info
- Product listings grouped by market
- Popular products and vendor counts per market

### 📊 Vendor Analytics
- Dashboard with product statistics
- Price update tracking and history
- Products grouped by market and category
- Bulk price update tools
- Product export functionality (CSV)

### 🛡️ Security Features
- Email verification required for all accounts
- KYC verification for vendors
- Rate limiting on sensitive actions
- Session management with "Remember Me" option
- CSRF protection and secure cookies
- Password strength validation

---

## 🛠️ Tech Stack

| Layer          | Technology                                           |
| -------------- | ---------------------------------------------------- |
| **Frontend**   | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5, Bootstrap Icons, jQuery |
| **Backend**    | Django 6.0 (Python 3.12)                             |
| **Database**   | SQLite (Development), PostgreSQL (Production)        |
| **Authentication** | Django Auth, django-allauth (Google OAuth), Custom Email Auth |
| **Email**      | SMTP (Gmail), Custom email templates                  |
| **Storage**    | Django File Storage (Local/Cloud)                    |
| **Security**   | Rate limiting, Session management, CSRF protection   |
| **PWA**        | Progressive Web App capabilities for mobile devices  |

---

## 📊 Database Models

### Core Models
- **User** - Extended Django user model with profile pictures
- **Profile** - Common profile data for all users
- **ConsumerProfile** - Shopper-specific data
- **VendorProfile** - Vendor data with verification status
- **Market** - Market locations with details and cover images
- **Category** - Product categories with icons
- **Product** - Base product definitions with single image

### Vendor Models
- **VendorProduct** - Vendor-specific product listings with prices
- **VendorKYC** - KYC documents and verification status with rejection reasons
- **CategoryRequest** - Vendor requests for new categories

### Consumer Models
- **PriceAlert** - User-set price alerts with frequency options
- **FavoriteProduct** - Saved favorite products with notes
- **FavoriteVendor** - Saved favorite vendors (following)
- **Comparison** - Saved product comparisons with shareable UUIDs

### Notification Models
- **Notification** - In-app notifications for all users
- **NotificationPreference** - User notification preferences
- **EmailVerification** - Email verification tokens
- **PasswordReset** - Password reset tokens
- **RateLimit** - Rate limiting for security

---

## 🎨 Design System

### Color Palette
- **Primary (#1E2A38)** - Deep navy for trust and professionalism
- **Accent (#4DA8DA)** - Bright blue for clarity and information
- **Success (#2ECC71)** - Fresh green for positive actions
- **Warning (#F4A261)** - Warm amber for pending states
- **Danger (#E63946)** - Coral red for errors and alerts
- **Background (#F5F7FA)** - Light gray for clean interfaces

### Typography
- **Inter** - Primary font family
- Clean, modern, and highly readable
- Responsive font sizing for all devices

### UI Components
- Card-based layouts for products and markets
- Responsive tables for data display
- Toast notifications for user feedback
- Loading spinners for async operations
- Modal dialogs for confirmations
- Breadcrumb navigation
- Image preview modals with crop/confirm options

---

## 🔒 Security Implementation

### Authentication & Authorization
- Email verification required before login
- Role-based access control (Consumer/Vendor/Admin)
- Custom email authentication backend
- Google OAuth integration
- Session management with configurable expiry

### Rate Limiting
- Login attempts: 3 per hour
- Registration attempts: 3 per hour
- Password reset requests: 3 per hour
- Email verification requests: 3 per hour
- 1-hour block after exceeding limits

### Data Protection
- Password hashing with Django's default PBKDF2
- CSRF protection on all forms
- XSS protection via Django templates
- Secure session cookies (HTTPOnly, SameSite)
- HTTPS enforcement in production

---

## 📱 Progressive Web App (PWA)

MarketLens is PWA-enabled for mobile devices:

- **Installable** - Add to home screen on mobile devices
- **Smart Prompt** - Shows install prompt only on mobile/tablet
- **Fast Loading** - Optimized assets and caching
- **App-like Experience** - Full-screen mode, splash screen
- **Offline Support** - Basic functionality works offline

---

## 📧 Email Templates

The system includes professional email templates for:

- **Account Verification** - Welcome emails with verification links
- **Password Reset** - Secure password reset instructions
- **KYC Status** - Vendor KYC approval/rejection notifications
- **Price Alerts** - Price drop notifications with savings details
- **Category Requests** - Category approval/rejection updates
- **Welcome Emails** - Role-specific welcome messages
- **Vendor Activity** - Notifications for followers when vendors update products

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- pip (Python package manager)
- Git (optional)

### Quick Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/marketlens.git
cd marketlens

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Load initial data
python manage.py loaddata fixtures/categories.json
python manage.py loaddata fixtures/markets.json

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Environment Variables
```env
# Django Settings
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Email Settings
DJANGO_EMAIL_HOST_USER=your-email@gmail.com
DJANGO_EMAIL_HOST_PASSWORD=your-app-password

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Site URL
SITE_URL=http://127.0.0.1:8000
```

---

## 📁 Project Structure

```
market_prices/
├── accounts/           # User accounts, profiles, authentication
│   ├── views/          # Auth, admin, vendor, consumer views
│   ├── models.py       # User profiles, KYC, favorites
│   └── forms.py        # Registration, KYC, password forms
├── core/               # Core functionality
│   ├── views.py        # Home, search, product detail, comparisons
│   ├── urls.py         # Consumer-facing URLs
│   └── models.py       # Comparison model
├── market/             # Market data
│   ├── models.py       # Category, Market, Product models
│   └── forms.py        # Market and category forms
├── vendor/             # Vendor-specific logic
│   ├── views.py        # Product management, analytics
│   ├── models.py       # VendorProduct, VendorKYC
│   └── forms.py        # Product forms, category requests
├── notifications/      # Notification system
│   ├── services.py     # Notification service
│   ├── models.py       # Notification models
│   └── context_processors.py # Unread count
├── static/             # CSS, JavaScript, images
│   ├── css/
│   └── images/
├── templates/          # HTML templates
│   ├── accounts/       # Login, registration, profile
│   ├── core/           # Home, search, product detail
│   ├── dashboards/     # Consumer, vendor, admin dashboards
│   │   ├── consumer/   # Consumer-specific templates
│   │   ├── vendor/     # Vendor-specific templates
│   │   └── admin/      # Admin management templates
│   └── notifications/  # Email templates
├── media/              # User-uploaded files
├── fixtures/           # Initial data (categories, markets)
└── market_prices/      # Project settings, URLs, WSGI
```

---

## 🔄 Key Workflows

### Vendor Registration Flow
1. Register with email → Verify email → Submit KYC → Admin approval → Access vendor dashboard

### Product Listing Flow
1. Add product with name, category, unit → Market auto-filled from KYC → Upload image → Set price → Publish

### Price Alert Flow
1. Browse products → Set target price → System monitors (management command) → Price drops → Instant notification

### Category Request Flow
1. Request category → Admin notified → Admin approves/rejects → Vendor notified → Category available

### Vendor Following Flow
1. Consumer views vendor → Clicks "Follow" → FavoriteVendor record created → Vendor adds product → Follower notified

### Comparison Flow
1. Select up to 4 products → Compare side-by-side → Save comparison → Get shareable link → Share publicly

---

## 📈 Future Enhancements

- **Geolocation-based results** - Find products near your location
- **Real-time price trends** - Advanced analytics and forecasting
- **Mobile app** - Native mobile applications
- **Multi-language support** - Yoruba, Hausa, Igbo languages
- **Payment integration** - In-app payments and transactions
- **Vendor ratings & reviews** - Community feedback system
- **Bulk product import** - CSV/Excel upload for vendors
- **API access** - Public API for third-party integrations
- **WhatsApp notifications** - Alternative notification channel

---

## 📄 License

Copyright © 2026 MarketLens. All rights reserved.

---

> ✨ **MarketLens** - Bringing transparency to every market in Alimosho, one price at a time.
```