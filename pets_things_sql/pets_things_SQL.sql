-- =========================================================
-- 01) CREATE DATABASE
-- =========================================================
DROP DATABASE IF EXISTS pets_things_db;
CREATE DATABASE pets_things_db;
USE pets_things_db;

-- =========================================================
-- 02) CREATE TABLES (SCHEMA)
-- =========================================================

-- USERS
CREATE TABLE users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('admin','employee','customer') NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CATEGORY
CREATE TABLE category (
  category_id INT AUTO_INCREMENT PRIMARY KEY,
  category_name VARCHAR(80) NOT NULL UNIQUE
);

-- PRODUCT
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

-- BRANCH
CREATE TABLE branch (
  branch_id INT AUTO_INCREMENT PRIMARY KEY,
  branch_name VARCHAR(80) NOT NULL UNIQUE,
  address VARCHAR(150),
  phone VARCHAR(30)
);

-- STOCK (Inventory)
CREATE TABLE stock (
  branch_id INT NOT NULL,
  product_id INT NOT NULL,
  on_hand_qty INT NOT NULL DEFAULT 0,
  min_qty INT NOT NULL DEFAULT 0,
  last_restock_date DATE NULL,
  PRIMARY KEY (branch_id, product_id),
  CONSTRAINT fk_stock_branch
    FOREIGN KEY (branch_id)
    REFERENCES branch(branch_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  CONSTRAINT fk_stock_product
    FOREIGN KEY (product_id)
    REFERENCES product(product_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE
);

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

CREATE TABLE stock_movement (
  movement_id INT AUTO_INCREMENT PRIMARY KEY,

  branch_id INT NOT NULL,
  product_id INT NOT NULL,

  change_qty INT NOT NULL, -- + for restock, - for sale
  movement_type VARCHAR(20) NOT NULL, -- 'RESTOCK' or 'SALE'

  reference_sale_id INT NULL, -- filled only for SALE
  performed_by INT NOT NULL,  -- user_id (employee/admin)
  movement_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  note VARCHAR(255) NULL,

  CONSTRAINT fk_sm_branch
    FOREIGN KEY (branch_id) REFERENCES branch(branch_id),

  CONSTRAINT fk_sm_product
    FOREIGN KEY (product_id) REFERENCES product(product_id),

  CONSTRAINT fk_sm_user
    FOREIGN KEY (performed_by) REFERENCES users(user_id),

  CONSTRAINT fk_sm_sale
    FOREIGN KEY (reference_sale_id) REFERENCES sale(sale_id)
);




-- =========================================================
-- 03) INSERT SAMPLE DATA (SMALL & CLEAN)
-- =========================================================
select database();
-- Admin user (temporary password hash)
INSERT INTO users (full_name, email, password_hash, role)
VALUES ('Owner Admin', 'admin@pets.com', 'TEMP_HASH', 'admin');
select * from users;
-- Categories (4 only)
INSERT INTO category (category_name) VALUES
('Pet Food'),
('Pet Toys'),
('Pet Accessories'),
('Pet Grooming');

-- One branch
INSERT INTO branch (branch_name, address, phone)
VALUES ('Main Branch', 'Ramallah', '0590000000');

-- Products (8 only)
INSERT INTO product (product_name, category_id, unit_price, description, is_active) VALUES
('Premium Dog Food 2kg', 1, 35.00, 'Dry food for adult dogs', 1),
('Cat Dry Food 1kg', 1, 25.00, 'Nutritious dry food for cats', 1),
('Rubber Dog Ball', 2, 10.00, 'Durable chew toy for dogs', 1),
('Cat Feather Toy', 2, 8.50, 'Interactive toy for cats', 1),
('Adjustable Dog Collar', 3, 15.00, 'Comfortable adjustable collar', 1),
('Stainless Steel Pet Bowl', 3, 12.00, 'Easy to clean bowl', 1),
('Pet Shampoo 500ml', 4, 14.00, 'Gentle shampoo for pets', 1),
('Nail Clipper', 4, 9.00, 'Safe nail clipper for pets', 0);

-- Stock (for one branch)
INSERT INTO stock (branch_id, product_id, on_hand_qty, min_qty) VALUES
(1, 1, 20, 5),
(1, 2, 15, 5),
(1, 3, 3, 6),
(1, 4, 10, 4),
(1, 5, 8, 3),
(1, 6, 12, 5),
(1, 7, 6, 4),
(1, 8, 1, 5);

-- =========================================================
-- 04) QUERIES (AS REQUESTED)
-- =========================================================

-- Get only ACTIVE products
SELECT 
    p.product_id,
    p.product_name,
    c.category_name,
    p.unit_price,
    p.description,
    p.is_active
FROM product p
INNER JOIN category c ON p.category_id = c.category_id
WHERE p.is_active = 1
ORDER BY p.product_name ASC;

-- Get products by specific category (parameterized)
-- Usage in Flask: cursor.execute(query, (category_id,))
SELECT 
    p.product_id,
    p.product_name,
    c.category_name,
    p.unit_price,
    p.description,
    p.is_active
FROM product p
INNER JOIN category c ON p.category_id = c.category_id
WHERE c.category_id = 1
ORDER BY p.product_name ASC;

-- Get products with price range filter (parameterized)
-- Usage: cursor.execute(query, (min_price, max_price))
SELECT 
    p.product_id,
    p.product_name,
    c.category_name,
    p.unit_price,
    p.description,
    p.is_active
FROM product p
INNER JOIN category c ON p.category_id = c.category_id
WHERE p.unit_price BETWEEN 10 AND 50
ORDER BY p.unit_price ASC;

-- Count products per category
SELECT 
    c.category_name,
    COUNT(p.product_id) AS product_count
FROM category c
LEFT JOIN product p ON c.category_id = p.category_id
GROUP BY c.category_id, c.category_name
ORDER BY product_count DESC;

-- Check for products without categories
SELECT * 
FROM product 
WHERE category_id NOT IN (SELECT category_id FROM category);

-- View all products with full details (main products page)
SELECT 
    p.product_id,
    p.product_name,
    c.category_name,
    p.unit_price,
    p.description,
    CASE 
        WHEN p.is_active = 1 THEN 'Active'
        ELSE 'Inactive'
    END AS status
FROM product p
INNER JOIN category c ON p.category_id = c.category_id
ORDER BY p.product_name;
SELECT * FROM product ORDER BY product_id DESC;
select * from users;
show tables;
SELECT DATABASE();
SELECT COUNT(*) FROM users;
SELECT * FROM users ORDER BY 1 DESC LIMIT 5;
select * from product;