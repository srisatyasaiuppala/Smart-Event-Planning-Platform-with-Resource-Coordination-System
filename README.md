# Smart Event Planning Platform with Resource Coordination System

A web-based Event Registration Platform developed using Django for managing college events, event categories, member registrations, attendance, notifications, user profiles, and completed events.

## 🎯 Objectives

- To provide an online platform for college event management.
- To allow administrators to create and manage events.
- To allow users to register for events online.
- To manage event categories and members.
- To record and manage attendance.
- To provide users with a personal dashboard.
- To provide notifications for important event activities.
- To maintain event information in a centralized database.

---

## 🛠️ Technologies Used

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- Django

### Database
- SQLite

### Development Tools
- Visual Studio Code
- Git
- GitHub

---

# ⚙️ Platform Process

              EVENT REGISTRATION PLATFORM
                            │
                            ▼
                    User Registration
                            │
                            ▼
                         Login
                            │
                            ▼
                       Dashboard
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
       View Events      Profile       Notifications
             │
             ▼
       Event Details
             │
             ▼
          Register
             │
             ▼
    My Registered Events
             │
             ▼
      Event Attendance
             │
             ▼
       Attendance Record


Django ORM is used to communicate with the database

# Installation and Setup
'''bash
Step 1: Clone the Repository  
git clone
https://github.com/srisatyasaiuppala/Smart-Event-Planning-Platform-with-Resource-Coordination-System.git

Step 2: Open the Project  
cd event-registration-platform

Step 3: Create a Virtual Environment  
python -m venv venv

Step 4: Activate the Virtual Environment  
Windows  
venv\Scripts\activate

Step 5: Install Django  
pip install django

Step 6: Apply Database Migrations  
python manage.py migrate

Step 7: Run the Development Server  
python manage.py runserver

Open the application in your browser:  
http://127.0.0.1:8000/
