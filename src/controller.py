import sys
from app.messaging import RabbitMQClient
from app.config import load_config
from app.logging_setup import init_logger
import logging

def enviar_comandos():
    init_logger()
    logger = logging.getLogger("controller")
    config = load_config()
    mq = RabbitMQClient()
    try:
        mq.connect()
        mq.declare_queue(config.queue_commands)
    except Exception:
        logger.error("Não foi possível conectar ao RabbitMQ. Verifique se o serviço está ativo.")
        return

    print("\n🎮 Controlador Iniciado!")
    print("="*40)
    print("🕹️  MOVIMENTO:  UP, DOWN, LEFT, RIGHT")
    print("🔴 BOTÕES:     A, B, START, SELECT")
    print("⚙️  VELOCIDADE: TURBO, NORMAL, LENTO")
    print("🔊 ÁUDIO:      VOL+, VOL-, MUTE")
    print("="*40)
    print("Digite 'SAIR' para encerrar.\n")

    while True:
        try:
            comando = input("Comando >> ").strip().upper()

            if comando == 'SAIR':
                break
            
            comandos_validos = [
                'UP', 'DOWN', 'LEFT', 'RIGHT', 'A', 'B', 'START', 'SELECT',
                'TURBO', 'NORMAL', 'LENTO',
                'MUTE', 'UNMUTE', 'VOL+', 'VOL-'
            ]

            if comando in comandos_validos:

                mq.publish(config.queue_commands, comando)
                logger.info("Comando enviado: %s", comando)
            else:
                if comando:
                    print(f" ⚠️  Comando desconhecido.")
        
        except KeyboardInterrupt:
            break

    print("\nEncerrando controlador...")
    mq.close()

if __name__ == '__main__':
    enviar_comandos()