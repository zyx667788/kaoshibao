import subprocess, sys, os
py = sys.executable
base = r'D:\gdx\kaoshibao'
out = open(os.path.join(base, 'debug', 'local_srv_out.log'), 'w', encoding='utf-8')
err = open(os.path.join(base, 'debug', 'local_srv_err.log'), 'w', encoding='utf-8')
p = subprocess.Popen(
    [py, '-m', 'flask', '--app', 'app', 'run', '--host=127.0.0.1', '--port=5678',
     '--no-debugger', '--no-reload'],
    cwd=base, stdout=out, stderr=err)
print('PID', p.pid)
