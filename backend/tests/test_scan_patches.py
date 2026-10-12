"""Advisory patch policy, exact-hash approval and independent non-executing checks."""
import backend.routes.scan_patches as routes
from backend.ai_provider import PatchLineOutput
from backend.tests.test_product import product, register


def _finding(client, headers):
    project = client.post('/api/projects', headers=headers, json={'name': 'patch sample'}).json()['id']
    source = b'def lookup(conn, user_id):\n    return conn.execute(f"SELECT * FROM users WHERE id={user_id}")\n'
    assert client.post(f'/api/projects/{project}/upload-file', headers={**headers, 'Content-Type': 'text/plain', 'X-File-Name': 'main.py'}, content=source).status_code == 200
    scan = client.post(f'/api/projects/{project}/scan', headers=headers).json()
    finding = client.get(f'/api/projects/{project}/findings').json()[0]
    return project, scan, finding, source


def test_patch_consent_hash_approval_and_inconclusive_check(product, monkeypatch):
    calls = []
    class FakeProvider:
        model = 'mock-model'
        def propose_line_patch(self, context):
            calls.append(context)
            return PatchLineOutput(replacement_line='    return conn.execute("SELECT * FROM users WHERE id=?", (user_id,))',
                                   root_cause='Dynamic SQL construction', explanation='Bind the identifier.'), self.model
    monkeypatch.setattr(routes, 'GeminiReviewProvider', FakeProvider)
    alice, ah = register(product, 'patch-alice@example.test')
    bob, bh = register(product, 'patch-bob@example.test')
    project, scan, finding, original = _finding(alice, ah)
    endpoint = f'/api/scan-findings/{finding["id"]}/patch'
    assert alice.post(endpoint, headers=ah, json={'consent': False, 'approved_file': 'main.py'}).status_code == 422
    assert bob.post(endpoint, headers=bh, json={'consent': True, 'approved_file': 'main.py'}).status_code == 404
    assert calls == []
    response = alice.post(endpoint, headers=ah, json={'consent': True, 'approved_file': 'main.py'})
    assert response.status_code == 201, response.text
    patch = response.json()
    assert patch['diff'].startswith('--- a/main.py\n+++ b/main.py')
    assert len(calls) == 1
    proposal_id = patch['id']
    assert bob.get(f'/api/scan-patches/{proposal_id}').status_code == 404
    assert alice.post(f'/api/scan-patches/{proposal_id}/verify', headers=ah).status_code == 409
    assert alice.post(f'/api/scan-patches/{proposal_id}/approval', headers=ah,
                      json={'patch_hash': 'sha256:' + '0'*64, 'decision': 'APPROVE'}).status_code == 409
    assert alice.post(f'/api/scan-patches/{proposal_id}/approval', headers=ah,
                      json={'patch_hash': patch['patch_hash'], 'decision': 'APPROVE'}).status_code == 200
    checked = alice.post(f'/api/scan-patches/{proposal_id}/verify', headers=ah)
    assert checked.status_code == 200, checked.text
    assert checked.json()['status'] == 'INCONCLUSIVE'
    assert checked.json()['checks']['python_syntax'] is True
    assert checked.json()['checks']['selected_static_pattern_removed'] is True
    assert checked.json()['checks']['source_modified'] is False
    assert (product.state.workflow.settings.project_root / project / 'source' / 'main.py').read_bytes() == original
    activity = alice.get('/api/security-activity').json()
    assert {'SCAN_COMPLETED','PATCH_PROPOSED','PATCH_APPROVED','PATCH_CHECKED'} <= {row['event_type'] for row in activity}
    assert bob.get('/api/security-activity').json() == []
    assert 'SELECT * FROM users' not in str(activity)
    with product.state.workflow.db.read() as db:
        assert db.execute('SELECT purpose FROM source_share_consents').fetchone()[0] == 'PATCH_DRAFT'


def test_incorrect_patch_fails_static_check(product, monkeypatch):
    class FakeProvider:
        model = 'mock-model'
        def propose_line_patch(self, context):
            return PatchLineOutput(replacement_line='    return conn.execute(f"SELECT * FROM users WHERE id={user_id}") # unchanged pattern',
                                   root_cause='test', explanation='test'), self.model
    monkeypatch.setattr(routes, 'GeminiReviewProvider', FakeProvider)
    client, headers = register(product, 'patch-fail@example.test')
    _, _, finding, _ = _finding(client, headers)
    patch = client.post(f'/api/scan-findings/{finding["id"]}/patch', headers=headers,
                        json={'consent': True, 'approved_file': 'main.py'}).json()
    assert patch['id'].startswith('sp-')
    client.post(f'/api/scan-patches/{patch["id"]}/approval', headers=headers,
                json={'patch_hash': patch['patch_hash'], 'decision': 'APPROVE'})
    result = client.post(f'/api/scan-patches/{patch["id"]}/verify', headers=headers)
    assert result.json()['status'] == 'FAILED'
