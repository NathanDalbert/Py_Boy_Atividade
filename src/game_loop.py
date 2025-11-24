import pika
import time
import os
from pyboy import PyBoy
from pyboy.utils import WindowEvent
try:
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    import comtypes  # noqa: F401 (necessária para pycaw funcionar)
except ImportError:  # Se pycaw não instalado, operações de volume real serão ignoradas
    AudioUtilities = None


ROM_PATH = "roms/pokemon_red.gb"
VOLUME_INICIAL = 0


MEM_X_POS = 0xD362 
MEM_Y_POS = 0xD361

MEM_BATTLE = 0xD057 


modo_lento_ativo = False
volume_atual = VOLUME_INICIAL  # valor lógico 0..100
ultimo_volume_real = 0.5  # volume em escala 0.0..1.0 para restaurar após UNMUTE
_cache_audio_volume = None  # cache da interface de volume do processo

def _obter_interface_volume():
    global _cache_audio_volume
    if _cache_audio_volume is not None:
        return _cache_audio_volume
    if AudioUtilities is None:
        return None
    try:
        pid_atual = os.getpid()
        for session in AudioUtilities.GetAllSessions():
            proc = session.Process
            if proc and proc.pid == pid_atual:
                vol = session._ctl.QueryInterface(ISimpleAudioVolume)
                _cache_audio_volume = vol
                return vol
    except Exception:
        return None
    return None

def main():
    global modo_lento_ativo, volume_atual
    
    print(f"Iniciando PyBoy com ROM: {ROM_PATH}")
    
  

    # Ative o som definindo sound=True. Requer pysdl2-dll instalado (já está em requirements) e dispositivo de saída disponível.
    pyboy = PyBoy(ROM_PATH, window_type="SDL2", sound=True)
    pyboy.set_emulation_speed(1) 

    # Mostrar estado inicial de áudio
    vol_iface_boot = _obter_interface_volume()
    if vol_iface_boot:
        try:
            inicial = vol_iface_boot.GetMasterVolume()
            print(f"🔊 Volume inicial do processo: {int(inicial*100)}%")
        except Exception:
            print("⚠️ Não foi possível ler volume inicial do processo.")
    else:
        if AudioUtilities is None:
            print("ℹ️ pycaw não disponível: controle de volume real desativado.")
        else:
            print("ℹ️ Interface de volume não encontrada para este processo.")


    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='fila_comandos')
        channel.queue_declare(queue='fila_eventos')  
    except Exception as e:
        print(f"❌ Erro ao conectar no RabbitMQ: {e}")
        return

    print(" [*] Jogo rodando! Ouvindo comandos e publicando eventos...")


    def callback(ch, method, properties, body):
        global modo_lento_ativo, volume_atual
        comando = body.decode().upper()
        print(f" [!] Comando recebido: {comando}")
        
      
        if comando == 'TURBO':
            modo_lento_ativo = False
            pyboy.set_emulation_speed(0)
        elif comando == 'NORMAL':
            modo_lento_ativo = False
            pyboy.set_emulation_speed(1)
        elif comando == 'LENTO':
            modo_lento_ativo = True
        elif comando == 'MUTE':
            volume_atual = 0
            # PyBoy mute
            if hasattr(pyboy, 'set_sound_enabled'):
                try:
                    pyboy.set_sound_enabled(False)
                except Exception:
                    pass
            # Sistema (pycaw)
            vol_iface = _obter_interface_volume()
            if vol_iface:
                try:
                    atual = vol_iface.GetMasterVolume()
                    if atual > 0.01:
                        # guardar último volume não zero
                        global ultimo_volume_real
                        ultimo_volume_real = atual
                    vol_iface.SetMasterVolume(0.0, None)
                    print(" 🔇 Som desativado (PyBoy + Sistema)")
                except Exception:
                    print(" ⚠️ Falha ao mutar volume do sistema")
            else:
                print(" 🔇 Mute lógico (sem interface de volume)")
        elif comando == 'UNMUTE':
            # PyBoy unmute
            if hasattr(pyboy, 'set_sound_enabled'):
                try:
                    pyboy.set_sound_enabled(True)
                except Exception:
                    pass
            # Sistema (pycaw)
            vol_iface = _obter_interface_volume()
            if vol_iface:
                try:
                    alvo = ultimo_volume_real if ultimo_volume_real > 0.01 else 0.5
                    vol_iface.SetMasterVolume(alvo, None)
                    volume_atual = int(alvo * 100)
                    print(f" 🔊 Som reativado (PyBoy + Sistema) -> {volume_atual}%")
                except Exception:
                    print(" ⚠️ Falha ao restaurar volume do sistema")
            else:
                print(" 🔊 Reativação lógica (sem interface de volume)")
        elif comando == 'VOL+':
            if volume_atual < 100:
                volume_atual += 10
            vol_iface = _obter_interface_volume()
            if vol_iface:
                try:
                    novo = min(1.0, volume_atual / 100.0)
                    vol_iface.SetMasterVolume(novo, None)
                    ultimo_volume_real = novo if novo > 0.01 else ultimo_volume_real
                    print(f" 🔊 Volume + -> {volume_atual}%")
                except Exception:
                    print(" ⚠️ Falha ao ajustar volume +")
        elif comando == 'VOL-':
            if volume_atual > 0:
                volume_atual -= 10
            vol_iface = _obter_interface_volume()
            if vol_iface:
                try:
                    novo = max(0.0, volume_atual / 100.0)
                    vol_iface.SetMasterVolume(novo, None)
                    if novo > 0.01:
                        ultimo_volume_real = novo
                    print(f" 🔉 Volume - -> {volume_atual}%")
                except Exception:
                    print(" ⚠️ Falha ao ajustar volume -")
            
    
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
                for _ in range(15): pyboy.tick() # Segura
                pyboy.send_input(release)
                for _ in range(10): pyboy.tick() # Solta

        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='fila_comandos', on_message_callback=callback)

  
    last_x = pyboy.memory[MEM_X_POS]
    last_y = pyboy.memory[MEM_Y_POS]
    in_battle = False

    try:
        while pyboy.tick():
            
            connection.process_data_events(time_limit=0)
            
         
            
       
            curr_x = pyboy.memory[MEM_X_POS]
            curr_y = pyboy.memory[MEM_Y_POS]
            
            if curr_x != last_x or curr_y != last_y:
             
                channel.basic_publish(exchange='', routing_key='fila_eventos', body='EVENTO_PASSO')
                last_x = curr_x
                last_y = curr_y

     
            battle_val = pyboy.memory[MEM_BATTLE]
            if battle_val != 0 and not in_battle:
              
                channel.basic_publish(exchange='', routing_key='fila_eventos', body='EVENTO_BATALHA')
                in_battle = True
            elif battle_val == 0:
                in_battle = False

       
            if modo_lento_ativo:
                time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\nFechando emulador...")
    finally:
        pyboy.stop()
        if connection.is_open:
            connection.close()

if __name__ == '__main__':
    main()