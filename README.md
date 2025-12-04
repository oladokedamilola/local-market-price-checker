# 🛍️ Market Price Comparison System

A web-based platform designed to help residents of Alimosho Local Government access transparent and up-to-date market prices while enabling verified vendors to manage and publish their product prices independently.

---

## 📌 Overview

Market shoppers in the Alimosho area often face difficulties in determining fair prices for essential goods due to inconsistent pricing and limited visibility into market information. This system solves that problem by:

- Allowing authenticated users to browse and compare prices of products across markets.
- Providing vendors a dedicated dashboard where they can independently list product prices.
- Ensuring full privacy and isolation so that vendors cannot access competitor pricing.
- Implementing a KYC verification process to maintain marketplace integrity.

---

## ✨ Key Features

### 🌍 For Consumers (Shoppers)
- View market product listings 🔍
- Compare prices across multiple vendors ⚖️
- Search by product and market location 📌
- Requires account login for access 🔐

### 🏪 For Vendors
- Vendor registration with KYC upload (NIN/BVN/ID)
- Admin-approved account activation
- Add/update product prices they sell
- Access only to their own listings (isolated data)
- Cannot see or copy competitors’ prices

### 👩‍💼 For Admin
- Review and verify vendor identities 🛂
- Manage users, products, and markets
- Full system monitoring and oversight

---

## 🔐 User Roles & Access Control

| Role | Price Search | Manage Own Prices | Access Competitor Data | Requires Approval |
|------|:------------:|:----------------:|:---------------------:|:----------------:|
| Consumer | ✔️ | ❌ | ❌ | ❌ |
| Vendor | Limited to own | ✔️ | ❌ | ✔️ |
| Admin | ✔️ Full | ✔️ Full | ✔️ Full | — |

📌 Only authenticated users (consumers & vendors) can access price comparison pages.

---

## 🧠 System Logic (How It Works)

1. Users register as either **Consumer** or **Vendor**
2. Vendors upload ID for verification (KYC)
3. Admin reviews and activates vendor accounts
4. Vendors list products they sell with prices and market location
5. Consumers log in and search for product prices
6. System displays **isolated** vendor data:
   - Consumers see all prices for comparison
   - Vendors see only their own listings

This ensures transparency for shoppers while protecting competitive vendor information.

---

## 🛠️ Tech Stack

| Layer | Technology |
|------|------------|
| Frontend | HTML, CSS, JavaScript, Bootstrap 5 |
| Backend | Django (Python) |
| Database | SQLite (Development), PostgreSQL (Production Option) |
| Authentication | Django Auth (Roles: Consumer, Vendor, Admin) |

---

## 🚀 Project Scope

A secure, role-based marketplace system focused on price transparency, vendor privacy, and user-friendly access to real market data within Alimosho Local Government.

---

> ✨ Future enhancements include mobile-first optimization, geolocation-based results, vendor analytics, and real-time price trends.

