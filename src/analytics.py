import sys
from app.messaging import RabbitMQClient
from app.config import load_config
from app.logging_setup import init_logger
import logging


stats = {
    'passos': 0,
    'batalhas': 0
}

def gerar_relatorio_final():
    print("\n" + "="*40)
    print("📊 RELATÓRIO FINAL DA SESSÃO (TRIO)")
    print("="*40)
    print(f"👣 Total de Passos:      {stats['passos']}")
    print(f"⚔️  Batalhas Iniciadas:  {stats['batalhas']}")
    print("="*40)
    print("Fim da execução.")

def main():
    
    init_logger()
    logger = logging.getLogger("analytics")
    config = load_config()
    mq = RabbitMQClient()
    try:
        mq.connect()
        mq.declare_queue(config.queue_events)
    except Exception as e:
        logger.error("Erro ao conectar no RabbitMQ: %s", e)
        return

    logger.info("Analytics iniciado. Aguardando eventos...")

    def on_event(evento: str):
        if evento == 'EVENTO_PASSO':
            stats['passos'] += 1
            print(".", end="", flush=True)
        elif evento == 'EVENTO_BATALHA':
            stats['batalhas'] += 1
            print(f"\n[⚔️ BATALHA DETECTADA! Total: {stats['batalhas']}]")
    mq.consume(config.queue_events, on_event)

    try:
        mq.start_consuming()
    except KeyboardInterrupt:
        mq.stop_consuming()
        gerar_relatorio_final()
        mq.close()

if __name__ == '__main__':
    main()