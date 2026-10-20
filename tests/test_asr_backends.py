"""Selection/failure contract tests; mocks are NOT evidence of GPU inference."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import asr_backends as b


class AsrBackendTests(unittest.TestCase):
    def test_apple_auto_prefers_mlx_and_explicit_cpu_is_respected(self):
        sample={'backend':'mlx','device':'gpu'}
        with patch.object(b,'apple_silicon',return_value=True),patch.object(b,'mlx_infer',return_value=sample) as gpu,patch.object(b,'faster_infer',return_value={'device':'cpu'}) as cpu:
            self.assertIs(b.infer(np.zeros(10),'cpu','mlx','auto','auto','en'),sample)
            cpu.assert_not_called();gpu.assert_called_once()
            self.assertEqual(b.infer(np.zeros(10),'cpu','mlx','auto','cpu','en')['device'],'cpu')
            self.assertEqual(gpu.call_count,1)

    def test_mlx_native_failure_uses_cpu_and_keeps_reason(self):
        with patch.object(b,'apple_silicon',return_value=True),patch.object(b,'mlx_infer',side_effect=RuntimeError('worker exited -6')),patch.object(b,'faster_infer',return_value={'backend':'faster-whisper','device':'cpu','fallback_errors':[]}) as cpu:
            result=b.infer(np.zeros(10),'cpu','mlx','auto','auto','en')
            self.assertEqual(result['device'],'cpu')
            self.assertIn('worker exited -6',result['fallback_errors'][0]['error'])
            self.assertEqual(cpu.call_args.args[2],'cpu')

    def test_non_apple_auto_does_not_load_mlx(self):
        with patch.object(b,'apple_silicon',return_value=False),patch.object(b,'mlx_infer') as gpu,patch.object(b,'faster_infer',return_value={'device':'cpu'}):
            b.infer(np.zeros(10),'cpu','mlx','auto','auto','en');gpu.assert_not_called()

    def test_local_ct2_weights_cannot_trigger_mlx_hub_download(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);(p/'config.json').write_text('{}');(p/'model.bin').write_bytes(b'not MLX')
            with self.assertRaisesRegex(ValueError,'not compatible'):b.mlx_local_model(p)
            (p/'weights.npz').write_bytes(b'fixture only')
            self.assertEqual(b.mlx_local_model(p),p.resolve())

    def test_conflicting_backend_device_is_not_silently_reinterpreted(self):
        for backend,device in [('mlx','cpu'),('mlx','cuda'),('faster-whisper','gpu')]:
            with self.assertRaises(ValueError):b.infer(np.zeros(10),'cpu','mlx',backend,device,'en')


if __name__=='__main__':unittest.main()
