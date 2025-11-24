import subprocess
import sys
import time
import os
import signal

PYTHON = sys.executable
VENV_PATH = os.getenv("VENV_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv"))
ACTIVATE_PS1 = os.path.join(VENV_PATH, "Scripts", "Activate.ps1")
USE_VENV = os.path.isfile(ACTIVATE_PS1)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE_DIR, 'src')

def _build_commands():
    base_cmds = [
        ("GameLoop", f"python {os.path.join(SRC, 'game_loop.py')}"),
        ("Controller", f"python {os.path.join(SRC, 'controller.py')}"),
        ("Analytics", f"python {os.path.join(SRC, 'analytics.py')}"),
    ]
    if USE_VENV:
        wrapped = []
        for name, raw in base_cmds:
            # Encadear ativação da venv antes do comando
            # Usamos ; para sequenciar em PowerShell
            cmd = f"& '{ACTIVATE_PS1}'; {raw}"
            wrapped.append((name, cmd))
        return wrapped
    return base_cmds

COMMANDS = _build_commands()

def _kill_process(proc):
    if proc.poll() is not None:
        return
    try:
        
        if os.name == 'nt':
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
        for _ in range(10):
            if proc.poll() is not None:
                return
            time.sleep(0.1)
        
        if os.name == 'nt':
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            proc.kill()
    except Exception:
        pass


def kill_all(procs):
    print("\nEncerrando todos os processos...")
    for name, p in procs:
        _kill_process(p)
    print("Todos encerrados.")


def launch_all(auto_shutdown_on_exit=True):
    procs = []
    for name, cmd in COMMANDS:
        creationflags = 0
        if os.name == 'nt':
            creationflags = subprocess.CREATE_NEW_CONSOLE
        print(f"Iniciando {name}: {cmd}")
        
        if USE_VENV and os.name == 'nt':
            p = subprocess.Popen(["powershell", "-NoExit", "-Command", cmd], creationflags=creationflags)
        else:
            p = subprocess.Popen(cmd, creationflags=creationflags, shell=True)
        procs.append((name, p))
        time.sleep(0.4)

    print("\nTodos iniciados. CTRL+C aqui para encerrar todos juntos.")
    try:
        while True:
            time.sleep(2)
            mortos = [n for n, pr in procs if pr.poll() is not None]
            if mortos:
                print(f"Processos finalizados: {', '.join(mortos)}")
                if auto_shutdown_on_exit:
                    print("Um processo terminou; encerrando o restante (auto_shutdown_on_exit=True).")
                    break
    except KeyboardInterrupt:
        print("\nCTRL+C recebido.")
    finally:
        kill_all(procs)

if __name__ == '__main__':
    launch_all()
