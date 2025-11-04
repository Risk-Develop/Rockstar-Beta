import psycopg2

# Connect to PostgreSQL
try:
    connection = psycopg2.connect(
        host="localhost",       # or your server IP if remote
        database="company_db",
        user="postgres",
        password="Admin!123",
        port="5432"
    )

    print("✅ Connected to PostgreSQL successfully!")

    # Create a cursor to execute SQL commands
    cursor = connection.cursor()
    cursor.execute("SELECT version();")
    record = cursor.fetchone()
    print("Database version:", record)

except Exception as e:
    print("❌ Error while connecting to PostgreSQL:", e)

finally:
    if connection:
        cursor.close()
        connection.close()
        print("🔒 Connection closed.")
