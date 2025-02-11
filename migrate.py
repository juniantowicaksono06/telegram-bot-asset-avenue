import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
load_dotenv()

# Define the SQL statements for table creation
SQL_STATEMENTS = """
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    first_name VARCHAR(200) NOT NULL,
    last_name VARCHAR(255),
    username VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    group_id BIGINT NOT NULL,
    `message_id` BIGINT NOT NULL,
    score INT NOT NULL,
    `date` DATE NOT NULL,
    activity_type ENUM('message','media','poll','competition','referral','registration') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bot_config (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `MESSAGE_POINTS` INT NOT NULL,
    `MEDIA_POINTS` INT NOT NULL,
    `MAX_MESSAGE_POINTS` INT NOT NULL,
    `MAX_MEDIA_POINTS` INT NOT NULL,
    `REFERRED_MIN_ACTIVATION` INT NOT NULL,
    `REFERRAL_ACTIVE_DAYS` INT NOT NULL,
    `REFERRAL_POINTS` INT NOT NULL,
    `MAX_LEADERBOARD_DATA_PER_PAGE` INT NOT NULL DEFAULT 5,
    `MAX_REFERRAL_PER_DAY` INT NOT NULL DEFAULT 2,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS referral_links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    `link` VARCHAR(100) NOT NULL,
    group_id BIGINT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS referrals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    referrer_id BIGINT NOT NULL,
    referred_id BIGINT NOT NULL,
    link_id INT NOT NULL,
    status TINYINT DEFAULT 0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (referrer_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (referred_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (link_id) REFERENCES referral_links(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS referral_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    referral_id INT NOT NULL,
    `datetime` DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS user_stage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    stage INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

ALTER TABLE scores MODIFY COLUMN activity_type ENUM('message','media','poll','competition','referral','registration','extra point') NOT NULL;

CREATE TABLE IF NOT EXISTS whitelist_users_private (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS `groups` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id BIGINT NOT NULL UNIQUE,
    group_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS `polls` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    poll_id BIGINT NOT NULL,
    group_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def migrate_database():
    try:
        # Connect to the MySQL database
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),  # Replace with your database host
            user=os.getenv("DB_USER"),       # Replace with your database username
            password=os.getenv("DB_PASS"),  # Replace with your database password
            database=os.getenv("DB_NAME"),  # Replace with your database name
            port=os.getenv("DB_PORT")
        )

        if connection.is_connected():
            print("Connected to the database successfully.")

            # Create a cursor object to execute SQL statements
            cursor = connection.cursor()

            # Execute the SQL statements
            for statement in SQL_STATEMENTS.split(";"):
                if statement.strip():  # Ignore empty statements
                    cursor.execute(statement)

            print("Migration completed successfully.")

    except Error as e:
        print(f"Error during migration: {e}")

    finally:
        # Close the cursor and connection
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()
            print("Database connection closed.")

# Run the migration function
if __name__ == "__main__":
    migrate_database()