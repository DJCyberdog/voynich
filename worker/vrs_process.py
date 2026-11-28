"""Platform-specific background process options and conservative liveness evidence."""
import os
import subprocess


def background_options(*, managed=False, platform=None):
    """No shell, no console on Windows; no DETACHED_PROCESS flag conflict."""
    platform = os.name if platform is None else platform
    if platform == 'nt':
        # Win32 CREATE_NO_WINDOW / CREATE_NEW_PROCESS_GROUP. Constants are
        # explicit so the Windows option contract is testable on Linux too.
        return dict(creationflags=0x08000000 | (0x00000200 if managed else 0), shell=False)
    return dict(shell=False, **({'start_new_session': True} if managed else {}))


def liveness(pid, created, psutil):
    """Return ACTIVE, ABSENT or UNKNOWN; RSS denial does not imply process exit."""
    try:
        proc = psutil.Process(pid)
        if abs(proc.create_time()-created) >= .01 or proc.status() == psutil.STATUS_ZOMBIE:
            return 'ABSENT', None
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return 'ABSENT', None
    except (psutil.Error, OSError):
        return 'UNKNOWN', None
    try:
        return 'ACTIVE', proc.memory_info().rss
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return 'ABSENT', None
    except (psutil.Error, OSError):
        return 'ACTIVE', None


def session_state(recorded, observation, stop_requested):
    if observation == 'UNKNOWN':
        return 'UNKNOWN'
    if observation == 'ACTIVE':
        return 'STOP_REQUESTED' if stop_requested or recorded in ('STOPPED','FAILED') else 'RUNNING'
    if observation == 'ABSENT':
        return recorded if recorded in ('STOPPED','FAILED') else 'NOT_RUNNING'
    raise ValueError('Invalid process observation')
