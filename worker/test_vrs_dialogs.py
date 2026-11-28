import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import vrs_dialogs as d


class DialogTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='VRS ü space ')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.sub=self.root/'Quellen ü'; self.sub.mkdir()
        self.file=self.sub/'f1r.pdf';self.file.write_bytes(b'fixture')

    def test_existing_file_and_folder(self):
        for p in (self.file,self.sub,self.file.relative_to(self.root),'Quellen ü/new.json'):
            self.assertEqual(d.initial_directory(self.root,p),str(self.sub))

    def test_missing_or_external_fallback(self):
        for p in (None,'','missing/deep/new.pdf',self.root.parent,'../outside.txt'):
            self.assertEqual(d.initial_directory(self.root,p),str(self.root))
        self.assertFalse((self.root/'missing').exists())

    def test_open_save_directory_and_cancel(self):
        parent=object()
        for result in ('',str(self.file),str(self.sub/'new.json'),str(self.sub)):
            dialog=Mock(return_value=result)
            self.assertEqual(d.choose(dialog,parent=parent,workspace=self.root,current=self.file,title='VRS'),result)
            dialog.assert_called_once_with(parent=parent,initialdir=str(self.sub),title='VRS')
        with self.assertRaises(ValueError):d.choose(Mock(),parent=parent,workspace=self.root,initialdir='outside')

    def test_portable_root(self):
        with patch.dict(os.environ,{'VRS_PORTABLE_LOG_ROOT':str(self.sub)}):
            self.assertEqual(d.portable_workspace(self.root),self.sub)
        with patch.dict(os.environ,{'VRS_PORTABLE_LOG_ROOT':str(self.root/'missing')}):
            self.assertEqual(d.portable_workspace(self.root),self.root)
        with patch.dict(os.environ,{'VRS_PORTABLE_LOG_ROOT':str(self.file)}):
            self.assertEqual(d.portable_workspace(self.root),self.root)

    def test_invalid_workspace(self):
        with self.assertRaises(ValueError):d.initial_directory(self.file)
        with self.assertRaises(FileNotFoundError):d.initial_directory(self.root/'missing')

if __name__=='__main__':unittest.main()
