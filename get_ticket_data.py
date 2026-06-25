import requests
from requests.auth import HTTPBasicAuth
import json

email = 'k.boltovskij@iridi.tech'
key = 'a87bdc0bdd5442e1b1d31841c'
base = 'https://iridi.omnidesk.ru'
auth = HTTPBasicAuth(email, key)

ticket_id = 411895040

# Get ticket detail
r = requests.get(f'{base}/api/cases/{ticket_id}.json', auth=auth, timeout=30)
print('=== TICKET DETAIL ===')
if r.status_code == 200:
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))
else:
    print(f'Error: {r.status_code} {r.text[:500]}')

# Get messages
r2 = requests.get(f'{base}/api/cases/{ticket_id}/messages.json', auth=auth,
                  params={'limit': 100, 'order': 'asc'}, timeout=30)
print('\n=== MESSAGES ===')
if r2.status_code == 200:
    print(json.dumps(r2.json(), ensure_ascii=False, indent=2))
else:
    print(f'Error: {r2.status_code} {r2.text[:500]}')
