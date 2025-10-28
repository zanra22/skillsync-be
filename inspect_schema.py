import requests
import json

URL = "http://127.0.0.1:8000/graphql/"

INTROSPECTION = {
    "query": """
    query IntrospectionQuery {
      __schema {
        mutationType { name fields { name args { name type { name kind ofType { name kind } } } type { name kind ofType { name kind } } } }
      }
    }
    """
}

def main():
    try:
        r = requests.post(URL, json=INTROSPECTION, timeout=10)
    except Exception as e:
        print(f"Failed to reach {URL}: {e}")
        return

    try:
        data = r.json()
    except Exception as e:
        print("Invalid JSON response:", e)
        print(r.text)
        return

    if 'errors' in data:
        print('Introspection errors:')
        print(json.dumps(data['errors'], indent=2))
        return

    fields = data.get('data', {}).get('__schema', {}).get('mutationType', {}).get('fields', [])
    if not fields:
        print('No mutation fields found or mutationType is null')
        return

    print('Mutation fields:')
    for f in fields:
        name = f.get('name')
        typ = f.get('type', {})
        type_name = typ.get('name') or (typ.get('ofType') or {}).get('name')
        args = [a['name'] + ':' + (a.get('type', {}).get('name') or (a.get('type', {}).get('ofType') or {}).get('name') or str(a.get('type'))) for a in f.get('args', [])]
        print(f" - {name}({', '.join(args)}) -> {type_name}")

if __name__ == '__main__':
    main()
