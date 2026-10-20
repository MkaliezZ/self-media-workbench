"""Isolated NVIDIA CUDA inference; stdout is JSON and native diagnostics persist."""
import argparse
import contextlib
import json
import sys
import numpy as np
from asr_backends import faster_direct


def main():
    p=argparse.ArgumentParser();p.add_argument('--audio',required=True)
    p.add_argument('--model',required=True);p.add_argument('--language',default='zh');args=p.parse_args()
    with contextlib.redirect_stdout(sys.stderr):
        result=faster_direct(np.load(args.audio,allow_pickle=False),args.model,'cuda',args.language)
    print(json.dumps(result,ensure_ascii=False,allow_nan=False))


if __name__=='__main__':main()
