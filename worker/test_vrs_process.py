import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
import vrs_process as p


class Error(Exception): pass
class NoSuchProcess(Error): pass
class ZombieProcess(NoSuchProcess): pass
class AccessDenied(Error): pass


class ProcessTests(unittest.TestCase):
    def fixture(self):
        proc=Mock();proc.create_time.return_value=100.;proc.status.return_value='running';proc.memory_info.return_value=SimpleNamespace(rss=123)
        ps=SimpleNamespace(Process=Mock(return_value=proc),Error=Error,NoSuchProcess=NoSuchProcess,ZombieProcess=ZombieProcess,STATUS_ZOMBIE='zombie')
        return ps,proc

    def test_windows_flags(self):
        self.assertEqual(p.background_options(platform='nt'),dict(creationflags=0x08000000,shell=False))
        self.assertEqual(p.background_options(platform='nt',managed=True),dict(creationflags=0x08000200,shell=False))
        self.assertEqual(p.background_options(platform='posix',managed=True),dict(start_new_session=True,shell=False))

    def test_actual_subprocess(self):
        result=subprocess.run([sys.executable,'-c','print(42)'],capture_output=True,text=True,check=True,**p.background_options())
        self.assertEqual(result.stdout.strip(),'42')
        proc=subprocess.Popen([sys.executable,'-c','raise SystemExit(7)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**p.background_options(managed=True))
        self.assertEqual(proc.wait(timeout=10),7)

    def test_identity_and_rss(self):
        ps,proc=self.fixture();self.assertEqual(p.liveness(12,100.,ps),('ACTIVE',123))
        proc.memory_info.side_effect=AccessDenied();self.assertEqual(p.liveness(12,100.,ps),('ACTIVE',None))
        self.assertEqual(p.liveness(12,99.,ps),('ABSENT',None))
        proc.status.return_value='zombie';self.assertEqual(p.liveness(12,100.,ps),('ABSENT',None))

    def test_denied_and_exited(self):
        ps,proc=self.fixture();proc.create_time.side_effect=AccessDenied();self.assertEqual(p.liveness(12,100.,ps),('UNKNOWN',None))
        ps.Process.side_effect=NoSuchProcess();self.assertEqual(p.liveness(12,100.,ps),('ABSENT',None))

    def test_states(self):
        for recorded,observation,stop,expected in [('RUNNING','ACTIVE',False,'RUNNING'),('RUNNING','ACTIVE',True,'STOP_REQUESTED'),('STOPPED','ACTIVE',False,'STOP_REQUESTED'),('FAILED','ACTIVE',False,'STOP_REQUESTED'),('STOPPED','ABSENT',False,'STOPPED'),('RUNNING','ABSENT',False,'NOT_RUNNING'),('STOPPED','UNKNOWN',False,'UNKNOWN')]:
            self.assertEqual(p.session_state(recorded,observation,stop),expected)
        with self.assertRaises(ValueError):p.session_state('RUNNING','OTHER',False)

if __name__=='__main__':unittest.main()
