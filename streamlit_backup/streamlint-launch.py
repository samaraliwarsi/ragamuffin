import os
from streamlit_desktop_app import start_desktop_app

if __name__ == "__main__":
    # Get the absolute path to the streamlit_app.py in the same folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(current_dir, "streamlit_app.py")
    
    start_desktop_app(
        app_path, 
        title="Ragamuffin (Streamlit Backup)", 
        width=1200, 
        height=800,
        options={"server.headless": True}
    )