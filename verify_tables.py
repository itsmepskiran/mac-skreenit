#!/usr/bin/env python
"""Quick verification that user_subscriptions table exists"""
import mysql.connector

conn = mysql.connector.connect(
    host='127.0.0.1',
    user='root',
    password='',
    database='skreenit'
)
cursor = conn.cursor()
cursor.execute('DESCRIBE user_subscriptions')
rows = cursor.fetchall()

print("\n✅ USER_SUBSCRIPTIONS TABLE STRUCTURE:\n")
print(f"{'Column':<25} {'Type':<30} {'Null':<6} {'Key':<10} {'Default':<15}")
print("-" * 85)

for r in rows:
    col_name, col_type, nullable, key, default, extra = r
    nullable_str = 'YES' if nullable == 'YES' else 'NO'
    key_str = key if key else ''
    default_str = str(default) if default else ''
    print(f"{col_name:<25} {col_type:<30} {nullable_str:<6} {key_str:<10} {default_str:<15}")

conn.close()
print(f"\n✅ Table successfully created with {len(rows)} columns!")
