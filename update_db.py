import sqlite3
import os

def update_database():
    # Flask-SQLAlchemy 3+ places SQLite databases in the 'instance' folder by default
    db_path = os.path.join('instance', 'grocery.db')
    if not os.path.exists(db_path):
        db_path = 'grocery.db'  # Fallback just in case
        
    print(f"Connecting to database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN wallet_balance FLOAT DEFAULT 0.0")
        cursor.execute("ALTER TABLE users ADD COLUMN successful_orders_count INTEGER DEFAULT 0")
        print("Successfully added new columns to the users table!")
    except sqlite3.OperationalError as e:
        print(f"Notice: {e}")
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    update_database()