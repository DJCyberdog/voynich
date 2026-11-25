"""v0.8.1 local review notifier; no worker control, network or automatic startup."""
import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import active_review as ar
import worker as w

VERSION = '0.8.1'
PATH_KEYS = ('manifest', 'predictions', 'references', 'output')


def configuration(path):
    path = Path(path).resolve()
    data = w.read(path)
    w.require(set(data) == {'schema', 'poll_seconds', 'notify_at', 'cooldown_seconds', 'sessions'} and data['schema'] == 1, 'Invalid tray config')
    for name, lo, hi in [('poll_seconds', 5, 3600), ('notify_at', 1, 100000), ('cooldown_seconds', 60, 86400)]:
        w.require(type(data[name]) is int and lo <= data[name] <= hi, 'Invalid ' + name)
    w.require(isinstance(data['sessions'], list) and len(data['sessions']) <= 100, 'Invalid session list')
    ids, outputs, inputs = set(), set(), {path}
    sessions = []
    for row in data['sessions']:
        w.require(set(row) == {'id', 'reviewer', *PATH_KEYS}, 'Invalid session fields')
        jid = row['id']
        w.require(isinstance(jid, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', jid) and jid not in ids, 'Invalid or duplicate session ID')
        w.require(isinstance(row['reviewer'], str) and 0 < len(row['reviewer'].strip()) <= 128, 'Reviewer required')
        item = dict(row)
        for key in PATH_KEYS:
            value = row[key]
            w.require(isinstance(value, str) and value.strip(), 'Missing path: ' + key)
            item[key] = (path.parent / value).resolve()
        w.require(item['output'] not in outputs, 'Duplicate review output')
        ids.add(jid); outputs.add(item['output']); inputs.update(item[k] for k in PATH_KEYS[:-1]); sessions.append(item)
    w.require(not outputs & inputs, 'Review output aliases a source or configuration')
    return {**data, 'sessions': sessions}


@dataclass(frozen=True)
class Status:
    id: str
    pending: int = 0
    reviewed: int = 0
    state: str = 'ready'
    error: str = ''


class Monitor:
    """Cache validated immutable inputs by hash; validate each saved decision on every poll."""
    def __init__(self, config):
        self.config = Path(config).resolve()
        self.cache = {}
        self.settings = None
        self.sessions = {}

    def inspect(self, row):
        ident = row['id']
        try:
            paths = tuple(row[k] for k in PATH_KEYS[:-1])
            hashes = tuple(w.sha(p) for p in paths)
            key = (paths, hashes)
            cached = self.cache.get(ident)
            if cached is None or cached[0] != key:
                schemes = ar.catalog(row['references']); rows = ar.queue(row['manifest'], row['predictions'])
                w.require(hashes == tuple(w.sha(p) for p in paths), 'Sources changed during validation')
                cached = (key, schemes, {r['id'] for r in rows}); self.cache[ident] = cached
            _, schemes, ids = cached
            binding = dict(version=ar.VERSION, manifest_sha256=hashes[0], predictions_sha256=hashes[1], catalog_sha256=hashes[2], reviewer=row['reviewer'])
            data = w.read(row['output']) if row['output'].exists() else dict(binding=binding, decisions={})
            w.require(data['binding'] == binding and set(data['decisions']) <= ids, 'Review provenance mismatch')
            for d in data['decisions'].values(): ar.validate_decision(d, schemes)
            done = len(data['decisions'])
            return Status(ident, len(ids)-done, done)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            self.cache.pop(ident, None)
            # Keep paths, reviewer names and exception contents out of tray notifications.
            return Status(ident, state='blocked', error=type(exc).__name__)

    def poll(self):
        self.settings = None; self.sessions = {}
        settings = configuration(self.config)
        self.settings = settings
        self.sessions = {r['id']: r for r in settings['sessions']}
        self.cache = {k: v for k,v in self.cache.items() if k in self.sessions}
        return [self.inspect(row) for row in settings['sessions']]

    def review_args(self, ident):
        row = self.sessions[ident]
        args = [sys.executable, str(Path(__file__).with_name('review_client.py'))]
        for k in (*PATH_KEYS, 'reviewer'):
            args.extend(['--'+k, str(row[k])])
        return args


class Notices:
    def __init__(self):
        self.last_at = None; self.last_total = 0; self.last_ids = set(); self.below = True

    def due(self, statuses, threshold, cooldown, now):
        pending = {s.id: s.pending for s in statuses if s.state == 'ready' and s.pending}
        total = sum(pending.values()); ids = set(pending)
        if total < threshold:
            self.below = True
            return False
        changed = self.below or total > self.last_total or bool(ids-self.last_ids)
        if changed and (self.last_at is None or now-self.last_at >= cooldown):
            self.last_at = now; self.last_total = total; self.last_ids = ids; self.below = False
            return True
        return False


class Controller:
    def __init__(self, monitor, spawn=subprocess.Popen):
        self.monitor = monitor; self.spawn = spawn; self.child = None; self.statuses = []; self.notices = Notices()
        self.lock = threading.RLock(); self.error = None

    def refresh(self, now=None):
        with self.lock:
            try:
                self.statuses = self.monitor.poll(); self.error = None
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                self.statuses = []; self.error = 'Konfiguration ungültig oder nicht verfügbar'; return None
            cfg = self.monitor.settings
            if self.notices.due(self.statuses, cfg['notify_at'], cfg['cooldown_seconds'], time.monotonic() if now is None else now):
                total = sum(s.pending for s in self.statuses)
                return f'{total} Glyphen warten auf deine Prüfung.'
            return None

    def open_next(self):
        with self.lock:
            if self.child is not None and self.child.poll() is None:
                return False
            # Fresh validation, not the old tray snapshot. No arbitrary commands.
            try: rows = self.monitor.poll()
            except (OSError, ValueError, KeyError, TypeError, AttributeError): return False
            self.statuses = rows
            next_row = next((s for s in rows if s.state == 'ready' and s.pending), None)
            if next_row is None: return False
            self.child = self.spawn(self.monitor.review_args(next_row.id), shell=False)
            return True

    def title(self):
        with self.lock:
            if self.error: return 'Voynich · Konfiguration prüfen'
            pending = sum(s.pending for s in self.statuses)
            blocked = sum(s.state == 'blocked' for s in self.statuses)
            return f'Voynich · {pending} offen' + (f' · {blocked} blockiert' if blocked else '')


def icon_image():
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (64,64), (16,24,32,255)); d=ImageDraw.Draw(im)
    d.rounded_rectangle((5,5,58,58),radius=12,outline='#55cbb8',width=4)
    d.line([(16,19),(32,45),(48,19)],fill='#55cbb8',width=6,joint='curve')
    return im


def run_tray(config, backend=None):
    if backend is None:
        if os.name != 'nt': raise RuntimeError('Native tray currently supported on Windows only; use --once on other platforms')
        try: import pystray as backend
        except ImportError as exc: raise RuntimeError('Optional pystray dependency missing; see TRAY.md or use --once') from exc
    config = Path(config).resolve(); configuration(config)
    lockfile = config.with_name(config.name+'.tray.lock')
    fd = os.open(lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    stop = threading.Event(); wake = threading.Event(); controller=Controller(Monitor(config)); thread=None
    try:
        with os.fdopen(fd,'w') as f: f.write(str(os.getpid()))
        def open_review(icon, item):
            try:
                if not controller.open_next() and icon.HAS_NOTIFICATION: icon.notify('Kein offener Fall oder Review bereits geöffnet.', 'Voynich')
            except OSError:
                if icon.HAS_NOTIFICATION: icon.notify('Review-Fenster konnte nicht geöffnet werden.', 'Voynich')
        def refresh(icon, item): wake.set()
        def quit_tray(icon,item): stop.set(); wake.set(); icon.stop()
        def loop(icon):
            while not stop.is_set():
                message=controller.refresh(); icon.title=controller.title()
                if message and icon.HAS_NOTIFICATION:
                    try: icon.notify(message,'Voynich · Glyph Review')
                    except (RuntimeError,OSError,NotImplementedError): pass
                cfg=controller.monitor.settings or {'poll_seconds':60}
                wake.wait(cfg['poll_seconds']); wake.clear()
        def setup(icon):
            nonlocal thread
            icon.visible=True; thread=threading.Thread(target=loop,args=(icon,),daemon=True); thread.start()
        icon=backend.Icon('voynich-review',icon_image(),'Voynich · Review',menu=backend.Menu(
            backend.MenuItem('Nächsten Review öffnen',open_review,default=True),
            backend.MenuItem('Status aktualisieren',refresh),backend.MenuItem('Tray beenden',quit_tray)))
        icon.run(setup=setup)
    finally:
        stop.set(); wake.set()
        if thread is not None: thread.join()
        lockfile.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('config'); parser.add_argument('--once',action='store_true')
    args=parser.parse_args()
    try:
        if args.once:
            rows=Monitor(args.config).poll(); print(json.dumps([r.__dict__ for r in rows],indent=2))
            return 1 if any(r.state=='blocked' for r in rows) else 0
        run_tray(args.config); return 0
    except (OSError,ValueError,RuntimeError,KeyError,TypeError,AttributeError) as exc:
        print(f'Tray error: {exc}',file=sys.stderr); return 1


if __name__ == '__main__': sys.exit(main())
