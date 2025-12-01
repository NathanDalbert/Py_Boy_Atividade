import time
from pyboy import PyBoy
from pyboy.utils import WindowEvent
from app.constants import MEM_X_POS, MEM_Y_POS, MEM_BATTLE
from app.config import load_config
from app.volume import VolumeService
from app.messaging import RabbitMQClient
from app.logging_setup import init_logger
from app.health import HealthCheck, HealthCheckMonitor
import logging
try:
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    import comtypes
except ImportError:
    AudioUtilities = None

VOLUME_INICIAL = 0
CONFIG = load_config()
modo_lento_ativo = False
volume_atual = VOLUME_INICIAL
volume_service = VolumeService(initial_percent=50)

def main():
    global modo_lento_ativo, volume_atual
    print(f"🎮 Iniciando PyBoy com ROM: {CONFIG.rom_path}")
    pyboy = PyBoy(CONFIG.rom_path, window_type="SDL2", sound=True)
    pyboy.set_emulation_speed(1)

    if volume_service.is_available():
        print(f"🔊 Volume inicial do processo: {volume_service.get_percent()}%")
    else:
        print("ℹ️ Controle de volume real indisponível.")

    init_logger()
    logger = logging.getLogger("game_loop")

    health = HealthCheck("GameLoop")

    mq = RabbitMQClient(enable_resilience=True)

    connection_success = mq.connect()
    if connection_success:
        mq.declare_queue(CONFIG.queue_commands)
        mq.declare_queue(CONFIG.queue_events)
        logger.info("✅ RabbitMQ conectado com sucesso")
    else:
        logger.warning("⚠️  Iniciando em MODO DEGRADADO sem RabbitMQ")
        logger.warning("    O emulador continuará funcionando localmente")
        logger.warning("    Comandos remotos não estarão disponíveis")

    health.register_check("rabbitmq", lambda: mq.is_connected)
    health.register_check("pyboy", lambda: pyboy is not None)
    health.register_check("volume", lambda: volume_service.is_available())

    monitor = HealthCheckMonitor(health, interval=30.0)
    monitor.start()

    logger.info("Loop iniciado. Aguardando comandos e emitindo eventos...")

    if mq.is_degraded:
        print("\n" + "="*60)
        print("⚠️  MODO DEGRADADO ATIVO")
        print("="*60)
        print("O emulador está rodando, mas sem conexão com RabbitMQ.")
        print("Funcionalidades disponíveis:")
        print("  ✅ Emulação do jogo (funcionando normalmente)")
        print("  ✅ Controle local via teclado")
        print("  ❌ Comandos remotos (indisponíveis)")
        print("  ❌ Analytics (indisponível)")
        print("\nO serviço tentará reconectar automaticamente.")
        print("="*60 + "\n")

    def on_command(comando: str):
        global modo_lento_ativo, volume_atual
        comando = comando.upper()
        logger.debug("Comando recebido: %s", comando)

        if comando == 'TURBO':
            modo_lento_ativo = False
            pyboy.set_emulation_speed(0)
        elif comando == 'NORMAL':
            modo_lento_ativo = False
            pyboy.set_emulation_speed(1)
        elif comando == 'LENTO':
            modo_lento_ativo = True
        elif comando == 'MUTE':
            volume_service.mute()
            volume_atual = 0
            if hasattr(pyboy, 'set_sound_enabled'):
                try:
                    pyboy.set_sound_enabled(False)
                except Exception:
                    pass
            print(" 🔇 Som desativado")
        elif comando == 'UNMUTE':
            percent = volume_service.unmute()
            volume_atual = percent
            if hasattr(pyboy, 'set_sound_enabled'):
                try:
                    pyboy.set_sound_enabled(True)
                except Exception:
                    pass
            print(f" 🔊 Som reativado -> {percent}%")
        elif comando == 'VOL+':
            volume_atual = volume_service.increase()
            print(f" 🔊 Volume + -> {volume_atual}%")
        elif comando == 'VOL-':
            volume_atual = volume_service.decrease()
            print(f" 🔉 Volume - -> {volume_atual}%")

        else:
            mapa_comandos = {
                'UP': (WindowEvent.PRESS_ARROW_UP, WindowEvent.RELEASE_ARROW_UP),
                'DOWN': (WindowEvent.PRESS_ARROW_DOWN, WindowEvent.RELEASE_ARROW_DOWN),
                'LEFT': (WindowEvent.PRESS_ARROW_LEFT, WindowEvent.RELEASE_ARROW_LEFT),
                'RIGHT': (WindowEvent.PRESS_ARROW_RIGHT, WindowEvent.RELEASE_ARROW_RIGHT),
                'A': (WindowEvent.PRESS_BUTTON_A, WindowEvent.RELEASE_BUTTON_A),
                'B': (WindowEvent.PRESS_BUTTON_B, WindowEvent.RELEASE_BUTTON_B),
                'START': (WindowEvent.PRESS_BUTTON_START, WindowEvent.RELEASE_BUTTON_START),
                'SELECT': (WindowEvent.PRESS_BUTTON_SELECT, WindowEvent.RELEASE_BUTTON_SELECT)
            }

            if comando in mapa_comandos:
                press, release = mapa_comandos[comando]
                pyboy.send_input(press)
                for _ in range(15): pyboy.tick()
                pyboy.send_input(release)
                for _ in range(10): pyboy.tick()

    if mq.is_connected:
        mq.consume(CONFIG.queue_commands, on_command)
        logger.info("✅ Consumidor de comandos ativo")
    else:
        logger.warning("⚠️  Consumidor de comandos inativo (modo degradado)")

    last_x = pyboy.memory[MEM_X_POS]
    last_y = pyboy.memory[MEM_Y_POS]
    in_battle = False
    last_health_check = time.time()

    try:
        while pyboy.tick():

            try:
                mq.process_data_events(time_limit=0)
            except Exception as e:
                logger.debug(f"Erro ao processar eventos: {e}")

            curr_x = pyboy.memory[MEM_X_POS]
            curr_y = pyboy.memory[MEM_Y_POS]

            if curr_x != last_x or curr_y != last_y:

                if not mq.publish(CONFIG.queue_events, 'EVENTO_PASSO'):
                    logger.debug("Evento de passo não publicado (modo degradado)")
                last_x = curr_x
                last_y = curr_y

            battle_val = pyboy.memory[MEM_BATTLE]
            if battle_val != 0 and not in_battle:
                if not mq.publish(CONFIG.queue_events, 'EVENTO_BATALHA'):
                    logger.debug("Evento de batalha não publicado (modo degradado)")
                in_battle = True
            elif battle_val == 0:
                in_battle = False

            if modo_lento_ativo:
                time.sleep(0.05)

            now = time.time()
            if now - last_health_check > 60:
                health.check_all()
                if mq.is_connected and not mq.is_degraded:
                    logger.info("✅ Serviço saudável - RabbitMQ conectado")
                elif not mq.is_connected:
                    logger.warning("⚠️  Serviço degradado - RabbitMQ desconectado, tentando reconectar...")
                last_health_check = now

    except KeyboardInterrupt:
        logger.info("Encerrando emulador...")
    finally:
        monitor.stop()
        health.print_status()
        pyboy.stop()
        mq.close()
        logger.info("Game Loop encerrado")

if __name__ == '__main__':
    main()