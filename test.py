import requests
res = requests.post('http://127.0.0.1:8001/api/v1/interactions', json={
    'hcp_id': '7e979e31-f44a-4261-81d0-19063b36d902',
    'interaction_date': '2026-07-13T00:00:00Z',
    'sentiment': 'positive',
    'summary': 'Great meeting',
    'status': 'COMPLETED',
    'product_ids': ['4543ce63-8d93-4dbd-9128-629d19fbaa72'],
    'follow_ups': [{'action_item': 'Send samples', 'priority': 'High'}]
})
print(res.json())
