# 🐾 Pets & Things Store Management System

## 📌 Project Overview

The **Pets & Things Store Management System** is a desktop-based management application developed for *Pets & Things Pet Store* located in **Ein Musbah, Ramallah, Palestine**.
The system automates daily store operations, replacing manual record-keeping with a centralized digital solution that improves accuracy, efficiency, and data consistency.

---

## 🏬 Business Description

Pets & Things is a pet store operating on two floors:

* **First Floor:** Retail pet products for cats and dogs (food, treats, toys, accessories)
* **Second Floor:** A **cat hotel service**, allowing customers to book rooms for their cats

The store is managed by the owner with the help of one employee. Manual handling of sales, inventory, purchases, bookings, and attendance was time-consuming and error-prone. This system was developed to simplify and organize all operations in one platform.

---

## ⚙️ System Features

* Role-based user management (Admin, Employee, Customer)
* Product and category management
* Separate inventory for warehouse and branches
* Sales processing with receipt generation
* Supplier and purchase management
* Stock transfers and stock movement tracking
* Cat hotel booking and room occupancy management
* Employee attendance tracking (check-in / check-out)
* Dashboard with summaries and alerts
* Reports and analytics
* Search and filtering functionality

---

## 👥 User Roles

* **Admin:** Full system access, manage users, products, inventory, reports, and bookings
* **Employee:** Handle sales, bookings, attendance, and inventory operations
* **Customer:** Manage pet information and book cat hotel rooms

---

## 🧱 System Modules

* User Management
* Product Management
* Inventory Management
* Sales Management
* Purchase & Supplier Management
* Stock Transfer & Movement
* Booking Management (Cat Hotel)
* Attendance Management
* Reports & Analytics
* Dashboard

---

## 🗄️ Database Design

* Database implemented using **MySQL**
* Fully normalized to **Third Normal Form (3NF)**
* Separate stock tables for warehouse and branches
* Stock movement table used to audit all inventory changes
* Relationships designed to avoid redundancy and update anomalies

---

## 📊 Reports Available

* Sales Analytics
* Top-Selling Products
* Occupancy Analytics (Cat Hotel)
* Employee Attendance Reports

---

## 🛠 Technologies Used

| Component            | Technology / Tool  | Description                   |
| -------------------- | ------------------ | ----------------------------- |
| Programming Language | Python             | Core application logic        |
| Framework            | Flask              | Backend framework and routing |
| Database             | MySQL              | Data storage and management   |
| Database Design      | MySQL Workbench    | ERD and schema design         |
| Frontend             | HTML, CSS          | User interface                |
| Charts & Analytics   | Chart.js           | Visual reports and analytics  |
| Authentication       | Flask Sessions     | User login and access control |
| IDE                  | Visual Studio Code | Development environment       |

---

## 📂 Project Structure

```text
Pets-And-Things-Store-Management-System/
│
├── app.py                      # Main Flask application
├── db.py                       # Database connection and queries
├── seed_admin.py               # Script to create initial admin user
├── hash_employee_password.py   # Password hashing utility
├── .env                        # Environment variables
│
├── routes/                     # Flask route modules
│
├── sql/                        # SQL scripts (schema and seed data)
│
├── static/
│   ├── css/
│   │   └── style.css           # Application styling
│   ├── images/                 # System images and icons
│   └── uploads_products/       # Uploaded product images
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── products.html
│   ├── product_form.html
│   ├── inventory.html
│   ├── sales.html
│   ├── sales_new.html
│   ├── sale_detail.html
│   ├── sale_receipt.html
│   ├── purchases.html
│   ├── purchase_form.html
│   ├── purchase_detail.html
│   ├── suppliers.html
│   ├── supplier_form.html
│   ├── stock_movements.html
│   ├── sales_analytics.html
│   ├── report_top_products.html
│   ├── occupancy_analytics.html
│   ├── rooms_occupancy.html
│   ├── bookings_today.html
│   ├── admin_bookings.html
│   ├── my_bookings.html
│   ├── booking_new.html
│   ├── booking_search.html
│   ├── my_cats.html
│   └── report_employee_attendance.html
│
├── venv/                       # Python virtual environment
├── .vscode/                    # VS Code configuration
├── __pycache__/                # Python cache files
│
└── README.md                   # Project documentation
```

---

## 🚀 How to Run the Project

1. Install **Python 3.x**
2. Create and activate a virtual environment
3. Install required packages:

   ```bash
   pip install flask mysql-connector-python python-dotenv
   ```
4. Import the database schema from the `sql` folder into MySQL
5. Configure database credentials in `.env`
6. Run the application:

   ```bash
   python app.py
   ```
7. Open your browser and go to:

   ```
   http://localhost:5000
   ```

---

## 🔮 Future Enhancements

* Email notifications for bookings and reminders
* Advanced data visualization dashboards
* Online booking portal
* Multi-branch expansion support

---

## 📌 Project Status

✔ Core features implemented
✔ Database normalized to 3NF
✔ Dashboard and reports functional

---

## 👤 Author

**Pets & Things Store Management System**
Developed as an academic project for database systems coursework.

