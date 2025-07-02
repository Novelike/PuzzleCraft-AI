import subprocess
import sys
import os
import time
import threading
from pathlib import Path

def run_service(name, command, cwd=None):
    """Run a service in a separate process"""
    print(f"🚀 Starting {name}...")
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Print output in real-time
        for line in iter(process.stdout.readline, ''):
            if line.strip():
                print(f"[{name}] {line.strip()}")
                
        process.wait()
        
    except Exception as e:
        print(f"❌ Error starting {name}: {e}")

def main():
    """Start all required services"""
    print("🎯 PuzzleCraft AI - Starting Backend Services")
    print("=" * 50)
    
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # Service configurations
    services = [
        {
            "name": "API Gateway",
            "command": "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload",
            "cwd": project_root / "backend" / "api-gateway"
        },
        {
            "name": "Puzzle Generator",
            "command": "python -m uvicorn main:app --host 0.0.0.0 --port 8004 --reload",
            "cwd": project_root / "backend" / "puzzle-generator"
        }
    ]
    
    # Check if directories exist
    for service in services:
        if not service["cwd"].exists():
            print(f"❌ Directory not found: {service['cwd']}")
            return
    
    print("✅ All service directories found")
    print("\n📋 Services to start:")
    for service in services:
        print(f"  - {service['name']}: {service['command']}")
        print(f"    Directory: {service['cwd']}")
    
    print(f"\n🌐 Services will be available at:")
    print(f"  - API Gateway: http://localhost:8000")
    print(f"  - API Gateway Docs: http://localhost:8000/docs")
    print(f"  - Puzzle Generator: http://localhost:8004")
    print(f"  - Puzzle Generator Docs: http://localhost:8004/docs")
    
    print(f"\n🔧 Frontend should be configured to use:")
    print(f"  - VITE_PUZZLE_GENERATOR_URL=http://localhost:8000/api/v1/puzzles")
    print(f"  - VITE_API_URL=http://localhost:8000/api")
    
    input("\n⏳ Press Enter to start services...")
    
    # Start services in separate threads
    threads = []
    for service in services:
        thread = threading.Thread(
            target=run_service,
            args=(service["name"], service["command"], service["cwd"])
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)
        time.sleep(2)  # Stagger startup
    
    print("\n🎉 All services started!")
    print("💡 Press Ctrl+C to stop all services")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        sys.exit(0)

if __name__ == "__main__":
    main()