-- =========================================================
-- UPDATED DATABASE SCHEMA FOR WAREHOUSE + BRANCH INVENTORY
-- =========================================================

DROP DATABASE IF EXISTS pets_things_db;
CREATE DATABASE pets_things_db;
USE pets_things_db;

-- =========================================================
-- EXISTING TABLES (users, category, product, branch)
-- =========================================================

CREATE TABLE users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('admin','employee','customer') NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE category (
  category_id INT AUTO_INCREMENT PRIMARY KEY,
  category_name VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE product (
  product_id INT AUTO_INCREMENT PRIMARY KEY,
  product_name VARCHAR(120) NOT NULL,
  category_id INT NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  description VARCHAR(255) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT fk_product_category
    FOREIGN KEY (category_id)
    REFERENCES category(category_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);
ALTER TABLE product
ADD COLUMN product_image VARCHAR(255) NULL;

CREATE TABLE branch (
  branch_id INT AUTO_INCREMENT PRIMARY KEY,
  branch_name VARCHAR(80) NOT NULL UNIQUE,
  address VARCHAR(150),
  phone VARCHAR(30)
);

-- =========================================================
-- NEW: WAREHOUSE TABLE
-- =========================================================
CREATE TABLE warehouse (
  warehouse_id INT AUTO_INCREMENT PRIMARY KEY,
  warehouse_name VARCHAR(80) NOT NULL UNIQUE,
  address VARCHAR(150),
  phone VARCHAR(30),
  is_main TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- UPDATED: SEPARATE BRANCH AND WAREHOUSE STOCK
-- =========================================================

-- Branch stock (for sales)
CREATE TABLE branch_stock (
  branch_id INT NOT NULL,
  product_id INT NOT NULL,
  on_hand_qty INT NOT NULL DEFAULT 0,
  min_qty INT NOT NULL DEFAULT 0,
  last_restock_date DATE NULL,
  PRIMARY KEY (branch_id, product_id),
  CONSTRAINT fk_branch_stock_branch
    FOREIGN KEY (branch_id)
    REFERENCES branch(branch_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  CONSTRAINT fk_branch_stock_product
    FOREIGN KEY (product_id)
    REFERENCES product(product_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE
);

-- Warehouse stock (receives purchases)
CREATE TABLE warehouse_stock (
  warehouse_id INT NOT NULL,
  product_id INT NOT NULL,
  on_hand_qty INT NOT NULL DEFAULT 0,
  min_qty INT NOT NULL DEFAULT 0,
  last_purchase_date DATE NULL,
  PRIMARY KEY (warehouse_id, product_id),
  CONSTRAINT fk_warehouse_stock_warehouse
    FOREIGN KEY (warehouse_id)
    REFERENCES warehouse(warehouse_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  CONSTRAINT fk_warehouse_stock_product
    FOREIGN KEY (product_id)
    REFERENCES product(product_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE
);

-- =========================================================
-- SALES (unchanged logic, uses branch_stock)
-- =========================================================
CREATE TABLE sale (
  sale_id INT AUTO_INCREMENT PRIMARY KEY,
  branch_id INT NOT NULL,
  sale_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  employee_id INT NOT NULL,
  customer_id INT NULL,
  total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  notes VARCHAR(255) NULL,
  CONSTRAINT fk_sale_branch
    FOREIGN KEY (branch_id) REFERENCES branch(branch_id),
  CONSTRAINT fk_sale_employee
    FOREIGN KEY (employee_id) REFERENCES users(user_id),
  CONSTRAINT fk_sale_customer
    FOREIGN KEY (customer_id) REFERENCES users(user_id)
);

CREATE TABLE sale_line (
  sale_line_id INT AUTO_INCREMENT PRIMARY KEY,
  sale_id INT NOT NULL,
  product_id INT NOT NULL,
  quantity INT NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL,
  line_total DECIMAL(10,2) NOT NULL,
  CONSTRAINT fk_sale_line_sale
    FOREIGN KEY (sale_id) REFERENCES sale(sale_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_sale_line_product
    FOREIGN KEY (product_id) REFERENCES product(product_id),
  CONSTRAINT chk_sale_line_qty
    CHECK (quantity > 0)
);

-- =========================================================
-- NEW: PURCHASES (supplier → warehouse)
-- =========================================================
CREATE TABLE purchase (
  purchase_id INT AUTO_INCREMENT PRIMARY KEY,
  warehouse_id INT NOT NULL,
  purchase_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  supplier_name VARCHAR(120) NOT NULL,
  total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  performed_by INT NOT NULL,
  notes VARCHAR(255) NULL,
  CONSTRAINT fk_purchase_warehouse
    FOREIGN KEY (warehouse_id) REFERENCES warehouse(warehouse_id),
  CONSTRAINT fk_purchase_user
    FOREIGN KEY (performed_by) REFERENCES users(user_id)
);

CREATE TABLE purchase_line (
  purchase_line_id INT AUTO_INCREMENT PRIMARY KEY,
  purchase_id INT NOT NULL,
  product_id INT NOT NULL,
  quantity INT NOT NULL,
  unit_cost DECIMAL(10,2) NOT NULL,
  line_total DECIMAL(10,2) NOT NULL,
  CONSTRAINT fk_purchase_line_purchase
    FOREIGN KEY (purchase_id) REFERENCES purchase(purchase_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_purchase_line_product
    FOREIGN KEY (product_id) REFERENCES product(product_id),
  CONSTRAINT chk_purchase_line_qty
    CHECK (quantity > 0)
);

-- =========================================================
-- NEW: STOCK TRANSFERS (warehouse → branch)
-- =========================================================
CREATE TABLE stock_transfer (
  transfer_id INT AUTO_INCREMENT PRIMARY KEY,
  warehouse_id INT NOT NULL,
  branch_id INT NOT NULL,
  product_id INT NOT NULL,
  quantity INT NOT NULL,
  transfer_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  performed_by INT NOT NULL,
  notes VARCHAR(255) NULL,
  CONSTRAINT fk_transfer_warehouse
    FOREIGN KEY (warehouse_id) REFERENCES warehouse(warehouse_id),
  CONSTRAINT fk_transfer_branch
    FOREIGN KEY (branch_id) REFERENCES branch(branch_id),
  CONSTRAINT fk_transfer_product
    FOREIGN KEY (product_id) REFERENCES product(product_id),
  CONSTRAINT fk_transfer_user
    FOREIGN KEY (performed_by) REFERENCES users(user_id),
  CONSTRAINT chk_transfer_qty
    CHECK (quantity > 0)
);

-- =========================================================
-- UPDATED: STOCK MOVEMENTS (audit trail)
-- =========================================================
CREATE TABLE stock_movement (
  movement_id INT AUTO_INCREMENT PRIMARY KEY,
  
  -- Location (either warehouse or branch)
  warehouse_id INT NULL,
  branch_id INT NULL,
  product_id INT NOT NULL,
  
  change_qty INT NOT NULL,
  movement_type ENUM('PURCHASE', 'SALE', 'TRANSFER_IN', 'TRANSFER_OUT') NOT NULL,
  
  -- References
  reference_sale_id INT NULL,
  reference_purchase_id INT NULL,
  reference_transfer_id INT NULL,
  
  performed_by INT NOT NULL,
  movement_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  note VARCHAR(255) NULL,
  
  CONSTRAINT fk_sm_warehouse
    FOREIGN KEY (warehouse_id) REFERENCES warehouse(warehouse_id),
  CONSTRAINT fk_sm_branch
    FOREIGN KEY (branch_id) REFERENCES branch(branch_id),
  CONSTRAINT fk_sm_product
    FOREIGN KEY (product_id) REFERENCES product(product_id),
  CONSTRAINT fk_sm_user
    FOREIGN KEY (performed_by) REFERENCES users(user_id),
  CONSTRAINT fk_sm_sale
    FOREIGN KEY (reference_sale_id) REFERENCES sale(sale_id),
  CONSTRAINT fk_sm_purchase
    FOREIGN KEY (reference_purchase_id) REFERENCES purchase(purchase_id),
  CONSTRAINT fk_sm_transfer
    FOREIGN KEY (reference_transfer_id) REFERENCES stock_transfer(transfer_id),
    
  -- Ensure exactly one location is specified
  CONSTRAINT chk_sm_location
    CHECK ((warehouse_id IS NOT NULL AND branch_id IS NULL) OR 
           (warehouse_id IS NULL AND branch_id IS NOT NULL))
);


CREATE TABLE room (
  room_id INT AUTO_INCREMENT PRIMARY KEY,
  room_number VARCHAR(20) NOT NULL UNIQUE,
  room_type VARCHAR(30) DEFAULT 'Standard',
  is_active TINYINT NOT NULL DEFAULT 1,
  notes VARCHAR(255)
);


CREATE TABLE cat (
  cat_id INT AUTO_INCREMENT PRIMARY KEY,
  owner_id INT NOT NULL,
  cat_name VARCHAR(80) NOT NULL,
  breed VARCHAR(60),
  age_years INT,
  gender ENUM('M','F'),
  medical_notes VARCHAR(400),
  is_active TINYINT NOT NULL DEFAULT 1,
  CONSTRAINT fk_cat_owner FOREIGN KEY (owner_id) REFERENCES users(user_id)
);


CREATE TABLE booking (
  booking_id INT AUTO_INCREMENT PRIMARY KEY,
  customer_id INT NOT NULL,
  date_from DATE NOT NULL,
  date_to DATE NOT NULL,
  status ENUM('PENDING','CONFIRMED','CANCELLED','COMPLETED') NOT NULL DEFAULT 'PENDING',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_by INT NOT NULL,
  total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  CONSTRAINT fk_booking_customer FOREIGN KEY (customer_id) REFERENCES users(user_id),
  CONSTRAINT fk_booking_created_by FOREIGN KEY (created_by) REFERENCES users(user_id),
  CONSTRAINT chk_booking_dates CHECK (date_to > date_from)
);



CREATE TABLE booking_room (
  booking_room_id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  room_id INT NOT NULL,
  cat_id INT NOT NULL,
  nights INT NOT NULL,
  price_per_night DECIMAL(10,2) NOT NULL DEFAULT 30.00,
  discount_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  line_total DECIMAL(10,2) NOT NULL,

  CONSTRAINT fk_br_booking FOREIGN KEY (booking_id) REFERENCES booking(booking_id) ON DELETE CASCADE,
  CONSTRAINT fk_br_room FOREIGN KEY (room_id) REFERENCES room(room_id),
  CONSTRAINT fk_br_cat FOREIGN KEY (cat_id) REFERENCES cat(cat_id),

  UNIQUE (booking_id, room_id),
  UNIQUE (booking_id, cat_id)
);





-- =========================================================
-- SAMPLE DATA
-- =========================================================

-- Admin user
INSERT INTO users (full_name, email, password_hash, role)
VALUES ('Owner Admin', 'admin@pets.com', 'TEMP_HASH', 'admin');

-- Categories
INSERT INTO category (category_name) VALUES
('Pet Food'),
('Pet Toys'),
('Pet Accessories'),
('Pet Grooming');

-- Main warehouse
INSERT INTO warehouse (warehouse_name, address, phone, is_main)
VALUES ('Main Warehouse', 'Industrial Zone, Ramallah', '0591111111', 1);

-- Branch
INSERT INTO branch (branch_name, address, phone)
VALUES ('Main Branch', 'Downtown Ramallah', '0590000000');

-- Products
INSERT INTO product (product_name, category_id, unit_price, description, is_active) VALUES
('Premium Dog Food 2kg', 1, 35.00, 'Dry food for adult dogs', 1),
('Cat Dry Food 1kg', 1, 25.00, 'Nutritious dry food for cats', 1),
('Rubber Dog Ball', 2, 10.00, 'Durable chew toy for dogs', 1),
('Cat Feather Toy', 2, 8.50, 'Interactive toy for cats', 1),
('Adjustable Dog Collar', 3, 15.00, 'Comfortable adjustable collar', 1),
('Stainless Steel Pet Bowl', 3, 12.00, 'Easy to clean bowl', 1),
('Pet Shampoo 500ml', 4, 14.00, 'Gentle shampoo for pets', 1),
('Nail Clipper', 4, 9.00, 'Safe nail clipper for pets', 1);

-- Initialize warehouse stock for all products
INSERT INTO warehouse_stock (warehouse_id, product_id, on_hand_qty, min_qty) VALUES
(1, 1, 100, 20),
(1, 2, 80, 15),
(1, 3, 50, 10),
(1, 4, 60, 10),
(1, 5, 40, 8),
(1, 6, 45, 10),
(1, 7, 35, 8),
(1, 8, 25, 5);

-- Initialize branch stock for all products
INSERT INTO branch_stock (branch_id, product_id, on_hand_qty, min_qty) VALUES
(1, 1, 20, 5),
(1, 2, 15, 5),
(1, 3, 3, 6),
(1, 4, 10, 4),
(1, 5, 8, 3),
(1, 6, 12, 5),
(1, 7, 6, 4),
(1, 8, 1, 5);
INSERT INTO room (room_number, room_type, is_active)
VALUES ('R01','Standard',1),('R02','Standard',1),('R03','Standard',1),('R04','Standard',1),('R05','Standard',1);

select * from users;