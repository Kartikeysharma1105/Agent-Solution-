"""Constrained advisory patch proposals for Python static findings.

No uploaded code is executed or modified. Syntax and static-pattern checks cannot prove
runtime behavior, so they never return VERIFIED.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
from uuid import uuid4

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..ai_provider import GeminiReviewProvider, ProviderUnavailable
from ..analysis import SECRET_NAME, scan
from ..auth import current_user
from ..database import utc_now
from ..models import WorkflowError
from ..security_activity import record
from .projects import SENSITIVE, _project, _source_dir

router = APIRouter(tags=['patches'])


class PatchRequest(BaseModel):
    consent: bool
    approved_file: str


class DecisionRequest(BaseModel):
    patch_hash: str
    decision: str


def _finding(request: Request, finding_id: str) -> dict:
    with request.app.state.workflow.db.read() as db:
        row = db.execute('''SELECT f.* FROM scan_findings f JOIN projects p ON p.id=f.project_id
                            WHERE f.id=? AND p.owner_id=?''', (finding_id, current_user())).fetchone()
    if row is None:
        raise WorkflowError('finding not found', 404, 'FINDING_NOT_FOUND')
    return dict(row)


def _proposal(request: Request, proposal_id: str) -> dict:
    with request.app.state.workflow.db.read() as db:
        row = db.execute('''SELECT q.*, f.file_path, f.category, f.scan_id FROM scan_patch_proposals q
                            JOIN scan_findings f ON f.id=q.finding_id JOIN projects p ON p.id=q.project_id
                            WHERE q.id=? AND p.owner_id=?''', (proposal_id, current_user())).fetchone()
    if row is None:
        raise WorkflowError('patch not found', 404, 'PATCH_NOT_FOUND')
    return dict(row)


def _file(request: Request, finding: dict) -> Path:
    _project(request, finding['project_id'])
    rel = PurePosixPath(finding['file_path'])
    if rel.is_absolute() or '..' in rel.parts or rel.suffix != '.py' or SENSITIVE.search(finding['file_path']):
        raise WorkflowError('only nonsensitive Python findings support advisory patch drafts', 422, 'PATCH_UNSUPPORTED')
    root = _source_dir(request, finding['project_id']).resolve()
    path = (root / finding['file_path']).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink() or path.stat().st_size > 65536:
        raise WorkflowError('source file is unavailable or too large', 409, 'SOURCE_UNAVAILABLE')
    return path


@router.post('/api/scan-findings/{finding_id}/patch', status_code=201)
def create_patch(finding_id: str, payload: PatchRequest, request: Request):
    finding = _finding(request, finding_id)
    if finding['category'] in {'HARDCODED_SECRET', 'BOLA_IDOR'}:
        raise WorkflowError('use the protected BOLA workflow or manual secret rotation', 422, 'PATCH_UNSUPPORTED')
    if payload.consent is not True or payload.approved_file != finding['file_path']:
        raise WorkflowError('explicit approval of the exact source file is required', 422, 'CONSENT_REQUIRED')
    path = _file(request, finding)
    original = path.read_bytes().decode('utf-8')
    lines = original.splitlines(keepends=True)
    index = finding['line_start'] - 1
    if index < 0 or index >= len(lines):
        raise WorkflowError('finding location is stale', 409, 'SOURCE_CHANGED')
    context_lines = lines[max(0, index - 8):min(len(lines), index + 9)]
    if any(SECRET_NAME.search(line) for line in context_lines):
        raise WorkflowError('source context contains credential-like text', 422, 'SENSITIVE_SOURCE')
    snippet = ''.join(context_lines)
    if len(snippet.encode()) > 4096:
        raise WorkflowError('source context exceeds AI limit', 422, 'CONTEXT_TOO_LARGE')
    try:
        provider = GeminiReviewProvider()
    except ProviderUnavailable as exc:
        raise WorkflowError(str(exc), 503, 'AI_UNAVAILABLE') from None
    consent_id = 'consent-' + uuid4().hex
    with request.app.state.workflow.db.transaction() as db:
        db.execute('INSERT INTO source_share_consents (id, project_id, scan_id, user_id, files_json, model, created_at, purpose) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                   (consent_id, finding['project_id'], finding['scan_id'], current_user(), json.dumps([finding['file_path']]), provider.model, utc_now(), 'PATCH_DRAFT'))
    try:
        result, model = provider.propose_line_patch({'finding_id': finding_id, 'category': finding['category'],
            'evidence': finding['evidence'], 'recommendation': finding['recommendation'],
            'path': finding['file_path'], 'line': finding['line_start'], 'source_context': snippet})
    except ProviderUnavailable as exc:
        raise WorkflowError(str(exc), 503, 'AI_UNAVAILABLE') from None
    replacement = result.replacement_line
    if (not replacement or '\n' in replacement or '\r' in replacement or len(replacement) > 500 or
            replacement == lines[index].rstrip('\r\n') or SECRET_NAME.search(replacement)):
        raise WorkflowError('AI patch output failed the one-line policy', 422, 'PATCH_POLICY_REJECTED')
    revised = lines.copy()
    ending = '\r\n' if lines[index].endswith('\r\n') else ('\n' if lines[index].endswith('\n') else '')
    revised[index] = replacement + ending
    patched = ''.join(revised)
    try:
        ast.parse(patched)
    except SyntaxError:
        raise WorkflowError('AI patch output fails Python syntax', 422, 'PATCH_POLICY_REJECTED') from None
    diff = ''.join(difflib.unified_diff(lines, revised, fromfile='a/' + finding['file_path'],
                                        tofile='b/' + finding['file_path'], n=3))
    if not diff or len(diff) > 8192:
        raise WorkflowError('AI patch exceeds diff policy', 422, 'PATCH_POLICY_REJECTED')
    patch_hash = 'sha256:' + hashlib.sha256(diff.encode()).hexdigest()
    source_hash = 'sha256:' + hashlib.sha256(original.encode()).hexdigest()
    proposal_id = 'sp-' + uuid4().hex
    with request.app.state.workflow.db.transaction() as db:
        db.execute('INSERT INTO scan_patch_proposals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   (proposal_id, finding_id, finding['project_id'], source_hash, patch_hash,
                    diff, replacement, result.root_cause[:2000], result.explanation[:2000], model, utc_now()))
        record(db, finding['project_id'], 'PATCH_PROPOSED', proposal_id, 'PENDING')
    request.app.state.workflow._telemetry('patch.generated', project_id=finding['project_id'], success=True)
    request.app.state.workflow._telemetry('patch.validation.completed', project_id=finding['project_id'], success=True)
    return {'id': proposal_id, 'finding_id': finding_id, 'project_id': finding['project_id'],
            'file_path': finding['file_path'], 'diff': diff, 'patch_hash': patch_hash,
            'root_cause': result.root_cause[:2000], 'explanation': result.explanation[:2000],
            'approval_status': 'PENDING', 'verification_status': 'NOT_RUN',
            'notice': 'Advisory proposal only. The source file has not been modified.'}


@router.get('/api/scan-findings/{finding_id}/patches')
def list_patches(finding_id: str, request: Request):
    _finding(request, finding_id)
    with request.app.state.workflow.db.read() as db:
        rows = db.execute('''SELECT q.id, q.patch_hash, q.created_at,
                             COALESCE(a.decision, 'PENDING') AS approval_status,
                             COALESCE((SELECT c.status FROM scan_patch_checks c WHERE c.proposal_id=q.id
                                       ORDER BY c.created_at DESC LIMIT 1), 'NOT_RUN') AS verification_status
                             FROM scan_patch_proposals q LEFT JOIN scan_patch_approvals a ON a.proposal_id=q.id
                             WHERE q.finding_id=? ORDER BY q.created_at DESC''', (finding_id,)).fetchall()
    return [dict(row) for row in rows]


@router.get('/api/scan-patches')
def all_patches(request: Request):
    with request.app.state.workflow.db.read() as db:
        rows = db.execute('''SELECT q.id, q.finding_id, q.project_id, q.patch_hash, q.created_at,
                             f.file_path, f.category, p.name AS project_name,
                             COALESCE(a.decision, 'PENDING') AS approval_status,
                             COALESCE((SELECT c.status FROM scan_patch_checks c WHERE c.proposal_id=q.id
                                       ORDER BY c.created_at DESC LIMIT 1), 'NOT_RUN') AS verification_status
                             FROM scan_patch_proposals q JOIN scan_findings f ON f.id=q.finding_id
                             JOIN projects p ON p.id=q.project_id
                             LEFT JOIN scan_patch_approvals a ON a.proposal_id=q.id
                             WHERE p.owner_id=? ORDER BY q.created_at DESC LIMIT 500''', (current_user(),)).fetchall()
    return [dict(row) for row in rows]


@router.get('/api/scan-patches/{proposal_id}')
def get_patch(proposal_id: str, request: Request):
    proposal = _proposal(request, proposal_id)
    with request.app.state.workflow.db.read() as db:
        approval = db.execute('SELECT decision, patch_hash, created_at FROM scan_patch_approvals WHERE proposal_id=?', (proposal_id,)).fetchone()
        check = db.execute('SELECT status, result_json, created_at FROM scan_patch_checks WHERE proposal_id=? ORDER BY created_at DESC LIMIT 1', (proposal_id,)).fetchone()
    proposal['approval_status'] = approval['decision'] if approval else 'PENDING'
    proposal['verification_status'] = check['status'] if check else 'NOT_RUN'
    proposal['verification'] = json.loads(check['result_json']) if check else None
    return proposal


@router.post('/api/scan-patches/{proposal_id}/approval')
def approve_patch(proposal_id: str, payload: DecisionRequest, request: Request):
    proposal = _proposal(request, proposal_id)
    if payload.patch_hash != proposal['patch_hash']:
        raise WorkflowError('approved hash does not match the proposal', 409, 'PATCH_HASH_MISMATCH')
    if payload.decision not in {'APPROVE', 'REJECT'}:
        raise WorkflowError('decision must be APPROVE or REJECT', 422, 'INVALID_DECISION')
    with request.app.state.workflow.db.transaction() as db:
        if db.execute('SELECT 1 FROM scan_patch_approvals WHERE proposal_id=?', (proposal_id,)).fetchone():
            raise WorkflowError('proposal already has a decision', 409, 'DECISION_EXISTS')
        db.execute('INSERT INTO scan_patch_approvals VALUES (?, ?, ?, ?, ?, ?)',
                   ('spa-' + uuid4().hex, proposal_id, current_user(), payload.patch_hash, payload.decision, utc_now()))
        record(db, proposal['project_id'], 'PATCH_APPROVED' if payload.decision == 'APPROVE' else 'PATCH_REJECTED', proposal_id, payload.decision)
    request.app.state.workflow._telemetry('approval.recorded', project_id=proposal['project_id'], success=payload.decision == 'APPROVE')
    return {'proposal_id': proposal_id, 'patch_hash': payload.patch_hash, 'decision': payload.decision}


@router.post('/api/scan-patches/{proposal_id}/verify')
def check_patch(proposal_id: str, request: Request):
    proposal = _proposal(request, proposal_id)
    with request.app.state.workflow.db.read() as db:
        approval = db.execute('SELECT decision, patch_hash FROM scan_patch_approvals WHERE proposal_id=?', (proposal_id,)).fetchone()
    if approval is None or approval['decision'] != 'APPROVE' or approval['patch_hash'] != proposal['patch_hash']:
        raise WorkflowError('exact patch approval is required', 409, 'APPROVAL_REQUIRED')
    finding = _finding(request, proposal['finding_id'])
    path = _file(request, finding)
    original = path.read_bytes().decode('utf-8')
    if 'sha256:' + hashlib.sha256(original.encode()).hexdigest() != proposal['source_sha256']:
        raise WorkflowError('source changed since proposal generation', 409, 'SOURCE_CHANGED')
    lines = original.splitlines(keepends=True)
    index = finding['line_start'] - 1
    if index < 0 or index >= len(lines):
        raise WorkflowError('finding location is stale', 409, 'SOURCE_CHANGED')
    original_lines = lines.copy()
    ending = '\r\n' if lines[index].endswith('\r\n') else ('\n' if lines[index].endswith('\n') else '')
    lines[index] = proposal['replacement_line'] + ending
    expected_diff = ''.join(difflib.unified_diff(original_lines, lines, fromfile='a/' + finding['file_path'], tofile='b/' + finding['file_path'], n=3))
    if expected_diff != proposal['diff'] or 'sha256:' + hashlib.sha256(expected_diff.encode()).hexdigest() != proposal['patch_hash']:
        raise WorkflowError('stored proposal no longer matches the approved patch', 409, 'PATCH_HASH_MISMATCH')
    patched = ''.join(lines)
    checks = {'python_syntax': False, 'selected_static_pattern_removed': False,
              'runtime_tests_executed': False, 'source_modified': False}
    try:
        ast.parse(patched)
        checks['python_syntax'] = True
        with tempfile.TemporaryDirectory(prefix='sentinel-check-') as temporary:
            root = Path(temporary)
            target = root / finding['file_path']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(patched, encoding='utf-8')
            _, matches = scan(root)
            checks['selected_static_pattern_removed'] = not any(item['category'] == finding['category'] for item in matches)
        status = 'INCONCLUSIVE' if checks['selected_static_pattern_removed'] else 'FAILED'
    except (SyntaxError, OSError):
        status = 'FAILED'
    result = {'status': status, 'checks': checks,
              'reason': 'Syntax and pattern checks cannot prove runtime behavior.' if status == 'INCONCLUSIVE' else 'The proposed edit failed an applicable local check.'}
    with request.app.state.workflow.db.transaction() as db:
        db.execute('INSERT INTO scan_patch_checks VALUES (?, ?, ?, ?, ?)',
                   ('spc-' + uuid4().hex, proposal_id, status, json.dumps(result), utc_now()))
        record(db, proposal['project_id'], 'PATCH_CHECKED', proposal_id, status)
    return {'proposal_id': proposal_id, **result}
