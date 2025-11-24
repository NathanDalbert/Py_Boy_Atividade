import pika
import sys

def enviar_comandos():
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='fila_comandos')
    except pika.exceptions.AMQPConnectionError:
        print("❌ Erro: Não foi possível conectar ao RabbitMQ.")
        print("Certifique-se de que o Docker está rodando: 'docker start rabbitmq-trio'")
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
       
                channel.basic_publish(exchange='',
                                      routing_key='fila_comandos',
                                      body=comando)
                print(f" [x] Enviado: '{comando}'")
            else:
                if comando:
                    print(f" ⚠️  Comando desconhecido.")
        
        except KeyboardInterrupt:
            break

    print("\nEncerrando controlador...")
    connection.close()

if __name__ == '__main__':
    enviar_comandos()