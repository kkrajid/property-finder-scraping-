import streamlit as st
import pandas as pd
import os
import subprocess
import sys
import time
import threading
import queue
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Configure page
st.set_page_config(
    page_title="DeleScrap - Property Scraper",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for DeleScrap text next to toggle
st.markdown("""
<style>
    /* Position DeleScrap text next to the toggle button */
    .delescrap-label {
        position: absolute;
        top: 1rem;
        left: 0.5rem;
        z-index: 998;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-family: 'Arial', sans-serif;
        font-weight: bold;
        font-size: 14px;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        transition: all 0.3s ease;
        pointer-events: none;
        opacity: 1;
        transform: translateX(0);
    }
    
    /* Hide when sidebar is collapsed */
    .css-1rs6os.edgvbvh3 + .css-1d391kg .delescrap-label,
    [data-testid="stSidebar"][aria-expanded="false"] + * .delescrap-label,
    .css-1rs6os[data-testid="stSidebar"]:not([aria-expanded="true"]) ~ * .delescrap-label {
        opacity: 0;
        transform: translateX(-20px);
        visibility: hidden;
    }
    
    /* Show only when sidebar is expanded */
    [data-testid="stSidebar"][aria-expanded="true"] ~ * .delescrap-label,
    .css-1d391kg:not(.css-1rs6os) .delescrap-label {
        opacity: 1;
        transform: translateX(0);
        visibility: visible;
    }
    
    /* Original styling for main header */
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
        color: white;
    }
    
    .metric-container {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    
    .status-running {
        background-color: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 10px 0;
    }
    
    .status-stopped {
        background-color: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #dc3545;
        margin: 10px 0;
    }
    
    .status-completed {
        background-color: #cce5ff;
        color: #004085;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 10px 0;
    }
    
    .console-output {
        background-color: #1e1e1e;
        color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        max-height: 400px;
        overflow-y: auto;
        white-space: pre-wrap;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Add DeleScrap text that shows/hides with sidebar
st.markdown("""
<div class="delescrap-label">
    DeleScrap
</div>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🏠 Property Finder Scraper Dashboard</h1>
    <p>Advanced Real Estate Data Collection & Analysis Platform</p>
    <p><em>Powered by your existing main.py scraper</em></p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'scraper_running' not in st.session_state:
    st.session_state.scraper_running = False
if 'scraper_output' not in st.session_state:
    st.session_state.scraper_output = ""
if 'selected_option' not in st.session_state:
    st.session_state.selected_option = None
if 'scraper_process' not in st.session_state:
    st.session_state.scraper_process = None
if 'output_queue' not in st.session_state:
    st.session_state.output_queue = queue.Queue()

# Check if main.py exists
MAIN_PY_EXISTS = os.path.exists("main.py")
if not MAIN_PY_EXISTS:
    st.error("❌ main.py file not found! Please ensure your scraper file is named 'main.py' and in the same directory.")
    st.stop()

def run_scraper_with_option(option):
    """Run the main.py scraper with the selected option"""
    try:
        # Set environment variables for proper Unicode support
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONLEGACYWINDOWSSTDIO'] = '0'
        
        # Create input string with all expected inputs for the selected option
        input_sequence = f"{option}\n"
        
        # Add confirmations and inputs based on option
        if option == "4":
            input_sequence += "y\n"  # Confirm large scrape
        elif option == "5":
            input_sequence += "y\n"  # Confirm very slow scrape
            input_sequence += "y\n"  # Confirm large scrape
        elif option == "6":
            # Custom configuration - use values from session state
            if 'custom_config' in st.session_state:
                config = st.session_state.custom_config
                input_sequence += f"{config['start_page']}\n"  # Starting page
                
                # Max pages input
                if config['max_pages'] == 0:
                    input_sequence += "\n"  # Empty for unlimited
                else:
                    input_sequence += f"{config['max_pages']}\n"
                
                # Detailed data
                input_sequence += "y\n" if config['detailed_data'] else "n\n"
                
                # Auto detect
                input_sequence += "y\n" if config['auto_detect'] else "n\n"
                
                # If detailed data and unlimited, add confirmations
                if config['detailed_data'] and config['max_pages'] == 0:
                    input_sequence += "y\n"  # Confirm extremely slow
            else:
                # Fallback defaults if no custom config
                input_sequence += "1\n"    # Start page 1
                input_sequence += "5\n"    # 5 pages
                input_sequence += "n\n"    # No detailed data
                input_sequence += "y\n"    # Auto detect
        
        # Create a subprocess to run main.py
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=0,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        # Send all inputs at once
        process.stdin.write(input_sequence)
        process.stdin.close()  # Signal no more input
        
        return process
        
    except Exception as e:
        st.error(f"Error starting scraper: {e}")
        return None

def read_process_output(process, output_queue):
    """Read output from the scraper process and put it in queue"""
    output_lines = []
    try:
        while True:
            try:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    # Clean the output to handle any encoding issues
                    cleaned_output = output.strip()
                    # Replace problematic Unicode characters if any remain
                    cleaned_output = cleaned_output.encode('utf-8', 'replace').decode('utf-8')
                    output_lines.append(cleaned_output)
                    # Put output in queue instead of directly updating session state
                    output_queue.put("\n".join(output_lines[-50:]))  # Keep last 50 lines
            except UnicodeDecodeError as e:
                # Handle any remaining Unicode issues gracefully
                error_msg = f"[Encoding issue in output: {str(e)}]"
                output_lines.append(error_msg)
                output_queue.put("\n".join(output_lines[-50:]))
        
        # Get final return code
        rc = process.poll()
        if rc == 0:
            output_lines.append("🎉 Scraping completed successfully!")
        else:
            output_lines.append(f"❌ Scraping ended with error code: {rc}")
            if rc == 1:
                output_lines.append("💡 This might be due to Unicode encoding issues.")
                output_lines.append("💡 Try running the scraper directly in terminal to see full error details.")
            
        output_queue.put("\n".join(output_lines[-50:]))
        output_queue.put("PROCESS_COMPLETE")  # Signal completion
        
    except Exception as e:
        output_lines.append(f"Error reading output: {e}")
        output_queue.put("\n".join(output_lines[-50:]))
        output_queue.put("PROCESS_COMPLETE")

def update_output_from_queue():
    """Update session state from queue (called from main thread)"""
    try:
        while not st.session_state.output_queue.empty():
            message = st.session_state.output_queue.get_nowait()
            if message == "PROCESS_COMPLETE":
                st.session_state.scraper_running = False
                break
            else:
                st.session_state.scraper_output = message
    except queue.Empty:
        pass

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Scraper Configuration")
    st.write("**Using your existing main.py scraper**")
    
    # Main function options exactly as in your original main()
    st.subheader("Select Option (1-6)")
    
    options = {
        "1": "🚀 Quick scrape (3 pages, no detailed data)",
        "2": "📊 Standard scrape (5 pages, no detailed data)", 
        "3": "📈 Comprehensive scrape (10 pages, no detailed data)",
        "4": "♾️ UNLIMITED scrape (all pages, no detailed data)",
        "5": "⚠️ UNLIMITED with detailed data (WARNING: VERY SLOW)",
        "6": "🔧 Custom configuration"
    }
    
    selected_option = st.radio("Choose scraping option:", list(options.keys()), 
                              format_func=lambda x: options[x],
                              key="option_selector")
    
    st.session_state.selected_option = selected_option
    
    st.divider()
    
    # Show option details
    st.subheader("📋 Selected Configuration")
    if selected_option == "1":
        st.info("✅ Quick scrape: 3 pages, no detailed data")
    elif selected_option == "2":
        st.info("✅ Standard scrape: 5 pages, no detailed data")
    elif selected_option == "3":
        st.info("✅ Comprehensive scrape: 10 pages, no detailed data")
    elif selected_option == "4":
        st.warning("✅ UNLIMITED scrape: All available pages, no detailed data")
        st.warning("⚡ This will scrape until no more properties are found")
    elif selected_option == "5":
        st.error("✅ UNLIMITED with detailed data")
        st.error("⚠️ WARNING: This will be VERY SLOW but collect maximum data")
        st.error("⏰ This could take hours to complete")
    elif selected_option == "6":
        st.info("✅ Custom configuration")
        st.write("Configure your custom scraping parameters below:")
        
        # Custom configuration fields
        with st.expander("Custom Configuration Settings", expanded=True):
            custom_start_page = st.number_input("Starting page number", min_value=1, value=1, key="custom_start_page")
            
            custom_max_pages = st.number_input("Number of pages to scrape (0 for unlimited)", min_value=0, value=5, key="custom_max_pages")
            
            custom_detailed = st.checkbox("Collect detailed data from each property (slower)", key="custom_detailed")
            
            custom_auto_detect = st.checkbox("Auto-detect when no more pages available", value=True, key="custom_auto_detect")
            
            # Store custom settings in session state
            st.session_state.custom_config = {
                'start_page': custom_start_page,
                'max_pages': custom_max_pages,
                'detailed_data': custom_detailed,
                'auto_detect': custom_auto_detect
            }
            
            # Show configuration summary
            st.write("**Configuration Summary:**")
            st.write(f"• Starting page: {custom_start_page}")
            st.write(f"• Pages to scrape: {'Unlimited' if custom_max_pages == 0 else custom_max_pages}")
            st.write(f"• Detailed data: {'Yes' if custom_detailed else 'No'}")
            st.write(f"• Auto-detect end: {'Yes' if custom_auto_detect else 'No'}")
            
            if custom_detailed and custom_max_pages == 0:
                st.warning("⚠️ WARNING: Unlimited pages + detailed data = EXTREMELY SLOW")
    
    st.write(f"**Target:** LAND properties only (t=5 parameter)")
    
    st.divider()
    
    # Troubleshooting section
    with st.expander("🔧 Troubleshooting"):
        st.write("**Common Issues:**")
        st.write("• **Unicode Error**: If you see encoding errors, try running the scraper directly in terminal first")
        st.write("• **Option 4/5 Issues**: These options may require manual confirmation - check console output")
        st.write("• **Process Timeout**: Large scrapes may appear to hang - this is normal for unlimited options")
        
        st.write("**Tips:**")
        st.write("• Use Options 1-3 for testing and smaller datasets")
        st.write("• Option 4 is best for production unlimited scraping")
        st.write("• Option 5 should only be used when you need detailed property data")
        
        if st.button("🧪 Test main.py directly", key="test_main"):
            st.code("python main.py", language="bash")
            st.info("Run this command in your terminal to test the scraper directly")
    
    st.divider()
    
    # Filters section for data viewing
    st.header("🔍 Data Filters")
    
    # Get available files for filtering
    excel_files = [f for f in os.listdir(".") if f.endswith(".xlsx") and "property_data" in f]
    
    if excel_files:
        try:
            latest_file = max(excel_files, key=lambda x: os.path.getctime(x))
            df_for_filters = pd.read_excel(latest_file)
            
            # Location filter
            if "location" in df_for_filters.columns:
                location_filter = st.multiselect("Location", 
                                        df_for_filters["location"].dropna().unique(),
                                        key="location_filter")
            else:
                location_filter = []
            
            # Property type filter
            if "property_type" in df_for_filters.columns:
                prop_type_filter = st.multiselect("Property Type", 
                                         df_for_filters["property_type"].dropna().unique(),
                                         key="property_type_filter")
            else:
                prop_type_filter = []
                
        except Exception as e:
            st.error(f"Error loading filter data: {e}")
            location_filter = []
            prop_type_filter = []
    else:
        location_filter = []
        prop_type_filter = []
        st.info("No data files found yet. Run scraper to generate data.")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🚀 Scraper Controls")
    
    # Control buttons
    button_col1, button_col2 = st.columns(2)
    
    with button_col1:
        if st.button("▶️ Start Scraping", type="primary", width="stretch", 
                    disabled=st.session_state.scraper_running):
            if not st.session_state.scraper_running:
                st.session_state.scraper_running = True
                st.session_state.scraper_output = f"🚀 Starting scraper with option {st.session_state.selected_option}...\n"
                
                # Add custom config info to output if option 6
                if st.session_state.selected_option == "6" and 'custom_config' in st.session_state:
                    config = st.session_state.custom_config
                    config_info = f"""
Custom Configuration:
- Starting page: {config['start_page']}
- Pages to scrape: {'Unlimited' if config['max_pages'] == 0 else config['max_pages']}
- Detailed data: {'Yes' if config['detailed_data'] else 'No'}
- Auto-detect end: {'Yes' if config['auto_detect'] else 'No'}

"""
                    st.session_state.scraper_output += config_info
                
                # Start the scraper process
                process = run_scraper_with_option(st.session_state.selected_option)
                if process:
                    st.session_state.scraper_process = process
                    
                    # Start reading output in a separate thread with queue
                    threading.Thread(
                        target=read_process_output, 
                        args=(process, st.session_state.output_queue), 
                        daemon=True
                    ).start()
                    
                    st.success(f"✅ Scraper started with option {st.session_state.selected_option}")
                    st.rerun()
                else:
                    st.session_state.scraper_running = False
    
    with button_col2:
        if st.button("⏹️ Stop Scraper", width="stretch",
                    disabled=not st.session_state.scraper_running):
            if st.session_state.scraper_running and st.session_state.scraper_process:
                try:
                    st.session_state.scraper_process.terminate()
                    st.session_state.scraper_running = False
                    st.session_state.scraper_output += "\n⏹️ Scraper stopped by user"
                    st.warning("⏹️ Scraper stopped")
                except Exception as e:
                    st.error(f"Error stopping scraper: {e}")

with col2:
    st.subheader("📊 Status")
    
    # Status indicator
    if st.session_state.scraper_running:
        st.markdown('<div class="status-running">🔄 Scraper Running</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-stopped">⏸️ Scraper Idle</div>', unsafe_allow_html=True)
    
    # Quick stats from latest file
    if excel_files:
        try:
            latest_file = max(excel_files, key=lambda x: os.path.getctime(x))
            df_stats = pd.read_excel(latest_file)
            
            st.metric("Latest File", latest_file.replace("property_data_", "").replace(".xlsx", ""))
            st.metric("Total Properties", len(df_stats))
            
            if 'property_type' in df_stats.columns:
                land_count = len(df_stats[df_stats['property_type'] == 'Land'])
                if land_count == len(df_stats):
                    st.success(f"✅ All {land_count} are LAND properties")
                else:
                    st.warning(f"⚠️ {land_count}/{len(df_stats)} are LAND properties")
                    
        except Exception as e:
            st.error(f"Error reading stats: {e}")

# Console Output Section
if st.session_state.scraper_output or st.session_state.scraper_running:
    st.subheader("📺 Console Output")
    
    # Update output from queue if scraper is running
    if st.session_state.scraper_running:
        update_output_from_queue()
        # Auto-refresh console while running
        time.sleep(1)  # Small delay to prevent excessive refreshes
        st.rerun()
    
    # Display console output
    st.markdown(f'<div class="console-output">{st.session_state.scraper_output}</div>', 
                unsafe_allow_html=True)

# File Management Section
st.subheader("📁 Data Files Management")

# Bulk File Operations Section
if excel_files:
    with st.expander("🗂️ Bulk File Operations", expanded=False):
        st.write("**Select multiple files for bulk operations:**")
        
        # Multi-select for files
        files_to_delete = st.multiselect(
            "Select files to delete:",
            options=excel_files,
            default=[],
            key="bulk_delete_selector"
        )
        
        col_bulk1, col_bulk2, col_bulk3 = st.columns([1, 1, 2])
        
        with col_bulk1:
            if st.button("🗑️ Delete Selected", type="secondary", width="stretch", disabled=len(files_to_delete) == 0):
                deleted_count = 0
                failed_files = []
                
                for file in files_to_delete:
                    try:
                        os.remove(file)
                        deleted_count += 1
                    except Exception as e:
                        failed_files.append(f"{file}: {str(e)}")
                
                if deleted_count > 0:
                    st.success(f"Successfully deleted {deleted_count} file(s)")
                
                if failed_files:
                    st.error(f"Failed to delete: {', '.join(failed_files)}")
                
                if deleted_count > 0 or failed_files:
                    st.rerun()
        
        with col_bulk2:
            if st.button("🧹 Delete All", type="secondary", width="stretch"):
                if st.session_state.get('confirm_delete_all', False):
                    deleted_count = 0
                    failed_files = []
                    
                    for file in excel_files:
                        try:
                            os.remove(file)
                            deleted_count += 1
                        except Exception as e:
                            failed_files.append(f"{file}: {str(e)}")
                    
                    st.success(f"Deleted {deleted_count} file(s)")
                    if failed_files:
                        st.error(f"Failed: {', '.join(failed_files)}")
                    
                    st.session_state.confirm_delete_all = False
                    st.rerun()
                else:
                    st.session_state.confirm_delete_all = True
                    st.warning("Click again to confirm deletion of all files")
        
        with col_bulk3:
            if files_to_delete:
                st.info(f"Selected {len(files_to_delete)} file(s) for deletion")
            else:
                st.info("No files selected")

# Individual File Viewing Section
if excel_files:
    col_file1, col_file2, col_file3 = st.columns([2, 1, 1])
    
    with col_file1:
        selected_file = st.selectbox("📂 Select Excel File to View", excel_files, key="file_selector")
    
    with col_file2:
        if st.button("🔄 Refresh Files", width="stretch"):
            st.rerun()
    
    with col_file3:
        if selected_file and st.button("🗑️ Delete File", width="stretch", type="secondary"):
            try:
                os.remove(selected_file)
                st.success(f"Deleted {selected_file}")
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting file: {e}")
    
    if selected_file:
        try:
            # Load and display data
            df = pd.read_excel(selected_file)
            
            # File info
            file_stats = {
                "File Size": f"{os.path.getsize(selected_file) / 1024:.1f} KB",
                "Total Properties": len(df),
                "Columns": len(df.columns),
                "Date Created": datetime.fromtimestamp(os.path.getctime(selected_file)).strftime('%Y-%m-%d %H:%M')
            }
            
            # Display file stats
            stat_cols = st.columns(4)
            for i, (key, value) in enumerate(file_stats.items()):
                with stat_cols[i]:
                    st.metric(key, value)
            
            # Apply filters
            filtered_df = df.copy()
            if location_filter:
                filtered_df = filtered_df[filtered_df["location"].isin(location_filter)]
            if prop_type_filter:
                filtered_df = filtered_df[filtered_df["property_type"].isin(prop_type_filter)]
            
            # Data preview
            st.subheader("🔍 Data Preview")
            
            if len(location_filter) > 0 or len(prop_type_filter) > 0:
                st.info(f"Showing {len(filtered_df)} of {len(df)} properties (filtered)")
            
            st.dataframe(filtered_df, width="stretch", height=400)
            
            # Visualizations
            if len(filtered_df) > 0:
                st.subheader("📊 Data Visualizations")
                
                viz_col1, viz_col2 = st.columns(2)
                
                with viz_col1:
                    if 'property_type' in filtered_df.columns:
                        property_counts = filtered_df['property_type'].value_counts()
                        fig_pie = px.pie(values=property_counts.values, 
                                        names=property_counts.index,
                                        title="Properties by Type")
                        st.plotly_chart(fig_pie, width="stretch")
                
                with viz_col2:
                    if 'location' in filtered_df.columns:
                        location_counts = filtered_df['location'].value_counts().head(10)
                        fig_bar = px.bar(x=location_counts.values,
                                        y=location_counts.index,
                                        orientation='h',
                                        title="Top 10 Locations")
                        fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'})
                        st.plotly_chart(fig_bar, width="stretch")
            
            # Download button
            with open(selected_file, 'rb') as file:
                st.download_button(
                    label="📥 Download Excel File",
                    data=file,
                    file_name=selected_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch"
                )
                
        except Exception as e:
            st.error(f"Error loading file {selected_file}: {str(e)}")

else:
    st.info("No property data files found. Run the scraper to generate data files.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    🏠 Property Finder Scraper Dashboard v2.0 | Built with Streamlit<br>
    <em>Integrated with your existing main.py scraper</em>
</div>
""", unsafe_allow_html=True)