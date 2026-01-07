# VoxCity SCE Asset Visualization Platform

![VoxCity Banner](https://img.shields.io/badge/VoxCity-3D%20Visualization-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9+-green?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31+-red?style=for-the-badge&logo=streamlit)

An interactive Streamlit application for generating high-fidelity 3D voxel models of any location on Earth, with integrated Southern California Edison (SCE) utility asset visualization capabilities.

## 🎯 Project Goals

This experimental platform aims to:

1. **Democratize 3D Urban Modeling**: Enable anyone to generate professional-quality 3D city models through an intuitive web interface, without requiring coding skills or GIS expertise.

2. **Integrate Utility Infrastructure**: Overlay electrical grid assets (circuits, poles, towers, boundaries) onto accurate 3D representations of the urban environment for enhanced spatial analysis.

3. **Enable Advanced Analysis**: Support vegetation management, clearance analysis, circuit planning, and infrastructure siting through 3D visualization and computational tools.

4. **Streamline Workflows**: Reduce the time and complexity of utility planning and operations tasks by providing integrated data and visualization in one platform.

5. **Explore VoxCity Capabilities**: Demonstrate the power of the [VoxCity](https://github.com/kunifujiwara/VoxCity) library for multi-source geospatial data integration and 3D urban modeling.

## 🌟 Features

### Current (Phase 1)
- ✅ Interactive map-based location selection
- ✅ 3D voxel city model generation using VoxCity
- ✅ Multiple mesh resolution options (1m - 10m)
- ✅ Auto-selected data sources (buildings, terrain, vegetation, land cover)
- ✅ Web-based 3D visualization interface

### Coming Soon (Phase 2)
- 🔄 SCE administrative boundary overlays
- 🔄 Electrical circuit visualization (3D lines)
- 🔄 Utility structure rendering (poles, towers, transformers)
- 🔄 Asset filtering and search tools
- 🔄 Multi-format export (OBJ, GeoJSON, KML)

### Future (Phase 3)
- 📋 Clearance analysis (vegetation vs. circuits)
- 📋 Vegetation risk assessment
- 📋 Solar exposure calculations
- 📋 Automated report generation
- 📋 Real-time collaboration features

## 🚀 Quick Start Guide

Follow these steps to get the application running on your local machine.

### Prerequisites

- **Python 3.9 or higher** - [Download Python](https://www.python.org/downloads/)
- **uv** (fast Python package installer) - Optional but recommended
- **Google Earth Engine account** - Required for VoxCity data access

### Step 1: Install uv (Recommended)

`uv` is a fast Python package installer and virtual environment manager. Install it using:

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Alternative (using pip):**
```bash
pip install uv
```

### Step 2: Clone or Download This Repository

```bash
# If using git
git clone <repository-url>
cd voxgrid

# Or download and extract the ZIP file, then navigate to the folder
```

### Step 3: Create a Virtual Environment

Using `uv` (fast):
```bash
uv venv
```

Or using standard Python:
```bash
python -m venv venv
```

### Step 4: Activate the Virtual Environment

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

You should see `(.venv)` or similar prefix in your terminal prompt.

### Step 5: Install Dependencies

Using `uv` (fast):
```bash
uv pip install -r requirements.txt
```

Or using standard pip:
```bash
pip install -r requirements.txt
```

**Note**: Installing VoxCity and its dependencies (especially Google Earth Engine) may take several minutes.

### Step 6: Authenticate with Google Earth Engine

VoxCity requires Google Earth Engine (GEE) access. Authenticate once:

```bash
earthengine authenticate --auth_mode=notebook
```

This will:
1. Open a browser window
2. Ask you to sign in with your Google account
3. Generate an authentication token
4. Paste the token back into your terminal

**First time using GEE?**
- Create a free account at [Google Earth Engine](https://earthengine.google.com/)
- Register your project (if prompted during authentication)

### Step 7: Run the Streamlit App

```bash
streamlit run app.py
```

The app will automatically open in your default web browser at `http://localhost:8501`

If it doesn't open automatically, navigate to the URL shown in your terminal.

### Step 8: Use the Application

1. **Select Location** (Tab 1):
   - Enter a city name
   - Draw a rectangle on the map to define your area
   - Or manually enter coordinates

2. **Generate Model** (Tab 2):
   - Choose mesh resolution (5m recommended for first try)
   - Click "Generate VoxCity Model"
   - Wait 2-10 minutes depending on area size and resolution

3. **Visualize** (Tab 3):
   - Explore your 3D model
   - Adjust visualization settings
   - Export screenshots or 3D files

## 📁 Project Structure

```
voxgrid/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── PRD_VoxCity_SCE_Integration.md  # Product Requirements Document
├── voxcity_demo.ipynb             # Original VoxCity demo notebook
└── .venv/                         # Virtual environment (created during setup)
```

## 🛠️ Development Setup

For developers who want to extend or modify the application:

### Install Development Dependencies

```bash
# Create a dev requirements file
cat > requirements-dev.txt << EOF
-r requirements.txt
pytest>=7.4.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
jupyter>=1.0.0
EOF

# Install
uv pip install -r requirements-dev.txt
```

### Code Formatting

```bash
black app.py
```

### Type Checking

```bash
mypy app.py
```

### Run Tests

```bash
pytest tests/
```

## 🐛 Troubleshooting

### Issue: "earthengine authenticate" fails

**Solution**: 
- Ensure you have a Google Earth Engine account
- Try authenticating in a standard browser (not incognito)
- Check firewall settings if connection fails

### Issue: Streamlit won't start

**Solution**:
```bash
# Check if port 8501 is in use
netstat -an | findstr "8501"  # Windows
lsof -i :8501                 # macOS/Linux

# Run on different port
streamlit run app.py --server.port 8502
```

### Issue: VoxCity generation takes too long

**Solution**:
- Reduce area size (draw smaller rectangle)
- Increase mesh size (try 10m instead of 5m)
- Check internet connection (downloads map data)

### Issue: Import errors or missing packages

**Solution**:
```bash
# Reinstall all dependencies
uv pip install --force-reinstall -r requirements.txt
```

### Issue: Memory errors during generation

**Solution**:
- Reduce area size
- Increase mesh size (uses fewer voxels)
- Close other applications to free RAM

## 📊 Performance Tips

- **Area Size**: Start with small areas (< 1 km²) for testing
- **Mesh Resolution**: 5m is a good balance between detail and speed
- **Downsampling**: Use 2x or 4x downsampling for large models
- **Caching**: VoxCity caches some data; subsequent generations may be faster

## 🤝 Contributing

This is an experimental project. Contributions, ideas, and feedback are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📚 Resources

- **VoxCity Documentation**: [GitHub](https://github.com/kunifujiwara/VoxCity)
- **Streamlit Documentation**: [docs.streamlit.io](https://docs.streamlit.io)
- **Google Earth Engine**: [earthengine.google.com](https://earthengine.google.com)
- **Folium (Maps)**: [python-visualization.github.io/folium](https://python-visualization.github.io/folium/)

## 📄 License

[Specify your license here - e.g., MIT, Apache 2.0, etc.]

## 🙏 Acknowledgments

- [VoxCity](https://github.com/kunifujiwara/VoxCity) by Kunihiko Fujiwara
- Google Earth Engine for satellite and geospatial data
- OpenStreetMap contributors
- Microsoft Building Footprints dataset
- Streamlit for the web framework

## 📧 Contact

For questions, issues, or feedback:
- Open an issue on GitHub
- Contact: [Your contact information]

---

**Built with ❤️ using VoxCity, Streamlit, and Python**

*Last updated: January 7, 2026*
