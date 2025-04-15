import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from utils.location_validator import is_valid_nsw_location
from utils.tidal_api import get_tidal_data

# Page configuration
st.set_page_config(
    page_title="NSW Tidal Information",
    page_icon="🌊",
    layout="wide"
)

# App title and description
st.title("NSW Tidal Information")
st.markdown("""
    This application provides real-time and predicted tidal information for coastal locations in New South Wales, Australia.
    Enter your GPS coordinates below to get started.
""")

# Create two columns for input
col1, col2 = st.columns(2)

with col1:
    latitude = st.number_input(
        "Latitude",
        min_value=-37.5,
        max_value=-28.0,
        value=-33.865143,
        step=0.000001,
        format="%.6f",
        help="Enter latitude (NSW is approximately between -37.5° and -28.0°)"
    )

with col2:
    longitude = st.number_input(
        "Longitude",
        min_value=140.999922,
        max_value=153.638747,
        value=151.209900,
        step=0.000001,
        format="%.6f",
        help="Enter longitude (NSW is approximately between 141.0° and 153.6°)"
    )

# Button to get tidal information
if st.button("Get Tidal Information"):
    # Display a spinner while processing
    with st.spinner("Validating location and fetching tidal data..."):
        # Validate if coordinates are in NSW coastal area
        location_valid, location_info = is_valid_nsw_location(latitude, longitude)
        
        if not location_valid:
            st.error("The coordinates you provided are not within NSW coastal region. Please enter valid NSW coordinates.")
        else:
            # Display location information
            st.subheader("Location Information")
            st.write(f"**Area**: {location_info.get('area', 'Unknown')}")
            st.write(f"**Locality**: {location_info.get('locality', 'Unknown')}")
            st.write(f"**Distance from coast**: Approximately {location_info.get('coast_distance', 'Unknown')} km")
            
            # Fetch tidal data
            tidal_data = get_tidal_data(latitude, longitude)
            
            if not tidal_data:
                st.error("Unable to fetch tidal data for the provided location. Please try again or try a different location.")
            else:
                # Current tide information
                st.subheader("Current Tide Information")
                current_tide = tidal_data['current']
                
                # Create columns for current tide info
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Current Tide Level", 
                        f"{current_tide['height']:.2f} m",
                        f"{current_tide['trend']}"
                    )
                
                with col2:
                    st.metric(
                        "Tide Status", 
                        current_tide['status']
                    )
                
                with col3:
                    st.write("**Last Updated:**")
                    st.write(f"{current_tide['timestamp']}")
                
                # Upcoming tides section
                st.subheader("Upcoming Tides")
                
                # Create a DataFrame from the forecast data
                forecast_df = pd.DataFrame(tidal_data['forecast'])
                
                # Split the display into columns
                tide_cols = st.columns(min(4, len(forecast_df)))
                
                for i, (_, tide) in enumerate(forecast_df.iterrows()):
                    if i < len(tide_cols):
                        with tide_cols[i]:
                            st.markdown(f"**{tide['type']} Tide**")
                            st.markdown(f"Time: {tide['time']}")
                            st.markdown(f"Height: {tide['height']:.2f} m")
                
                # Add tidal chart
                st.subheader("Tidal Chart (48 Hours)")
                
                # Prepare data for plotting
                chart_df = pd.DataFrame(tidal_data['chart_data'])
                
                # Create the line chart
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=chart_df['time'],
                    y=chart_df['height'],
                    mode='lines',
                    name='Tide Height',
                    line=dict(color='#1E88E5', width=3)
                ))
                
                # Add markers for high and low tides
                high_tides = chart_df[chart_df['type'] == 'High']
                low_tides = chart_df[chart_df['type'] == 'Low']
                
                fig.add_trace(go.Scatter(
                    x=high_tides['time'],
                    y=high_tides['height'],
                    mode='markers',
                    name='High Tide',
                    marker=dict(color='#D32F2F', size=10)
                ))
                
                fig.add_trace(go.Scatter(
                    x=low_tides['time'],
                    y=low_tides['height'],
                    mode='markers',
                    name='Low Tide',
                    marker=dict(color='#388E3C', size=10)
                ))
                
                # Add a line for the current time
                now = datetime.datetime.now()
                fig.add_vline(x=now, line_width=2, line_dash="dash", line_color="gray")
                
                # Update layout
                fig.update_layout(
                    title="Tide Height Forecast",
                    xaxis_title="Time",
                    yaxis_title="Height (meters)",
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    height=500,
                    margin=dict(l=0, r=0, t=30, b=0),
                )
                
                # Display the chart
                st.plotly_chart(fig, use_container_width=True)
                
                # Additional information section
                st.subheader("Additional Information")
                st.markdown("""
                    - Tide times are in local time.
                    - Tide heights are measured in meters.
                    - The data is retrieved from the Australian Bureau of Meteorology or similar reliable sources.
                    - For navigation purposes, always consult official maritime sources.
                """)
                
                # Data source acknowledgment
                st.markdown("---")
                st.caption("Data sourced from Willyweather API or similar services. Last updated: " + 
                          datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Display help information at the bottom
with st.expander("Help & Information"):
    st.markdown("""
    ### How to use this app
    
    1. Enter the latitude and longitude of your NSW location
    2. Click "Get Tidal Information" to retrieve and display the tidal data
    3. View current tide information, upcoming tides, and the 48-hour forecast chart
    
    ### About NSW Tidal Regions
    
    New South Wales (NSW) has a coastline of about 2,137 km, featuring a variety of coastal environments including beaches, bays, and estuaries. Major coastal areas include:
    
    - Sydney Harbour
    - Port Stephens
    - Jervis Bay
    - Byron Bay
    - Newcastle
    - Wollongong
    
    ### About Tidal Data
    
    Tidal information is important for various activities such as:
    - Fishing
    - Boating and sailing
    - Beach activities
    - Coastal research
    - Marine wildlife observation
    """)
