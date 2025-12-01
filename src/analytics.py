import pika
import time
import logging
from datetime import datetime
from collections import defaultdict
from app.messaging import RabbitMQClient
from app.config import load_config
from app.health import HealthCheck, HealthCheckMonitor
from app.logging_setup import init_logger

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
    'historico_passos': [],
    'eventos_perdidos': 0
}

def gerar_relatorio_final():

    stats['fim_sessao'] = datetime.now()

    timestamp = stats['fim_sessao'].strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"relatorio_{timestamp}.txt"

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

    relatorio = [
        "="*60,
        "📊 RELATÓRIO FINAL DA SESSÃO - POKÉMON RED EMULATOR",
        "="*60,
        f"📅 Data/Hora Final: {stats['fim_sessao'].strftime('%d/%m/%Y %H:%M:%S')}",
        ""
    ]

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

    relatorio.extend([
        "🚶 MOVIMENTO E EXPLORAÇÃO",
        "-" * 60,
        f"   👣 Total de Passos:       {stats['passos']:,}",
        f"   📍 Distância Percorrida:  ~{stats['passos']} tiles",
    ])
    if passos_por_minuto > 0:
        relatorio.append(f"   🏃 Ritmo de Jogo:         {passos_por_minuto:.1f} passos/min")
    relatorio.append("")

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

        if stats['comandos_detalhados']:
            top_comandos = sorted(stats['comandos_detalhados'].items(),
                                 key=lambda x: x[1], reverse=True)[:5]
            relatorio.extend([
                "   🏆 Top 5 Comandos Mais Usados:",
            ])
            for i, (cmd, count) in enumerate(top_comandos, 1):
                relatorio.append(f"      {i}. {cmd:8} → {count:4} vezes")
            relatorio.append("")

    if duracao and stats['comandos_total'] > 0:
        comandos_por_minuto = stats['comandos_total'] / (duracao.total_seconds() / 60)
        relatorio.extend([
            "⚡ PERFORMANCE",
            "-" * 60,
            f"   🎯 Comandos/minuto:       {comandos_por_minuto:.1f}",
            f"   🎮 APM (Actions/min):     {comandos_por_minuto:.0f}",
            ""
        ])

    relatorio.extend([
        "="*60,
    ])

    if stats['eventos_perdidos'] > 0:
        relatorio.append(f"⚠️  Eventos perdidos (modo degradado): {stats['eventos_perdidos']}")
        relatorio.append("")

    relatorio.extend([
        "✅ Fim da execução - Sessão encerrada com sucesso!",
        "="*60
    ])

    for linha in relatorio:
        print(linha)

    try:
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write('\n'.join(relatorio))
        print(f"\n💾 Relatório salvo em: {nome_arquivo}")
    except Exception as e:
        print(f"\n⚠️ Erro ao salvar relatório: {e}")

def main():

    stats['inicio_sessao'] = datetime.now()

    init_logger()
    logger = logging.getLogger("analytics")

    health = HealthCheck("Analytics")

    config = load_config()

    mq = RabbitMQClient(enable_resilience=True)

    connection_success = mq.connect()

    if connection_success:
        mq.declare_queue(config.queue_events)
        logger.info("✅ RabbitMQ conectado com sucesso")
    else:
        logger.warning("⚠️  Iniciando em MODO DEGRADADO sem RabbitMQ")
        print("\n" + "="*60)
        print("⚠️  AVISO: Analytics em MODO DEGRADADO")
        print("="*60)
        print("Analytics continuará rodando, mas não receberá eventos.")
        print("Dados serão coletados quando o RabbitMQ voltar.")
        print("="*60 + "\n")

    health.register_check("rabbitmq", lambda: mq.is_connected)

    monitor = HealthCheckMonitor(health, interval=30.0)
    monitor.start()

    print("📈 Analytics iniciado! Ouvindo eventos do jogo...")
    print("➡️  Pressione CTRL+C para encerrar e ver o relatório.")

    if mq.is_degraded:
        print("⚠️  Status: MODO DEGRADADO (sem RabbitMQ)")
        print("    Tentará reconectar automaticamente...\n")

    movimentos = {'UP', 'DOWN', 'LEFT', 'RIGHT'}
    botoes = {'A', 'B', 'START', 'SELECT'}
    velocidades = {'TURBO', 'NORMAL', 'LENTO'}
    audio = {'VOL+', 'VOL-', 'MUTE', 'UNMUTE'}

    def callback_eventos(evento: str):
        """Callback para processar eventos do RabbitMQ"""
        if evento == 'EVENTO_PASSO':
            stats['passos'] += 1
            print(".", end="", flush=True)

        elif evento == 'EVENTO_BATALHA':
            stats['batalhas'] += 1
            print(f"\n[⚔️ BATALHA DETECTADA! Total: {stats['batalhas']}]")

        elif evento.startswith('COMANDO_'):
            comando = evento.replace('COMANDO_', '')

            stats['comandos_total'] += 1
            stats['comandos_detalhados'][comando] += 1

            if comando in movimentos:
                stats['comandos_movimento'] += 1
            elif comando in botoes:
                stats['comandos_botao'] += 1
            elif comando in velocidades:
                stats['comandos_velocidade'] += 1
            elif comando in audio:
                stats['comandos_audio'] += 1

    if mq.is_connected:
        mq.consume(config.queue_events, callback_eventos)
        logger.info("✅ Consumidor de eventos ativo")
    else:
        logger.warning("⚠️  Consumidor de eventos inativo (modo degradado)")

    last_reconnect_attempt = time.time()
    reconnect_interval = 30.0

    try:
        while True:
            if mq.is_connected:

                try:
                    mq.process_data_events(time_limit=1)
                except Exception as e:
                    logger.warning(f"Erro ao processar eventos: {e}")
                    stats['eventos_perdidos'] += 1
            else:

                now = time.time()
                if now - last_reconnect_attempt > reconnect_interval:
                    logger.info("🔄 Tentando reconectar ao RabbitMQ...")
                    if mq.connect():
                        mq.declare_queue(config.queue_events)
                        mq.consume(config.queue_events, callback_eventos)
                        logger.info("✅ Reconectado! Analytics voltou ao normal")
                        print("\n[✅ Analytics reconectado ao RabbitMQ!]")
                    last_reconnect_attempt = now

                time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Encerrando Analytics...")
    finally:
        monitor.stop()
        mq.close()
        gerar_relatorio_final()
        logger.info("Analytics encerrado")

if __name__ == '__main__':
    main()