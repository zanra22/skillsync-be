import requests
import json

URL = "http://127.0.0.1:8000/graphql/"
TYPE_NAME = "LoginPayload"

QUERY = {
    "query": f"""
    query TypeQuery {{
      __type(name: \"{TYPE_NAME}\") {{
        name
        fields {{ name type {{ name kind ofType {{ name kind }}}} }}
      }}
    }}
    """
}

def main():
    r = requests.post(URL, json=QUERY, timeout=10)
    try:
        data = r.json()
    except Exception as e:
        print('Invalid JSON:', e)
        print(r.text)
        return

    if 'errors' in data:
        print('Errors:')
        print(json.dumps(data['errors'], indent=2))
        return

    t = data.get('data', {}).get('__type')
    if not t:
        print('Type not found or null')
        return

    print(f"Type: {t.get('name')}")
    for f in t.get('fields', []):
        typ = f.get('type', {})
        name = typ.get('name') or (typ.get('ofType') or {}).get('name')
        print(f" - {f.get('name')} : {name}")

if __name__ == '__main__':
    main()
