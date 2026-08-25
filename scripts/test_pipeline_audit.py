import requests
import json

base = 'http://localhost:8000'
with open('data/user_samples/sample_transactions.csv', 'r') as f:
    csv_text = f.read()

# 1. Preview
r1 = requests.post(f'{base}/stream/upload/preview', json={'content': csv_text, 'file_format': 'csv'})
print('1. Preview status:', r1.status_code, 'inferred_mapping:', r1.json().get('inferred_mapping'))

# 2. Validate
r2 = requests.post(f'{base}/stream/validate', json={'content': csv_text, 'file_format': 'csv', 'mapping': r1.json().get('inferred_mapping')})
print('2. Validate status:', r2.status_code, 'valid rows:', r2.json().get('valid_rows_count'))

# 3. Start Session
r3 = requests.post(f'{base}/stream/session/start', json={'content': csv_text, 'file_format': 'csv', 'mapping': r1.json().get('inferred_mapping')})
print('3. Session start:', r3.status_code, r3.json())

# 4. Step through all rows
step_count = 0
while True:
    r_step = requests.post(f'{base}/stream/step')
    data = r_step.json()
    event = data.get('event')
    if not event:
        break
    step_count += 1
    t_id = event.get('transaction_id')
    dec = event.get('decision')
    trig = event.get('primary_trigger')
    ml_stat = event.get('ml_status')
    ml_prob = event.get('ml_probability')
    feat = event.get('features', {})
    vel = feat.get('pi_velocity_count_1h', 1)
    ring = event.get('graph_ring_score', 0.0)
    print(f"Step {step_count:02d}: {t_id} | {dec:7s} | Trig: {trig:<28s} | ML={ml_prob*100:4.1f}% [{ml_stat}] | Vel={vel} | Ring={ring:.2f}")
    inv = event.get('investigation')
    if inv:
        hyp = inv.get('hypotheses', [{}])[0].get('hypothesis', 'None')
        print(f"   -> AI Investigation Primary Hypothesis: {hyp}")

# 5. Check final live state
r_state = requests.get(f'{base}/stream/live-state')
state = r_state.json()
print("\nFinal Session Counters:")
print(json.dumps(state.get('counters'), indent=2))
if state.get('active_incident'):
    print("\nActive Live Incident:")
    print(json.dumps(state.get('active_incident'), indent=2))
