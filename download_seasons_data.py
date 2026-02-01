import os
import requests
import subprocess

# Configuration
BASE_URL = "https://sailgp.com/content/v1/races?seasons="
TARGET_DIR = "races-info"
FORMATTER_SCRIPT = "json_formatter.py"
# Update this list if more seasons become available
SEASONS = [1, 2, 3, 4, 5, 6] 

def setup_directory():
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        print(f"Created directory: {TARGET_DIR}")

def download_and_format():
    setup_directory()
    
    for season in SEASONS:
        filename = f"season_{season}.json"
        filepath = os.path.join(TARGET_DIR, filename)
        url = f"{BASE_URL}{season}"
        
        print(f"--- Processing Season {season} ---")
        
        # 1. Download the data
        try:
            print(f"Downloading from: {url}")
            response = requests.get(url)
            response.raise_for_status() # Check for HTTP errors
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"Saved to: {filepath}")
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to download Season {season}: {e}")
            continue

        # 2. Run the formatter script
        if os.path.exists(FORMATTER_SCRIPT):
            print(f"Running formatter on {filename}...")
            # Using subprocess to run: python json_formatter.py path/to/file.json
            result = subprocess.run(
                ["python", FORMATTER_SCRIPT, filepath], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                print(f"Successfully formatted {filename}")
            else:
                print(f"Error formatting {filename}: {result.stderr}")
        else:
            print(f"Warning: {FORMATTER_SCRIPT} not found. Skipping format step.")

if __name__ == "__main__":
    download_and_format()