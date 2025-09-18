#!/usr/bin/env python
"""
Test script to verify custom JWT tokens include role field
"""
import requests
import json
import base64

def test_jwt_with_role():
    # Test login to get new JWT token with role
    login_data = {
        "query": """
        mutation {
            auth {
                login(input: {email: "test@skillsync.com", password: "test123456"}) {
                    success
                    message
                    accessToken
                    user {
                        id
                        email
                        role
                    }
                }
            }
        }
        """
    }

    try:
        print("Testing custom JWT token generation...")
        response = requests.post('http://127.0.0.1:8000/graphql/', json=login_data)
        print(f'Response Status: {response.status_code}')
        
        result = response.json()
        print('Response:', json.dumps(result, indent=2))
        
        # If we get a token, decode it to check the payload
        if response.status_code == 200 and 'data' in result:
            data = result['data']
            if data and 'auth' in data and data['auth'] and 'login' in data['auth'] and data['auth']['login'] and data['auth']['login']['accessToken']:
                token = data['auth']['login']['accessToken']
                print(f"\nReceived Access Token: {token[:50]}...")
                
                # Decode JWT payload
                payload_b64 = token.split('.')[1]
                # Add padding if needed
                payload_b64 += '=' * (4 - len(payload_b64) % 4)
                payload = json.loads(base64.b64decode(payload_b64).decode())
                
                print('\n=== JWT Payload with Custom Token ===')
                print(json.dumps(payload, indent=2))
                
                # Check if role is included
                if 'role' in payload:
                    print(f"\n✅ SUCCESS: Role field found in JWT: {payload['role']}")
                elif 'user_role' in payload:
                    print(f"\n✅ SUCCESS: User role field found in JWT: {payload['user_role']}")
                else:
                    print("\n❌ ISSUE: No role field found in JWT payload")
                    print("Available fields:", list(payload.keys()))
            else:
                print("\n❌ No access token in response")
        else:
            print(f"\n❌ Login failed or invalid response")
            
    except Exception as e:
        print(f'Error: {str(e)}')

if __name__ == "__main__":
    test_jwt_with_role()