#!/bin/bash
# RECON verification — judge runs: ./verification/smoke-test.sh [BASE_URL]
set -e
BASE="${1:-http://localhost:8000}"
echo "== RECON smoke test vs $BASE =="
check() { python3 -c "
import json, urllib.request
def post(p, b):
    r = urllib.request.Request('$BASE'+p, data=json.dumps(b).encode(), headers={'Content-Type':'application/json'}, method='POST')
    return json.load(urllib.request.urlopen(r))
def get(p):
    return json.load(urllib.request.urlopen('$BASE'+p))
assert get('/health')['status'] == 'ok'; print('API reachable')
post('/reset', {}) if False else None
import urllib.request as u
u.urlopen(u.Request('$BASE/reset', data=b'{}', headers={'Content-Type':'application/json'}, method='POST')).read()
post('/observations', {'fact_id':'cert:ABC','value':'valid'})
post('/observations', {'fact_id':'ins:ABC','value':'valid'})
post('/decisions', {'decision_id':'D-104','objective':'approve vendor ABC','dependencies':['cert:ABC','ins:ABC']})
assert post('/authorize', {'decision_id':'D-104','action_id':'A-772'})['verdict'] == 'ALLOW'; print('decision VALID, payment ALLOWED')
post('/observations', {'fact_id':'cert:ABC','value':'EXPIRED'})
assert post('/revalidate', {'decision_id':'D-104'})['verdict'] == 'INVALIDATED'; print('evidence mutated -> INVALIDATED')
assert post('/authorize', {'decision_id':'D-104','action_id':'A-772'})['verdict'] == 'BLOCK'; print('payment BLOCKED')
print('SMOKE OK')
"; }
check
