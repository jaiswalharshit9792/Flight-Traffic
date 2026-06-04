CREATE DATABASE IF NOT EXISTS flights CHARACTER SET utf8mb4;
USE flights;

CREATE TABLE airports (
    id INT PRIMARY KEY,
    name VARCHAR(200),
    city VARCHAR(100),
    country VARCHAR(100),
    iata_code VARCHAR(3),
    latitude DECIMAL(10,6),
    longitude DECIMAL(11,6),
    altitude INT,
    embedding VECTOR(384),
    INDEX idx_embedding(embedding)
) ENGINE=InnoDB;

CREATE TABLE routes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    airline VARCHAR(10),
    source_airport_id INT,
    dest_airport_id INT,
    distance_km DECIMAL(10,2),
    FOREIGN KEY (source_airport_id) REFERENCES airports(id),
    FOREIGN KEY (dest_airport_id) REFERENCES airports(id)
) ENGINE=InnoDB;

CREATE TABLE route_analytics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_airport VARCHAR(4),
    dest_airport VARCHAR(4),
    search_count INT DEFAULT 0,
    popularity_score DECIMAL(5,2)
) ENGINE=InnoDB;
