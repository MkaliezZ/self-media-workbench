"""Vendor routing and proof boundaries; mocks do not establish real GPU support."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import accelerators as a
import asr_backends as b
from cpp_asr import parse_result,gpu_evidence


def hardware(*vendors,system='win32'):
    return {'platform':system,'adapters':[{'vendor':v} for v in vendors]}


class AcceleratorTests(unittest.TestCase):
    def test_display_vendor_not_processor_brand(self):
        self.assertEqual(a.vendor('Display','PCI\\VEN_1002&DEV_1234'),'amd')
        self.assertEqual(a.vendor('NVIDIA GeForce RTX 5060'),'nvidia')
        self.assertEqual(a.vendor('Intel(R) Arc(TM) Graphics'),'intel')
        self.assertEqual(a.vendor('Microsoft Basic Render Driver'),'unknown')

    def test_nvidia_precedes_integrated_intel_and_optional_vulkan(self):
        self.assertEqual(a.plan('auto','auto',hardware('intel','nvidia'),cpp_ready=True),
            [('faster-whisper','cuda'),('whisper.cpp','vulkan'),('faster-whisper','cpu')])

    def test_amd_and_intel_never_probe_cuda(self):
        for v in ['amd','intel']:
            self.assertEqual(a.plan('auto','auto',hardware(v)),[('whisper.cpp','vulkan'),('faster-whisper','cpu')])
            self.assertEqual(a.plan('auto','auto',hardware(v,system='darwin')),[('whisper.cpp','metal'),('faster-whisper','cpu')])

    def test_cpu_override_and_headless_are_cpu_only(self):
        self.assertEqual(a.plan('auto','cpu',hardware('nvidia')),[('faster-whisper','cpu')])
        self.assertEqual(a.plan('auto','auto',hardware()),[('faster-whisper','cpu')])
        self.assertEqual(a.plan('auto','auto',hardware('apple',system='darwin'),apple=True),[('mlx','gpu'),('faster-whisper','cpu')])

    def test_require_gpu_never_returns_cpu(self):
        self.assertEqual(a.plan('auto','auto',hardware('amd'),require_gpu=True),[('whisper.cpp','vulkan')])
        with self.assertRaises(ValueError):a.plan('auto','cpu',hardware('nvidia'),require_gpu=True)
        with patch.object(b,'apple_silicon',return_value=False),patch.object(a,'inventory',return_value=hardware('nvidia')),patch.object(b,'faster_infer',side_effect=RuntimeError('missing cuDNN')) as call:
            with self.assertRaisesRegex(RuntimeError,'missing cuDNN'):b.infer(np.zeros(1),'ct2','mlx','auto','auto','zh',require_gpu=True)
            self.assertEqual(call.call_count,1)

    def test_vulkan_failure_preserved_before_cpu_fallback(self):
        with patch.object(b,'apple_silicon',return_value=False),patch.object(a,'inventory',return_value=hardware('amd')),patch('cpp_asr.cpp_infer',side_effect=RuntimeError('driver unavailable')),patch.object(b,'faster_infer',return_value={'device':'cpu','fallback_errors':[]}) as cpu:
            result=b.infer(np.zeros(1),'ct2','mlx','auto','auto','zh')
            self.assertEqual(cpu.call_args.args[2],'cpu')
            self.assertEqual(result['fallback_errors'][0]['device'],'vulkan')
            self.assertIn('driver unavailable',result['fallback_errors'][0]['error'])

    def test_compiled_flags_or_detected_device_are_not_gpu_inference(self):
        for log in ['VULKAN = 1', 'ggml_vulkan: Found 1 Vulkan devices',
                    'whisper_backend_init_gpu: using Vulkan0 backend\nwhisper_model_load: CPU total size = 74 MB',
                    'whisper_backend_init_gpu: using Vulkan0 backend\nwhisper_model_load: Vulkan0 total size = 0 MB']:
            with self.assertRaises(RuntimeError):gpu_evidence(log,'vulkan')
        proof=gpu_evidence('whisper_backend_init_gpu: using Vulkan0 backend\nwhisper_model_load: Vulkan0 total size = 74.1 MB','vulkan')
        self.assertEqual(proof['selected_native_backend'],'Vulkan0')

    def test_cuda_native_exit_is_contained_with_log_and_reason(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory,patch.object(b,'apple_silicon',return_value=False),patch.object(a,'inventory',return_value=hardware('nvidia')),patch.object(b.subprocess,'run',return_value=SimpleNamespace(returncode=9)),patch.object(b,'faster_direct',return_value={'backend':'faster-whisper','device':'cpu','fallback_errors':[]}):
            result=b.infer(np.zeros(10),'ct2','mlx','auto','auto','zh',evidence_dir=Path(directory))
            self.assertEqual(result['device'],'cpu')
            self.assertIn('CUDA worker exited 9',result['fallback_errors'][0]['error'])
            self.assertTrue(list(Path(directory).glob('cuda-*/failure.json')))
            self.assertTrue(list(Path(directory).glob('cuda-*/stderr.txt')))

    def test_real_offsets_preserved_and_missing_alignment_is_coarse(self):
        segment={'text':'不要删','offsets':{'from':100,'to':900},'tokens':[
            {'text':'不要','offsets':{'from':100,'to':600},'p':.8},
            {'text':'删','offsets':{'from':600,'to':900},'p':.7}]}
        words=parse_result({'transcription':[segment]})
        self.assertEqual([w['start'] for w in words],[.1,.6])
        self.assertEqual(''.join(w['word'] for w in words),'不要删')
        del segment['tokens'][0]['offsets']
        words=parse_result({'transcription':[segment]})
        self.assertEqual(len(words),1)
        self.assertEqual(words[0]['alignment'],'model_segment_group')
        self.assertIsNone(words[0]['probability'])
        segment['offsets']['to']=0
        with self.assertRaises(ValueError):parse_result({'transcription':[segment]})


if __name__=='__main__':unittest.main()
