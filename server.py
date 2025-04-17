import asyncio
import uvicorn
from pyngrok import ngrok # type: ignore
import os
import sys
import socket
import argparse
from dotenv import load_dotenv
from api import app

# Load environment variables 
load_dotenv()
ngrok_token = os.getenv("NGROK_AUTHTOKEN")

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

async def start_server(use_ngrok=True, port=7000):
    # Check if port is already in use and find an available one if needed
    if is_port_in_use(port):
        print(f"Port {port} is already in use.")
        if not use_ngrok:  # Only auto-select port when not using ngrok
            for test_port in range(port+1, port+20):
                if not is_port_in_use(test_port):
                    print(f"Using alternative port: {test_port}")
                    port = test_port
                    break
            else:
                print("Could not find an available port. Please specify a different port with --port.")
                return
        else:
            print("Please close any existing servers or specify a different port with --port.")
            return
    
    # Configure uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    
    if use_ngrok:
        try:
            # Set ngrok auth token
            ngrok.set_auth_token(ngrok_token)
            
            # Start ngrok tunnel
            public_url = ngrok.connect(port)
            print("=" * 50)
            print("Public URL for server (Copy this for the frontend):", public_url)
            print("=" * 50)
        except Exception as e:
            print("=" * 50)
            print("Error setting up ngrok tunnel:", str(e))
            print("Running server without ngrok - only accessible on local network")
            print(f"Local URL: http://localhost:{port}")
            print("If you need public access, you can:")
            print("1. Close other ngrok sessions: https://dashboard.ngrok.com/agents")
            print("2. Or run without ngrok and use another tunneling service")
            print("=" * 50)
    else:
        print("=" * 50)
        print("Running server without ngrok - only accessible on local network")
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
    parser.add_argument("--no-ngrok", action="store_true", help="Run without ngrok")
    parser.add_argument("--port", type=int, default=7000, help="Port to run the server on (default: 7000)")
    
    args = parser.parse_args()
    use_ngrok = not args.no_ngrok
    port = args.port
    
    # Run the server
    asyncio.run(start_server(use_ngrok=use_ngrok, port=port))