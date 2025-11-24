import pika
import sys

def enviar_comandos():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='fila_comandos')

    print("🎮 Controlador Iniciado!")
    print("Botões: UP, DOWN, LEFT, RIGHT, A, B, START, SELECT")
    print("Configurações: TURBO, NORMAL, LENTO")
    print("Digite 'SAIR' para encerrar.")

    while True:
        comando = input(">> ").strip().upper()

        if comando == 'SAIR':
            break
        
        # Lista expandida com comandos de configuração
        comandos_validos = [
            'UP', 'DOWN', 'LEFT', 'RIGHT', 'A', 'B', 'START', 'SELECT', # Jogo
            'TURBO', 'NORMAL', 'LENTO' # Configurações
        ]

        if comando in comandos_validos:
            channel.basic_publish(exchange='',
                                  routing_key='fila_comandos',
                                  body=comando)
            print(f" [x] Enviado: '{comando}'")
        else:
            print(f" ⚠️  Comando inválido. Tente: {comandos_validos}")

    connection.close()

if __name__ == '__main__':
    try:
        enviar_comandos()
    except KeyboardInterrupt:
        sys.exit(0)