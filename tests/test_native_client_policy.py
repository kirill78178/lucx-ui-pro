"""Retire only Pro client triggers when the author provides the fix."""
from contextlib import closing
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

repo = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compat_policy', repo/'assets/compat/pro-compat.py')
compat = importlib.util.module_from_spec(spec); spec.loader.exec_module(compat)


class NativeClientPolicy(unittest.TestCase):
    def test_version_boundary_and_future_releases(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); binary=root/'usr/local/x-ui/x-ui'
            binary.parent.mkdir(parents=True); binary.touch()
            for version, native in [('3.9.0-lucx.286',False),('3.9.0-lucx.287',False),
                                    ('3.9.0-lucx.288',True),('3.9.0-lucx.289',True),
                                    ('3.9.0-lucx.290',True),('3.10.0-lucx.1',True)]:
                with self.subTest(version=version), patch.object(compat.subprocess,'run',
                        return_value=SimpleNamespace(returncode=0,stdout=version)):
                    self.assertEqual(compat.native_client_fix(root),native)

    def test_native_policy_removes_only_our_triggers_without_rewriting_data(self):
        with closing(sqlite3.connect(':memory:')) as db:
            db.executescript('''CREATE TABLE inbounds(id INTEGER PRIMARY KEY,protocol TEXT,settings TEXT);
              CREATE TABLE clients(id INTEGER PRIMARY KEY,email TEXT UNIQUE,enable INTEGER,uuid TEXT,sub_id TEXT);
              CREATE TABLE client_inbounds(client_id INTEGER,inbound_id INTEGER,PRIMARY KEY(client_id,inbound_id));
              INSERT INTO clients VALUES(1,'client',1,'uuid','sub');
              INSERT INTO inbounds VALUES(1,'openflux','{"secret":"keep","future":42}');
              INSERT INTO client_inbounds VALUES(1,1);''')
            compat.sync_clients(db)
            db.execute('CREATE TRIGGER native_client_trigger AFTER INSERT ON clients BEGIN SELECT 1; END')
            before={t:list(db.execute('SELECT * FROM '+t)) for t in ('inbounds','clients','client_inbounds')}
            with patch.object(compat,'native_client_fix',return_value=True):
                compat.apply_client_policy(db,Path('/'))
                compat.apply_client_policy(db,Path('/'))
            triggers=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'")]
            self.assertEqual(triggers,['native_client_trigger'])
            for table, values in before.items(): self.assertEqual(list(db.execute('SELECT * FROM '+table)),values)

    def test_legacy_policy_keeps_compatibility(self):
        with closing(sqlite3.connect(':memory:')) as db:
            db.executescript('''CREATE TABLE inbounds(id INTEGER PRIMARY KEY,protocol TEXT,settings TEXT);
              CREATE TABLE clients(id INTEGER PRIMARY KEY,email TEXT UNIQUE,enable INTEGER);
              CREATE TABLE client_inbounds(client_id INTEGER,inbound_id INTEGER,PRIMARY KEY(client_id,inbound_id));''')
            with patch.object(compat,'native_client_fix',return_value=False):
                compat.apply_client_policy(db,Path('/'))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'lucx_shareonly_clients_%'").fetchone()[0],7)


if __name__=='__main__': unittest.main()
