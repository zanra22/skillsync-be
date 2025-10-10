#!/usr/bin/env python
"""
Test the specific user's onboarding completion
"""
import requests
import json
import base64

def test_specific_user_onboarding():
    print("🔐 Step 1: Testing onboarding completion with existing token...")
    
    # Use the existing token from the logs
    existing_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU4MjE3NjgyLCJpYXQiOjE3NTgyMTczODIsImp0aSI6ImY5NGI2N2E5YzNjYjQ3MzhiMzlkYTk3NjA5MWYxYTEzIiwidXNlcl9pZCI6InNEVjZUWkhaalQiLCJyb2xlIjoibmV3X3VzZXIiLCJ1c2VyX3JvbGUiOiJuZXdfdXNlciIsImVtYWlsIjoiYXJuYXpkajY5QGdtYWlsLmNvbSIsImlzcyI6IlNraWxsU3luYyJ9.ed5Kujvxq8dAayDAt9o9HbAVjaR8HHOVCE71hz8WUrU'
    
    onboarding_data = {
        "query": """
        mutation {
            onboarding {
                completeOnboarding(input: {
                    role: "learner",
                    firstName: "Test",
                    lastName: "User",
                    bio: "Testing onboarding completion again",
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
    
    try:
        onboarding_response = requests.post(
            'http://127.0.0.1:8000/graphql/',
            json=onboarding_data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {existing_token}',
                'Cookie': f'auth-token={existing_token}'
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
                        print("🎉 SUCCESS: Backend is correctly generating fresh tokens!")
                        print("❌ ISSUE: Frontend is not receiving this token correctly")
                    else:
                        print(f"❌ ISSUE: Expected role 'learner', got '{fresh_payload.get('role')}'")
                else:
                    print("❌ No fresh access token in onboarding response")
            else:
                print(f"❌ Onboarding completion failed: {completion_data.get('message')}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_specific_user_onboarding()