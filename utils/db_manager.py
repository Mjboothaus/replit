import os
import duckdb
import pandas as pd
from typing import Optional, List, Dict, Any, Tuple
import datetime

# Database file path
DB_PATH = "tidal_data.duckdb"

def initialize_db():
    """
    Initialize the database, creating tables if they don't exist.
    """
    with duckdb.connect(DB_PATH) as conn:
        # Create table for storing location information
        conn.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY,
                latitude DOUBLE NOT NULL,
                longitude DOUBLE NOT NULL,
                area VARCHAR,
                locality VARCHAR,
                coast_distance DOUBLE,
                query_count INTEGER DEFAULT 1,
                last_queried TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create table for storing tidal information
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tidal_records (
                id INTEGER PRIMARY KEY,
                location_id INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                current_height DOUBLE NOT NULL,
                current_status VARCHAR,
                current_trend VARCHAR,
                data_source VARCHAR DEFAULT 'API',
                FOREIGN KEY (location_id) REFERENCES locations(id)
            )
        """)
        
        # Create table for storing tide forecast entries
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tide_forecasts (
                id INTEGER PRIMARY KEY,
                tidal_record_id INTEGER NOT NULL,
                tide_type VARCHAR NOT NULL,
                tide_time TIMESTAMP NOT NULL,
                tide_height DOUBLE NOT NULL,
                FOREIGN KEY (tidal_record_id) REFERENCES tidal_records(id)
            )
        """)

def save_location_data(latitude: float, longitude: float, location_info: Dict[str, Any]) -> int:
    """
    Save location information to the database.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        location_info: Dictionary containing location details
        
    Returns:
        The location ID from the database
    """
    with duckdb.connect(DB_PATH) as conn:
        # Check if location already exists (within small distance)
        result = conn.execute("""
            SELECT id, query_count FROM locations 
            WHERE ABS(latitude - ?) < 0.01 AND ABS(longitude - ?) < 0.01
            LIMIT 1
        """, [latitude, longitude]).fetchone()
        
        if result:
            # Update existing location
            location_id, query_count = result
            conn.execute("""
                UPDATE locations 
                SET query_count = ?, last_queried = CURRENT_TIMESTAMP
                WHERE id = ?
            """, [query_count + 1, location_id])
            return location_id
        else:
            # Insert new location
            conn.execute("""
                INSERT INTO locations (latitude, longitude, area, locality, coast_distance)
                VALUES (?, ?, ?, ?, ?)
            """, [
                latitude, 
                longitude, 
                location_info.get('area', 'Unknown'), 
                location_info.get('locality', 'Unknown'),
                location_info.get('coast_distance', 0)
            ])
            
            # Get the ID of the inserted location
            location_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            return location_id

def save_tidal_data(location_id: int, tidal_data: Dict[str, Any]) -> int:
    """
    Save tidal information to the database.
    
    Args:
        location_id: The location ID from the database
        tidal_data: Dictionary containing tidal data
        
    Returns:
        The tidal record ID from the database
    """
    with duckdb.connect(DB_PATH) as conn:
        # Extract current tide information
        current = tidal_data.get('current', {})
        
        # Insert tidal record
        conn.execute("""
            INSERT INTO tidal_records (
                location_id, timestamp, current_height, 
                current_status, current_trend, data_source
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            location_id,
            datetime.datetime.now(),
            current.get('height', 0),
            current.get('status', 'Unknown'),
            current.get('trend', 'Unknown'),
            'Simulated' if 'API_KEY' not in os.environ else 'API'
        ])
        
        # Get the ID of the inserted tidal record
        tidal_record_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        # Insert forecast tides
        forecast = tidal_data.get('forecast', [])
        for tide in forecast:
            # Parse the tide time - expected format is like "14:30 15-Apr"
            try:
                tide_datetime = datetime.datetime.strptime(
                    f"{tide.get('time')} {datetime.datetime.now().year}", 
                    "%H:%M %d-%b %Y"
                )
            except ValueError:
                # If parsing fails, use current time as a fallback
                tide_datetime = datetime.datetime.now()
            
            conn.execute("""
                INSERT INTO tide_forecasts (
                    tidal_record_id, tide_type, tide_time, tide_height
                )
                VALUES (?, ?, ?, ?)
            """, [
                tidal_record_id,
                tide.get('type', 'Unknown'),
                tide_datetime,
                tide.get('height', 0)
            ])
        
        return tidal_record_id

def get_most_queried_locations(limit: int = 5) -> pd.DataFrame:
    """
    Get the most frequently queried locations.
    
    Args:
        limit: Maximum number of locations to return
        
    Returns:
        DataFrame containing the most queried locations
    """
    with duckdb.connect(DB_PATH) as conn:
        result = conn.execute("""
            SELECT 
                latitude, longitude, area, locality, 
                coast_distance, query_count, last_queried
            FROM locations
            ORDER BY query_count DESC
            LIMIT ?
        """, [limit]).fetchdf()
        
        return result

def get_location_history(latitude: float, longitude: float, limit: int = 10) -> pd.DataFrame:
    """
    Get historical tidal data for a specific location.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        limit: Maximum number of records to return
        
    Returns:
        DataFrame containing historical tidal data
    """
    with duckdb.connect(DB_PATH) as conn:
        result = conn.execute("""
            SELECT 
                t.timestamp, t.current_height, t.current_status, 
                t.current_trend, t.data_source
            FROM tidal_records t
            JOIN locations l ON t.location_id = l.id
            WHERE ABS(l.latitude - ?) < 0.01 AND ABS(l.longitude - ?) < 0.01
            ORDER BY t.timestamp DESC
            LIMIT ?
        """, [latitude, longitude, limit]).fetchdf()
        
        return result

def get_tide_statistics(days: int = 30) -> pd.DataFrame:
    """
    Get statistical information about tides over a period.
    
    Args:
        days: Number of days to look back
        
    Returns:
        DataFrame containing tide statistics
    """
    with duckdb.connect(DB_PATH) as conn:
        # DuckDB doesn't support parameterized interval, so we construct the query
        query = f"""
            SELECT 
                l.area,
                AVG(t.current_height) as avg_height,
                MAX(t.current_height) as max_height,
                MIN(t.current_height) as min_height,
                COUNT(*) as record_count
            FROM tidal_records t
            JOIN locations l ON t.location_id = l.id
            WHERE t.timestamp > CURRENT_TIMESTAMP - INTERVAL '{days} DAYS'
            GROUP BY l.area
            ORDER BY avg_height DESC
        """
        result = conn.execute(query).fetchdf()
        
        return result

# Initialize database when this module is imported
initialize_db()