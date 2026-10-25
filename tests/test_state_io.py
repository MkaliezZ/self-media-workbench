"""Job polling must not lose the final atomic state on Windows."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import app as w


class StateIOTests(unittest.TestCase):
    def test_concurrent_polling_keeps_terminal_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'job.json';w.write(path,{'status':'running','step':0})
            stop=threading.Event();errors=[]
            def poll():
                while not stop.is_set():
                    try:w.read(path)
                    except Exception as exc:errors.append(str(exc));break
            thread=threading.Thread(target=poll);thread.start()
            try:
                for i in range(150):w.write(path,{'status':'running','step':i})
                w.write(path,{'status':'done','step':150})
            finally:stop.set();thread.join(5)
            self.assertFalse(errors,errors);self.assertFalse(thread.is_alive())
            self.assertEqual(w.read(path)['status'],'done')
            self.assertFalse(list(Path(directory).glob('*.tmp')))

    def test_transient_replace_denial_retries_same_complete_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'job.json';w.write(path,{'status':'running'})
            real=w.os.replace;attempts=[]
            def replace(source,target):
                attempts.append(1)
                if len(attempts)<3:raise PermissionError('controlled Windows sharing conflict')
                return real(source,target)
            with patch.object(w.os,'replace',side_effect=replace):
                w.write(path,{'status':'done'})
            self.assertEqual(len(attempts),3)
            self.assertEqual(w.read(path)['status'],'done')


if __name__=='__main__':unittest.main()
