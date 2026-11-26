"""VRS 0.9.2: versioned, fixed-scope local manifests and aggregate evidence.
No scheduler, training, experiment creation, network, or GitHub writes.
"""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from vrs_core import require, sha

VERSION = '0.9.2'
SCHEMA = 1
MODULE = 'voynich-manuscript'
PROTOCOL = 'fixed-manuscript-v1'
STAGES = ('script_regions', 'glyph_segmentation', 'glyph_classification',
          'exception_review', 'transcription_alignment')
ROLES = ('manuscript', 'groups', 'references', 'model', 'recognition_policy')
STATES = ('PENDING', 'COMPLETED', 'BLOCKED', 'FAILED')
REASONS = ('NONE', 'NOT_STARTED', 'DEPENDENCY', 'REVIEW_PENDING',
           'UNSUPPORTED', 'INVALID_INPUT', 'PROCESSING_ERROR')
MAX_JSON = 1024 * 1024
HEX = re.compile(r'[0-9a-f]{64}')
GIT = re.compile(r'[0-9a-f]{40}')
NONCE = re.compile(r'[0-9a-f]{32}')
REPO = re.compile(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}')


def fields(obj, names):
    require(type(obj) is dict and set(obj) == set(names), 'Unexpected or missing fields')


def digest_ok(value, pattern=HEX):
    require(type(value) is str and pattern.fullmatch(value) is not None, 'Invalid digest')


def number(value, max_value=2**53-1):
    require(type(value) is int and 0 <= value <= max_value, 'Invalid count or number')


def version(obj):
    require(type(obj.get('schema')) is int and obj['schema'] == SCHEMA, 'Unsupported schema')
    require(obj['module'] == MODULE and obj['protocol'] == PROTOCOL, 'Outside fixed scope')


def canonical(obj):
    raw = json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
    require(len(raw) <= MAX_JSON, 'Contract exceeds size limit')
    return raw


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def reject(value):
        raise ValueError('Invalid JSON constant')
    with Path(path).open('rb') as f:
        raw = f.read(MAX_JSON + 1)
    require(len(raw) <= MAX_JSON, 'Contract exceeds size limit')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=reject)


def artifact(root, obj):
    fields(obj, ('path', 'sha256'))
    digest_ok(obj['sha256'])
    name = obj['path']
    require(type(name) is str and 0 < len(name) <= 512, 'Invalid local path')
    require(not any(c in name for c in ('\\', ':', '\x00')) and not name.startswith('/'), 'Unsafe local path')
    require(all(p not in ('', '.', '..') for p in name.split('/')), 'Unsafe local path')
    root = Path(root).resolve(strict=True)
    path = root
    for part in PurePosixPath(name).parts:
        path = path / part
        require(not path.is_symlink(), 'Symlink not allowed')
    resolved = path.resolve(strict=True)
    require(resolved.is_relative_to(root) and resolved.is_file(), 'Artifact outside workspace or not a file')
    require(sha(resolved) == obj['sha256'], 'Artifact hash mismatch')
    return resolved


def manifest(root, obj):
    fields(obj, ('schema', 'module', 'protocol', 'inputs', 'transcriptions', 'backend', 'seed', 'run_nonce'))
    version(obj)
    require(obj['backend'] in ('auto', 'cpu', 'cuda'), 'Unsupported backend')
    number(obj['seed'], 2**32-1)
    digest_ok(obj['run_nonce'], NONCE)
    fields(obj['inputs'], ROLES)
    require(type(obj['transcriptions']) is list and 1 <= len(obj['transcriptions']) <= 12, 'Invalid transcription inventory')
    refs = [obj['inputs'][role] for role in ROLES] + obj['transcriptions']
    paths = [artifact(root, ref) for ref in refs]
    require(len(set(paths)) == len(paths), 'Aliased input paths')
    return digest(obj)


