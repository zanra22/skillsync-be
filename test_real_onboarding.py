#!/usr/bin/env python
"""
Test onboarding completion to see detailed logs
"""
import requests
import json
import base64

def test_onboarding_completion():
    # Use the GraphQL endpoint directly to test onboarding completion
    graphql_data = {
        "query": """
        mutation {
            onboarding {
                completeOnboarding(input: {
                    role: "learner",
                    firstName: "Test",
                    lastName: "User",
                    bio: "Testing onboarding completion",
                    industry: "Technology",
                    careerStage: "entry_level",
                    goals: [{
                        skillName: "Web Development",
                        description: "Learn modern web development",
                        targetSkillLevel: "intermediate",
                        priority: 1
                    }],
                    preferences: {
                        learningStyle: "visual",
                        timeCommitment: "part_time"
                    }
                }) {
                    success
                    message
                    user {
                        id
                        email
                        role
                        firstName
                        lastName
                    }
                    accessToken
                    expiresIn
                }
            }
        }
        """
    }
    
    print("🚀 Testing onboarding completion with GraphQL...")
    
    try:
        response = requests.post(
            'http://127.0.0.1:8000/graphql/',
            json=graphql_data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU4MjE2NTkxLCJpYXQiOjE3NTgyMTYyOTEsImp0aSI6IjczODdiM2E1ZDhjNDQ0ZWM4ZTc1YmMxZjQ1MDRjZjczIiwidXNlcl9pZCI6InNEVjZUWkhaalQiLCJyb2xlIjoibmV3X3VzZXIiLCJ1c2VyX3JvbGUiOiJuZXdfdXNlciIsImVtYWlsIjoiYXJuYXpkajY5QGdtYWlsLmNvbSIsImlzcyI6IlNraWxsU3luYyJ9.9kqg_deT8hLhsasnUS3hzDTKuxpb2eD810GEngZ16pI',
                'Cookie': 'auth-token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU4MjE2NTkxLCJpYXQiOjE3NTgyMTYyOTEsImp0aSI6IjczODdiM2E1ZDhjNDQ0ZWM4ZTc1YmMxZjQ1MDRjZjczIiwidXNlcl9pZCI6InNEVjZUWkhaalQiLCJyb2xlIjoibmV3X3VzZXIiLCJ1c2VyX3JvbGUiOiJuZXdfdXNlciIsImVtYWlsIjoiYXJuYXpkajY5QGdtYWlsLmNvbSIsImlzcyI6IlNraWxsU3luYyJ9.9kqg_deT8hLhsasnUS3hzDTKuxpb2eD810GEngZ16pI'
            }
        )
        
        print(f"Response Status: {response.status_code}")
        result = response.json()
        print("Response:", json.dumps(result, indent=2))
        
        # Check if we got an access token
        if 'data' in result and result['data'] and 'onboarding' in result['data']:
            onboarding_data = result['data']['onboarding']['completeOnboarding']
            if onboarding_data and onboarding_data.get('accessToken'):
                token = onboarding_data['accessToken']
                print(f"\n✅ Received fresh access token: {token[:50]}...")
                
                # Decode and check the role
                payload_b64 = token.split('.')[1]
                payload_b64 += '=' * (4 - len(payload_b64) % 4)
                payload = json.loads(base64.b64decode(payload_b64).decode())
                
                print("\n🔍 Fresh token payload:")
                print(json.dumps(payload, indent=2))
                print(f"\nRole in fresh token: {payload.get('role')}")
                
            else:
                print("❌ No access token in response")
        else:
            print("❌ Invalid response structure")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_onboarding_completion()