"""VRS-094 B: local operational ceilings and bounded immutable feature cache."""
from collections import OrderedDict
from threading import RLock

import vrs_hardware as h

KEYS = ('cpu_workers', 'ram_bytes', 'vram_bytes', 'disk_bytes', 'cache_bytes', 'batch_items')


def limits(obj=None):
    if obj is None:
        return {}
    if type(obj) is not dict or set(obj)-set(KEYS):
        raise ValueError('Unknown resource limit')
    for k, value in obj.items():
        h.positive(value, k, zero=k in ('cache_bytes', 'vram_bytes', 'disk_bytes'))
    return dict(obj)


def plan(info, work, request='auto', preset=h.DEFAULT_PRESET, overrides=None):
    caps = limits(overrides)
    preset = 'quiet' if preset == 'silent' else preset
    out = h.plan(info, work, request, preset)
    for key, limit in (('cpu_workers','cpu_workers'), ('ram_budget','ram_bytes'), ('vram_budget','vram_bytes')):
        if limit in caps:
            out[key] = min(out[key], caps[limit])
    disk = min(caps.get('disk_bytes', info['disk_free']), info['disk_free']-out['disk_reserve'])
    if work['disk'] > disk:
        raise h.ResourceBlocked('Configured disk limit exceeded')
    host = out['ram_budget']-work['ram_base']
    # Reserve two host chunks plus a cache. Prefer even a single item over caching.
    if host < 2*work['ram_item']:
        raise h.ResourceBlocked('Insufficient host budget for two chunks')
    cache = min(max(0, host-2*work['ram_item']), out['ram_budget']//20, caps.get('cache_bytes', out['ram_budget']))
    batch = min(out['batch_ceiling'], (host-cache)//(2*work['ram_item']), caps.get('batch_items', work['items']))
    if out['backend']=='cuda':
        batch = min(batch, (out['vram_budget']-work['vram_base'])//work['vram_item'])
    if batch < 1:
        raise h.ResourceBlocked('Configured memory limits cannot fit one item')
    out.update(batch_ceiling=batch, cache_budget=cache, limits=caps, disk_budget=disk)
    return out


class FeatureCache:
    """Per-run LRU, immutable byte payloads, synchronized accounting; not a disk cache."""
    def __init__(self, budget):
        self.budget = h.positive(budget, 'cache budget', zero=True)
        self.used = self.hits = self.misses = self.evictions = 0
        self.entries = OrderedDict()
        self.lock = RLock()

    def get(self, key):
        with self.lock:
            if key not in self.entries:
                self.misses += 1
                return None
            self.hits += 1
            self.entries.move_to_end(key)
            return self.entries[key][0]

    def put(self, key, value):
        if type(value) is not bytes:
            raise ValueError('Cache payload must be immutable bytes')
        # Conservative accounting for the bounded digest/box key and Python overhead.
        size = len(value)+512
        with self.lock:
            if size > self.budget:
                return
            if key in self.entries:
                self.used -= self.entries.pop(key)[1]
            while self.used+size > self.budget:
                self.used -= self.entries.popitem(last=False)[1][1]
                self.evictions += 1
            self.entries[key] = (value,size)
            self.used += size

    def resize(self, budget):
        with self.lock:
            self.budget = h.positive(budget,'cache budget',zero=True)
            while self.used > self.budget:
                self.used -= self.entries.popitem(last=False)[1][1]
                self.evictions += 1

    def stats(self):
        with self.lock:
            return dict(budget=self.budget, used=self.used, hits=self.hits, misses=self.misses, evictions=self.evictions, entries=len(self.entries))
