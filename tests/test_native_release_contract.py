"""New native service permissions stay authoritative through updater adaptation."""
from pathlib import Path
import tempfile,unittest
from test_update_compat import compat

class NativeReleaseContract(unittest.TestCase):
    def test_native_caps_and_future_fields_are_preserved(self):
        native=('ReadWritePaths=-/etc/x-ui -/etc/amnezia -/etc/ufw -/etc/default/ufw\n'
                'CapabilityBoundingSet=CAP_DAC_OVERRIDE CAP_NET_ADMIN CAP_NET_BIND_SERVICE CAP_NET_RAW CAP_SETUID CAP_SETGID CAP_CHOWN CAP_KILL\n'
                'FuturePanelDirective=leave-intact\n')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'update.sh'
            path.write_text(native+'XUI_UPDATE_TAG=x\n    config_after_update\n        bash "${awg_installer}" || echo failed\n')
            compat.adapt_updater(path)
            self.assertTrue(path.read_text().startswith(native))
