"""Only explicitly registered update backups may be retired."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'assets/backup/lucx-ui-backup.sh').read_text(encoding='utf-8')
OWNER = 'lucx-ui-pro:automatic-update-backup:v1\n'
HELPER = SOURCE.split("<<'PY_AUTO_UPDATE_BACKUPS'\n", 1)[1].split('\nPY_AUTO_UPDATE_BACKUPS', 1)[0]


@unittest.skipUnless(os.name == 'posix', 'Linux backup retention')
class UpdateBackupRetention(unittest.TestCase):
    def archive(self, folder, index, registered=True):
        path = folder / f'lucx-ui-backup-20261011-1200{index:02d}-123-auto-update.tar.gz'
        path.write_bytes(b'test archive')
        os.utime(path, (index, index))
        Path(str(path) + '.sha256').write_text('checksum')
        if registered:
            Path(str(path) + '.auto-update').write_text(OWNER)
        return path

    def run_helper(self, path):
        result = subprocess.run(['python3', '-c', HELPER, str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_only_three_registered_auto_backups_keep_manual_and_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            archives = [self.archive(folder, n) for n in range(1, 6)]
            manual = folder / 'lucx-ui-backup-20261010-120000.tar.gz'
            manual.write_bytes(b'manual')
            unknown = self.archive(folder, 0, registered=False)
            self.run_helper(archives[-1])
            self.assertEqual([p.exists() for p in archives], [False, False, True, True, True])
            for deleted in archives[:2]:
                self.assertFalse(Path(str(deleted) + '.sha256').exists())
                self.assertFalse(Path(str(deleted) + '.auto-update').exists())
            self.assertEqual(manual.read_bytes(), b'manual')
            self.assertTrue(unknown.exists())
            self.run_helper(archives[-1])
            self.assertTrue(all(p.exists() for p in archives[2:]))

    def test_clock_rollback_keeps_new_backup_and_symlinks_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            archives = [self.archive(folder, n) for n in range(1, 5)]
            os.utime(archives[-1], (0, 0))
            outside = folder / 'manual.tar.gz'
            outside.write_bytes(b'manual')
            linked = folder / 'lucx-ui-backup-20261011-120059-123-auto-update.tar.gz'
            linked.symlink_to(outside)
            Path(str(linked) + '.auto-update').write_text(OWNER)
            self.run_helper(archives[-1])
            self.assertTrue(archives[-1].exists())
            self.assertEqual(sum(p.exists() for p in archives), 3)
            self.assertTrue(linked.is_symlink())
            self.assertEqual(outside.read_bytes(), b'manual')

    def test_update_opt_in_and_validation_precedes_retirement(self):
        main = (ROOT / 'lucx-ui-latest.sh').read_text(encoding='utf-8')
        self.assertIn('bash "$stage/backup.sh" backup --automatic-update || return 1', main)
        command = SOURCE.split('cmd_backup() {', 1)[1].split('\n# Keep the official', 1)[0]
        self.assertLess(command.index('tar -tzf "$dest"'), command.index('register_automatic_update_backup "$dest"'))
        self.assertIn('[[ "$automatic" == --automatic-update ]]', command)
        self.assertIn('backup)  cmd_backup "${2:-}" ;;', SOURCE)


if __name__ == '__main__':
    unittest.main()
