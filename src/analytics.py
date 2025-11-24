import pika
import sys


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
  
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='fila_eventos') # Escuta a fila de saída
    except Exception as e:
        print(f"❌ Erro ao conectar no RabbitMQ: {e}")
        return

    print("📈 Analytics iniciado! Ouvindo eventos do jogo...")
    print("➡️  Pressione CTRL+C para encerrar e ver o relatório.")

    def callback(ch, method, properties, body):
        evento = body.decode()
        
        if evento == 'EVENTO_PASSO':
            stats['passos'] += 1
            print(".", end="", flush=True)
            
        elif evento == 'EVENTO_BATALHA':
            stats['batalhas'] += 1
            print(f"\n[⚔️ BATALHA DETECTADA! Total: {stats['batalhas']}]")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue='fila_eventos', on_message_callback=callback)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
      
        channel.stop_consuming()
        gerar_relatorio_final()
        connection.close()

if __name__ == '__main__':
    main()