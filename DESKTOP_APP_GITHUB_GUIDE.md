# NHGCC Oshodi Church Database — Desktop App Distribution & Cloud Sync Guide

This guide explains how to package the **NHGCC Oshodi Church Management System** as an installable **Windows Desktop Application**, distribute it to church workers via **GitHub Releases**, and ensure that **all laptops and devices stay connected to the exact same live church database without getting disconnected**.

---

## 💡 The Core Problem & The Solution

```mermaid
flowchart TD
    subgraph Old["❌ Previous Setup (Why it disconnected)"]
        LaptopA1["Laptop A (Entrance Desk)"] --> DB1[("Isolated Local SQLite A<br>(%LOCALAPPDATA%)")]
        LaptopB1["Laptop B (Office)"] --> DB2[("Isolated Local SQLite B<br>(%LOCALAPPDATA%)")]
        DB1 -.->|No Sync! Changes on Laptop A are invisible on Laptop B| DB2
    end

    subgraph New["✅ Connected Desktop App Setup (How it works now)"]
        GH["GitHub Repository<br>(Releases / Downloads)"] -->|1-Click Download| AppA["Laptop A<br>(Desktop App .exe)"]
        GH -->|1-Click Download| AppB["Laptop B<br>(Desktop App .exe)"]
        GH -->|1-Click Download| AppC["Pastor's PC<br>(Desktop App .exe)"]
        
        AppA -->|Secure Internet Connection| CentralDB[("⛪ Shared Central Cloud Database<br>(Neon.tech / Supabase PostgreSQL)<br>298 Members • Live Sunday Attendance")]
        AppB -->|Secure Internet Connection| CentralDB
        AppC -->|Secure Internet Connection| CentralDB
    end
```

### Why it disconnected previously
The old standalone `.exe` created an isolated SQLite file on each computer (`%LOCALAPPDATA%\NHGCC_Church_Database\nhgcc_church.db`). Changes made on one computer stayed locked on that computer's hard drive.

### How it stays connected now
1. **The App is a Desktop Application**: Church workers install and run a desktop app with an official desktop icon and Start menu shortcut.
2. **The Database is Centralized**: Instead of each PC writing to its own local file, all installed desktop apps connect to your **Central Cloud Database (PostgreSQL)** over the internet.
3. **Real-time Synchronization**: When an usher checks in an attendee on Laptop A, Laptop B instantly reflects that person as **Present** with their check-in timestamp.
4. **Distribution & Updates via GitHub**: You host the app code on GitHub, and GitHub Actions automatically builds the `.exe` installer whenever you publish updates.

---

## 🚀 Step 1: Create Your Free Central Cloud Database

We use **Neon.tech** because it is a managed PostgreSQL database that is 100% free forever and provides instant, secure SSL connections.

1. Go to [https://neon.tech](https://neon.tech) and sign up with Google or GitHub.
2. Click **Create Project**, name it `nhgcc-church-database`.
3. Copy your PostgreSQL connection string:
   ```text
   postgresql://nhgcc_db_owner:abcdef123456@ep-sample-12345.us-east-2.aws.neon.tech/nhgcc_db?sslmode=require
   ```

---

## 📦 Step 2: Migrate All Existing Church Data to the Cloud

Run the included migration script to upload all 298 members and 144 attendance logs to your new cloud database:

```powershell
python migrate_to_postgres.py "YOUR_NEON_POSTGRES_CONNECTION_STRING"
```

The script will:
- Connect to `nhgcc_church.db`.
- Initialize all tables in PostgreSQL.
- Batch transfer all 298 members, 144 attendance records, and system settings.
- Reset serial ID sequences so new registrations increment cleanly without conflicts.

---

## ⚙️ Step 3: Configure the Desktop App with the Cloud Database

In your project folder, create or edit `.env` (or set `DATABASE_URL` in `app/config.py`):

```ini
DATABASE_URL=postgresql://nhgcc_db_owner:abcdef123456@ep-sample-12345.us-east-2.aws.neon.tech/nhgcc_db?sslmode=require
```

When the desktop app is built, it will communicate directly with this central database.

---

## 🛠️ Step 4: Build and Distribute the Desktop App via GitHub

### Option A: Automated Build with GitHub Actions (Recommended)
We have already created the automated build workflow in [`.github/workflows/build_desktop_app.yml`](.github/workflows/build_desktop_app.yml).

1. Push your repository to GitHub:
   ```powershell
   git init
   git add .
   git commit -m "NHGCC Oshodi Church Desktop Application with Cloud Sync"
   git remote add origin https://github.com/your-username/nhgcc-church-database.git
   git push -u origin main
   ```

2. To generate an official installer release:
   - Go to your repository on GitHub.
   - Click **Releases > Draft a new release**.
   - Create a tag like `v1.0.0`, add a title (e.g. `NHGCC Oshodi Church Database v1.0.0`), and click **Publish release**.
   - GitHub Actions will automatically compile `NHGCC_Church_Database.exe` and attach it to the release!

3. **Distribute to Church Workers**:
   - Send church workers the download link:
     `https://github.com/your-username/nhgcc-church-database/releases/latest/download/NHGCC_Church_Database.exe`
   - They download the `.exe`, double-click it, and the 1-click installer:
     - Installs the app on their computer.
     - Adds the **NHGCC Oshodi Church Database** icon to their Desktop.
     - Adds it to their Windows Start Menu.
     - Connects to the central cloud database!

### Option B: Build Locally on Your Computer
If you want to compile the `.exe` right on your computer:
1. Double-click [`build_app.bat`](build_app.bat) (or run `pyinstaller --noconfirm nhgcc_desktop.spec`).
2. The compiled standalone installer will be created in the `dist\` folder:
   `dist\NHGCC_Church_Database.exe`
3. You can copy this file to a flash drive or upload it to Google Drive / GitHub for anyone to install.

---

## 🔄 Step 5: How App Changes & Updates Work

Whenever you want to make changes to the app (new features, reports, UI improvements):

1. Make your code changes in the project.
2. Push your changes to GitHub with a new release tag (e.g., `v1.0.1`):
   ```powershell
   git commit -am "Added new Sunday attendance features"
   git tag v1.0.1
   git push origin main --tags
   ```
3. GitHub Actions builds the new `NHGCC_Church_Database.exe`.
4. Users download and run the new `.exe`:
   - It updates their desktop app in-place.
   - **Their database connection is 100% preserved.**
   - All church records remain live in the cloud database.

---

## 🖥️ Summary of Desktop App Features

- **1-Click Windows Self-Installer**: Automatically copies to `%LOCALAPPDATA%\NHGCC_Church_Database`, creates Desktop shortcut and Start Menu entry, and includes an uninstaller (`Uninstall_NHGCC_App.bat`).
- **Single-Instance Management**: If the user double-clicks the desktop shortcut when the app is already open, it brings the existing window to the front instead of crashing.
- **Port Conflict Resolver**: If port 5000 is occupied, it automatically selects an available port between 5001–5050.
- **Multi-Device Live Sync**: All installations across different computers read and write to the same central cloud database.
