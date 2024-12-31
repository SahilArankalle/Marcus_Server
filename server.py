import asyncio
import websockets
import json

user_db = {}  # Store user credentials (username, password)
signup_count = {}  # Track the number of signups per device (based on WebSocket remote address)
MAX_USERS_PER_DEVICE = 3  # Maximum allowed users per device
clients = {}  # Dictionary to store connected clients with their WebSocket references (using username)

# Handler for each WebSocket connection
async def handle_connection(websocket, path):
    try:
        device_id = websocket.remote_address[0]  # Use IP address as device ID
        print(f"A client connected from {device_id}!")

        # Send success message to the client
        await websocket.send(json.dumps({"status": "success", "message": "Connected to server!"}))

        # Add connected client to the clients dictionary, with websocket as value
        username = None  # Initialize username to None to associate after login/signup
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")

            if action == "signup":
                await handle_signup(data, websocket, device_id)
            elif action == "login":
                username = await handle_login(data, websocket)
                if username:  # If login is successful, associate this username with the websocket
                    clients[username] = websocket
            elif action == "command":
                await handle_command(data)

    except websockets.exceptions.ConnectionClosed:
        print("A client disconnected.")
    finally:
        # Clean up the client from the dictionary if they disconnected
        if username and username in clients:
            del clients[username]

# Handle signup logic
async def handle_signup(data, websocket, device_id):
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        await websocket.send(json.dumps({"status": "error", "message": "Invalid input"}))
        return

    # Check the signup limit for the device
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
        return None  # Return None if login fails

    stored_password = user_db.get(username)

    if stored_password == password:
        await websocket.send(json.dumps({"status": "success", "message": "Login successful", "username": username}))
        return username  # Return the username if login is successful
    else:
        await websocket.send(json.dumps({"status": "error", "message": "Invalid username or password"}))
        return None  # Return None if login fails

# Handle command received from Raspberry Pi
async def handle_command(data):
    command = data.get("command")
    print(f"Received command: {command}")

    # Forward the command to all connected Android clients
    if clients:
        for username, client in clients.items():
            await client.send(json.dumps({"action": "command", "command": command}))
            print(f"Command forwarded to app ({username}): {command}")
    else:
        print("No connected clients to forward command to.")

# Start WebSocket server
async def main():
    async with websockets.serve(handle_connection, "0.0.0.0", 12345):
        print("Server started on ws://0.0.0.0:12345")
        await asyncio.Future()  # Run the server forever

# Run the server
asyncio.run(main())