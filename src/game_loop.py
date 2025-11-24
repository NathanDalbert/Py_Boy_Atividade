import pika
import time
from pyboy import PyBoy
from pyboy.utils import WindowEvent

ROM_PATH = "roms/pokemon_red.gb"

# Variável global para controlar se o modo lento está ativo
modo_lento_ativo = False

def main():
    global modo_lento_ativo
    
    print("Iniciando o Game Boy...")
    # Define volume baixo (20) na inicialização para não incomodar
    pyboy = PyBoy(ROM_PATH, window_type="SDL2", sound=True, sound_volume=20)
    pyboy.set_emulation_speed(1) 

    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='fila_comandos')

    print(" [*] Aguardando comandos...")

    def callback(ch, method, properties, body):
        global modo_lento_ativo
        comando = body.decode().upper()
        print(f" [!] Recebido: {comando}")
        
        # --- LÓGICA DE CONFIGURAÇÃO ---
        if comando == 'TURBO':
            print("🚀 MODO TURBO ATIVADO!")
            modo_lento_ativo = False
            pyboy.set_emulation_speed(0) # 0 = Velocidade máxima (ilimitada)
            
        elif comando == 'NORMAL':
            print("▶️ MODO NORMAL ATIVADO.")
            modo_lento_ativo = False
            pyboy.set_emulation_speed(1) # 1 = Tempo real
            
        elif comando == 'LENTO':
            print("🐢 MODO LENTO ATIVADO.")
            modo_lento_ativo = True
            pyboy.set_emulation_speed(1) # Mantém speed 1, mas vamos frear no loop
            
        # --- LÓGICA DE BOTÕES ---
        else:
            mapa_comandos = {
                'UP': WindowEvent.PRESS_ARROW_UP,
                'DOWN': WindowEvent.PRESS_ARROW_DOWN,
                'LEFT': WindowEvent.PRESS_ARROW_LEFT,
                'RIGHT': WindowEvent.PRESS_ARROW_RIGHT,
                'A': WindowEvent.PRESS_BUTTON_A,
                'B': WindowEvent.PRESS_BUTTON_B,
                'START': WindowEvent.PRESS_BUTTON_START,
                'SELECT': WindowEvent.PRESS_BUTTON_SELECT
            }
            
            # Mapeamento de soltura (Release)
            mapa_release = {
                'UP': WindowEvent.RELEASE_ARROW_UP,
                'DOWN': WindowEvent.RELEASE_ARROW_DOWN,
                'LEFT': WindowEvent.RELEASE_ARROW_LEFT,
                'RIGHT': WindowEvent.RELEASE_ARROW_RIGHT,
                'A': WindowEvent.RELEASE_BUTTON_A,
                'B': WindowEvent.RELEASE_BUTTON_B,
                'START': WindowEvent.RELEASE_BUTTON_START,
                'SELECT': WindowEvent.RELEASE_BUTTON_SELECT
            }

            if comando in mapa_comandos:
                pyboy.send_input(mapa_comandos[comando])
                for _ in range(15): pyboy.tick() # Segura
                pyboy.send_input(mapa_release[comando]) # Solta
                for _ in range(15): pyboy.tick() # Espera

        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='fila_comandos', on_message_callback=callback)

    try:
        while pyboy.tick():
            connection.process_data_events(time_limit=0)
            
            # Se o modo lento estiver ligado, forçamos uma pausa a cada frame
            if modo_lento_ativo:
                time.sleep(0.02) 
            
    except KeyboardInterrupt:
        print("Fechando...")
    finally:
        pyboy.stop()
        connection.close()

if __name__ == '__main__':
    main()