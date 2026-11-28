"""Explicit existing start directories for portable file dialogs; no registry writes."""
from pathlib import Path
import os


def initial_directory(workspace, current=None):
    """Prefer the user's existing selection within the workspace, else its root.

    Dialog navigation itself remains unrestricted. Import/export authorization
    is still enforced by the respective caller. No directories are created here.
    """
    root = Path(workspace).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Dialog workspace is not a directory')
    if current:
        try:
            p = Path(current)
            if not p.is_absolute():
                p = root / p
            p = p.resolve(strict=False)
            if not p.is_dir():
                p = p.parent
            if p.is_relative_to(root) and p.is_dir():
                return str(p)
        except (OSError, ValueError, RuntimeError):
            pass
    return str(root)


def portable_workspace(fallback):
    """Use launcher-provided application root; reject missing roots gracefully."""
    raw = os.environ.get('VRS_PORTABLE_LOG_ROOT')
    if raw:
        try:
            p = Path(raw).resolve(strict=True)
            if p.is_dir():
                return p
        except (OSError, ValueError, RuntimeError):
            pass
    return Path(fallback).resolve(strict=True)


def choose(dialog, *, parent, workspace, current=None, **options):
    """Pass a valid explicit initialdir, preserve native return/cancel semantics."""
    if 'initialdir' in options:
        raise ValueError('Use workspace/current for initial directory')
    return dialog(parent=parent, initialdir=initial_directory(workspace, current), **options)
