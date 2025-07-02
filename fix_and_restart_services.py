#!/usr/bin/env python3
"""
Script to apply the style transfer fixes and restart services
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def install_opencv_contrib():
    """Install opencv-contrib-python to replace opencv-python"""
    print("Installing opencv-contrib-python...")
    
    # First uninstall opencv-python
    success, stdout, stderr = run_command("pip uninstall opencv-python -y")
    if success:
        print("✓ Uninstalled opencv-python")
    else:
        print(f"⚠ Warning: Could not uninstall opencv-python: {stderr}")
    
    # Install opencv-contrib-python
    success, stdout, stderr = run_command("pip install opencv-contrib-python==4.8.1.78")
    if success:
        print("✓ Installed opencv-contrib-python")
        return True
    else:
        print(f"✗ Failed to install opencv-contrib-python: {stderr}")
        return False

def restart_style_transfer_service():
    """Restart the style transfer service"""
    print("Restarting style transfer service...")
    
    # Kill existing processes
    run_command("taskkill /f /im python.exe")
    time.sleep(2)
    
    # Start style transfer service
    style_transfer_dir = Path("backend/style-transfer")
    if style_transfer_dir.exists():
        print("Starting style transfer service...")
        # Note: This will start the service in the background
        # In a real deployment, you'd use a process manager like PM2 or systemd
        success, stdout, stderr = run_command(
            "python main.py", 
            cwd=str(style_transfer_dir)
        )
        return True
    else:
        print("✗ Style transfer directory not found")
        return False

def main():
    """Main function to apply fixes"""
    print("=" * 60)
    print("STYLE TRANSFER FIX APPLICATION")
    print("=" * 60)
    
    print("\n1. Installing opencv-contrib-python dependency...")
    print("-" * 40)
    if install_opencv_contrib():
        print("✓ OpenCV dependency updated successfully")
    else:
        print("✗ Failed to update OpenCV dependency")
        print("Please manually run: pip uninstall opencv-python -y && pip install opencv-contrib-python==4.8.1.78")
        return False
    
    print("\n2. Checking if services need restart...")
    print("-" * 40)
    print("Note: You may need to manually restart the services:")
    print("- Style Transfer Service (port 8007)")
    print("- API Gateway (port 8000)")
    
    print("\n3. Summary of fixes applied:")
    print("-" * 40)
    print("✓ Updated requirements.txt to use opencv-contrib-python")
    print("✓ Added comprehensive error handling and logging")
    print("✓ Fixed endpoint mismatches between API gateway and style service")
    print("✓ Added style compatibility testing")
    print("✓ Updated default styles to exclude problematic ones")
    print("✓ Improved error messages and debugging information")
    
    print("\n4. Next steps:")
    print("-" * 40)
    print("1. Restart your services manually or using your deployment script")
    print("2. Run the test script: python test_style_fixes.py")
    print("3. Check the logs for detailed error information")
    print("4. If oil_painting style works, add it back to default styles")
    
    print("\n" + "=" * 60)
    print("FIX APPLICATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()