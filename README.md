# Smart Event Planning Platform with Resource Coordination System

A web-based Event Registration Platform developed using Django for managing college events, event categories, member registrations, attendance, notifications, user profiles, and completed events.

## 📌 Project Overview

The Event Registration Platform provides a centralized system for creating and managing college events. Administrators can create event categories, publish events, manage members, track registrations, and record attendance.

Users can create an account, log in, view available events, register for events, view their registered events, manage their profile, and receive notifications.

The platform reduces manual event management and provides an organized digital solution for managing the complete event lifecycle.

---

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

## 1. User Registration

A new user starts by creating an account using the Sign Up page.

The user provides the required information and creates login credentials.

The registration information is stored in the Django database.

**Process:**

Sign Up → Enter Details → Account Created → Login

---

## 2. User Login

Registered users can log in using their username/email and password.

Django Authentication is used to verify the user's credentials.

**Process:**

Login → Authentication → User Dashboard

---

## 3. Dashboard

After successful login, the user is redirected to the dashboard.

The dashboard provides access to the main features of the platform, including:

- Dashboard
- Event Categories
- Events
- Members
- Attendance
- Profile
- Notifications
- Registered Events
- Logout

---

# 👨‍💼 Admin/Event Management Process

## 4. Event Category Management

The administrator can create and manage event categories.

Examples:

- Technical Events
- Cultural Events
- Sports
- Workshops
- Seminars

### Operations

- Create category
- View categories
- Edit category
- Delete category

**Process:**

Admin → Event Category → Create/Edit/Delete → Database

---

## 5. Event Creation

The administrator can create new events.

Event information can include:

- Event name
- Event category
- Description
- Event date
- End date
- Location
- Event details
- Registration information

The event information is stored in the database.

**Process:**

Admin → Create Event → Enter Event Details → Save → Event Published

---

## 6. Event Management

Administrators can view and manage existing events.

Available operations include:

- View events
- Edit events
- Delete events
- View event details
- Manage registrations

---

# 👥 Member Registration Process

## 7. Event Registration

Users can view available events and register for events they are interested in.

**Process:**

User Login
↓
View Events
↓
Select Event
↓
View Event Details
↓
Register
↓
Registration Saved

The registration information is stored in the database.

---

## 8. My Registered Events

Users can view the events they have registered for from their personal dashboard.

The page displays their registered events and relevant event information.

**Process:**

User Dashboard → My Registered Events → View Registered Events

---

# 📋 Attendance Management

## 9. Mark Attendance

Administrators can manage attendance for registered members.

The attendance system allows the administrator to record whether a registered member attended an event.

**Process:**

Admin → Attendance → Select Event → Select Member → Mark Attendance → Save

---

## 10. Attendance Records

Attendance records are stored in the database and can be viewed or edited by authorized users.

This helps administrators track event participation.

---

# 🔔 Notification System

## 11. Notifications

The platform provides notifications to users for important event-related activities.

Notifications can contain information about:

- Events
- Registrations
- Event updates
- Other important activities

Users can view their notifications from the platform.

---

# 👤 User Profile

## 12. Profile Management

Users can view and update their profile information.

The platform supports:

- View profile
- Edit profile
- Profile picture
- Change password

**Process:**

User → Profile → View/Edit Information → Save

---

# 🔐 Authentication and Security

Django's built-in authentication system is used for user authentication.

The platform provides:

- User login
- User registration
- Logout
- Password change
- Password reset
- Authentication-protected pages
- User sessions

Access to different platform functions is controlled according to the user's role and permissions.

---

# 🗄️ Database

The project uses SQLite as the database during development.

The database stores information related to:

- Users
- Profiles
- Event Categories
- Events
- Registrations
- Attendance
- Notifications
- Messages

Django ORM is used to communicate with the database

# Installation and Setup

Step 1: Clone the Repository  
git clone https://github.com/srisatyasaiuppala/event-registration-platform.git

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
