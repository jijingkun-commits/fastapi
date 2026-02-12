import asyncio
import os
import json
import httpx

# Configuration
BASE_URL = os.getenv("LIVE_API_BASE", "http://127.0.0.1:8000/api/v1")
BACKEND_PORT = os.getenv("TEST_BACKEND_PORT", "8000")
USERNAME = "admin"
PASSWORD = "123456"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0, trust_env=False) as client:
        # 1. Login
        print(f"Logging in as {USERNAME}...")
        try:
            response = await client.post("/login", json={
                "username": USERNAME,
                "password": PASSWORD
            })
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data["access_token"]
            print("Login successful! Token received.")
        except httpx.HTTPStatusError as e:
            print(f"Login failed: status={e.response.status_code} text={e.response.text}")
            return
        except Exception as e:
            print(f"An error occurred during login: {e}")
            return

        # 2. Start Chat Stream
        print("\nStarting chat stream...")
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        payload = {
            "prompt": "Hello, this is a test message.",
            "delay_ms": 100
        }

        try:
            async with client.stream("POST", "/chat/stream", headers=headers, json=payload) as response:
                response.raise_for_status()
                print("Stream connected. Waiting for messages...\n")
                
                async for line in response.aiter_lines():
                    if line:
                        print(f"Received: {line}")
                        
        except httpx.HTTPStatusError as e:
             print(f"Stream request failed: {e.response.text}")
        except Exception as e:
            print(f"An error occurred during streaming: {e}")

if __name__ == "__main__":
    asyncio.run(main())
