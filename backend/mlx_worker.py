"""Isolated native MLX worker. Local models only; stdout is JSON protocol."""
import argparse
import contextlib
import json
import sys


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['probe','transcribe'])
    parser.add_argument('--model');parser.add_argument('--audio');parser.add_argument('--language',default='zh')
    args=parser.parse_args()
    from asr_backends import apple_silicon,mlx_local_model
    if not apple_silicon():raise RuntimeError('Native Apple Silicon macOS is required')
    with contextlib.redirect_stdout(sys.stderr):
        import mlx.core as mx
        available=bool(mx.metal.is_available())
        if args.command=='probe':result={'metal_available':available}
        else:
            if not available:raise RuntimeError('Metal GPU is unavailable')
            model=mlx_local_model(args.model)
            import numpy as np
            import mlx_whisper
            mx.set_default_device(mx.gpu)
            check=mx.sum(mx.arange(8,dtype=mx.float32));mx.eval(check)
            if float(check.item())!=28.0:raise RuntimeError('MLX GPU kernel self-check failed')
            output=mlx_whisper.transcribe(np.load(args.audio,allow_pickle=False),path_or_hf_repo=str(model),
                language=args.language or None,word_timestamps=True,temperature=0.0,
                condition_on_previous_text=False,verbose=None)
            words=[w for segment in output['segments'] for w in segment.get('words',[])]
            if output.get('text','').strip() and not words:raise RuntimeError('MLX text has no word alignment')
            result={'backend':'mlx','device':'gpu','model':str(model),'language':output['language'],
                'words':words,'fallback_errors':[],
                'execution':{'metal_available':True,'gpu_kernel_verified':True,'isolated_worker':True}}
    print(json.dumps(result,ensure_ascii=False,allow_nan=False))


if __name__=='__main__':main()
