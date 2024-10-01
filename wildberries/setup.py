import subprocess
import sys

def install_dependencies():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def setup_playwright():
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

if __name__ == "__main__":
    print("Installing dependencies...")
    install_dependencies()
    print("Setting up Playwright...")
    setup_playwright()
    print("Setup complete!")