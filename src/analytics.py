import pika
from datetime import datetime


stats = {
    'passos': 0,
    'batalhas': 0
}

def gerar_relatorio_final():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"relatorio_{timestamp}.txt"

    relatorio = [
        "="*40,
        "📊 RELATÓRIO FINAL DA SESSÃO (TRIO)",
        "="*40,
        f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "",
        f"👣 Total de Passos:      {stats['passos']}",
        f"⚔️  Batalhas Iniciadas:  {stats['batalhas']}",
        "="*40,
        "Fim da execução."
    ]

    for linha in relatorio:
        print(linha)

    try:
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write('\n'.join(relatorio))
        print(f"\n💾 Relatório salvo em: {nome_arquivo}")
    except Exception as e:
        print(f"\n⚠️ Erro ao salvar relatório: {e}")

def main():
  
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='fila_eventos')
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