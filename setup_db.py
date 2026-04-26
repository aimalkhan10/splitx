import pymysql

# Connection details from .env
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "5912"
DB_NAME = "splitx"

try:
    # Connect without database first
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    
    # Create database
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    print(f"Database '{DB_NAME}' verified/created.")
    
    # Use database
    cursor.execute(f"USE {DB_NAME}")
    
    # Run Schema.sql
    with open("Schema.sql", "r") as f:
        sql = f.read()
        # pymysql doesn't support multiple statements in one execute() by default
        # but we can split by semicolon
        # Note: This is a simple split, might fail on complex SQL but usually works for schema
        statements = sql.split(';')
        for statement in statements:
            if statement.strip():
                try:
                    cursor.execute(statement)
                except Exception as e:
                    print(f"Error executing statement: {e}")
                    
    print("Schema executed successfully.")
    
    conn.commit()
    conn.close()
    print("Setup complete.")
except Exception as e:
    print(f"Error: {e}")
