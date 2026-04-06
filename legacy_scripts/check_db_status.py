
import sqlite3
from datetime import datetime

def check_db():
    conn = sqlite3.connect('price_tracker.sqlite3')
    cursor = conn.cursor()
    
    print("--- 理쒓렐 20媛??섏쭛 ?곗씠??---")
    cursor.execute("""
        SELECT target_name, collected_at, success, status, price, error_message 
        FROM observations 
        ORDER BY collected_at DESC 
        LIMIT 20
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    
    print("\n--- ?寃잙퀎 理쒖떊 ?섏쭛 ?쒓컖 ---")
    cursor.execute("""
        SELECT target_name, MAX(collected_at), success
        FROM observations
        GROUP BY target_name
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(row)
        
    conn.close()

if __name__ == "__main__":
    check_db()

