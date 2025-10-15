#!/usr/bin/env python
"""
Complete test: Login first, then test onboarding completion
"""
import requests
import json
import base64

def test_login_and_onboarding():
    print("🔐 Step 1: Login to get fresh token...")
    
    # First, login to get a fresh token
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
        # Login first
        login_response = requests.post('http://127.0.0.1:8000/graphql/', json=login_data)
        print(f"Login Response Status: {login_response.status_code}")
        
        login_result = login_response.json()
        print("Login Response:", json.dumps(login_result, indent=2))
        
        if not (login_result.get('data') and 
                login_result['data'].get('auth') and 
                login_result['data']['auth'].get('login') and 
                login_result['data']['auth']['login'].get('accessToken')):
            print("❌ Login failed - cannot get access token")
            return
            
        access_token = login_result['data']['auth']['login']['accessToken']
        user_data = login_result['data']['auth']['login']['user']
        
        print(f"✅ Login successful - User: {user_data['email']}, Role: {user_data['role']}")
        print(f"🎯 Access token: {access_token[:50]}...")
        
        # Decode the token to check role
        payload_b64 = access_token.split('.')[1]
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64).decode())
        print(f"🔍 Token role: {payload.get('role')}")
        
        print("\n🚀 Step 2: Testing onboarding completion...")
        
        # Now test onboarding completion with fresh token
        onboarding_data = {
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
        
        onboarding_response = requests.post(
            'http://127.0.0.1:8000/graphql/',
            json=onboarding_data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'Cookie': f'auth-token={access_token}'
            }
        )
        
        print(f"Onboarding Response Status: {onboarding_response.status_code}")
        onboarding_result = onboarding_response.json()
        print("Onboarding Response:", json.dumps(onboarding_result, indent=2))
        
        # Check for fresh token in onboarding response
        if (onboarding_result.get('data') and 
            onboarding_result['data'].get('onboarding') and 
            onboarding_result['data']['onboarding'].get('completeOnboarding')):
            
            completion_data = onboarding_result['data']['onboarding']['completeOnboarding']
            
            if completion_data.get('success'):
                print("✅ Onboarding completion successful!")
                
                if completion_data.get('accessToken'):
                    fresh_token = completion_data['accessToken']
                    print(f"🎯 Fresh token received: {fresh_token[:50]}...")
                    
                    # Decode fresh token
                    fresh_payload_b64 = fresh_token.split('.')[1]
                    fresh_payload_b64 += '=' * (4 - len(fresh_payload_b64) % 4)
                    fresh_payload = json.loads(base64.b64decode(fresh_payload_b64).decode())
                    
                    print("\n🔍 Fresh token payload:")
                    print(json.dumps(fresh_payload, indent=2))
                    print(f"\n✅ Fresh token role: {fresh_payload.get('role')}")
                    
                    if fresh_payload.get('role') == 'learner':
                        print("🎉 SUCCESS: JWT token correctly updated with new role!")
                    else:
                        print(f"❌ ISSUE: Expected role 'learner', got '{fresh_payload.get('role')}'")
                else:
                    print("❌ No fresh access token in onboarding response")
            else:
                print(f"❌ Onboarding completion failed: {completion_data.get('message')}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login_and_onboarding()