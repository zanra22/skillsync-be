import os
import requests
import json

URL = os.environ.get('GRAPHQL_URL', 'http://127.0.0.1:8000/graphql/')

MUTATION = '''
mutation Login($input: LoginInput!) {
  auth { login(input: $input) { success message accessToken expiresIn user { id email } } }
}
'''

VARIABLES = {"input": {"email": "student@test.com", "password": "password123"}}

def main():
    print('POST', URL)
    resp = requests.post(URL, json={"query": MUTATION, "variables": VARIABLES}, timeout=15)
    print('HTTP', resp.status_code)
    print('TEXT:\n', resp.text[:2000])
    try:
        data = resp.json()
        print('\nJSON:\n', json.dumps(data, indent=2)[:4000])
    except Exception as e:
        print('Failed to parse JSON:', e)

if __name__ == '__main__':
    main()
