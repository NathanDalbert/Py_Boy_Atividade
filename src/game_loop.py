import time
from pyboy import PyBoy
from pyboy.utils import WindowEvent
from app.constants import MEM_X_POS, MEM_Y_POS, MEM_BATTLE
from app.config import load_config
from app.volume import VolumeService
from app.messaging import RabbitMQClient
from app.logging_setup import init_logger
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
    print(f"Iniciando PyBoy com ROM: {CONFIG.rom_path}")
    pyboy = PyBoy(CONFIG.rom_path, window_type="SDL2", sound=True)
    pyboy.set_emulation_speed(1) 

    if volume_service.is_available():
        print(f"🔊 Volume inicial do processo: {volume_service.get_percent()}%")
    else:
        print("ℹ️ Controle de volume real indisponível.")


    init_logger()
    logger = logging.getLogger("game_loop")
    mq = RabbitMQClient()
    try:
        mq.connect()
        mq.declare_queue(CONFIG.queue_commands)
        mq.declare_queue(CONFIG.queue_events)
    except Exception:
        logger.error("Falha ao iniciar conexões RabbitMQ")
        return

    logger.info("Loop iniciado. Aguardando comandos e emitindo eventos...")


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

    mq.consume(CONFIG.queue_commands, on_command)

    last_x = pyboy.memory[MEM_X_POS]
    last_y = pyboy.memory[MEM_Y_POS]
    in_battle = False

    try:
        while pyboy.tick():
            mq.process_data_events(time_limit=0)
            curr_x = pyboy.memory[MEM_X_POS]
            curr_y = pyboy.memory[MEM_Y_POS]
            
            if curr_x != last_x or curr_y != last_y:
                mq.publish(CONFIG.queue_events, 'EVENTO_PASSO')
                last_x = curr_x
                last_y = curr_y
            battle_val = pyboy.memory[MEM_BATTLE]
            if battle_val != 0 and not in_battle:
                mq.publish(CONFIG.queue_events, 'EVENTO_BATALHA')
                in_battle = True
            elif battle_val == 0:
                in_battle = False
            if modo_lento_ativo:
                time.sleep(0.05)
            
    except KeyboardInterrupt:
        logger.info("Encerrando emulador...")
    finally:
        pyboy.stop()
        mq.close()

if __name__ == '__main__':
    main()