import sys, os
sys.path.append(os.path.abspath('.'))
from app import app, db
from models import Permit

with app.app_context():
    permit = Permit.query.first()
    if not permit:
        print('No permits found in database.')
    else:
        client = app.test_client()
        resp = client.get(f'/verify/{permit.uuid}')
        print('Status code:', resp.status_code)
        # Print a snippet of the HTML for quick verification
        snippet = resp.data.decode('utf-8')[:800]
        print('--- HTML snippet start ---')
        print(snippet)
        print('--- HTML snippet end ---')
