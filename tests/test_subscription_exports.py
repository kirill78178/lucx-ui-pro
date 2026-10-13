import importlib.util
from pathlib import Path
import sqlite3,tempfile,unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('exports_compat',ROOT/'assets/compat/pro-compat.py')
compat=importlib.util.module_from_spec(spec);spec.loader.exec_module(compat)

class SubscriptionExports(unittest.TestCase):
    def fixture(self,root):
        state=root/'var/lib/lucx-ui-preinstall';state.mkdir(parents=True)
        (state/'owned-by-lucx-ui-pro').touch();(state/'domains').write_text('main.example\ncover.example\n')
        snippet=root/'etc/nginx/snippets/includes.conf';snippet.parent.mkdir(parents=True)
        snippet.write_text('    location /user-route/ { return 204; }\n')
        db=sqlite3.connect(':memory:');db.execute('CREATE TABLE settings(key TEXT,value TEXT)')
        settings={'subURI':'https://main.example/sub/','subPort':'27347','subCertFile':'/cert','subKeyFile':'/key','subJsonPath':'/json-random/','subJsonURI':'https://main.example/json-random?name=','subAwgPath':'/awg/','customFutureOption':'keep'}
        db.executemany('INSERT INTO settings VALUES(?,?)',settings.items())
        return db,settings,snippet

    def test_legacy_exports_repaired_idempotently_without_other_settings_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);db,settings,snippet=self.fixture(root)
            compat.repair_subscription_exports(root,db,settings)
            self.assertEqual(settings['subAwgURI'],'https://main.example/awg/')
            self.assertEqual(settings['subJsonURI'],'https://main.example/json-random/')
            self.assertIn('location ^~ /awg/',snippet.read_text())
            self.assertIn('proxy_pass https://127.0.0.1:27347;',snippet.read_text())
            before=snippet.read_text();rows=db.execute('SELECT * FROM settings').fetchall()
            compat.repair_subscription_exports(root,db,settings)
            self.assertEqual(before,snippet.read_text());self.assertEqual(rows,db.execute('SELECT * FROM settings').fetchall())
            self.assertEqual(settings['customFutureOption'],'keep')
            self.assertIn('location /user-route/',before)
            db.close()

    def test_internal_awg_url_retired_but_custom_public_exports_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);db,settings,snippet=self.fixture(root)
            settings['subAwgURI']='https://main.example:27347/awg/'
            compat.repair_subscription_exports(root,db,settings)
            self.assertEqual(settings['subAwgURI'],'https://main.example/awg/')
            settings.update(subAwgURI='https://other.example/custom/',subJsonURI='https://other.example/custom-json/')
            compat.repair_subscription_exports(root,db,settings)
            self.assertEqual(settings['subAwgURI'],'https://other.example/custom/')
            self.assertEqual(settings['subJsonURI'],'https://other.example/custom-json/')
            text=snippet.read_text().replace('        proxy_redirect off;','        proxy_redirect off;\n        proxy_read_timeout 77s;')
            snippet.write_text(text);compat.repair_subscription_exports(root,db,settings)
            self.assertEqual(text,snippet.read_text());db.close()

    def test_unowned_or_custom_nginx_locations_and_future_paths_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);db,settings,snippet=self.fixture(root)
            snippet.write_text('    location ^~ /awg/ { return 204; }\n')
            compat.repair_subscription_exports(root,db,settings)
            self.assertEqual(snippet.read_text(),'    location ^~ /awg/ { return 204; }\n')
            settings['subAwgPath']='/future/path.v2/'
            compat.repair_subscription_exports(root,db,settings)
            self.assertEqual(snippet.read_text(),'    location ^~ /awg/ { return 204; }\n')
            (root/'var/lib/lucx-ui-preinstall/owned-by-lucx-ui-pro').unlink()
            settings['subAwgURI']=''
            compat.repair_subscription_exports(root,db,settings)
            self.assertEqual(settings['subAwgURI'],'');db.close()

if __name__=='__main__':unittest.main()
