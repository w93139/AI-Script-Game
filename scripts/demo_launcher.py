#!/usr/bin/env python3
"""One-command local demo launcher: start / stop / restart / status / rollback.

Reads a local JSON config (never committed) that points at the private runtime,
state directory, frontend build and ports. Never reads or prints API keys.

Usage:
    python scripts/demo_launcher.py status
    python scripts/demo_launcher.py start | stop | restart
    python scripts/demo_launcher.py rollback      # start the fallback runtime

Config lookup order: $DEMO_CONFIG, ./demo.local.json, ~/.ai-jubensha-demo/config.json
"""
import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DEFAULT_CONFIGS = ['./demo.local.json', str(Path.home() / '.ai-jubensha-demo' / 'config.json')]


def load_config():
    candidates = []
    if os.environ.get('DEMO_CONFIG'):
        candidates.append(os.environ['DEMO_CONFIG'])
    candidates += DEFAULT_CONFIGS
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_file():
            config = json.loads(path.read_text('utf-8'))
            config['_config_path'] = str(path)
            return config
    raise SystemExit('未找到 demo 配置：设置 $DEMO_CONFIG，或在仓库根放置 demo.local.json')


def port_busy(port):
    with socket.socket() as sock:
        return sock.connect_ex(('127.0.0.1', int(port))) == 0


def http_ok(url, timeout=3):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, response.read(8192)
    except Exception:
        return None, b''


def read_pids(path):
    try:
        return json.loads(Path(path).read_text('utf-8'))
    except Exception:
        return {}


def write_pids(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2) + '\n', 'utf-8')


def port_pids(port):
    try:
        out = subprocess.run(['lsof', '-tiTCP:%d' % int(port), '-sTCP:LISTEN'],
                             capture_output=True, text=True).stdout.split()
        return [int(x) for x in out]
    except Exception:
        return []


def log_path(config, name):
    directory = Path(config.get('logs', '.')).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    return directory / name


def start(config, module_override=None):
    backend = config['backend']
    frontend = config['frontend']
    pid_path = config['pid_file']
    for label, port in (('后端', backend['port']), ('前端', frontend['port'])):
        if port_busy(port):
            raise SystemExit('%s端口 %s 已被占用；先 stop 或换端口。' % (label, port))
    module = module_override or backend['module']
    backend_cmd = [config['python'], module, '--live', '--state-dir', backend['state_dir']]
    next_bin = str(Path(frontend['dir']) / 'node_modules' / 'next' / 'dist' / 'bin' / 'next')
    frontend_cmd = [config['node'], next_bin, 'start', '-H', '127.0.0.1', '-p', str(frontend['port'])]

    backend_log = open(log_path(config, 'backend.log'), 'ab')
    frontend_log = open(log_path(config, 'frontend.log'), 'ab')
    backend_proc = subprocess.Popen(backend_cmd, cwd=str(Path(module).parent),
                                    stdout=backend_log, stderr=subprocess.STDOUT,
                                    start_new_session=True)
    frontend_proc = subprocess.Popen(frontend_cmd, cwd=frontend['dir'],
                                     stdout=frontend_log, stderr=subprocess.STDOUT,
                                     start_new_session=True)
    write_pids(pid_path, {'backend': backend_proc.pid, 'frontend': frontend_proc.pid,
                          'backend_module': module})
    health_url = 'http://127.0.0.1:%s/health' % backend['port']
    root_url = 'http://127.0.0.1:%s/' % frontend['port']
    for _ in range(60):
        if backend_proc.poll() is not None or frontend_proc.poll() is not None:
            raise SystemExit('启动失败，请查看 %s 下的日志。' % config.get('logs', '.'))
        status, _ = http_ok(health_url)
        fstatus, _ = http_ok(root_url)
        if status == 200 and fstatus == 200:
            print('已启动：后端 %s，前端 %s' % (health_url, root_url))
            return
        time.sleep(1)
    raise SystemExit('启动超时；进程仍在运行，可查看日志。')


def stop(config):
    pid_path = config['pid_file']
    pids = read_pids(pid_path)
    targets = []
    for key in ('backend', 'frontend'):
        if pids.get(key):
            targets.append(int(pids[key]))
    for port in (config['backend']['port'], config['frontend']['port']):
        targets += port_pids(port)
    stopped = set()
    for pid in dict.fromkeys(targets):
        if pid in stopped:
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            stopped.add(pid)
        except ProcessLookupError:
            pass
    time.sleep(1)
    for port in (config['backend']['port'], config['frontend']['port']):
        for pid in port_pids(port):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        Path(pid_path).unlink()
    except FileNotFoundError:
        pass
    print('已停止后端/前端（未改动存档与账本）。')


def status(config):
    backend = config['backend']
    frontend = config['frontend']
    status_code, body = http_ok('http://127.0.0.1:%s/health' % backend['port'])
    if status_code == 200:
        try:
            data = json.loads(body)
            print('后端: 正常 | provider=%s model=%s 已记账=%s 费用=%s 上限=%s'
                  % (data.get('provider'), data.get('model'), data.get('accounted_calls'),
                     data.get('accounted_cost_cny'), data.get('max_calls')))
        except Exception:
            print('后端: 正常（无法解析 health）')
    else:
        print('后端: 未运行或异常 (http=%s)' % status_code)
    fstatus, _ = http_ok('http://127.0.0.1:%s/' % frontend['port'])
    print('前端: %s | %s' % ('正常' if fstatus == 200 else '未运行或异常',
                             'http://127.0.0.1:%s/' % frontend['port']))
    pids = read_pids(config['pid_file'])
    if pids:
        print('记录进程:', pids)


def rollback(config):
    fallback = config['backend'].get('rollback_module')
    if not fallback:
        raise SystemExit('配置缺少 backend.rollback_module')
    stop(config)
    start(config, module_override=fallback)
    print('已回退到:', fallback)


def main():
    parser = argparse.ArgumentParser(description='本机 demo 启动器')
    parser.add_argument('command', choices=['start', 'stop', 'restart', 'status', 'rollback'])
    args = parser.parse_args()
    config = load_config()
    if args.command == 'status':
        status(config)
    elif args.command == 'start':
        start(config)
    elif args.command == 'stop':
        stop(config)
    elif args.command == 'restart':
        stop(config)
        start(config)
    elif args.command == 'rollback':
        rollback(config)


if __name__ == '__main__':
    sys.exit(main())
