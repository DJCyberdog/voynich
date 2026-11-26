"""VRS-094 A follow-up: explicit platform and dependency preflight.
Read-only, offline; unknown capability is never treated as certified support.
"""
import argparse
import importlib.metadata as md
import json
import os
import sys
from pathlib import Path

import vrs_hardware as h
import vrs_inference as v


def avx2(system):
    try:
        if system == 'Windows':
            import ctypes
            # WinNT.h: PF_AVX2_INSTRUCTIONS_AVAILABLE = 40.
            return bool(ctypes.windll.kernel32.IsProcessorFeaturePresent(40))
        if system == 'Linux':
            flags = [set(line.split(':', 1)[1].split()) for line in Path('/proc/cpuinfo').read_text().splitlines()
                     if line.startswith('flags') and ':' in line]
            return all('avx2' in f for f in flags) if flags else None
    except (OSError, AttributeError, ValueError):
        pass
    return None


def os_version(system):
    if system == 'Windows':
        try:
            return sys.getwindowsversion().build >= 22000
        except AttributeError:
            return None
    return True if system == 'Linux' else None


def storage_ssd(workspace, system):
    # Linux direct block-device mount only. Overlay, RAID, dm, virtual and
    # unmapped Windows storage are deliberately UNKNOWN, not guessed.
    if system != 'Linux':
        return None
    try:
        dev = Path(workspace).stat().st_dev
        link = Path('/sys/dev/block') / f'{os.major(dev)}:{os.minor(dev)}'
        node = link.resolve(strict=True)
        if '/virtual/' in node.as_posix():
            return None
        for p in (node, node.parent):
            flag = p / 'queue/rotational'
            if flag.is_file():
                value = flag.read_text().strip()
                return {'0': True, '1': False}.get(value)
    except OSError:
        pass
    return None


def display():
    try:
        import tkinter as tk
        root = tk.Tk()
        try:
            root.withdraw()
            return (root.winfo_screenwidth(), root.winfo_screenheight())
        finally:
            root.destroy()
    except Exception:
        return None


def dependencies(profile):
    expected = {'Pillow': '12.3.0', 'psutil': '7.2.2'}
    if profile != 'review':
        expected.update({'numpy': '2.3.5', 'PyMuPDF': '1.26.7',
                         'torch': '2.10.0+cpu' if profile == 'cpu' else '2.10.0+cu128'})
    result = {}
    for package, wanted in expected.items():
        try:
            actual = md.version(package)
        except md.PackageNotFoundError:
            actual = None
        result[package] = {'expected': wanted, 'actual': actual,
                           'status': 'PASS' if actual == wanted else 'NOT_MET'}
    return result


def check(workspace, profile, *, gui=False):
    info = h.snapshot(workspace, profile)
    base = v.minimum(info, profile)
    system = info['system']
    def status(value):
        return 'UNKNOWN' if value is None else ('PASS' if value else 'NOT_MET')
    screen = display() if gui or profile == 'review' else None
    screen_status = status(screen[0] >= 1280 and screen[1] >= 720 if screen else None) if gui or profile == 'review' else 'NOT_APPLICABLE'
    deps = dependencies(profile)
    checks = {'base': 'PASS' if base['meets_checked_minimum'] else 'NOT_MET',
              'os_version': status(os_version(system)),
              'avx2': status(avx2(system)) if profile != 'review' else 'NOT_APPLICABLE',
              'ssd': status(storage_ssd(workspace, system)),
              'display': screen_status,
              'dependencies': 'PASS' if all(x['status'] == 'PASS' for x in deps.values()) else 'NOT_MET',
              'representative_throughput': 'UNKNOWN'}
    # Neither successful probes nor package versions establish native throughput.
    state = 'NOT_MET' if 'NOT_MET' in checks.values() else ('UNVERIFIED' if 'UNKNOWN' in checks.values() else 'PASS')
    return {'profile': profile, 'status': state, 'checks': checks, 'issues': base['issues'],
            'dependencies': deps, 'display_pixels': screen, 'hardware': info}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('workspace', type=Path)
    p.add_argument('--profile', choices=('review', 'cpu', 'cuda'), default='review')
    p.add_argument('--gui', action='store_true')
    a = p.parse_args()
    result = check(a.workspace, a.profile, gui=a.gui)
    print(json.dumps(result, indent=2, sort_keys=True))
    return {'PASS': 0, 'NOT_MET': 1, 'UNVERIFIED': 2}[result['status']]


if __name__ == '__main__':
    raise SystemExit(main())
