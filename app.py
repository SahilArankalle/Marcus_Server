import asyncio
import websockets
import json
from flask import Flask, render_template
from threading import Thread

user_db = {}
signup_count = {}
MAX_USERS_PER_DEVICE = 3
clients = {}

app = Flask(__name__)

# Handler for each WebSocket connection
async def handle_connection(websocket, path):
    try:
        device_id = websocket.remote_address[0]
        print(f"A client connected from {device_id}!")

        await websocket.send(json.dumps({"status": "success", "message": "Connected to server!"}))

        username = None
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")

            if action == "signup":
                await handle_signup(data, websocket, device_id)
            elif action == "login":
                username = await handle_login(data, websocket)
                if username:
                    clients[username] = websocket
            elif action == "command":
                await handle_command(data)

    except websockets.exceptions.ConnectionClosed:
        print("A client disconnected.")
    finally:
        if username and username in clients:
            del clients[username]

# Handle signup logic
async def handle_signup(data, websocket, device_id):
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        await websocket.send(json.dumps({"status": "error", "message": "Invalid input"}))
        return

    device_signups = signup_count.get(device_id, 0)
    if device_signups >= MAX_USERS_PER_DEVICE:
        await websocket.send(json.dumps({"status": "error", "message": "Signup limit reached for this device"}))
        return

    if username in user_db:
        await websocket.send(json.dumps({"status": "error", "message": "Username already taken"}))
        return

    user_db[username] = password
    signup_count[device_id] = device_signups + 1

    await websocket.send(json.dumps({"status": "success", "message": "Signup successful"}))

# Handle login logic
async def handle_login(data, websocket):
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        await websocket.send(json.dumps({"status": "error", "message": "Invalid input"}))
        return None

    stored_password = user_db.get(username)

    if stored_password == password:
        await websocket.send(json.dumps({"status": "success", "message": "Login successful", "username": username}))
        return username
    else:
        await websocket.send(json.dumps({"status": "error", "message": "Invalid username or password"}))
        return None

# Handle command received from Raspberry Pi
async def handle_command(data):
    command = data.get("command")
    print(f"Received command: {command}")

    if clients:
        for username, client in clients.items():
            await client.send(json.dumps({"action": "command", "command": command}))
            print(f"Command forwarded to app ({username}): {command}")
    else:
        print("No connected clients to forward command to.")

# WebSocket server
async def websocket_server():
    async with websockets.serve(handle_connection, "0.0.0.0", 12345):
        print("WebSocket server started on ws://0.0.0.0:12345")
        await asyncio.Future()

# Start Flask app
@app.route('/')
def index():
    return render_template('index.html')

def start_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    # Run both the Flask server and WebSocket server in separate threads
    flask_thread = Thread(target=start_flask)
    flask_thread.start()

    # Run WebSocket server in the main thread
    asyncio.run(websocket_server())
