from streamlit_desktop_app import start_desktop_app

if __name__ == "__main__":
    start_desktop_app(
        "app.py",
        title="Ragamuffin: Kinor Lore Master",
        width=1200,
        height=800,
        options={"server.headless": True} # Runs silently
    )