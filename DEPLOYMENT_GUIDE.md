# NHGCC Oshodi Church Database — Production Deployment Guide

This guide walks you step-by-step through deploying the **NHGCC Oshodi Church Management System** to production with a shared cloud database so that all church workers, laptops, tablets, and mobile phones access the exact same live data in real time.

---

## 📋 Table of Contents
1. [Why the Offline Desktop Version Didn't Sync](#1-why-the-offline-desktop-version-didn-t-sync)
2. [Architecture Overview](#2-architecture-overview)
3. [Step 1: Set Up a Free Cloud Database (PostgreSQL)](#step-1-set-up-a-free-cloud-database-postgresql)
4. [Step 2: Migrate All Existing Church Data](#step-2-migrate-all-existing-church-data)
5. [Step 3: Deploy the Application to Production](#step-3-deploy-the-application-to-production)
   - [Option A: Deploy to Render.com (Recommended for Free 24/7 Scheduling)](#option-a-deploy-to-rendercom-recommended)
   - [Option B: Deploy to Vercel (Ultra-fast Serverless)](#option-b-deploy-to-vercel)
6. [Step 4: Configure Email Notifications (SMTP)](#step-4-configure-email-notifications-smtp)
7. [Step 5: Verifying Multi-Device Access](#step-5-verifying-multi-device-access)

---

## 1. Why the Offline Desktop Version Didn't Sync
The original desktop executable stored church records in a local SQLite file on each individual machine at:
`%LOCALAPPDATA%\NHGCC_Church_Database\nhgcc_church.db`

When the app folder or executable was copied to another computer, each computer had its own separate, isolated database file. If an usher checked in members on Computer A, Computer B knew nothing about it.

By connecting the application to a cloud PostgreSQL database, **every device reads and writes to one single central database**.

---

## 2. Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │        NHGCC Church Workers            │
                      │  (Laptops, Tablets, Entrance Desks)    │
                      └──────────────────┬─────────────────────┘
                                         │ HTTPS Web Traffic
                                         ▼
                      ┌────────────────────────────────────────┐
                      │        Cloud Hosting Platform          │
                      │     (Render.com / Vercel.com)          │
                      │   - Flask Web App                      │
                      │   - Check-in Desk, Search, Excel       │
                      │   - Background Retention Schedulers    │
                      └──────────────────┬─────────────────────┘
                                         │ Secure SSL Connection
                                         ▼
                      ┌────────────────────────────────────────┐
                      │    Managed Cloud PostgreSQL Database   │
                      │          (Neon.tech / Supabase)        │
                      │   - 298 Registered Members             │
                      │   - Sunday Attendance Records          │
                      │   - Pastoral Follow-Up Logs            │
                      │   - System Configuration Settings      │
                      └────────────────────────────────────────┘
```

---

## Step 1: Set Up a Free Cloud Database (PostgreSQL)

We recommend **Neon.tech** or **Supabase** because they provide free, high-performance managed PostgreSQL databases with SSL enabled by default.

### Recommended: Neon.tech (100% Free Forever)
1. Go to [https://neon.tech](https://neon.tech) and sign up (with Google or GitHub).
2. Click **Create Project**.
3. Name your project: `nhgcc-church-database`.
4. Leave the default region and PostgreSQL version, then click **Create Project**.
5. You will immediately see your **Connection Details**.
6. Copy the connection string. It will look like:
   ```text
   postgresql://nhgcc_db_owner:abcdef123456@ep-cool-sample-a27z6u9c.us-east-2.aws.neon.tech/nhgcc_db?sslmode=require
   ```

---

## Step 2: Migrate All Existing Church Data

We have built a dedicated 1-click migration script (`migrate_to_postgres.py`) that transfers all 298 registered members, 144 attendance logs, and settings from your local SQLite database directly into your new PostgreSQL cloud database.

1. Open PowerShell or Command Prompt in the project folder:
   ```powershell
   cd c:\Users\Home\Documents\NHGCC_Church_Database
   ```

2. Run the migration script with your PostgreSQL connection string:
   ```powershell
   python migrate_to_postgres.py "YOUR_NEON_POSTGRES_CONNECTION_STRING"
   ```

3. The script will:
   - Connect to `nhgcc_church.db`.
   - Initialize the tables on your cloud database.
   - Batch insert all members, attendance, follow-ups, and settings.
   - Reset ID sequence counters.
   - Print a verification summary confirming all rows are live in the cloud.

---

## Step 3: Deploy the Application to Production

### Option A: Deploy to Render.com (Recommended)
Render is recommended because it runs a continuous web service with Gunicorn, allowing the built-in APScheduler to execute background checks (daily birthday alerts and weekly absentee digests) 24/7.

1. Push your project code to GitHub or GitLab:
   ```powershell
   git init
   git add .
   git commit -m "Initial production release of NHGCC Church Database"
   git remote add origin https://github.com/your-username/nhgcc-church-database.git
   git push -u origin main
   ```

2. Go to [https://render.com](https://render.com) and create an account.
3. Click **New +** -> **Web Service**.
4. Connect your GitHub repository.
5. Configure the service:
   - **Name**: `nhgcc-church-database`
   - **Region**: Choose closest to Nigeria / West Africa (e.g., Frankfurt / Europe)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app`
   - **Instance Type**: `Free`
6. Under **Environment Variables**, add:
   - `DATABASE_URL`: *(Your Neon PostgreSQL connection string)*
   - `SECRET_KEY`: *(Any long random string, e.g. `nhgcc-oshodi-secret-2026`)*
   - `CHURCH_NAME`: `National Holy Ghost Church of Christ`
   - `CHURCH_BRANCH`: `Oshodi Parish, Lagos`
   - `CHURCH_EMAIL`: `nhgccoshodi@gmail.com`
7. Click **Deploy Web Service**.
8. Within 2-3 minutes, Render will provide a live HTTPS URL (e.g., `https://nhgcc-church-database.onrender.com`).

---

### Option B: Deploy to Vercel (Ultra-fast Serverless)

If you prefer Vercel:

1. Install the Vercel CLI (or connect via GitHub on [vercel.com](https://vercel.com)):
   ```powershell
   npm install -g vercel
   vercel
   ```
2. During setup:
   - Set project name to `nhgcc-church-database`.
   - Accept default settings (`vercel.json` and `api/index.py` are preconfigured).
3. In the Vercel Dashboard under **Project Settings > Environment Variables**, add:
   - `DATABASE_URL`: *(Your Neon PostgreSQL connection string)*
   - `SECRET_KEY`: *(Any random secret string)*
4. Redeploy to apply environment variables:
   ```powershell
   vercel --prod
   ```

---

## Step 4: Configure Email Notifications (SMTP)

Once the application is live:
1. Log in to the web dashboard and navigate to **Settings** (`/settings`).
2. Enter your church Gmail address and a **Google App Password**:
   - **SMTP Server**: `smtp.gmail.com`
   - **SMTP Port**: `587`
   - **Use TLS**: `True`
   - **SMTP Username**: `nhgccoshodi@gmail.com`
   - **SMTP Password**: *(Your 16-character Google App Password)*
   - **Default Sender**: `NHGCC Oshodi Secretariat <nhgccoshodi@gmail.com>`
3. Click **Save Settings**.
4. Use the **Test Email** feature on the settings page to verify delivery.

---

## Step 5: Verifying Multi-Device Access

Once deployed:
1. Open the live URL on your computer: `https://your-app.onrender.com/attendance/checkin`.
2. Open the same URL on a smartphone or tablet connected to mobile data or Wi-Fi.
3. Check in a member on the tablet.
4. Refresh the computer screen — the member's status will instantly reflect as **Present** with the exact check-in time stamp!
5. All updates are synchronized globally.
