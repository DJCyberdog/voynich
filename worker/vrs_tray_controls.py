"""Pure tray policy: explicit single-run actions, fresh target checks, no Tk calls."""
from dataclasses import dataclass

ACTIONS = ('start', 'stop', 'pause', 'resume')
STARTABLE = ('NOT_MANAGED', 'STOPPED', 'FAILED', 'NOT_RUNNING')


@dataclass(frozen=True)
class Snapshot:
    state: str = 'UNKNOWN'
    session: str | None = None
    pause: tuple = ()
    resume: tuple = ()
    review: int | None = None
    review_key: str = ''
    configured: bool = False


def snapshot(session, rows, configured, review_key):
    state = session['state']
    # Pause only READY runs; resume only PAUSED runs, never review-blocked ones.
    pause = tuple(sorted(r['id'] for r in rows if r['control'] == 'READY'))
    resume = tuple(sorted(r['id'] for r in rows if r['control'] == 'PAUSED' and not r['locked']))
    review = sum(r['stage'] == 'exception_review' and r['reason'] == 'REVIEW_PENDING' and r['control'] == 'BLOCKED' for r in rows)
    return Snapshot(state, session.get('id'), pause, resume, review, review_key, bool(configured))


def target(view, action):
    if action == 'start' and view.configured and view.state in STARTABLE:
        return (view.state, view.session)
    if action == 'stop' and view.state == 'RUNNING' and view.session:
        return (view.session,)
    if action in ('pause', 'resume') and view.configured and view.state == 'RUNNING' and view.session:
        candidates = getattr(view, action)
        if len(candidates) == 1:
            return (view.session, candidates[0])
    return None


def execute(api, interpreter, action, expected, fresh):
    if action not in ACTIONS or expected is None or target(fresh, action) != expected:
        raise ValueError('Tray action unavailable or target changed; refresh first')
    if action == 'start':
        return api.start(interpreter)
    if action == 'stop':
        return api.stop(expected_session=expected[0])
    return api.control(interpreter, action, expected[1])
