import math
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from typing import Dict, Tuple, Any, Optional, List

# NSW boundary coordinates (approximate)
NSW_MIN_LAT = -37.5
NSW_MAX_LAT = -28.0
NSW_MIN_LON = 140.999922
NSW_MAX_LON = 153.638747

# Coastal boundary - areas within this distance from coast are considered coastal
COASTAL_DISTANCE_KM = 20

# NSW major coastal locations for reference
NSW_COASTAL_LOCATIONS = [
    {"name": "Sydney", "lat": -33.865143, "lon": 151.209900},
    {"name": "Newcastle", "lat": -32.916668, "lon": 151.750000},
    {"name": "Wollongong", "lat": -34.425072, "lon": 150.893143},
    {"name": "Port Macquarie", "lat": -31.433334, "lon": 152.900000},
    {"name": "Coffs Harbour", "lat": -30.296665, "lon": 153.114136},
    {"name": "Byron Bay", "lat": -28.647980, "lon": 153.618698},
    {"name": "Batemans Bay", "lat": -35.708332, "lon": 150.174728},
    {"name": "Eden", "lat": -37.063755, "lon": 149.900543},
    {"name": "Port Stephens", "lat": -32.716667, "lon": 152.166672},
    {"name": "Jervis Bay", "lat": -35.040279, "lon": 150.727844}
]

def is_valid_nsw_location(latitude: float, longitude: float) -> Tuple[bool, Dict[str, Any]]:
    """
    Validates if the given coordinates are within NSW, Australia and near the coast.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        Tuple containing:
        - Boolean indicating if location is valid NSW coastal location
        - Dictionary with location information
    """
    # Check if coordinates are within NSW bounding box
    if not (NSW_MIN_LAT <= latitude <= NSW_MAX_LAT and 
            NSW_MIN_LON <= longitude <= NSW_MAX_LON):
        return False, {"error": "Location is outside NSW boundaries"}
    
    # Initialize location info dictionary
    location_info = {
        "lat": latitude,
        "lon": longitude,
        "state": "NSW",
        "country": "Australia",
        "area": "Unknown",
        "locality": "Unknown",
        "coast_distance": "Unknown"
    }
    
    # Attempt reverse geocoding to get location details
    try:
        geolocator = Nominatim(user_agent="nsw_tidal_info_app")
        location = geolocator.reverse(f"{latitude}, {longitude}", language="en")
        
        if location and location.raw.get("address"):
            address = location.raw.get("address", {})
            
            location_info.update({
                "area": address.get("state_district", address.get("county", "Unknown NSW Region")),
                "locality": address.get("city", address.get("town", address.get("village", "Unknown")))
            })
            
            # Check if the address mentions NSW or New South Wales
            address_str = str(address).lower()
            if "nsw" not in address_str and "new south wales" not in address_str:
                # Double check our boundary detection with geocoding result
                return False, {"error": "Location is outside NSW according to geocoding"}
    
    except (GeocoderTimedOut, GeocoderUnavailable):
        # Geocoding service unavailable, fall back to boundary check only
        pass
    
    # Check distance to coast by finding nearest coastal point
    coast_distance = find_distance_to_coast(latitude, longitude)
    location_info["coast_distance"] = coast_distance
    
    # Determine if location is coastal
    is_coastal = coast_distance <= COASTAL_DISTANCE_KM
    
    return is_coastal, location_info

def find_distance_to_coast(latitude: float, longitude: float) -> float:
    """
    Find approximate distance to the nearest coastal point.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        Approximate distance to coast in kilometers
    """
    # Calculate distances to known coastal locations
    distances = []
    
    for coastal_point in NSW_COASTAL_LOCATIONS:
        distance = haversine_distance(
            latitude, longitude,
            coastal_point["lat"], coastal_point["lon"]
        )
        distances.append(distance)
    
    # Return the minimum distance
    return min(distances)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on earth.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
        
    Returns:
        Distance in kilometers between the two points
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    
    return c * r
