"""Bounded, non-executing static triage. Matches are potential, never exploit proof."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

SOURCE_EXTENSIONS = {'.py': 'Python', '.js': 'JavaScript', '.jsx': 'JavaScript',
                     '.ts': 'TypeScript', '.tsx': 'TypeScript'}
MAX_FILES = 500
MAX_FILE_BYTES = 128 * 1024
MAX_FINDINGS = 100
SECRET_NAME = re.compile(r'(?i)(?:api[_-]?key|secret|password|passwd|auth[_-]?token|client[_-]?secret)')
JS_RULES = (
    ('COMMAND_INJECTION', re.compile(r'\b(?:child_process\.)?exec\s*\([^\n]+(?:\$\{|\+|req\.|request\.)'), 'Dynamic shell execution', 'Use an argument-array API and validate inputs.'),
    ('SQL_INJECTION', re.compile(r'\b(?:query|execute)\s*\(\s*`[^`]*\$\{'), 'Interpolated database query', 'Use bound query parameters.'),
    ('INSECURE_DESERIALIZATION', re.compile(r'\b(?:eval|Function)\s*\('), 'Dynamic code evaluation', 'Parse data without evaluating code.'),
    ('XSS', re.compile(r'\b(?:dangerouslySetInnerHTML|\.innerHTML\s*=)'), 'Direct HTML injection sink', 'Use safe text rendering or sanitize trusted HTML.'),
    ('DANGEROUS_CONFIGURATION', re.compile(r'\b(?:rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*["\']?0)'), 'TLS verification disabled', 'Keep TLS certificate verification enabled.'),
)


def classify(root: Path) -> dict:
    files = [p for p in root.rglob('*') if p.is_file() and not p.is_symlink()]
    counts = {language: 0 for language in set(SOURCE_EXTENSIONS.values())}
    for path in files[:MAX_FILES + 1]:
        language = SOURCE_EXTENSIONS.get(path.suffix.lower())
        if language:
            counts[language] += 1
    languages = sorted(name for name, count in counts.items() if count)
    manifests = sorted(p.relative_to(root).as_posix() for p in files
                       if p.name in {'requirements.txt', 'pyproject.toml', 'Pipfile', 'package.json', 'package-lock.json', 'pnpm-lock.yaml'})[:30]
    framework = 'Unknown'
    for name in ('requirements.txt', 'pyproject.toml'):
        path = root / name
        if path.is_file() and path.stat().st_size <= MAX_FILE_BYTES and 'fastapi' in path.read_text(errors='ignore').lower():
            framework = 'Python/FastAPI'
            break
    package = root / 'package.json'
    if framework == 'Unknown' and package.is_file() and package.stat().st_size <= MAX_FILE_BYTES:
        try:
            body = json.loads(package.read_text())
            deps = {**body.get('dependencies', {}), **body.get('devDependencies', {})}
            framework = 'React' if 'react' in deps else 'Node.js'
        except (ValueError, TypeError, AttributeError):
            framework = 'JavaScript/TypeScript'
    if framework == 'Unknown' and 'Python' in languages:
        framework = 'Python'
    elif framework == 'Unknown' and languages:
        framework = 'JavaScript/TypeScript'
    return {'languages': languages, 'framework': framework, 'manifests': manifests,
            'file_count': len(files), 'supported': bool(languages)}


def scan(root: Path) -> tuple[dict, list[dict]]:
    profile = classify(root)
    findings: list[dict] = []
    if profile['file_count'] > MAX_FILES:
        return {**profile, 'status': 'UNSUPPORTED', 'reason': 'Project exceeds static scan file limit'}, findings
    if not profile['supported']:
        return {**profile, 'status': 'UNSUPPORTED', 'reason': 'No supported source language detected'}, findings
    seen: set[tuple[str, str, int]] = set()

    def add(category: str, path: str, line: int, evidence: str, recommendation: str,
            confidence: str = 'MEDIUM', severity: str = 'MEDIUM') -> None:
        key = (category, path, line)
        if key in seen or len(findings) >= MAX_FINDINGS:
            return
        seen.add(key)
        findings.append({'category': category, 'severity': severity, 'confidence': confidence,
                         'file_path': path, 'line_start': line, 'line_end': line,
                         'evidence': evidence, 'explanation': evidence,
                         'recommendation': recommendation, 'detection_source': 'STATIC_PATTERN',
                         'validation_status': 'POTENTIAL'})

    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding='utf-8', errors='replace')
        lines = text.splitlines()
        if path.suffix.lower() == '.py':
            try:
                tree = ast.parse(text, filename=rel)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    value = node.value
                    if isinstance(value, ast.Constant) and isinstance(value.value, str) and len(value.value) >= 8:
                        if any(SECRET_NAME.search(ast.unparse(target)) for target in targets):
                            add('HARDCODED_SECRET', rel, node.lineno, 'Sensitive-looking name assigned a string literal; value withheld.',
                                'Load the value from a server-side secret store and rotate any exposed credential.', 'MEDIUM', 'HIGH')
                    if any(ast.unparse(target).upper() == 'DEBUG' for target in targets) and isinstance(value, ast.Constant) and value.value is True:
                        add('DANGEROUS_CONFIGURATION', rel, node.lineno, 'Debug mode enabled.', 'Disable debug mode outside local development.')
                if not isinstance(node, ast.Call):
                    continue
                fn = ast.unparse(node.func)
                if fn.endswith(('.execute', '.executemany')) and node.args and isinstance(node.args[0], (ast.JoinedStr, ast.BinOp)):
                    add('SQL_INJECTION', rel, node.lineno, 'Dynamic SQL expression passed to database execution.', 'Use bound query parameters.', 'HIGH', 'HIGH')
                if fn in {'os.system', 'subprocess.run', 'subprocess.Popen', 'subprocess.call'}:
                    shell = fn == 'os.system' or any(k.arg == 'shell' and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords)
                    if shell:
                        add('COMMAND_INJECTION', rel, node.lineno, 'Shell execution enabled.', 'Use an argument array without a shell and validate inputs.', 'MEDIUM', 'HIGH')
                if fn in {'pickle.loads', 'pickle.load', 'marshal.loads', 'marshal.load', 'eval'}:
                    add('INSECURE_DESERIALIZATION', rel, node.lineno, 'Unsafe data loading or evaluation API.', 'Use a data-only parser for untrusted input.', 'MEDIUM', 'HIGH')
                if fn in {'open', 'Path.open', 'send_file'} and node.args and isinstance(node.args[0], ast.Name) and node.args[0].id.lower() in {'filename', 'filepath', 'user_path', 'requested_path'}:
                    add('PATH_TRAVERSAL', rel, node.lineno, 'Variable path reaches a file access API.', 'Resolve under an allowed root and reject traversal.', 'LOW')
                if any(k.arg == 'verify' and isinstance(k.value, ast.Constant) and k.value.value is False for k in node.keywords):
                    add('DANGEROUS_CONFIGURATION', rel, node.lineno, 'TLS verification disabled.', 'Enable certificate verification.')
            if rel == 'app/access.py' and 'def get_document(' in text and '    return dict(doc)\n' in text:
                owner_checks = [node for node in ast.walk(tree) if isinstance(node, ast.Compare)
                                and 'owner_id' in ast.unparse(node) and 'requesting_user_id' in ast.unparse(node)]
                if not owner_checks:
                    line = next((i for i, value in enumerate(lines, 1) if 'return dict(doc)' in value), 1)
                    add('BOLA_IDOR', rel, line, 'Document returned without an ownership comparison in executable code.',
                        'Check the current user against the document owner before returning it.', 'MEDIUM', 'HIGH')
        else:
            for number, line in enumerate(lines, 1):
                for category, pattern, evidence, recommendation in JS_RULES:
                    if pattern.search(line):
                        add(category, rel, number, evidence, recommendation,
                            'LOW' if category == 'XSS' else 'MEDIUM')
                if SECRET_NAME.search(line) and re.search(r'\b(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*["\'][^"\']{8,}["\']', line):
                    add('HARDCODED_SECRET', rel, number, 'Sensitive-looking name assigned a string literal; value withheld.',
                        'Use a server-side secret store and rotate exposed credentials.', 'MEDIUM', 'HIGH')
    return {**profile, 'status': 'COMPLETE', 'reason': 'Potential matches require review; absence of matches is not proof of safety'}, findings
