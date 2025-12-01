"""
Script para iniciar todos os microserviços localmente (sem Docker)
Mais leve para PCs com recursos limitados
"""
import subprocess
import sys
import time
import os
import signal
from pathlib import Path

# Configurações
PYTHON = sys.executable
BASE_DIR = Path(__file__).parent
SRC_DIR = BASE_DIR / "src"

# Verificar se está no venv
VENV_PATHS = [
    BASE_DIR / "venv" / "Scripts" / "python.exe",  # Windows
    BASE_DIR / ".venv" / "Scripts" / "python.exe",  # Windows alternativo
    BASE_DIR / "venv" / "bin" / "python",  # Linux/Mac
    BASE_DIR / ".venv" / "bin" / "python",  # Linux/Mac alternativo
]

for venv_python in VENV_PATHS:
    if venv_python.exists():
        PYTHON = str(venv_python)
        break

print(f"🐍 Usando Python: {PYTHON}")

# Lista de serviços para iniciar
SERVICES = [
    {
        "name": "Analytics",
        "script": SRC_DIR / "analytics.py",
        "color": "\033[94m",  # Azul
        "required": False
    },
    {
        "name": "GameLoop",
        "script": SRC_DIR / "game_loop.py",
        "color": "\033[92m",  # Verde
        "required": False
    },
    {
        "name": "Controller",
        "script": SRC_DIR / "controller.py",
        "color": "\033[93m",  # Amarelo
        "required": False
    }
]

RESET_COLOR = "\033[0m"

processes = []


def check_rabbitmq():
    """Verifica se RabbitMQ está rodando"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5672))
        sock.close()
        return result == 0
    except:
        return False


def print_banner():
    """Imprime banner inicial"""
    print("\n" + "="*70)
    print("🎮 PyBoy Emulator - Microservices (Modo Local)")
    print("="*70)
    print("\n📋 Verificando ambiente...\n")


def print_service_status(name, status, color=""):
    """Imprime status de um serviço"""
    print(f"{color}  [{status}] {name}{RESET_COLOR}")


def start_service(service):
    """Inicia um serviço em processo separado"""
    name = service["name"]
    script = service["script"]
    color = service["color"]

    if not script.exists():
        print(f"❌ Script não encontrado: {script}")
        return None

    print(f"{color}▶️  Iniciando {name}...{RESET_COLOR}")

    try:
        if os.name == 'nt':  # Windows
            # Criar nova janela de console para cada serviço
            proc = subprocess.Popen(
                [PYTHON, str(script)],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=str(BASE_DIR)
            )
        else:  # Linux/Mac
            # Usar terminal do sistema
            proc = subprocess.Popen(
                [PYTHON, str(script)],
                cwd=str(BASE_DIR)
            )

        time.sleep(0.5)

        # Verificar se iniciou corretamente
        if proc.poll() is None:
            print_service_status(name, "OK", color)
            return proc
        else:
            print_service_status(name, "FALHOU", "\033[91m")
            return None

    except Exception as e:
        print(f"❌ Erro ao iniciar {name}: {e}")
        return None


def kill_process(proc, name):
    """Encerra um processo de forma segura"""
    if proc and proc.poll() is None:
        try:
            if os.name == 'nt':
                # Windows: usar taskkill para matar processo e filhos
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                # Linux/Mac: enviar SIGTERM
                proc.terminate()
                proc.wait(timeout=5)
        except:
            try:
                proc.kill()
            except:
                pass


def cleanup(signum=None, frame=None):
    """Limpa processos ao encerrar"""
    print("\n\n🛑 Encerrando todos os serviços...")

    for name, proc in processes:
        if proc:
            print(f"  ⏹️  Parando {name}...")
            kill_process(proc, name)

    print("\n✅ Todos os serviços foram encerrados.")
    print("="*70 + "\n")
    sys.exit(0)


def monitor_services():
    """Monitora serviços em execução"""
    print("\n" + "="*70)
    print("✅ Todos os serviços iniciados!")
    print("="*70)
    print("\n📊 Status dos Serviços:")
    print("  • Analytics  - Coletando métricas do jogo")
    print("  • GameLoop   - Emulando Pokémon Red")
    print("  • Controller - Aguardando comandos do usuário")
    print("\n💡 Dicas:")
    print("  • Use a janela do Controller para enviar comandos")
    print("  • Os serviços continuarão rodando mesmo se um falhar")
    print("  • Pressione CTRL+C aqui para encerrar TODOS os serviços")
    print("="*70 + "\n")

    try:
        while True:
            time.sleep(2)

            # Verificar se algum processo morreu
            dead_services = []
            for name, proc in processes:
                if proc and proc.poll() is not None:
                    dead_services.append(name)

            if dead_services:
                print(f"\n⚠️  Serviços encerrados: {', '.join(dead_services)}")
                print("   (Os outros serviços continuam rodando)")

    except KeyboardInterrupt:
        pass


def main():
    """Função principal"""
    # Configurar handler para CTRL+C
    signal.signal(signal.SIGINT, cleanup)
    if os.name != 'nt':
        signal.signal(signal.SIGTERM, cleanup)

    print_banner()

    # Verificar RabbitMQ
    rabbitmq_running = check_rabbitmq()
    if rabbitmq_running:
        print_service_status("RabbitMQ", "RODANDO", "\033[92m")
        print("  ✅ Broker de mensagens detectado em localhost:5672")
    else:
        print_service_status("RabbitMQ", "NÃO ENCONTRADO", "\033[93m")
        print("  ⚠️  Os serviços iniciarão em MODO DEGRADADO")
        print("  ℹ️  Para funcionalidade completa, inicie o RabbitMQ:")
        print("     • Windows: Execute 'rabbitmq-server' ou inicie o serviço")
        print("     • Linux/Mac: sudo systemctl start rabbitmq-server")
        print("     • Docker: docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management")

    print("\n🚀 Iniciando serviços...\n")

    # Iniciar cada serviço
    for service in SERVICES:
        proc = start_service(service)
        if proc:
            processes.append((service["name"], proc))
        time.sleep(1)  # Delay entre serviços

    if not processes:
        print("\n❌ Nenhum serviço foi iniciado com sucesso!")
        return 1

    # Monitorar serviços
    try:
        monitor_services()
    finally:
        cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
