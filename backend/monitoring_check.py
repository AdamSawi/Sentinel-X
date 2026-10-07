"""Read-only integration checks of Prometheus and provisioned Grafana."""
import base64
import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import psycopg

creds = Path('/run/sentinel')
admin = (creds / 'grafana-admin.password').read_text().strip()
authorization = 'Basic ' + base64.b64encode(('admin:' + admin).encode()).decode()


def get(url, payload=None):
    headers = {'Content-Type': 'application/json'}
    if url.startswith('http://grafana:3000/'):
        headers['Authorization'] = authorization
    req = Request(url, data=json.dumps(payload).encode() if payload else None, headers=headers)
    with urlopen(req, timeout=20) as response:
        return json.load(response)


for attempt in range(15):
    result = get('http://prometheus:9090/api/v1/query?' + urlencode({'query': 'up{job="sentinel-api"}'}))
    if result['data']['result'] and result['data']['result'][0]['value'][1] == '1':
        break
    time.sleep(2)
else:
    raise AssertionError('Prometheus cannot scrape the API')

for uid in ('sentinel-prometheus', 'sentinel-postgres'):
    result = get(f'http://grafana:3000/api/datasources/uid/{uid}/health')
    assert result.get('status') == 'OK', result

dashboard = get('http://grafana:3000/api/dashboards/uid/sentinel-overview')['dashboard']
queries = []
for panel in dashboard['panels']:
    for target in panel.get('targets', []):
        queries.append({**target, 'refId': f"{panel['id']}-{target['refId']}", 'datasource': panel['datasource'],
                        'intervalMs': 5000, 'maxDataPoints': 1000})
now = int(time.time() * 1000)
results = get('http://grafana:3000/api/ds/query', {'from': str(now - 86400000), 'to': str(now), 'queries': queries})
assert len(results['results']) == len(queries)
for ref, result in results['results'].items():
    assert not result.get('error'), (ref, result.get('error'))
    assert result.get('status', 200) == 200, (ref, result.get('status'))

with psycopg.connect(host='postgres', dbname='sentinel', user='grafana_reader',
                     password=(creds / 'grafana-db.password').read_text().strip()) as db:
    row = db.execute("SELECT has_table_privilege(current_user,'observations','INSERT'), has_table_privilege(current_user,'observations','SELECT')").fetchone()
    assert row == (False, True), row
    assert db.execute('SELECT count(*) FROM observations').fetchone()[0] > 0
    assert db.execute('SELECT count(*) FROM security_events').fetchone()[0] > 0
print(f'PASS: Prometheus scrape, both Grafana sources, {len(queries)} panel queries, persistent reports and SQL read-only permissions.')
