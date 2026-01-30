import asyncio
import json
import httpx
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v1"
USERNAME = "admin"
PASSWORD = "123456"

async def main():
    print("Starting verification for Skill Visibility...")
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
            print("Login successful.")
        except httpx.ConnectError:
            print("CRITICAL: Cannot connect to server at http://127.0.0.1:8000. Is it running?")
            sys.exit(1)
        except Exception as e:
            print(f"Login failed: {e}")
            sys.exit(1)

        # 2. Start Chat Stream with skill-triggering prompt
        print("Sending prompt: 'Give me some marketing ideas'...")
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        # Use valid parameters: use_multi_agent=True
        payload = {
            "prompt": "Give me some marketing ideas",
            "use_multi_agent": True
        }

        found_expected_status = False
        
        try:
            async with client.stream("POST", "/chat/stream", headers=headers, json=payload) as response:
                response.raise_for_status()
                
                current_event_type = None

                async for line in response.aiter_lines():
                    # print(f"DEBUG LINE: {line}") 
                    line = line.strip()
                    if not line:
                        continue
                        
                    if line.startswith("event: "):
                        current_event_type = line[7:].strip()
                        
                    elif line.startswith("data: "):
                        json_str = line[6:]
                        try:
                            # Skip DONE or empty data
                            if json_str.strip() == "[DONE]":
                                break
                                
                            data = json.loads(json_str)
                            # print(f"DEBUG RAW DATA: {data}")
                            
                            # Use tracked event type
                            if current_event_type == "status":
                                message = data.get("message", "")
                                print(f"DEBUG Status Message: {message}")
                                
                                # Verification Logic
                                if "已加载" in message and "marketing-ideas" in message:
                                    print(f"✅ Success! Found expected message: {message}")
                                    found_expected_status = True
                                    break
                                    
                        except json.JSONDecodeError:
                            pass
                            
        except Exception as e:
            print(f"Streaming failed: {e}")
            sys.exit(1)

    if found_expected_status:
        print("\nTEST RESULT: PASS")
        sys.exit(0)
    else:
        print("\nTEST RESULT: FAIL - Did not see status message with 'marketing-ideas'")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
