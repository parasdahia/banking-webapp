# Anna University - Banking WebApp Project

A secure, transaction-based banking portal built using **Python Flask** and **MySQL**. This web application allows users to view account details, transfer funds (IMPS/UPI), and view transaction history.

## 📌 Features
* **User Authentication**: Secure login with hashed passwords.
* **Dashboard**: View account balance, branch details, and profile info.
* **Fund Transfer**:
    * **IMPS**: Transfer money using Account Number.
    * **UPI**: Transfer money using UPI ID.
* **Transaction History**: View past credits and debits with status indicators.
* **Security**: CSRF protection, session management, and password hashing (SHA256 + Salt).

## 🛠️ Tech Stack
* **Backend**: Python (Flask)
* **Database**: MySQL
* **Frontend**: HTML, CSS, JavaScript

## ⚙️ Setup Instructions

### 1. ✅ Prerequisites
Ensure you have Python and MySQL installed on your system.

### 2. 📦 Install Dependencies
Run the following command to install the required Python libraries:
```bash
pip install -r requirements.txt
```

### 3. 🗄️ Database Setup
Import and execute the SQL script `ToDo_DatabaseSetup.txt` in your MySQL environment. This will automatically create the database and populate the required tables.

#### 🔑 Default Login Credentials
The system is pre-loaded with **5 test accounts** (`user1` to `user5`).

* **Default Password:** `enter`

> **Note:** You can update this password after logging in via the **Reset Password** tab on the dashboard.