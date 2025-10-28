import requests
import json
import os

URL = os.environ.get('GRAPHQL_URL', 'http://127.0.0.1:8000/graphql/')
TYPE_NAME = 'UsersMutation'

QUERY = {
    'query': f'''
    query TypeQuery {{
      __type(name: "{TYPE_NAME}") {{
        name
        fields {{
          name
          args {{ name type {{ name kind ofType {{ name kind }}}}}}
          type {{ name kind ofType {{ name kind }}}}
        }}
      }}
    }}
    '''
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
        print('Errors:', json.dumps(data['errors'], indent=2))
        return
    t = data.get('data', {}).get('__type')
    if not t:
        print('Type not found or null')
        return
    print(f"Type: {t.get('name')}")
    for f in t.get('fields', []):
        args = []
        for a in f.get('args', []):
            a_type = a.get('type', {})
            name = a_type.get('name') or (a_type.get('ofType') or {}).get('name')
            args.append(f"{a['name']}:{name}")
        ret = f.get('type', {})
        ret_name = ret.get('name') or (ret.get('ofType') or {}).get('name')
        print(f" - {f.get('name')}({', '.join(args)}) -> {ret_name}")

if __name__ == '__main__':
    main()
