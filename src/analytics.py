import pika
from datetime import datetime
from collections import defaultdict


stats = {
    'passos': 0,
    'batalhas': 0,
    'comandos_total': 0,
    'comandos_movimento': 0,
    'comandos_botao': 0,
    'comandos_velocidade': 0,
    'comandos_audio': 0,
    'comandos_detalhados': defaultdict(int),
    'inicio_sessao': None,
    'fim_sessao': None,
    'historico_passos': []  # [(timestamp, total_passos)]
}

def gerar_relatorio_final():
    # Marcar fim da sessão
    stats['fim_sessao'] = datetime.now()

    timestamp = stats['fim_sessao'].strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"relatorio_{timestamp}.txt"

    # Calcular métricas derivadas
    duracao = None
    passos_por_minuto = 0
    taxa_batalha = 0

    if stats['inicio_sessao']:
        duracao = stats['fim_sessao'] - stats['inicio_sessao']
        minutos = duracao.total_seconds() / 60
        if minutos > 0:
            passos_por_minuto = stats['passos'] / minutos

    if stats['passos'] > 0:
        taxa_batalha = (stats['batalhas'] / stats['passos']) * 100

    # Construir relatório
    relatorio = [
        "="*60,
        "📊 RELATÓRIO FINAL DA SESSÃO - POKÉMON RED EMULATOR",
        "="*60,
        f"📅 Data/Hora Final: {stats['fim_sessao'].strftime('%d/%m/%Y %H:%M:%S')}",
        ""
    ]

    # Seção: Tempo de Sessão
    if duracao:
        horas = int(duracao.total_seconds() // 3600)
        minutos = int((duracao.total_seconds() % 3600) // 60)
        segundos = int(duracao.total_seconds() % 60)
        relatorio.extend([
            "⏱️  TEMPO DE SESSÃO",
            "-" * 60,
            f"   Início:   {stats['inicio_sessao'].strftime('%d/%m/%Y %H:%M:%S')}",
            f"   Término:  {stats['fim_sessao'].strftime('%d/%m/%Y %H:%M:%S')}",
            f"   Duração:  {horas}h {minutos}m {segundos}s",
            ""
        ])

    # Seção: Estatísticas de Movimento
    relatorio.extend([
        "🚶 MOVIMENTO E EXPLORAÇÃO",
        "-" * 60,
        f"   👣 Total de Passos:       {stats['passos']:,}",
        f"   📍 Distância Percorrida:  ~{stats['passos']} tiles",
    ])
    if passos_por_minuto > 0:
        relatorio.append(f"   🏃 Ritmo de Jogo:         {passos_por_minuto:.1f} passos/min")
    relatorio.append("")

    # Seção: Batalhas
    relatorio.extend([
        "⚔️  BATALHAS",
        "-" * 60,
        f"   🎯 Batalhas Iniciadas:    {stats['batalhas']}",
    ])
    if stats['passos'] > 0:
        relatorio.append(f"   📊 Taxa de Encontros:     {taxa_batalha:.2f}% (batalhas/100 passos)")
        if stats['batalhas'] > 0:
            passos_por_batalha = stats['passos'] / stats['batalhas']
            relatorio.append(f"   📈 Média:                 1 batalha a cada {passos_por_batalha:.1f} passos")
    relatorio.append("")

    # Seção: Comandos Executados
    if stats['comandos_total'] > 0:
        relatorio.extend([
            "🎮 COMANDOS EXECUTADOS",
            "-" * 60,
            f"   📊 Total de Comandos:     {stats['comandos_total']:,}",
            f"      • Movimento:          {stats['comandos_movimento']} ({stats['comandos_movimento']/stats['comandos_total']*100:.1f}%)",
            f"      • Botões (A/B):       {stats['comandos_botao']} ({stats['comandos_botao']/stats['comandos_total']*100:.1f}%)",
            f"      • Velocidade:         {stats['comandos_velocidade']} ({stats['comandos_velocidade']/stats['comandos_total']*100:.1f}%)",
            f"      • Áudio:              {stats['comandos_audio']} ({stats['comandos_audio']/stats['comandos_total']*100:.1f}%)",
            ""
        ])

        # Top 5 comandos mais usados
        if stats['comandos_detalhados']:
            top_comandos = sorted(stats['comandos_detalhados'].items(),
                                 key=lambda x: x[1], reverse=True)[:5]
            relatorio.extend([
                "   🏆 Top 5 Comandos Mais Usados:",
            ])
            for i, (cmd, count) in enumerate(top_comandos, 1):
                relatorio.append(f"      {i}. {cmd:8} → {count:4} vezes")
            relatorio.append("")

    # Seção: Performance
    if duracao and stats['comandos_total'] > 0:
        comandos_por_minuto = stats['comandos_total'] / (duracao.total_seconds() / 60)
        relatorio.extend([
            "⚡ PERFORMANCE",
            "-" * 60,
            f"   🎯 Comandos/minuto:       {comandos_por_minuto:.1f}",
            f"   🎮 APM (Actions/min):     {comandos_por_minuto:.0f}",
            ""
        ])

    # Rodapé
    relatorio.extend([
        "="*60,
        "✅ Fim da execução - Sessão encerrada com sucesso!",
        "="*60
    ])

    # Exibir no console
    for linha in relatorio:
        print(linha)

    # Salvar em arquivo TXT
    try:
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write('\n'.join(relatorio))
        print(f"\n💾 Relatório salvo em: {nome_arquivo}")
    except Exception as e:
        print(f"\n⚠️ Erro ao salvar relatório: {e}")

def main():
    # Inicializar tempo de sessão
    stats['inicio_sessao'] = datetime.now()

    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='fila_eventos')
    except Exception as e:
        print(f"❌ Erro ao conectar no RabbitMQ: {e}")
        return

    print("📈 Analytics iniciado! Ouvindo eventos do jogo...")
    print("➡️  Pressione CTRL+C para encerrar e ver o relatório.")

    # Categorização de comandos
    movimentos = {'UP', 'DOWN', 'LEFT', 'RIGHT'}
    botoes = {'A', 'B', 'START', 'SELECT'}
    velocidades = {'TURBO', 'NORMAL', 'LENTO'}
    audio = {'VOL+', 'VOL-', 'MUTE', 'UNMUTE'}

    def callback_eventos(ch, method, _, body):
        evento = body.decode()

        if evento == 'EVENTO_PASSO':
            stats['passos'] += 1
            print(".", end="", flush=True)

        elif evento == 'EVENTO_BATALHA':
            stats['batalhas'] += 1
            print(f"\n[⚔️ BATALHA DETECTADA! Total: {stats['batalhas']}]")

        # Capturar comandos enviados pelo controller (prefixo COMANDO_)
        elif evento.startswith('COMANDO_'):
            comando = evento.replace('COMANDO_', '')

            # Contadores gerais
            stats['comandos_total'] += 1
            stats['comandos_detalhados'][comando] += 1

            # Categorização
            if comando in movimentos:
                stats['comandos_movimento'] += 1
            elif comando in botoes:
                stats['comandos_botao'] += 1
            elif comando in velocidades:
                stats['comandos_velocidade'] += 1
            elif comando in audio:
                stats['comandos_audio'] += 1

        ch.basic_ack(delivery_tag=method.delivery_tag)

    # Consumir apenas fila_eventos
    channel.basic_consume(queue='fila_eventos', on_message_callback=callback_eventos)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        gerar_relatorio_final()
        connection.close()

if __name__ == '__main__':
    main()