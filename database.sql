-- database.sql
CREATE DATABASE IF NOT EXISTS `showtimehub` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `showtimehub`;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS movies (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  image VARCHAR(255),
  price INT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  movie_id INT NOT NULL,
  seats VARCHAR(500) NOT NULL,       -- CSV of seat numbers
  total_amount INT NOT NULL,
  status ENUM('Booked','Cancelled') NOT NULL DEFAULT 'Booked',
  booking_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
);

-- seed two movies if not exists
INSERT INTO movies (name, image, price)
SELECT 'Avatar', 'avatar3.jpg', 150
WHERE NOT EXISTS (SELECT 1 FROM movies WHERE name='Avatar');

INSERT INTO movies (name, image, price)
SELECT 'Joker', 'joker2.jpg', 200
WHERE NOT EXISTS (SELECT 1 FROM movies WHERE name='Joker');
