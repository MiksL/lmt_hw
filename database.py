# DB tables for project:
# 1. base
# 2. interceptor
# 3. object (for detected objects, threats, etc)

import sqlite3
from enum import Enum

from radar import ThreatLevel

class InterceptorType(Enum):
    DRONE   = "drone"
    JET     = "jet"
    ROCKET  = "rocket"
    FIFTYCAL = "50cal"
    
class CostType(Enum):
    FLAT = "flat"
    PER_MINUTE = "per_minute"
    
con = sqlite3.connect('radar.db', check_same_thread=False)

# AI - setting row factory for easier access and enabling WAL for concurrent read/write
con.row_factory = sqlite3.Row
con.execute('PRAGMA journal_mode=WAL')

def create_tables():
    cur = con.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS base (
            id        INTEGER PRIMARY KEY,
            name      TEXT    NOT NULL UNIQUE,
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
            latitude            REAL    NOT NULL,
            longitude           REAL    NOT NULL,
            speed_ms            REAL    NOT NULL,
            altitude_m          REAL    NOT NULL,
            heading_deg         REAL    NOT NULL,
            classification      INTEGER DEFAULT 1,
            to_be_intercepted   INTEGER NOT NULL DEFAULT 0,
            is_destroyed        INTEGER NOT NULL DEFAULT 0
        )
    ''')
    
    # Target location table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS target (
            id        INTEGER PRIMARY KEY,
            name      TEXT    NOT NULL UNIQUE,
            latitude  REAL    NOT NULL,
            longitude REAL    NOT NULL,
            exclusion_zone_m INTEGER NOT NULL DEFAULT 0
        )
    ''')

    # Intercept decision table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS intercept_decision (
            id               INTEGER PRIMARY KEY,
            track_id         TEXT    NOT NULL UNIQUE,
            interceptor_type TEXT    NOT NULL,
            intercept_lat    REAL    NOT NULL,
            intercept_lon    REAL    NOT NULL,
            intercept_time_s REAL    NOT NULL,
            intercept_cost   REAL    NOT NULL,
            assigned_at      REAL    NOT NULL
        )
    ''')

    con.commit()
    
def add_data():
    cur = con.cursor()

    # Insert Riga base
    cur.execute('''
        INSERT OR IGNORE INTO base (name, latitude, longitude, range_m)
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
    
    cur.execute('''
      INSERT OR IGNORE INTO target (name, latitude, longitude, exclusion_zone_m) VALUES
          ('Riga Base',    56.97475845607155, 24.1670070219384, 1500),
          ('Riga HES',     56.853332609436414, 24.27977593312278, 2000),
          ('RIX',          56.920238123348426, 23.974672576950766, 3000),
          ('Adazu Poligons',        57.147684,          24.401109, 10000)
    ''')
    
    con.commit()
    
def init_db():
    create_tables()
    add_data()
    
def close_db():
    con.close()

# Method for returning base information - mainly used for range
def get_base():
    cur = con.cursor()
    cur.execute('SELECT * FROM base LIMIT 1')
    row = cur.fetchone()
    return dict(row) if row else None

def get_all_objects():
    cur = con.cursor()
    cur.execute('SELECT * FROM object WHERE is_destroyed = 0')
    return [dict(row) for row in cur.fetchall()]

def mark_object_destroyed(track_id):
    cur = con.cursor()
    cur.execute('UPDATE object SET is_destroyed = 1 WHERE track_id = ?', (track_id,))
    con.commit()

def get_all_targets():
    cur = con.cursor()
    cur.execute('SELECT * FROM target')
    return [dict(row) for row in cur.fetchall()]

def update_object_position(track_id, new_lat, new_lon):
    cur = con.cursor()
    cur.execute('''
        UPDATE object
        SET latitude = ?, longitude = ?
        WHERE track_id = ?
    ''', (new_lat, new_lon, track_id))
    con.commit()
    
def save_object(track_id, lat, lon, speed_ms, altitude_m, heading_deg, report_time):
    from radar import classify_threat
    classification = classify_threat(speed_ms, altitude_m)
    cur = con.cursor()
    cur.execute('''
        INSERT OR IGNORE INTO object (track_id, detection_time, latitude, longitude, speed_ms, altitude_m, heading_deg, classification)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (track_id, report_time, lat, lon, speed_ms, altitude_m, heading_deg, classification))
    con.commit()

def update_object_classification(track_id, classification):
    cur = con.cursor()
    cur.execute('''
        UPDATE object SET classification = ? WHERE track_id = ?
    ''', (classification, track_id))
    con.commit()

def get_all_interceptors():
    cur = con.cursor()
    cur.execute('SELECT * FROM interceptor')
    return [dict(row) for row in cur.fetchall()]

def save_intercept_decision(track_id, interceptor_type, intercept_lat, intercept_lon, intercept_time_s, intercept_cost, assigned_at):
    cur = con.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO intercept_decision
            (track_id, interceptor_type, intercept_lat, intercept_lon, intercept_time_s, intercept_cost, assigned_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (track_id, interceptor_type, intercept_lat, intercept_lon, intercept_time_s, intercept_cost, assigned_at))
    cur.execute('UPDATE object SET to_be_intercepted = 1 WHERE track_id = ?', (track_id,))
    con.commit()

def get_all_intercepts():
    cur = con.cursor()
    cur.execute('''
        SELECT d.* FROM intercept_decision d
        JOIN object o ON o.track_id = d.track_id
        WHERE o.is_destroyed = 0
    ''')
    return [dict(row) for row in cur.fetchall()]

def get_intercept_by_track_id(track_id):
    cur = con.cursor()
    cur.execute('SELECT * FROM intercept_decision WHERE track_id = ?', (track_id,))
    row = cur.fetchone()
    return dict(row) if row else None