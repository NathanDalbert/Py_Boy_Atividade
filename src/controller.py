import sys
import time
from app.messaging import RabbitMQClient
from app.config import load_config
from app.logging_setup import init_logger
from app.health import HealthCheck, HealthCheckMonitor
import logging

def enviar_comandos():
    init_logger()
    logger = logging.getLogger("controller")
    config = load_config()

    health = HealthCheck("Controller")

    mq = RabbitMQClient(enable_resilience=True)

    connection_success = mq.connect()

    if connection_success:
        mq.declare_queue(config.queue_commands)
        mq.declare_queue(config.queue_events)
        logger.info("✅ RabbitMQ conectado com sucesso")
    else:
        logger.warning("⚠️  Iniciando em MODO DEGRADADO sem RabbitMQ")
        print("\n" + "="*60)
        print("⚠️  AVISO: RabbitMQ não está disponível")
        print("="*60)
        print("O controlador continuará tentando enviar comandos.")
        print("Os comandos serão processados quando o RabbitMQ voltar.")
        print("="*60 + "\n")

    health.register_check("rabbitmq", lambda: mq.is_connected)

    monitor = HealthCheckMonitor(health, interval=30.0)
    monitor.start()

    print("\n🎮 Controlador Iniciado!")
    print("="*40)
    print("🕹️  MOVIMENTO:  UP, DOWN, LEFT, RIGHT")
    print("🔴 BOTÕES:     A, B, START, SELECT")
    print("⚙️  VELOCIDADE: TURBO, NORMAL, LENTO")
    print("🔊 ÁUDIO:      VOL+, VOL-, MUTE, UNMUTE")
    print("="*40)
    print("Digite 'SAIR' para encerrar.\n")

    if mq.is_degraded:
        print("⚠️  Status: MODO DEGRADADO (sem RabbitMQ)")
        print("    Tentará reconectar automaticamente...\n")

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

                cmd_sent = mq.publish(config.queue_commands, comando)
                evt_sent = mq.publish(config.queue_events, f'COMANDO_{comando}')

                if cmd_sent and evt_sent:
                    logger.info("✅ Comando enviado: %s", comando)
                elif not cmd_sent or not evt_sent:
                    print("⚠️  Comando não enviado - RabbitMQ indisponível")
                    logger.warning("Comando perdido em modo degradado: %s", comando)

                if not mq.is_connected:
                    print("   (Tentando reconectar ao RabbitMQ...)")

            else:
                if comando:
                    print(f" ⚠️  Comando desconhecido.")

        except KeyboardInterrupt:
            break

    print("\nEncerrando controlador...")
    monitor.stop()
    health.print_status()
    mq.close()
    logger.info("Controller encerrado")

if __name__ == '__main__':
    enviar_comandos()