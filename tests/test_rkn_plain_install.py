"""Upstream installer stays silent; diagnostics and exit status are retained."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

repo=Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name=='posix','Native Bash installation test')
class RknPlainInstall(unittest.TestCase):
    def invoke(self, exitcode):
        source=(repo/'lucx-ui-latest.sh').read_text()
        function=source.split('run_rkn_guard_installer() {',1)[1].split('\n}\n',1)[0]
        with tempfile.TemporaryDirectory() as folder:
            installer=Path(folder)/'installer.sh'
            installer.write_text('clear\n[[ ! -t 1 ]] || exit 99\n[[ "$1" == install ]] || exit 98\nprintf "STATE: installing\\n"\nexit '+str(exitcode)+'\n')
            log=Path(folder)/'install.log'
            result=subprocess.run(['bash','-c','run_rkn_guard_installer() {'+function+'\n}\nrun_rkn_guard_installer "$1" "$2"','test',str(installer),str(log)],capture_output=True,text=True)
            return result,log.read_text()

    def test_plain_output_without_screen_clear(self):
        result,log=self.invoke(0)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,'')
        self.assertEqual(result.stderr,'')
        self.assertEqual(log,'STATE: installing\n')

    def test_installer_failure_propagates_with_diagnostics_retained(self):
        result,log=self.invoke(7)
        self.assertEqual(result.returncode,7)
        self.assertEqual(result.stdout,'')
        self.assertEqual(log,'STATE: installing\n')


if __name__=='__main__': unittest.main()
