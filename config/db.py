import mysql.connector
from mysql.connector import Error
import time
import os

def connect_to_mysql(max_retries=5, retry_delay=5):
    config = {
        'host': os.getenv("DB_HOST"),  # Replace with your database host
        'user': os.getenv("DB_USER"),       # Replace with your database username
        'password': os.getenv("DB_PASS"),  # Replace with your database password
        'database': os.getenv("DB_NAME"),  # Replace with your database name
        'port': os.getenv("DB_PORT")
    }
    retries = 0
    while retries < max_retries:
        try:
            conn = mysql.connector.connect(**config)
            if conn.is_connected():
                return conn
        except Error as e:
            print(f"Error connecting to MySQL database: {e}")
            retries += 1
            if retries < max_retries:
                print(f"Retrying in {retry_delay} seconds... (Attempt {retries + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Could not connect to MySQL database.")
                return None
    return conn

def query(sql, params=None, dictionary=True, single=False):
    conn = connect_to_mysql()
    if conn is None: 
        return None
    cursor = conn.cursor(dictionary=dictionary)
    try: 
        if params is not None:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        if single:
            return cursor.fetchone()
        return cursor.fetchall()
    except Exception as e:
        print(f"Error executing SQL query: {e}")
        return None
    finally:
        if conn is not None:
            conn.close()

def command(sql, params=None):
    conn = connect_to_mysql()
    if conn is None: 
        return None
    cursor = conn.cursor(dictionary=True)
    try: 
        if params is not None:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        conn.commit()  
        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        print(f"Error executing SQL command: {e}")
        return None
    finally:
        if conn is not None:
            conn.close()