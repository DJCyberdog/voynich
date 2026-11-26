"""Optional portable worker instrumentation; no raw messages or runtime identity changes."""
import os
import re
from pathlib import Path
from vrs_portable_logs import event, crash

STAGES=('script_regions','glyph_segmentation','glyph_classification','exception_review','transcription_alignment')
STATES=('READY','BLOCKED','FAILED','COMPLETED','PAUSED','CANCELLED','STOP_REQUESTED')


class WorkerLog:
    def __init__(self,root):
        self.root=Path(root).resolve(strict=True)
        self.enabled=os.environ.get('VRS_PORTABLE_LOG_ROOT')==str(self.root)
        self.logging_failed=False

    def write(self,level,code,**fields):
        if self.enabled:
            try:event(self.root,'worker',level,code,**fields)
            except (OSError,ValueError,TypeError,KeyError):self.logging_failed=True

    def start(self):self.write('INFO','WORKER_START',state='RUNNING')
    def stop(self):self.write('INFO','WORKER_STOP',state='STOPPED')

    def failed(self,error):
        self.write('ERROR','WORKER_FAILED',state='FAILED')
        if self.enabled:
            try:crash(self.root,'worker',error)
            except (OSError,ValueError,TypeError,KeyError):self.logging_failed=True

    def sweep(self,rows):
        for row in rows:
            if not isinstance(row,dict):continue
            run=row.get('run_id'); state=row.get('control'); stage=row.get('stage')
            if not isinstance(run,str) or not re.fullmatch('[a-f0-9]{64}',run):continue
            if state not in STATES+('ERROR',):continue
            fields={'run':run}
            if state!='ERROR':fields['state']=state
            if stage in STAGES:fields['stage']=stage
            level='ERROR' if state in ('FAILED','ERROR') else 'WARNING' if state in ('BLOCKED','PAUSED') else 'INFO'
            self.write(level,'JOB_STATE',**fields)
