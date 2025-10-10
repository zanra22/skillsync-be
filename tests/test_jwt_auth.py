#!/usr/bin/env python
"""
Test script for JWT authentication with GraphQL
"""
import os
import django
import json
import requests
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

# GraphQL endpoint
GRAPHQL_URL = "http://localhost:8000/graphql/"

def test_login():
    """Test login mutation and JWT token generation"""
    
    # Login mutation
    login_mutation = """
    mutation Login($input: LoginInput!) {
        auth {
            login(input: $input) {
                success
                message
                user {
                    id
                    email
                    username
                    role
                    accountStatus
                    isPremium
                }
                accessToken
                expiresIn
            }
        }
    }
    """
    
    # Variables (replace with your superuser credentials)
    variables = {
        "input": {
            "email": "admin1@gmail.com",  # Replace with your superuser email
            "password": "123",        # Replace with your superuser password
            "rememberMe": True
        }
    }
    
    # Make request
    response = requests.post(
        GRAPHQL_URL,
        json={
            "query": login_mutation,
            "variables": variables
        },
        headers={
            "Content-Type": "application/json"
        }
    )
    
    print("=== LOGIN TEST ===")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("Response:")
        print(json.dumps(data, indent=2))
        
        # Extract tokens if login successful
        if data.get("data", {}).get("auth", {}).get("login", {}).get("success"):
            access_token = data["data"]["auth"]["login"]["accessToken"]
            # Refresh token is now in HTTP-only cookies, not in response
            print(f"\n✅ Login successful!")
            print(f"Access Token: {access_token[:50]}...")
            print("Refresh Token: Stored in HTTP-only cookie")
            return access_token, None  # Return None for refresh token since it's in cookies
        else:
            print(f"❌ Login failed: {data.get('data', {}).get('auth', {}).get('login', {}).get('message')}")
    else:
        print(f"❌ HTTP Error: {response.text}")
    
    return None, None

def test_users_query(access_token):
    """Test authenticated users query"""
    
    users_query = """
    query GetUsers {
        users {
            users {
                id
                email
                username
                role
                accountStatus
                isPremium
            }
        }
    }
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.post(
        GRAPHQL_URL,
        json={"query": users_query},
        headers=headers
    )
    
    print("\n=== USERS QUERY TEST ===")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("Response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ HTTP Error: {response.text}")

def test_refresh_token():
    """Test token refresh mutation using HTTP-only cookies"""
    
    refresh_mutation = """
    mutation RefreshToken {
        auth {
            refreshToken {
                success
                message
                accessToken
                expiresIn
            }
        }
    }
    """
    
    # No variables needed since refresh token is in cookies
    response = requests.post(
        GRAPHQL_URL,
        json={"query": refresh_mutation},
        headers={
            "Content-Type": "application/json"
        }
    )
    
    print("\n=== TOKEN REFRESH TEST ===")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("Response:")
        print(json.dumps(data, indent=2))
        
        if data.get("data", {}).get("auth", {}).get("refreshToken", {}).get("success"):
            new_access_token = data["data"]["auth"]["refreshToken"]["accessToken"]
            print(f"✅ Token refresh successful!")
            print(f"New Access Token: {new_access_token[:50]}...")
            return new_access_token
    else:
        print(f"❌ HTTP Error: {response.text}")
    
    return None

def test_logout():
    """Test logout mutation using HTTP-only cookies"""
    
    logout_mutation = """
    mutation Logout {
        auth {
            logout {
                success
                message
            }
        }
    }
    """
    
    # No variables needed since refresh token is in cookies
    response = requests.post(
        GRAPHQL_URL,
        json={"query": logout_mutation},
        headers={
            "Content-Type": "application/json"
        }
    )
    
    print("\n=== LOGOUT TEST ===")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("Response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ HTTP Error: {response.text}")

if __name__ == "__main__":
    print("🚀 Testing JWT Authentication with GraphQL\n")
    
    # Test login
    access_token, _ = test_login()  # refresh_token is now in cookies
    
    if access_token:
        # Test authenticated query
        test_users_query(access_token)
        
        # Test token refresh (using cookies)
        new_access_token = test_refresh_token()
        
        # Test logout (using cookies)
        test_logout()
    
    print("\n✨ Testing completed!")
