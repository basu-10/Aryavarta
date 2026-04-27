import sqlite3
db = sqlite3.connect("battlecells.db")
db.execute("UPDATE player SET food=5000,timber=5000,gold=5000,metal=5000 WHERE username='admin'")
db.commit()
print("done")
db.close()
