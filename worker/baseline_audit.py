"""Read-only VRS baseline audit; no third-party dependencies or network access."""
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath


def blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def audit(root, manifest):
    root = Path(root).resolve()
    if manifest.get('schema') != 1 or not isinstance(manifest.get('files'), dict):
        raise ValueError('unsupported baseline manifest')
    rows = []
    for name, expected in sorted(manifest['files'].items()):
        rel = PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name or not name:
            raise ValueError('unsafe manifest path')
        if not isinstance(expected, str) or len(expected) != 40 or any(c not in '0123456789abcdef' for c in expected):
            raise ValueError('invalid Git blob SHA')
        path = root.joinpath(*rel.parts).resolve()
        if not path.is_relative_to(root):
            raise ValueError('path escapes worker root')
        row = {'path': name, 'expected_blob': expected}
        if not path.is_file():
            row['status'] = 'MISSING'
        else:
            data = path.read_bytes()
            row['actual_blob'] = blob_sha(data)
            row['status'] = 'MATCH' if row['actual_blob'] == expected else 'CHANGED'
            if path.suffix in ('.py', '.pyw'):
                try:
                    tree = ast.parse(data, filename=name)
                except (SyntaxError, ValueError) as exc:
                    row['syntax_error'] = str(exc)
                else:
                    row['imports'] = sorted({alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names} | {'.' * node.level + (node.module or '') for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)})
                    row['test_functions'] = sorted(node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_'))
        rows.append(row)
    unexpected = sorted(str(p.relative_to(root).as_posix()) for p in root.rglob('*') if p.is_file() and p.suffix in ('.py', '.pyw') and not any(part.startswith('.') or part == '__pycache__' for part in p.relative_to(root).parts) and p.relative_to(root).as_posix() not in manifest['files'])
    ok = all(row['status'] == 'MATCH' and 'syntax_error' not in row for row in rows)
    return {'schema': 1, 'baseline_commit': manifest.get('baseline_commit'), 'status': 'MATCH' if ok else 'NOT_MATCH', 'files': rows, 'additional_python_files': unexpected, 'test_functions': sum(len(row.get('test_functions', [])) for row in rows), 'note': 'Source identity only; not test execution or scientific acceptance.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).resolve().with_name('baseline_v081.json'))
    args = parser.parse_args()
    report = audit(args.root, json.loads(args.manifest.read_text(encoding='utf-8')))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['status'] == 'MATCH' else 1


if __name__ == '__main__':
    raise SystemExit(main())
