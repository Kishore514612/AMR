"""
Telemetry Database & Historical Analytics Storage (SQLite)
"""
import sqlite3
import json
import time
import os
from typing import Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "edgefleet_telemetry.db")

class TelemetryDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS p2p_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    sender TEXT,
                    recipient TEXT,
                    message_type TEXT,
                    payload_json TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS benchmark_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    scenario_id TEXT,
                    baseline_time REAL,
                    decentralized_time REAL,
                    improvement_pct REAL,
                    collisions INTEGER
                )
            """)
            conn.commit()

    def log_p2p_event(self, sender: str, recipient: str, message_type: str, payload: dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO p2p_events (timestamp, sender, recipient, message_type, payload_json)
                    VALUES (?, ?, ?, ?, ?)
                """, (time.time(), sender, recipient, message_type, json.dumps(payload)))
                conn.commit()
        except Exception:
            pass

    def log_benchmark_result(self, result: dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO benchmark_history (timestamp, scenario_id, baseline_time, decentralized_time, improvement_pct, collisions)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    time.time(),
                    result.get("scenario_id", "UNKNOWN"),
                    result.get("baseline_time", 0.0),
                    result.get("decentralized_time", 0.0),
                    result.get("improvement_pct", 0.0),
                    result.get("collisions_decentralized", 0)
                ))
                conn.commit()
        except Exception:
            pass

    def get_recent_events(self, limit: int = 50) -> List[dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, sender, recipient, message_type, payload_json
                FROM p2p_events
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [
                {
                    "timestamp": r[0],
                    "sender": r[1],
                    "recipient": r[2],
                    "message_type": r[3],
                    "payload": json.loads(r[4])
                }
                for r in rows
            ]

telemetry_db = TelemetryDB()