def receipt(root, obj, run_id, stage):
    fields(obj, ('schema', 'run_id', 'stage', 'state', 'reason', 'artifact', 'counts'))
    require(type(obj['schema']) is int and obj['schema'] == SCHEMA, 'Unsupported schema')
    digest_ok(run_id)
    require(obj['run_id'] == run_id and obj['stage'] == stage and stage in STAGES, 'Receipt binding mismatch')
    state, reason = obj['state'], obj['reason']
    require(state in STATES and reason in REASONS, 'Invalid stage status')
    allowed = {'PENDING': ('NOT_STARTED',), 'COMPLETED': ('NONE',),
               'BLOCKED': ('DEPENDENCY', 'REVIEW_PENDING', 'UNSUPPORTED', 'INVALID_INPUT'),
               'FAILED': ('PROCESSING_ERROR', 'INVALID_INPUT')}
    require(reason in allowed[state], 'Inconsistent stage reason')
    require(reason != 'REVIEW_PENDING' or stage == 'exception_review', 'Invalid review state')
    if state == 'COMPLETED' or (stage == 'exception_review' and reason == 'REVIEW_PENDING'):
        artifact(root, obj['artifact'])
    else:
        require(obj['artifact'] is None, 'Unexpected stage artifact')
    if stage == 'glyph_classification' and state == 'COMPLETED':
        fields(obj['counts'], ('total', 'accepted', 'abstained', 'failed'))
        for value in obj['counts'].values():
            number(value)
        c = obj['counts']
        require(c['total'] == c['accepted'] + c['abstained'] + c['failed'], 'Classification denominator mismatch')
    elif stage == 'exception_review' and (state == 'COMPLETED' or reason == 'REVIEW_PENDING'):
        fields(obj['counts'], ('resolved', 'pending', 'deferred'))
        for value in obj['counts'].values():
            number(value)
        require((state == 'COMPLETED') == (obj['counts']['pending'] + obj['counts']['deferred'] == 0), 'Review completion mismatch')
    else:
        require(obj['counts'] is None, 'Unexpected stage counts')
    return digest(obj)


def evidence(root, local_manifest, receipts, repository, research_commit, allowed_repositories,
             actual_backend, worker_sha256):
    """Build a deterministic aggregate report; no local paths or private payloads exported."""
    run_id = manifest(root, local_manifest)
    require(type(repository) is str and REPO.fullmatch(repository) is not None, 'Invalid repository')
    require(type(allowed_repositories) in (tuple, list, set, frozenset) and repository in allowed_repositories, 'Repository not locally authorized')
    digest_ok(research_commit, GIT)
    digest_ok(worker_sha256)
    require(actual_backend in ('cpu', 'cuda'), 'Actual backend required')
    require(local_manifest['backend'] in ('auto', actual_backend), 'Backend mismatch')
    fields(receipts, STAGES)
    previous = True
    used_paths = {artifact(root, x) for x in [*local_manifest['inputs'].values(), *local_manifest['transcriptions']]}
    rows = {}
    classification = review = None
    for stage in STAGES:
        item = receipts[stage]
        receipt_hash = receipt(root, item, run_id, stage)
        state = item['state']
        if item['artifact'] is not None:
            path = artifact(root, item['artifact'])
            require(path not in used_paths, 'Stage artifact aliases another artifact')
            used_paths.add(path)
        require(previous or state in ('PENDING', 'BLOCKED'), 'Stage bypasses dependency')
        require(previous or item['reason'] in ('NOT_STARTED', 'DEPENDENCY'), 'Invalid dependent stage reason')
        previous = previous and state == 'COMPLETED'
        rows[stage] = {'state': state, 'reason': item['reason'], 'receipt_sha256': receipt_hash,
                       'artifact_sha256': item['artifact']['sha256'] if item['artifact'] else None}
        if stage == 'glyph_classification':
            classification = item['counts']
        elif stage == 'exception_review':
            review = item['counts']
    if review is not None:
        require(classification is not None and sum(review.values()) == classification['abstained'], 'Review denominator mismatch')
    elif classification is not None:
        review = {'resolved': 0, 'pending': classification['abstained'], 'deferred': 0}
    state = 'COMPLETED' if previous else ('FAILED' if any(r['state'] == 'FAILED' for r in rows.values()) else 'PARTIAL')
    report = {'schema': SCHEMA, 'module': MODULE, 'protocol': PROTOCOL, 'app_version': VERSION,
              'run_id': run_id, 'repository': repository, 'research_commit': research_commit,
              'worker_sha256': worker_sha256, 'backend': actual_backend, 'seed': local_manifest['seed'],
              'source_sha256': {role: local_manifest['inputs'][role]['sha256'] for role in ROLES},
              'transcription_sha256': [x['sha256'] for x in local_manifest['transcriptions']],
              'stages': rows, 'classification': classification, 'review': review,
              'technical_status': state, 'scientific_status': 'UNADJUDICATED'}
    canonical(report)
    return report


def verify_evidence(report, *args, **kwargs):
    """Rebuild from local verified inputs and reject any changed/extra field."""
    expected = evidence(*args, **kwargs)
    require(canonical(report) == canonical(expected), 'Evidence mismatch')
    return digest(expected)
