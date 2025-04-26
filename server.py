import asyncio
import uvicorn
import os
import sys
import socket
import argparse
from dotenv import load_dotenv
from api import app

# Load environment variables 
load_dotenv()

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

async def start_server(port=7000):
    # Check if port is already in use and find an available one if needed
    if is_port_in_use(port):
        print(f"Port {port} is already in use.")
        for test_port in range(port+1, port+20):
            if not is_port_in_use(test_port):
                print(f"Using alternative port: {test_port}")
                port = test_port
                break
        else:
            print("Could not find an available port. Please specify a different port with --port.")
            return
    
    # Configure uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    
    print("=" * 50)
    print("Running server on local network - only accessible on local network")
    print(f"Local URL: http://localhost:{port}")
    print("=" * 50)

    # Start the server
    try:
        await server.serve()
    except OSError as e:
        print(f"Error starting server: {e}")
        print("Please try a different port with --port argument")

if __name__ == "__main__":
    # Set up argparse for command line arguments
    parser = argparse.ArgumentParser(description="Run the API server with options")
    parser.add_argument("--port", type=int, default=7000, help="Port to run the server on (default: 7000)")
    
    args = parser.parse_args()
    port = args.port
    
    # Run the server
    asyncio.run(start_server(port=port))