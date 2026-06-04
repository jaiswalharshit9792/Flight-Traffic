-- Grant all privileges on flights database to flightuser
GRANT ALL PRIVILEGES ON flights.* TO 'flightuser'@'%';
FLUSH PRIVILEGES;
