import requests
import json

base = 'http://localhost:8000'
paths = [
    ('GET', '/health'),
    ('GET', '/health/live'),
    ('GET', '/health/ready'),
    ('GET', '/cases/'),
    ('GET', '/metrics/dashboard'),
    ('GET', '/metrics/summary'),
    ('POST', '/incidents/simulate/card_testing'),
    ('POST', '/incidents/simulate/ato'),
    ('POST', '/incidents/simulate/coordinated_ring'),
    ('POST', '/risk/evaluate'),
    ('GET', '/dashboard'),
    ('GET', '/download'),
    ('GET', '/stream/live-state'),
    ('POST', '/dashboard/evaluate-scenario/LEGITIMATE_TRANSACTION'),
    ('POST', '/dashboard/evaluate-scenario/ACCOUNT_TAKEOVER'),
    ('POST', '/dashboard/evaluate-scenario/COORDINATED_ABUSE_RING'),
    ('POST', '/dashboard/evaluate-scenario/CARD_TESTING'),
    ('POST', '/dashboard/evaluate-scenario/WHAT_BROKE_AT_2AM'),
]

for method, p in paths:
    if method == 'POST':
        if p == '/risk/evaluate':
            r = requests.post(f'{base}{p}', json={
                'transaction_id': 'TXN_TEST_01',
                'timestamp': '2025-06-01 12:00:00',
                'amount': 1500.0,
                'customer_id': 'CUST_01',
                'merchant_id': 'MERCH_01',
                'device_id': 'DEV_01',
                'payment_instrument_id': 'PI_01',
                'features': {'pi_velocity_count_1h': 1}
            })
        else:
            r = requests.post(f'{base}{p}')
        keys = list(r.json().keys()) if r.status_code == 200 else r.text[:60]
        print(f'{method} {p:<50s} -> Status: {r.status_code} | Res: {keys}')
    else:
        r = requests.get(f'{base}{p}')
        keys = list(r.json().keys()) if r.headers.get('content-type') == 'application/json' and r.status_code == 200 else 'non-json / html'
        print(f'{method}  {p:<50s} -> Status: {r.status_code} | Res: {keys}')
