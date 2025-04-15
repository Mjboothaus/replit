import requests
import os
import datetime
import time
import json
import math
from typing import Dict, List, Any, Optional

# Willyweather API is used for demonstration
# Alternative APIs could be:
# - Bureau of Meteorology (BOM)
# - NSW Tide Tables
# - Australian Hydrographic Service

# Get API key from environment variables
API_KEY = os.getenv("WILLYWEATHER_API_KEY", "")

def get_tidal_data(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """
    Fetch tidal data from the API for the given coordinates.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        Dictionary containing tidal information or None if the request fails
    """
    # If we don't have an API key, use fallback data structure
    if not API_KEY:
        # In a real scenario, we would return None or show an error
        # For this demo, we'll implement a function to generate realistic tidal data
        return generate_simulated_tidal_data(latitude, longitude)
    
    try:
        # Find the closest tidal station
        station_url = f"https://api.willyweather.com.au/v2/{API_KEY}/search.json"
        station_params = {
            "lat": latitude,
            "lng": longitude,
            "units": "distance:km",
            "types": "tide",
            "limit": 1
        }
        
        response = requests.get(station_url, params=station_params)
        response.raise_for_status()
        station_data = response.json()
        
        if not station_data["location"]:
            return None
            
        location_id = station_data["location"][0]["id"]
        
        # Get tidal data for this location
        tides_url = f"https://api.willyweather.com.au/v2/{API_KEY}/locations/{location_id}/weather.json"
        
        # Setting the forecast days to 2 (48 hours)
        tides_params = {
            "forecasts": "tides",
            "days": 2,
            "startDate": datetime.date.today().strftime('%Y-%m-%d')
        }
        
        response = requests.get(tides_url, params=tides_params)
        response.raise_for_status()
        tides_data = response.json()
        
        # Process the tide data to format needed by the app
        tides = tides_data.get("forecasts", {}).get("tides", {})
        
        # Get current tide data
        current_tide = {
            "height": tides.get("current", {}).get("height", 0),
            "status": "High" if tides.get("current", {}).get("isHigh", False) else "Low",
            "trend": "Rising" if tides.get("current", {}).get("rising", False) else "Falling",
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        
        # Get the forecast tides (next high and low)
        tide_points = tides.get("days", [])[0].get("entries", [])
        
        forecast_tides = []
        for point in tide_points:
            tide_time = datetime.datetime.fromisoformat(point.get("dateTime").replace('Z', '+00:00'))
            local_time = tide_time.astimezone().strftime('%H:%M %d-%b')
            
            forecast_tides.append({
                "type": "High" if point.get("type") == "high" else "Low",
                "time": local_time,
                "height": point.get("height", 0)
            })
        
        # Prepare chart data for 48-hour visualization
        all_points = []
        for day in tides.get("days", []):
            for point in day.get("points", []):
                tide_time = datetime.datetime.fromisoformat(point.get("dateTime").replace('Z', '+00:00'))
                
                all_points.append({
                    "time": tide_time.astimezone(),
                    "height": point.get("height", 0),
                    "type": "Normal"
                })
        
        # Add high and low tide markers for visualization
        for day in tides.get("days", []):
            for entry in day.get("entries", []):
                tide_time = datetime.datetime.fromisoformat(entry.get("dateTime").replace('Z', '+00:00'))
                
                tide_type = "High" if entry.get("type") == "high" else "Low"
                all_points.append({
                    "time": tide_time.astimezone(),
                    "height": entry.get("height", 0),
                    "type": tide_type
                })
        
        # Sort all points by time
        all_points.sort(key=lambda x: x["time"])
        
        return {
            "current": current_tide,
            "forecast": forecast_tides[:4],  # Next 4 tide events
            "chart_data": all_points
        }
        
    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        return None
    except Exception as e:
        print(f"Error fetching tidal data: {e}")
        return None

def generate_simulated_tidal_data(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Generate realistic tidal data for demo purposes when API key is missing.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        Dictionary containing simulated tidal information
    """
    # This is only used when no API key is available
    # In a production environment, we would return an error or prompt for API key
    
    now = datetime.datetime.now()
    
    # Base amplitude and period settings for a realistic tide pattern
    amplitude = 0.8 + (abs(latitude) % 10) / 50  # Vary between 0.6m and 1.0m
    period = 12.42  # Average tidal period (lunar semi-diurnal) in hours
    
    # Determine if currently rising or falling and current status
    hour_in_cycle = (now.hour + now.minute/60) % period
    is_rising = hour_in_cycle < period/2
    
    # Calculate current height using a sine wave approximation
    normalized_time = (hour_in_cycle / period) * 2 * 3.14159
    baseline = 1.5  # Mean sea level
    current_height = baseline + amplitude * (
        -1 * ((normalized_time - 3.14159/2) / 3.14159) 
        if is_rising else 
        ((normalized_time - 3.14159/2) / 3.14159)
    )
    
    # Determine if high or low tide
    is_high = hour_in_cycle > 0.8 * period/2 and hour_in_cycle < 1.2 * period/2
    
    # Current tide info
    current_tide = {
        "height": round(current_height, 2),
        "status": "Near High" if is_high else "Mid" if (0.3 < hour_in_cycle/period < 0.7) else "Near Low",
        "trend": "Rising" if is_rising else "Falling",
        "timestamp": now.strftime('%Y-%m-%d %H:%M')
    }
    
    # Generate forecast tides
    forecast_tides = []
    
    # Calculate time to next high/low tide
    hours_to_next = period/2 - hour_in_cycle if hour_in_cycle < period/2 else period - hour_in_cycle
    
    # Next high/low tide
    next_tide_time = now + datetime.timedelta(hours=hours_to_next)
    next_tide_type = "Low" if is_rising else "High"
    next_tide_height = baseline - amplitude if next_tide_type == "Low" else baseline + amplitude
    
    forecast_tides.append({
        "type": next_tide_type,
        "time": next_tide_time.strftime('%H:%M %d-%b'),
        "height": round(next_tide_height, 2)
    })
    
    # Generate subsequent tides
    for i in range(1, 4):
        subsequent_tide_time = next_tide_time + datetime.timedelta(hours=period/2 * i)
        subsequent_tide_type = "High" if (i % 2 == 1 and next_tide_type == "Low") or (i % 2 == 0 and next_tide_type == "High") else "Low"
        subsequent_tide_height = baseline + amplitude if subsequent_tide_type == "High" else baseline - amplitude
        
        forecast_tides.append({
            "type": subsequent_tide_type,
            "time": subsequent_tide_time.strftime('%H:%M %d-%b'),
            "height": round(subsequent_tide_height, 2)
        })
    
    # Generate 48-hour chart data
    chart_data = []
    
    # Generate a point every 30 minutes for 48 hours
    for i in range(96):  # 30 min intervals for 48 hours = 96 points
        point_time = now + datetime.timedelta(minutes=30 * i)
        hour_in_cycle = (point_time.hour + point_time.minute/60) % period
        normalized_time = (hour_in_cycle / period) * 2 * 3.14159
        
        point_height = baseline + amplitude * math.sin(normalized_time)
        
        # Identify if this is a high or low tide point (every 6.21 hours)
        point_type = "Normal"
        if i % 12 == 0:  # This creates high and low tide points
            point_type = "High" if (i // 12) % 2 == 0 else "Low"
        
        chart_data.append({
            "time": point_time,
            "height": round(point_height, 2),
            "type": point_type
        })
    
    return {
        "current": current_tide,
        "forecast": forecast_tides,
        "chart_data": chart_data
    }
