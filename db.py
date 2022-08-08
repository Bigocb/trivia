import sqlite3


connection = sqlite3.connect("aquarium.db")
print(connection.total_changes)
cursor = connection.cursor()
cursor.execute("CREATE TABLE correct (question TEXT, user INTEGER)")
cursor.execute("CREATE TABLE wrong (question TEXT, user INTEGER)")
cursor.execute('CREATE TABLE score (score TEXT, user INTEGER, count INTEGER)')
t = cursor.execute("delete from correct where user = 1")
user_data = cursor.execute("SELECT * FROM correct where user = 1").fetchall()
connection.commit()
print(user_data)
