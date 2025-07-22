import os
import subprocess
import sys

def main():
    """
    Run the Streamlit app locally, automatically configuring it for VS Code environment
    """
    print("Starting Customer Feedback Analyzer for local development...")
    
    # Create .streamlit directory if it doesn't exist
    os.makedirs(".streamlit", exist_ok=True)
    
    # Create a local config for VS Code that uses localhost
    with open(".streamlit/config.toml", "w") as f:
        f.write("""[server]
headless = false
enableCORS = false
enableXsrfProtection = false
address = "127.0.0.1"
port = 5000
""")
    
    print("Configuration set for local development.")
    print("You can access the app at: http://localhost:5000 or http://127.0.0.1:5000")
    
    # Run the Streamlit app with the local configuration
    subprocess.run([
        "streamlit", "run", "app.py",
        "--server.address", "127.0.0.1",
        "--server.port", "5000"
    ])

if __name__ == "__main__":
    main()