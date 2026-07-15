import json
import codecs

try:
    with codecs.open('repos.json', 'r', 'utf-8-sig') as f:
        data = json.load(f)
        for repo in data[:15]:
            print(f"- {repo.get('name')}: {repo.get('description')} ({repo.get('language')})")
except Exception as e:
    print(e)
