# 🏋️‍♂️ GymTK — Gym Management System

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![PySide6](https://img.shields.io/badge/Framework-PySide6-green.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey.svg)
![OpenCV](https://img.shields.io/badge/Feature-QR_Checkin-orange.svg)

**GymTK** is a modern gym management application built with Python and PySide6. The application supports member management, subscription registration, and automates the check-in process through real-time QR code scanning technology.

---

## ✨ Key Features

### 1. Dashboard & Statistics
* **Overview**: Provides a quick glance at key metrics such as total members, monthly revenue, and today's check-ins.
* **Visual Charts**: Integrates Matplotlib to draw Donut charts and Bar charts.
* **Reports**: Exports a list of members with expiring memberships to an Excel file with professional formatting.

### 2. Member Management
* **Full CRUD**: Add new, update information, and delete members.
* **Image Profile**: Captures photos directly from the Webcam for member identification.
* **Smart Search**: Uses *Debounce Search* technique for smooth searching.

### 3. Subscription System
* Manages flexible subscription types (Students, Adults).
* Automatically calculates start and end dates based on the subscription package.
* Tracks subscription status (Active/Expired) in real-time.

### 4. Automated QR Check-in
* **Background Scanning**: The QR scanning system runs continuously in the background via QRService.
* **Fast Recognition**: Automatically retrieves member information as soon as a valid QR code is detected.

---

## 🛠 Technologies Used

* **Language**: Python
* **GUI**: PySide6 (Qt for Python)
* **Database**: SQLite (raw SQL queries)
* **Computer Vision**: OpenCV & PyZbar
* **Data Processing & Reporting**: Matplotlib, Pandas, Openpyxl

---

## 📂 Directory Structure

```text
GymTK/
├── assets/                  
│   ├── error.wav            # Error beep sound (expired subscription / unregistered member)
│   └── success.wav          # Short beep sound (successful check-in)
├── controllers/              # Business logic handling
│   ├── checkin_controller.py
│   ├── dashboard_controller.py
│   ├── member_controller.py
│   ├── qr_controller.py
│   └── subscription_controller.py
├── images/
│   └── members/              # Member profile images storage (1.jpg, 3.jpg...)
├── qr_codes/                 # Member identification QR codes storage
├── services/                 # Background services
│   └── qr_service.py         # Manages camera stream and QR recognition
├── styles/                   
│   └── styles.qss            # Application UI stylesheet
├── ui/                       # User Interface components (PySide6)
│   ├── chart_widget.py       # Statistical chart component
│   ├── dashboard_page.py     # General overview page
│   ├── login_window.py       # System login window
│   ├── main_window.py        # Main application navigation window
│   ├── member_page.py        # Member list management
│   ├── qr_checkin_page.py    # Camera check-in page
│   └── subscription_page.py  # Subscription package management
├── utils/                    # Auxiliary tools
│   └── qr_generator.py       # QR code generation helper
├── .gitignore                # Git ignore configuration
├── database.py               # SQLite connection and database operations
├── gym.db                    # SQLite database file
├── gym_pic.png               # Application brand logo image
├── main.py                   # Main Entry Point of the application
├── README.md                 # Project documentation
└── requirements.txt          # List of dependencies to install
```
## 🚀 Setup and Test

* **Step 1**: Install libraries
Open the Terminal at the project folder and run the following command:
```text
    pip install -r requirements.txt
```

* **Step 2**: Run the application
After the installation is complete, launch the software using the command:
```text
    python main.py
```

## 👤 Thông tin tác giả
* **Full Name**: Kiều Quốc Thắng
* **Student ID**: 25AI051
* **Class**: 25GAI

* **Project**: Final Python Programming Project

* **Topic**: 9. Gym and Fitness Center Membership Management

* **Commitment**: The project is 100% original and complies with the technical requirements of the final assignment.