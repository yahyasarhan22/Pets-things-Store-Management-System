drop database pets_things_db;
CREATE DATABASE pets_things_db;
use pets_things_db;
CREATE TABLE users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,

  full_name VARCHAR(100) NOT NULL,

  email VARCHAR(120) NOT NULL UNIQUE,

  password_hash VARCHAR(255) NOT NULL,

  role ENUM('admin','employee','customer') NOT NULL,

  is_active TINYINT(1) NOT NULL DEFAULT 1,

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO users (full_name, email, password_hash, role) VALUES ('Owner Admin', 'admin@pets.com', 'TEMP_HASH', 'admin');
SELECT * FROM users;
SELECT email, password_hash FROM users WHERE email='admin@pets.com';

-- Category table
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
    FOREIGN KEY (category_id) REFERENCES category(category_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

CREATE TABLE branch (
  branch_id INT AUTO_INCREMENT PRIMARY KEY,
  branch_name VARCHAR(80) NOT NULL UNIQUE,
  address VARCHAR(150) NULL,
  phone VARCHAR(30) NULL
);

CREATE TABLE stock (
  branch_id INT NOT NULL,
  product_id INT NOT NULL,

  on_hand_qty INT NOT NULL DEFAULT 0,
  min_qty INT NOT NULL DEFAULT 0,
  last_restock_date DATE NULL,

  PRIMARY KEY (branch_id, product_id),

  CONSTRAINT fk_stock_branch
    FOREIGN KEY (branch_id) REFERENCES branch(branch_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,

  CONSTRAINT fk_stock_product
    FOREIGN KEY (product_id) REFERENCES product(product_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE
);

INSERT INTO category (category_name) VALUES
('Food'), ('Toys'), ('Accessories');

INSERT INTO branch (branch_name, address, phone)
VALUES ('Main Branch', 'Ramallah', '0590000000');


INSERT INTO product (product_name, category_id, unit_price, description)VALUES
('Cat Dry Food 1kg', 1, 25.00, 'Dry food for adult cats'),
('Dog Toy Ball', 2, 10.00, 'Rubber ball toy for dogs');


-- Stock per branch:
INSERT INTO stock (branch_id, product_id, on_hand_qty, min_qty)VALUES
(1, 1, 12, 5),   -- Cat Dry Food: OK stock
(1, 2, 2, 6);    -- Dog Toy Ball: LOW stock

show tables;
select * from stock;
