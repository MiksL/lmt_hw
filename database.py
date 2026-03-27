# DB tables for project:
# 1. base
# 2. interceptor
# 3. object (for detected objects, threats, etc)

import sqlite3
from enum import Enum

class InterceptorType(Enum):
    DRONE   = "drone"
    JET     = "jet"
    ROCKET  = "rocket"
    FIFTYCAL = "50cal"
    
class CostType(Enum):
    FLAT = "flat"
    PER_MINUTE = "per_minute"

def create_tables():
    con = sqlite3.connect('radar.db')
    cur = con.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS base (
            id        INTEGER PRIMARY KEY,
            name      TEXT    NOT NULL,
            latitude  REAL    NOT NULL,
            longitude REAL    NOT NULL,
            range_m   INTEGER NOT NULL
        )
    ''')
    
    # Interceptor table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS interceptor (
            id            INTEGER PRIMARY KEY,
            type          TEXT    NOT NULL UNIQUE,
            speed_ms      INTEGER NOT NULL,
            range_m       INTEGER NOT NULL,
            max_altitude_m INTEGER NOT NULL,
            cost          REAL    NOT NULL,
            cost_type     TEXT    NOT NULL
        )
    ''')
    
    # Object table - contains all objects detected by the radar
    cur.execute('''
        CREATE TABLE IF NOT EXISTS object (
            id                  INTEGER PRIMARY KEY,
            track_id            TEXT    NOT NULL UNIQUE,
            detection_time      INTEGER NOT NULL,
            lat         REAL    NOT NULL,
            lon         REAL    NOT NULL,
            speed_ms    REAL    NOT NULL,
            altitude_m  REAL    NOT NULL,
            heading_deg REAL    NOT NULL,
            classification      INTEGER NOT NULL,
            to_be_intercepted   INTEGER NOT NULL DEFAULT 0
        )
    ''')
    
    con.commit()
    con.close()
    
def add_data():
    con = sqlite3.connect('radar.db')
    cur = con.cursor()

    # Insert Riga base
    cur.execute('''
        INSERT INTO base (name, latitude, longitude, range_m)
        VALUES (?, ?, ?, ?)
    ''', ('Riga', 56.97475845607155, 24.1670070219384, 100000))
    
    # Interceptor insertions (OR IGNORE added by AI)
    cur.execute('''
        INSERT OR IGNORE INTO interceptor (type, speed_ms, range_m, max_altitude_m, cost, cost_type)
        VALUES
            ('drone',  80,   30000,    2000,   10000,  'flat'),
            ('jet',    700,  3500000,  15000,  1000,   'per_minute'),
            ('rocket', 1500, 10000000, 300000, 300000, 'flat'),
            ('50cal',  900,  2000,     2000,   1,      'flat')
    ''')
    
    con.commit()
    con.close()