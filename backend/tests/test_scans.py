"""Owned generalized static analysis, safe upload and explicit AI consent."""
from io import BytesIO
import zipfile

from backend.tests.test_product import product, register


def _zip(files):
    stream = BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return stream.getvalue()


def test_vulnerable_python_scan_and_cross_user_isolation(product):
    alice, headers = register(product, 'scan-alice@example.test')
    bob, bob_headers = register(product, 'scan-bob@example.test')
    project = alice.post('/api/projects', headers=headers, json={'name': 'Python sample'}).json()['id']
    data = _zip({'requirements.txt': 'fastapi==0.1\n', 'main.py': 'import sqlite3\n\ndef lookup(conn, user_id):\n    return conn.execute(f"SELECT * FROM users WHERE id={user_id}")\n'})
    uploaded = alice.post(f'/api/projects/{project}/upload', headers={**headers, 'Content-Type': 'application/zip'}, content=data)
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()['status'] == 'READY_FOR_SCAN'
    assert 'main.py' in alice.get(f'/api/projects/{project}/files').json()
    scan = alice.post(f'/api/projects/{project}/scan', headers=headers)
    assert scan.status_code == 201, scan.text
    assert scan.json()['finding_count'] == 1
    findings = alice.get(f'/api/projects/{project}/findings').json()
    assert findings[0]['category'] == 'SQL_INJECTION'
    assert findings[0]['validation_status'] == 'POTENTIAL'
    assert bob.get(f'/api/projects/{project}/findings').status_code == 404
    assert bob.get(f'/api/scan-findings/{findings[0]["id"]}').status_code == 404
    assert bob.post(f'/api/projects/{project}/scan', headers=bob_headers).status_code == 404
    preview = alice.get(f'/api/projects/{project}/ai-review/preview?scan_id={scan.json()["id"]}').json()
    assert preview['files'][0]['path'] == 'main.py'
    no_consent = alice.post(f'/api/projects/{project}/ai-review', headers=headers,
                           json={'scan_id': scan.json()['id'], 'approved_files': ['main.py'], 'consent': False})
    assert no_consent.status_code == 422
    with product.state.workflow.db.read() as db:
        assert db.execute('SELECT count(*) FROM source_share_consents').fetchone()[0] == 0


def test_safe_and_unsupported_files(product):
    client, headers = register(product, 'safe@example.test')
    project = client.post('/api/projects', headers=headers, json={'name': 'safe'}).json()['id']
    uploaded = client.post(f'/api/projects/{project}/upload-file', headers={**headers, 'Content-Type': 'text/plain', 'X-File-Name': 'safe.py'},
                           content=b'def add(a, b):\n    return a + b\n')
    assert uploaded.status_code == 200, uploaded.text
    assert client.post(f'/api/projects/{project}/scan', headers=headers).json()['finding_count'] == 0
    other = client.post('/api/projects', headers=headers, json={'name': 'unknown'}).json()['id']
    uploaded = client.post(f'/api/projects/{other}/upload-file', headers={**headers, 'Content-Type': 'text/plain', 'X-File-Name': 'notes.txt'}, content=b'hello')
    assert uploaded.json()['status'] == 'UNSUPPORTED'
    scan = client.post(f'/api/projects/{other}/scan', headers=headers).json()
    assert scan['status'] == 'UNSUPPORTED'
    assert scan['finding_count'] == 0
    malicious = client.post('/api/projects', headers=headers, json={'name': 'malicious'}).json()['id']
    assert client.post(f'/api/projects/{malicious}/upload-file', headers={**headers, 'Content-Type': 'text/plain', 'X-File-Name': '../escape.py'}, content=b'pass').status_code == 422


def test_ai_review_requires_exact_consent_and_redacts_sensitive_lines(product, monkeypatch):
    from backend.ai_provider import ReviewOutput, ReviewItem
    import backend.routes.scans as routes
    seen = []
    class FakeProvider:
        model = 'mock-model'
        def review(self, context):
            seen.append(context)
            return ReviewOutput(items=[ReviewItem(finding_id=context['findings'][0]['id'], assessment='POTENTIAL',
                                                  explanation='A reviewer should inspect this pattern.', recommendation='Use parameters.')]), self.model
    monkeypatch.setattr(routes, 'GeminiReviewProvider', FakeProvider)
    client, headers = register(product, 'ai@example.test')
    project = client.post('/api/projects', headers=headers, json={'name': 'review'}).json()['id']
    source = b'api_key = "secret-example-value"\nconn.execute(f"SELECT * FROM users WHERE id={user_id}")\n'
    client.post(f'/api/projects/{project}/upload-file', headers={**headers, 'Content-Type': 'text/plain', 'X-File-Name': 'main.py'}, content=source)
    scan = client.post(f'/api/projects/{project}/scan', headers=headers).json()
    assert scan['finding_count'] == 2
    rejected = client.post(f'/api/projects/{project}/ai-review', headers=headers,
                           json={'scan_id': scan['id'], 'approved_files': ['wrong.py'], 'consent': True})
    assert rejected.status_code == 422
    assert not seen
    accepted = client.post(f'/api/projects/{project}/ai-review', headers=headers,
                           json={'scan_id': scan['id'], 'approved_files': ['main.py'], 'consent': True})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()['items'][0]['assessment'] == 'POTENTIAL'
    assert len(seen) == 1
    assert 'secret-example-value' not in str(seen)
    history = client.get(f'/api/scan-findings/{accepted.json()["items"][0]["finding_id"]}/reviews')
    assert history.status_code == 200 and len(history.json()) == 1
    with product.state.workflow.db.read() as db:
        assert db.execute('SELECT count(*) FROM source_share_consents').fetchone()[0] == 1
        assert db.execute('SELECT purpose FROM source_share_consents').fetchone()[0] == 'AI_REVIEW'


def test_bola_demo_static_finding_and_javascript_pattern(product):
    from pathlib import Path
    client, headers = register(product, 'patterns@example.test')
    project = client.post('/api/projects', headers=headers, json={'name': 'BOLA'}).json()['id']
    root = Path(__file__).resolve().parents[2]
    lab = root / 'verification' / 'lab' / 'app'
    payload = _zip({'requirements.txt': 'fastapi==0.1', 'app/__init__.py': '',
                    'app/access.py': (lab / 'access.py').read_bytes(),
                    'app/sample_data.py': (lab / 'sample_data.py').read_bytes()})
    assert client.post(f'/api/projects/{project}/upload', headers={**headers, 'Content-Type': 'application/zip'}, content=payload).json()['status'] == 'SUPPORTED_BOLA_CONTRACT'
    scan = client.post(f'/api/projects/{project}/scan', headers=headers)
    assert scan.status_code == 201
    assert 'BOLA_IDOR' in {f['category'] for f in client.get(f'/api/projects/{project}/findings').json()}
    js = client.post('/api/projects', headers=headers, json={'name': 'React'}).json()['id']
    payload = _zip({'package.json': '{"dependencies":{"react":"18.3.1"}}',
                    'src/App.jsx': 'export default function App({html}) { return <div dangerouslySetInnerHTML={{__html: html}}/>; }'})
    assert client.post(f'/api/projects/{js}/upload', headers={**headers, 'Content-Type': 'application/zip'}, content=payload).json()['framework'] == 'React'
    scan = client.post(f'/api/projects/{js}/scan', headers=headers).json()
    assert scan['finding_count'] >= 1
    assert 'XSS' in {f['category'] for f in client.get(f'/api/projects/{js}/findings').json()}
