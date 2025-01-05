import asyncio
import websockets
import json

# In-memory storage for user data (you can replace this with a database)
users = []

async def handle_message(websocket, message):
    try:
        data = json.loads(message)
        if 'type' in data:
            if data['type'] == 'user_details':
                # Handle user details message
                print(f"Received user details: {data}")
                users.append(data)  # Save user details
                await websocket.send(json.dumps({"type": "user_details_ack", "status": "success"}))
            elif data['type'] == 'signup':
                # Handle signup message
                print(f"Received signup details: {data}")
                # Extract only the necessary fields for login
                user_data = { "username": data["username"], "password": data["password"] }
                users.append(user_data)  # Save signup details
                await websocket.send(json.dumps({"type": "signup_ack", "status": "success"}))
            elif data['type'] == 'login':
                # Handle login message
                print(f"Received login attempt: {data}")
                username = data.get("username")
                password = data.get("password")
                user = next((user for user in users if user.get("username") == username and user.get("password") == password), None)
                if user:
                    await websocket.send(json.dumps({"type": "login_ack", "status": "success"}))
                else:
                    await websocket.send(json.dumps({"type": "login_ack", "status": "failure", "message": "Invalid credentials"}))
            else:
                print(f"Unknown message type: {data}")
        else:
            print(f"Invalid message format: {message}")
            await websocket.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON message: {e}")
        await websocket.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
    except Exception as e:
        print(f"Other exception: {e}")
        await websocket.send(json.dumps({"type": "error", "message": str(e)}))

async def echo(websocket, path):
    print(f"Client connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            print(f"Received message from client: {message}")
            await handle_message(websocket, message)
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed with error: {e}")
    except Exception as e:
        print(f"Other exception: {e}")
    finally:
        print("Client disconnected")

async def main():
    async with websockets.serve(echo, "0.0.0.0", 8765):
        print("Server started at ws://0.0.0.0:8765")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())