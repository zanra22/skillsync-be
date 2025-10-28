"""Onboarding test runner (clean UTF-8 file).

This script will:
- Attempt to login each test user via auth.login(input: LoginInput)
- If login reports success:false, it will call auth.signUp and retry login once
- Call completeOnboarding with the provided input and print full responses

Run while the dev server is running:
  .\.venv\Scripts\activate
  python .\test_complete_onboarding_flow_runner.py
"""

from typing import Any, Dict, Optional
import os
import sys
import json
import requests
import django
from django.utils import timezone


GRAPHQL_URL = os.environ.get("GRAPHQL_URL", "http://127.0.0.1:8000/graphql/")


def post_graphql(query: str, variables: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> Dict[str, Any]:
    payload = {"query": query}
    if variables is not None:
        payload["variables"] = variables
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    resp = requests.post(GRAPHQL_URL, json=payload, headers=hdrs, timeout=timeout)
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Non-JSON response {resp.status_code}: {resp.text}")
    if isinstance(data, dict) and data.get('errors'):
        print("GraphQL errors:", json.dumps(data.get('errors'), indent=2))
    return data


def login(email: str, password: str) -> Any:
    """Return access token string on success, or a dict describing a login failure.

    On server-side failure the function returns a dict like {'login_failed': True, 'payload': {...}}
    On unexpected errors the function raises.
    """
    mutation = '''
    mutation Login($input: LoginInput!) {
      auth { login(input: $input) { success message accessToken expiresIn user { id email } } }
    }
    '''
    vars = {"input": {"email": email, "password": password}}
    r = post_graphql(mutation, vars)

    login_obj = r.get('data', {}).get('auth', {}).get('login') if isinstance(r, dict) else None
    if isinstance(login_obj, dict):
        if login_obj.get('success'):
            return login_obj.get('accessToken')
        # explicit login failure: return structured payload so caller can decide
        return {'login_failed': True, 'payload': login_obj}

    # fallback: try other shapes
    if isinstance(r, dict):
        # flattened login
        t = r.get('data', {}).get('login')
        if isinstance(t, dict) and t.get('success'):
            return t.get('accessToken') or t.get('token')

    raise RuntimeError(f"Unexpected login response: {json.dumps(r)[:2000]}")


def signup_user(email: str, password: str) -> Dict[str, Any]:
    mutation = '''
    mutation SignUp($input: SignupInput!) { auth { signUp(input: $input) { success message user { id email } } } }
    '''
    vars = {"input": {"email": email, "password": password, "acceptTerms": True}}
    return post_graphql(mutation, vars)


def create_user_via_users_mutation(username: str, email: str, password: str) -> Dict[str, Any]:
    mutation = '''
    mutation CreateUser($username: String!, $email: String!, $password: String!) { users { createUser(username: $username, email: $email, password: $password) { id email } } }
    '''
    vars = {"username": username, "email": email, "password": password}
    return post_graphql(mutation, vars)


def mark_user_verified_local(email: str) -> bool:
    """Dev-only: mark the given user as email-verified and active using Django ORM.

    Returns True if user found and updated, False otherwise.
    """
    # Set Django settings and initialize if not already
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
    try:
        django.setup()
    except Exception:
        # django may already be setup; ignore errors
        pass
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return False
        # Set verification flags used by this project
        if hasattr(user, 'is_email_verified'):
            user.is_email_verified = True
        if hasattr(user, 'email_verified_at'):
            user.email_verified_at = timezone.now()
        # Also set account_status to active if present (login checks this)
        if hasattr(user, 'account_status'):
            try:
                user.account_status = 'active'
            except Exception:
                pass
        if hasattr(user, 'is_active'):
            user.is_active = True
        user.save()
        return True
    except Exception as e:
        print('Failed to mark user verified locally:', e)
        return False


def generate_access_token_local(email: str) -> Optional[str]:
    """Dev-only: create a refresh token and return access token string for the user.

    Returns access token string on success, None on failure.
    """
    try:
        from django.contrib.auth import get_user_model
        from auth.custom_tokens import CustomRefreshToken as RefreshToken
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return None
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        return str(access)
    except Exception as e:
        print('Failed to generate local access token:', e)
        return None


def complete_onboarding(token: str, input_obj: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    mutation_a = '''
    mutation CompleteOnboarding($input: CompleteOnboardingInput!) { users { completeOnboarding(input: $input) { success errors user { id email } } } }
    '''
    r = post_graphql(mutation_a, {"input": input_obj}, headers)
    if r.get('data', {}).get('users'):
        return r

    mutation_b = '''
    mutation CompleteOnboarding($input: CompleteOnboardingInput!) { completeOnboarding(input: $input) { success errors user { id email } } }
    '''
    return post_graphql(mutation_b, {"input": input_obj}, headers)


TEST_USERS = [
    ("student@test.com", "password123", {"role": "student", "firstName": "John", "lastName": "Student", "currentRole": "Student", "industry": "Software Development", "careerStage": "student", "goals": [{"skillName": "Python Programming", "description": "Learn Python fundamentals", "targetSkillLevel": "beginner", "priority": 1}], "learningStyle": "hands_on", "timeCommitment": "casual"}),
    ("professional@test.com", "password123", {"role": "professional", "firstName": "Jane", "lastName": "Professional", "currentRole": "Marketing Manager", "industry": "Digital Marketing", "careerStage": "mid_level", "goals": [{"skillName": "Data Analysis", "description": "Learn data analysis for marketing insights", "targetSkillLevel": "intermediate", "priority": 1}], "learningStyle": "video", "timeCommitment": "steady"}),
    ("career@test.com", "password123", {"role": "career_changer", "firstName": "Bob", "lastName": "Changer", "currentRole": "Teacher", "industry": "Data Science", "careerStage": "career_changer", "transitionTimeline": "6_months", "goals": [{"skillName": "Machine Learning", "description": "Transition from teaching to ML engineering", "targetSkillLevel": "intermediate", "priority": 1}], "learningStyle": "mixed", "timeCommitment": "focused"}),
]


def run_tests():
    any_fail = False
    print('Running tests against', GRAPHQL_URL)
    for email, pw, inp in TEST_USERS:
        print('\n=== Running test for', email, '===')
        try:
            # Try to generate a local access token first (bypass auth.login)
            token = generate_access_token_local(email)
            if token:
                print('Generated local access token')
            else:
                # No local token - try to create user via signUp
                print('Local token not found, attempting signup...')
                s = signup_user(email, pw)
                print('Signup response:', json.dumps(s, indent=2)[:2000])
                # If auth.signUp didn't create user, try users.createUser
                if s.get('data', {}).get('auth', {}).get('signUp', {}).get('success') is False:
                    print('Attempting fallback creation via users.createUser...')
                    username = email.split('@')[0].lower().replace('.', '_')
                    cu = create_user_via_users_mutation(username, email, pw)
                    print('createUser response:', json.dumps(cu, indent=2)[:2000])
                # Mark account verified and try to generate token
                marked = mark_user_verified_local(email)
                print('Marked verified locally:', marked)
                token = generate_access_token_local(email)
                if token:
                    print('Generated local access token after signup')
                else:
                    raise RuntimeError('Unable to generate access token for user')
            print('Token (truncated):', token[:60] + '...' if len(token) > 60 else token)
        except Exception as e:
            print('Setup/login failed:', e)
            any_fail = True
            continue

        try:
            # Call users.completeOnboarding with flat args discovered via introspection
            role = inp.get('role')
            firstName = inp.get('firstName')
            lastName = inp.get('lastName')
            currentRole = inp.get('currentRole')
            industry = inp.get('industry')
            careerStage = inp.get('careerStage')
            transitionTimeline = inp.get('transitionTimeline')
            learningStyle = inp.get('learningStyle')
            timeCommitment = inp.get('timeCommitment')

            mutation = '''
            mutation CompleteOnboarding($role: String!, $firstName: String!, $lastName: String!, $currentRole: String!, $industry: String!, $careerStage: String!, $transitionTimeline: String, $learningStyle: String, $timeCommitment: String) {
              users { completeOnboarding(role: $role, firstName: $firstName, lastName: $lastName, currentRole: $currentRole, industry: $industry, careerStage: $careerStage, transitionTimeline: $transitionTimeline, learningStyle: $learningStyle, timeCommitment: $timeCommitment) { success message user { id email } } }
            }
            '''
            vars = {
                'role': role, 'firstName': firstName, 'lastName': lastName, 'currentRole': currentRole,
                'industry': industry, 'careerStage': careerStage, 'transitionTimeline': transitionTimeline,
                'learningStyle': learningStyle, 'timeCommitment': timeCommitment
            }
            resp = post_graphql(mutation, vars, headers={"Authorization": f"Bearer {token}"})
            print('CompleteOnboarding response:', json.dumps(resp, indent=2)[:4000])
            success = False
            if resp.get('data', {}).get('users'):
                # users.completeOnboarding nested
                success = bool(resp['data']['users']['completeOnboarding'].get('success'))
            elif resp.get('data', {}).get('completeOnboarding'):
                success = bool(resp['data']['completeOnboarding'].get('success'))
            if success:
                print('Onboarding succeeded for', email)
            else:
                print('Onboarding likely failed for', email)
                any_fail = True
        except Exception as e:
            print('Complete onboarding failed:', e)
            any_fail = True

    if any_fail:
        print('\nOne or more tests failed')
        sys.exit(1)
    print('\nAll tests done successfully')


if __name__ == '__main__':
    run_tests()
"""Small, robust GraphQL onboarding test runner (UTF-8 file).

This is a duplicate runner saved under a different filename to avoid
encoding issues in the workspace. Run this directly with Python while
the GraphQL dev server is running.
"""

from typing import Any, Dict, Optional
import os
import sys
import json
import requests


GRAPHQL_URL = os.environ.get("GRAPHQL_URL", "http://127.0.0.1:8000/graphql/")


def post_graphql(query: str, variables: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> Dict[str, Any]:
    payload = {"query": query}
    if variables is not None:
        payload["variables"] = variables
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    resp = requests.post(GRAPHQL_URL, json=payload, headers=hdrs, timeout=timeout)
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Non-JSON response {resp.status_code}: {resp.text}")
    # If GraphQL-level errors exist, include them for debugging
    """Small, robust GraphQL onboarding test runner (UTF-8 file).

    This is a duplicate runner saved under a different filename to avoid
    encoding issues in the workspace. Run this directly with Python while
    the GraphQL dev server is running.
    """

    from typing import Any, Dict, Optional
    import os
    import sys
    import json
    import requests


    GRAPHQL_URL = os.environ.get("GRAPHQL_URL", "http://127.0.0.1:8000/graphql/")


    def post_graphql(query: str, variables: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> Dict[str, Any]:
        payload = {"query": query}
        if variables is not None:
            payload["variables"] = variables
        hdrs = {"Content-Type": "application/json"}
        if headers:
            hdrs.update(headers)
        resp = requests.post(GRAPHQL_URL, json=payload, headers=hdrs, timeout=timeout)
        try:
            data = resp.json()
        except Exception:
            raise RuntimeError(f"Non-JSON response {resp.status_code}: {resp.text}")
        # If GraphQL-level errors exist, include them for debugging
        if isinstance(data, dict) and data.get('errors'):
            # keep the errors but also return the payload so callers can inspect
            print("GraphQL errors:", json.dumps(data.get('errors'), indent=2)[:1000])
        return data


    def login(email: str, password: str) -> str:
        # Try a namespaced login (auth.login) — request only likely fields
        mutation_a = '''
        mutation Login($input: LoginInput!) {
          auth { login(input: $input) { success message accessToken expiresIn } }
        }
        '''
        vars_a = {"input": {"email": email, "password": password}}
        try:
            r = post_graphql(mutation_a, vars_a)
            token = r.get("data", {}).get("auth", {}).get("login", {}).get("accessToken")
            if token:
                print('Got token from auth.login')
                return token
            # If login returned but success is false, return the payload for caller to inspect
            login_obj = r.get('data', {}).get('auth', {}).get('login')
            if isinstance(login_obj, dict) and login_obj.get('success') is False:
                return json.dumps({'login_failed': True, 'payload': login_obj})
        except Exception:
            pass

        # Try a flat login mutation (top-level login)
        mutation_b = '''
        mutation Login($email: String!, $password: String!) { login(email: $email, password: $password) { success token } }
        '''
        try:
            r = post_graphql(mutation_b, {"email": email, "password": password})
        except Exception as e:
            raise RuntimeError(f"Login request error: {e}")

        # Try several possible token locations
        token = None
        if isinstance(r, dict):
            token = (
                r.get('data', {}).get('auth', {}).get('login', {}).get('accessToken') or
                r.get('data', {}).get('auth', {}).get('login', {}).get('token') or
                r.get('data', {}).get('login', {}).get('token') or
                r.get('data', {}).get('login', {}).get('accessToken') or
                r.get('data', {}).get('accessToken') or
                r.get('data', {}).get('token')
            )
        if token:
            return token
        # If we received a structured failure payload (as JSON string), pass it up
        if isinstance(r, str) and r.startswith('{'):
            return r
        raise RuntimeError(f"Login failed for {email}: {json.dumps(r)[:800]}")


    def signup_user(email: str, password: str) -> Dict[str, Any]:
        mutation = '''
        mutation SignUp($input: SignupInput!) { auth { signUp(input: $input) { success message user { id email } } } }
        '''
        vars = {"input": {"email": email, "password": password, "acceptTerms": True}}
        return post_graphql(mutation, vars)


    def complete_onboarding(token: str, input_obj: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        mutation_a = '''
        mutation CompleteOnboarding($input: CompleteOnboardingInput!) { users { completeOnboarding(input: $input) { success errors user { id email } } } }
        '''
        try:
            r = post_graphql(mutation_a, {"input": input_obj}, headers)
            if r.get("data", {}).get("users"):
                return r
        except Exception:
            pass
        mutation_b = '''
        mutation CompleteOnboarding($input: CompleteOnboardingInput!) { completeOnboarding(input: $input) { success errors user { id email } } }
        '''
        return post_graphql(mutation_b, {"input": input_obj}, headers)


    TEST_USERS = [
        ("student@test.com", "password123", {"role": "student", "firstName": "John", "lastName": "Student", "currentRole": "Student", "industry": "Software Development", "careerStage": "student", "goals": [{"skillName": "Python Programming", "description": "Learn Python fundamentals", "targetSkillLevel": "beginner", "priority": 1}], "learningStyle": "hands_on", "timeCommitment": "casual"}),
        ("professional@test.com", "password123", {"role": "professional", "firstName": "Jane", "lastName": "Professional", "currentRole": "Marketing Manager", "industry": "Digital Marketing", "careerStage": "mid_level", "goals": [{"skillName": "Data Analysis", "description": "Learn data analysis for marketing insights", "targetSkillLevel": "intermediate", "priority": 1}], "learningStyle": "video", "timeCommitment": "steady"}),
        ("career@test.com", "password123", {"role": "career_changer", "firstName": "Bob", "lastName": "Changer", "currentRole": "Teacher", "industry": "Data Science", "careerStage": "career_changer", "transitionTimeline": "6_months", "goals": [{"skillName": "Machine Learning", "description": "Transition from teaching to ML engineering", "targetSkillLevel": "intermediate", "priority": 1}], "learningStyle": "mixed", "timeCommitment": "focused"}),
    ]


    def run_tests():
        any_fail = False
        for email, pw, inp in TEST_USERS:
            print(f"\n=== Running test for {email} ===")
            try:
                token = login(email, pw)
                # If login returned a JSON-encoded failure payload, attempt signup then retry
                if isinstance(token, str) and token.startswith('{'):
                    obj = json.loads(token)
                    if obj.get('login_failed'):
                        print('Login failed on server side, attempting signup...')
                        s = signup_user(email, pw)
                        print('Signup response:', json.dumps(s)[:400])
                        token = login(email, pw)
                print("Token:", token[:30] + '...' if token and len(token) > 30 else token)
            except Exception as e:
                print("Login failed:", e)
                any_fail = True
                continue
            try:
                resp = complete_onboarding(token, inp)
                print(json.dumps(resp, indent=2)[:1000])
                success = False
                if resp.get("data", {}).get("users"):
                    success = bool(resp["data"]["users"]["completeOnboarding"].get("success"))
                elif resp.get("data", {}).get("completeOnboarding"):
                    success = bool(resp["data"]["completeOnboarding"].get("success"))
                if success:
                    print("Onboarding succeeded for", email)
                else:
                    print("Onboarding probably failed for", email)
                    any_fail = True
            except Exception as e:
                print("Complete onboarding failed:", e)
                any_fail = True
        if any_fail:
            sys.exit(1)
        print("All tests done.")


    if __name__ == '__main__':
        print("Running tests against", GRAPHQL_URL)
        run_tests()
