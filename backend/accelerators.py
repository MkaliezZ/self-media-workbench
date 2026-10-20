"""Native display inventory and conservative ASR routing, not GPU execution proof."""
import json
import os
import platform
import subprocess
import sys


def vendor(name, identity=''):
    text=(name+' '+identity).casefold()
    if 'ven_10de' in text or 'nvidia' in text:return 'nvidia'
    if 'ven_1002' in text or any(s in text for s in ('amd','radeon','advanced micro devices','ati ')):return 'amd'
    if 'ven_8086' in text or 'intel' in text:return 'intel'
    if 'apple' in text:return 'apple'
    return 'unknown'


def inventory():
    result={'platform':sys.platform,'architecture':platform.machine(),'adapters':[],
            'errors':[],'execution_verified':False}
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    try:
        if sys.platform=='win32':
            command=['powershell','-NoProfile','-NonInteractive','-Command',
                '[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); '
                '@(Get-CimInstance Win32_VideoController | Select-Object Name,PNPDeviceID,DriverVersion) | ConvertTo-Json -Compress']
            proc=subprocess.run(command,capture_output=True,text=True,encoding='utf-8-sig',errors='strict',timeout=10,check=True,**options)
            rows=json.loads(proc.stdout or '[]')
            if isinstance(rows,dict):rows=[rows]
            result['adapters']=[{'name':r.get('Name',''),'vendor':vendor(r.get('Name',''),r.get('PNPDeviceID','')),
                                 'driver_version':r.get('DriverVersion')} for r in rows]
        elif sys.platform=='darwin':
            if platform.machine().lower() in ('arm64','aarch64'):
                result['adapters']=[{'name':'Apple Silicon','vendor':'apple'}]
            else:
                proc=subprocess.run(['system_profiler','SPDisplaysDataType','-json'],capture_output=True,
                    text=True,encoding='utf-8',timeout=15,check=True)
                rows=json.loads(proc.stdout).get('SPDisplaysDataType',[])
                result['adapters']=[{'name':r.get('sppci_model',r.get('_name','')),
                    'vendor':vendor(r.get('sppci_model',r.get('_name','')),r.get('spdisplays_vendor','')),
                    'metal_capability':r.get('spdisplays_metal')} for r in rows]
        else:
            result['errors'].append('Native inventory is implemented for Windows/macOS; explicitly configured accelerators remain usable')
    except (OSError,ValueError,subprocess.SubprocessError) as exc:result['errors'].append(str(exc))
    return result


def plan(backend,device,hardware,apple=False,cpp_ready=False,require_gpu=False):
    """Ordered attempts. Vendor is from display adapters, never the CPU brand."""
    if backend not in ('auto','faster-whisper','mlx','whisper.cpp'):raise ValueError('Unknown ASR backend')
    if device not in ('auto','cpu','cuda','gpu','vulkan','metal'):raise ValueError('Unknown ASR device')
    if backend=='mlx' and device not in ('auto','gpu'):raise ValueError('MLX accepts auto/gpu')
    if backend=='faster-whisper' and device not in ('auto','cpu','cuda'):raise ValueError('faster-whisper accepts auto/cpu/cuda')
    if backend=='whisper.cpp' and device=='cuda':raise ValueError('Use faster-whisper for CUDA')
    if require_gpu and device=='cpu':raise ValueError('CPU conflicts with require_gpu')
    if device=='cpu':return [('whisper.cpp' if backend=='whisper.cpp' else 'faster-whisper','cpu')]
    providers={a['vendor'] for a in hardware.get('adapters',[])}
    system=hardware.get('platform',sys.platform);attempts=[]
    if backend=='mlx' or (backend=='auto' and apple and device in ('auto','gpu')):attempts=[('mlx','gpu')]
    elif backend=='whisper.cpp' or device in ('vulkan','metal'):
        attempts=[('whisper.cpp',device if device in ('vulkan','metal') else ('metal' if system=='darwin' else 'vulkan'))]
    elif device=='cuda':attempts=[('faster-whisper','cuda')]
    elif 'nvidia' in providers and system!='darwin':
        attempts=[('faster-whisper','cuda')]
        if backend=='auto' and cpp_ready:attempts.append(('whisper.cpp','vulkan'))
    elif backend=='auto' and (providers & {'amd','intel'} or cpp_ready or device=='gpu'):
        attempts=[('whisper.cpp','metal' if system=='darwin' else 'vulkan')]
    elif device=='gpu':raise ValueError('No usable GPU strategy for the requested backend')
    if not require_gpu:attempts.append(('faster-whisper','cpu'))
    if not attempts:raise ValueError('No GPU strategy found; require_gpu forbids CPU fallback')
    return attempts
