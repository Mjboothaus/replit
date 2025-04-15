import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from utils.location_validator import is_valid_nsw_location
from utils.tidal_api import get_tidal_data
from utils.db_manager import (
    save_location_data, 
    save_tidal_data, 
    get_most_queried_locations,
    get_location_history,
    get_tide_statistics
)

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
                # Save data to DuckDB
                location_id = save_location_data(latitude, longitude, location_info)
                tidal_record_id = save_tidal_data(location_id, tidal_data)
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

# Add Database Analysis section
st.markdown("---")
st.header("Historical Data & Statistics")
st.markdown("Analysis of historical tidal data from the database")

tab1, tab2, tab3 = st.tabs(["Popular Locations", "Historical Data", "Tidal Statistics"])

with tab1:
    st.subheader("Most Queried Locations")
    popular_locations = get_most_queried_locations(limit=10)
    
    if not popular_locations.empty:
        # Format the data for display
        popular_locations['last_queried'] = pd.to_datetime(popular_locations['last_queried']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Display the table
        st.dataframe(
            popular_locations[['area', 'locality', 'latitude', 'longitude', 'query_count', 'last_queried']],
            use_container_width=True,
            column_config={
                "area": "Area",
                "locality": "Locality",
                "latitude": st.column_config.NumberColumn("Latitude", format="%.6f"),
                "longitude": st.column_config.NumberColumn("Longitude", format="%.6f"),
                "query_count": st.column_config.NumberColumn("Queries", help="Number of times this location was queried"),
                "last_queried": "Last Queried"
            }
        )
        
        # Add a map of most queried locations
        st.subheader("Map of Popular Locations")
        map_data = popular_locations[['latitude', 'longitude']].copy()
        if not map_data.empty:
            st.map(map_data)
    else:
        st.info("No location data available yet. Try searching for some locations first!")

with tab2:
    st.subheader("Location History")
    st.write("View historical tide data for a specific location")
    
    hist_col1, hist_col2 = st.columns(2)
    with hist_col1:
        hist_lat = st.number_input(
            "Latitude",
            min_value=-37.5,
            max_value=-28.0,
            value=-33.865143,
            step=0.000001,
            format="%.6f",
            key="hist_lat"
        )
    
    with hist_col2:
        hist_lon = st.number_input(
            "Longitude",
            min_value=140.999922,
            max_value=153.638747,
            value=151.209900,
            step=0.000001,
            format="%.6f",
            key="hist_lon"
        )
    
    if st.button("Get Historical Data"):
        history_data = get_location_history(hist_lat, hist_lon)
        
        if not history_data.empty:
            # Format the data for display
            history_data['timestamp'] = pd.to_datetime(history_data['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Display the table
            st.dataframe(
                history_data,
                use_container_width=True,
                column_config={
                    "timestamp": "Timestamp",
                    "current_height": st.column_config.NumberColumn("Tide Height (m)", format="%.2f"),
                    "current_status": "Status",
                    "current_trend": "Trend",
                    "data_source": "Data Source"
                }
            )
            
            # Create a chart of historical tide heights
            if len(history_data) > 1:
                st.subheader("Historical Tide Heights")
                
                # Convert timestamps back to datetime for plotting
                history_data['timestamp'] = pd.to_datetime(history_data['timestamp'])
                
                # Create the line chart
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=history_data['timestamp'],
                    y=history_data['current_height'],
                    mode='lines+markers',
                    name='Tide Height',
                    line=dict(color='#1E88E5', width=2)
                ))
                
                # Update layout
                fig.update_layout(
                    title="Historical Tide Heights",
                    xaxis_title="Time",
                    yaxis_title="Height (meters)",
                    height=400,
                    margin=dict(l=0, r=0, t=30, b=0),
                )
                
                # Display the chart
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No historical data available for this location.")

with tab3:
    st.subheader("Tidal Statistics")
    
    # Get time period for statistics
    days_for_stats = st.slider("Time Period (days)", min_value=1, max_value=90, value=30)
    
    stats_data = get_tide_statistics(days=days_for_stats)
    
    if not stats_data.empty:
        # Display the statistics table
        st.dataframe(
            stats_data,
            use_container_width=True,
            column_config={
                "area": "Area",
                "avg_height": st.column_config.NumberColumn("Average Height (m)", format="%.2f"),
                "max_height": st.column_config.NumberColumn("Maximum Height (m)", format="%.2f"),
                "min_height": st.column_config.NumberColumn("Minimum Height (m)", format="%.2f"),
                "record_count": st.column_config.NumberColumn("Number of Records")
            }
        )
        
        # Add a bar chart for average heights by area
        if len(stats_data) > 1:
            st.subheader("Average Tide Heights by Area")
            
            # Create the bar chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=stats_data['area'],
                y=stats_data['avg_height'],
                marker_color='#1E88E5'
            ))
            
            # Update layout
            fig.update_layout(
                xaxis_title="Area",
                yaxis_title="Average Height (meters)",
                height=400,
                margin=dict(l=0, r=0, t=10, b=0),
            )
            
            # Display the chart
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"No statistics available for the last {days_for_stats} days. Try a different time period or query more locations.")

# Display help information at the bottom
with st.expander("Help & Information"):
    st.markdown("""
    ### How to use this app
    
    1. Enter the latitude and longitude of your NSW location
    2. Click "Get Tidal Information" to retrieve and display the tidal data
    3. View current tide information, upcoming tides, and the 48-hour forecast chart
    4. Explore historical data and statistics in the tabs below
    
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
    
    ### About the Database
    
    This application uses DuckDB to store historical tidal data. Each time you query a location,
    the data is saved to the database for future reference and analysis.
    """)
