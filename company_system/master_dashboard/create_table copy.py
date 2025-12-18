import psycopg2

try:
    # Connect to PostgreSQL
    connection = psycopg2.connect(
        host="localhost",       # or your server IP if remote
        database="company_db",
        user="postgres",
        password="Admin!123",
        port="5432"
    )
    cursor = connection.cursor()
    print("✅ Connected to PostgreSQL!")

    # Create a table
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS employees (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100),
        position VARCHAR(50),
        salary DECIMAL(10, 2)
    );
    '''
    cursor.execute(create_table_query)
    connection.commit()
    print("🧱 Table 'employees' created successfully!")

    # Insert data
    insert_query = '''
    INSERT INTO employees (name, position, salary)
    VALUES
        ('John Doe', 'Developer', 70000.00),
        ('Jane Smith', 'Designer', 65000.00),
        ('Mark Wilson', 'Manager', 85000.00);
    '''
    cursor.execute(insert_query)
    connection.commit()
    print("📦 Data inserted successfully!")

    # Fetch and show data
    cursor.execute("SELECT * FROM employees;")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

except Exception as e:
    print("❌ Error:", e)

finally:
    if connection:
        cursor.close()
        connection.close()
        print("🔒 Connection closed.")
