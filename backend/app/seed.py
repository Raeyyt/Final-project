import sqlite3
from .database import DB_PATH
from .security import get_password_hash

def purge_non_admin_data() -> None:
    """Delete all school records and all users except username ``admin``."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("DELETE FROM announcements;")
        conn.execute("DELETE FROM attendance;")
        conn.execute("DELETE FROM payments;")
        conn.execute("DELETE FROM schedules;")
        conn.execute("DELETE FROM financial_reports;")
        conn.execute("DELETE FROM students;")
        conn.execute("DELETE FROM classes;")
        
        cursor = conn.execute("DELETE FROM users WHERE username != 'admin';")
        removed_users = cursor.rowcount
        
        conn.commit()
        print(f"Purge complete. Removed linked data and {removed_users} non-admin user(s).")
    except Exception as e:
        conn.rollback()
        print(f"Error during purge: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--purge":
        purge_non_admin_data()
    else:
        print("Initialization happens automatically on app startup now.")
