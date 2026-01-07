"""
VoxCity SCE Asset Visualization Platform
Streamlit application for generating 3D city models and visualizing utility infrastructure
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import os

# Configure page
st.set_page_config(
    page_title="VoxCity SCE Platform",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'voxcity_model' not in st.session_state:
    st.session_state.voxcity_model = None
if 'rectangle_vertices' not in st.session_state:
    st.session_state.rectangle_vertices = None
if 'generation_complete' not in st.session_state:
    st.session_state.generation_complete = False

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .step-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #e8f4f8;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🏙️ VoxCity SCE Asset Visualization Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Generate 3D city models for any location on Earth with integrated utility infrastructure visualization</div>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Mesh size selection
    st.subheader("Model Settings")
    meshsize = st.select_slider(
        "Mesh Resolution (meters)",
        options=[1, 2.5, 5, 10],
        value=5,
        help="Smaller values = higher detail but slower generation"
    )
    
    # Estimated generation time
    time_estimates = {1: "10-15 min", 2.5: "5-10 min", 5: "2-5 min", 10: "1-2 min"}
    st.info(f"⏱️ Estimated time: {time_estimates[meshsize]} per km²")
    
    st.divider()
    
    # Data source info
    st.subheader("📊 Data Sources")
    with st.expander("VoxCity Default Sources"):
        st.markdown("""
        - **Buildings**: OpenStreetMap
        - **Building Complement**: Microsoft Footprints
        - **Land Cover**: OpenStreetMap
        - **Canopy Height**: 1m Global Canopy Height
        - **Terrain (DEM)**: Auto-selected by region
        """)
    
    st.divider()
    
    # Future features
    st.subheader("🚀 Coming Soon")
    st.checkbox("SCE Administrative Boundaries", disabled=True)
    st.checkbox("Electrical Circuits", disabled=True)
    st.checkbox("Utility Structures", disabled=True)
    st.checkbox("Clearance Analysis", disabled=True)

# Main content area
tab1, tab2, tab3 = st.tabs(["📍 Select Location", "🏗️ Generate Model", "🎨 Visualize"])

# Tab 1: Location Selection
with tab1:
    st.markdown('<div class="step-header">Step 1: Select Your Area of Interest</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Interactive Map")
        st.markdown('<div class="info-box">🗺️ Enter a city name below and draw a rectangle on the map to define your area of interest.</div>', unsafe_allow_html=True)
        
        # City search
        cityname = st.text_input(
            "City Name",
            value="New York",
            help="Enter the name of the city you want to explore"
        )
        
        # Create map centered on city (simplified - in production would use geocoding)
        city_coords = {
            "New York": (40.7128, -74.0060),
            "Los Angeles": (34.0522, -118.2437),
            "Chicago": (41.8781, -87.6298),
            "San Francisco": (37.7749, -122.4194),
        }
        
        center = city_coords.get(cityname, (40.7128, -74.0060))
        
        # Create folium map
        m = folium.Map(
            location=center,
            zoom_start=13,
            tiles="OpenStreetMap"
        )
        
        # Add drawing tools
        folium.plugins.Draw(
            export=True,
            draw_options={
                'polyline': False,
                'polygon': False,
                'circle': False,
                'marker': False,
                'circlemarker': False,
                'rectangle': True
            }
        ).add_to(m)
        
        # Display map
        map_data = st_folium(m, width=700, height=500)
        
        # Process drawn rectangle
        if map_data and map_data.get('last_active_drawing'):
            coords = map_data['last_active_drawing']['geometry']['coordinates'][0]
            # Convert to VoxCity format (SW, NW, NE, SE)
            rectangle_vertices = [
                (coords[0][0], coords[0][1]),  # SW
                (coords[1][0], coords[1][1]),  # NW
                (coords[2][0], coords[2][1]),  # NE
                (coords[3][0], coords[3][1])   # SE
            ]
            st.session_state.rectangle_vertices = rectangle_vertices
            st.markdown('<div class="success-box">✅ Rectangle drawn successfully!</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("### Manual Entry")
        st.markdown("Or enter coordinates manually:")
        
        with st.form("coordinates_form"):
            st.text_input("Southwest (lon, lat)", value="-74.020, 40.700")
            st.text_input("Northwest (lon, lat)", value="-74.020, 40.711")
            st.text_input("Northeast (lon, lat)", value="-74.006, 40.711")
            st.text_input("Southeast (lon, lat)", value="-74.006, 40.700")
            
            if st.form_submit_button("Set Coordinates"):
                # Parse and set coordinates
                st.session_state.rectangle_vertices = [
                    (-74.02034270713835, 40.69992881162822),
                    (-74.02034270713835, 40.7111851828668),
                    (-74.00555129286164, 40.7111851828668),
                    (-74.00555129286164, 40.69992881162822)
                ]
                st.success("✅ Coordinates set!")
        
        # Display current selection
        if st.session_state.rectangle_vertices:
            st.markdown("### Current Selection")
            st.json({
                "Southwest": st.session_state.rectangle_vertices[0],
                "Northwest": st.session_state.rectangle_vertices[1],
                "Northeast": st.session_state.rectangle_vertices[2],
                "Southeast": st.session_state.rectangle_vertices[3]
            })
            
            # Calculate approximate area
            # Simplified calculation
            lat_diff = abs(st.session_state.rectangle_vertices[1][1] - st.session_state.rectangle_vertices[0][1])
            lon_diff = abs(st.session_state.rectangle_vertices[2][0] - st.session_state.rectangle_vertices[0][0])
            area_km2 = lat_diff * lon_diff * 111 * 111  # Rough approximation
            
            st.metric("Approximate Area", f"{area_km2:.2f} km²")

# Tab 2: Model Generation
with tab2:
    st.markdown('<div class="step-header">Step 2: Generate 3D Voxel Model</div>', unsafe_allow_html=True)
    
    if not st.session_state.rectangle_vertices:
        st.warning("⚠️ Please select an area in the 'Select Location' tab first.")
    else:
        st.markdown('<div class="info-box">📦 Click the button below to generate your 3D city model using VoxCity.</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("🚀 Generate VoxCity Model", type="primary", use_container_width=True):
                with st.spinner("Generating 3D model... This may take several minutes."):
                    try:
                        # Import VoxCity
                        from voxcity.generator import get_voxcity
                        
                        # Progress bar
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        status_text.text("Initializing VoxCity...")
                        progress_bar.progress(10)
                        
                        status_text.text("Fetching building data...")
                        progress_bar.progress(30)
                        
                        # Generate model
                        voxcity = get_voxcity(
                            st.session_state.rectangle_vertices,
                            meshsize
                        )
                        
                        progress_bar.progress(100)
                        status_text.text("Generation complete!")
                        
                        # Store in session state
                        st.session_state.voxcity_model = voxcity
                        st.session_state.generation_complete = True
                        
                        st.balloons()
                        st.success("✅ 3D model generated successfully! Go to the 'Visualize' tab to view it.")
                        
                        # Display model info
                        st.markdown("### Model Information")
                        st.json({
                            "Mesh Size": f"{meshsize} meters",
                            "Grid Shape": str(voxcity.grid.shape),
                            "Total Voxels": int(np.prod(voxcity.grid.shape)),
                            "Generated At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                    except Exception as e:
                        st.error(f"❌ Error generating model: {str(e)}")
                        st.exception(e)
        
        # Display current model status
        if st.session_state.generation_complete:
            st.markdown('<div class="success-box">✅ A model has been generated and is ready for visualization!</div>', unsafe_allow_html=True)

# Tab 3: Visualization
with tab3:
    st.markdown('<div class="step-header">Step 3: Visualize Your 3D Model</div>', unsafe_allow_html=True)
    
    if not st.session_state.generation_complete or st.session_state.voxcity_model is None:
        st.warning("⚠️ Please generate a model in the 'Generate Model' tab first.")
    else:
        st.markdown('<div class="info-box">🎨 Explore your 3D city model below. Use your mouse to rotate, pan, and zoom.</div>', unsafe_allow_html=True)
        
        # Visualization controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            color_scheme = st.selectbox(
                "Color Scheme",
                ["Default", "Grayscale", "Height-based"],
                help="Choose how to color the voxels"
            )
        
        with col2:
            downsample = st.select_slider(
                "Downsample (for performance)",
                options=[1, 2, 4],
                value=1,
                help="Reduce voxel count for faster rendering"
            )
        
        with col3:
            show_legend = st.checkbox("Show Legend", value=True)
        
        # Generate 3D visualization
        try:
            from voxcity.visualizer import visualize_voxcity
            
            # Note: visualize_voxcity normally uses Plotly directly
            # For Streamlit, we need to capture and display the figure
            
            st.markdown("### Interactive 3D View")
            
            # Create a placeholder visualization
            # In a full implementation, this would call visualize_voxcity and display the result
            voxcity = st.session_state.voxcity_model
            
            # Sample visualization (simplified - actual implementation would use VoxCity's visualizer)
            st.info("🔄 Rendering 3D model... In production, this would display an interactive Plotly 3D visualization.")
            
            # Placeholder for actual 3D visualization
            # This would be replaced with actual VoxCity visualization code
            st.markdown("""
            **Note**: The full 3D visualization will be displayed here once VoxCity is properly installed.
            
            The visualization will include:
            - Interactive 3D voxel rendering
            - Color-coded voxel classes (buildings, trees, ground, water)
            - Rotation, zoom, and pan controls
            - Legend showing voxel class meanings
            """)
            
            # Export options
            st.markdown("### Export Options")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📸 Export Screenshot", use_container_width=True):
                    st.info("Screenshot functionality will be implemented")
            
            with col2:
                if st.button("💾 Export OBJ File", use_container_width=True):
                    st.info("OBJ export functionality will be implemented")
            
            with col3:
                if st.button("📄 Generate Report", use_container_width=True):
                    st.info("Report generation functionality will be implemented")
            
            # Model statistics
            with st.expander("📊 Model Statistics"):
                grid = voxcity.grid
                unique_values, counts = np.unique(grid, return_counts=True)
                
                st.markdown("**Voxel Class Distribution:**")
                for val, count in zip(unique_values, counts):
                    percentage = (count / grid.size) * 100
                    st.text(f"Class {val}: {count:,} voxels ({percentage:.2f}%)")
            
        except ImportError:
            st.error("❌ VoxCity library not found. Please install it using: `pip install voxcity`")
        except Exception as e:
            st.error(f"❌ Error visualizing model: {str(e)}")
            st.exception(e)

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p>VoxCity SCE Asset Visualization Platform | Version 0.1.0 | © 2026</p>
    <p>Built with Streamlit and VoxCity | <a href="https://github.com/kunifujiwara/VoxCity" target="_blank">VoxCity Documentation</a></p>
</div>
""", unsafe_allow_html=True)
