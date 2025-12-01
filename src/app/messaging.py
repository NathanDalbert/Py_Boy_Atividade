from __future__ import annotations
import pika
import logging
import os
import time
from typing import Callable, Optional
from .circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = logging.getLogger(__name__)

class RabbitMQClient:

    def __init__(self, host: str = None, enable_resilience: bool = True):
        default_host = os.environ.get("RABBITMQ_HOST", "127.0.0.1")
        self._host = host or default_host
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.channel.Channel] = None
        self._enable_resilience = enable_resilience

        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30.0,
            expected_exception=Exception,
            name=f"RabbitMQ-{self._host}"
        )

        self._last_connection_attempt = 0
        self._reconnect_delay = 5.0
        self._max_reconnect_delay = 60.0
        self._connection_failures = 0

        self._degraded_mode = False

    def connect(self, max_retries: int = 3):

        if self._connection and self._connection.is_open:
            return True

        if self._enable_resilience and self._circuit_breaker.is_open:
            logger.warning("Circuit breaker ABERTO - não tentando conectar ao RabbitMQ")
            self._degraded_mode = True
            return False

        retry_count = 0
        delay = 2.0

        while retry_count < max_retries:
            try:
                params = pika.ConnectionParameters(
                    host=self._host,
                    connection_attempts=1,
                    retry_delay=1,
                    socket_timeout=5,
                    blocked_connection_timeout=300,
                    heartbeat=60
                )

                if self._enable_resilience:
                    self._connection = self._circuit_breaker.call(
                        pika.BlockingConnection, params
                    )
                else:
                    self._connection = pika.BlockingConnection(params)

                self._channel = self._connection.channel()
                self._degraded_mode = False
                self._connection_failures = 0
                self._reconnect_delay = 5.0

                logger.info("✅ Conectado ao RabbitMQ em %s", self._host)
                return True

            except CircuitBreakerOpenError as e:
                logger.warning(str(e))
                self._degraded_mode = True
                return False

            except Exception as e:
                retry_count += 1
                self._connection_failures += 1

                if retry_count < max_retries:
                    logger.warning(
                        f"Falha ao conectar RabbitMQ (tentativa {retry_count}/{max_retries}): {e}. "
                        f"Tentando novamente em {delay}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 30)
                else:
                    logger.error(f"❌ Falha ao conectar RabbitMQ após {max_retries} tentativas")
                    self._degraded_mode = True
                    return False

        return False

    def _auto_reconnect(self) -> bool:

        if self._connection and self._connection.is_open:
            return True

        now = time.time()
        if now - self._last_connection_attempt < self._reconnect_delay:
            return False

        self._last_connection_attempt = now
        logger.info("🔄 Tentando reconectar ao RabbitMQ...")

        success = self.connect(max_retries=1)

        if not success:

            self._reconnect_delay = min(
                self._reconnect_delay * 1.5,
                self._max_reconnect_delay
            )

        return success

    @property
    def channel(self):

        if not self._channel or not self._connection or not self._connection.is_open:
            if self._enable_resilience:
                self._auto_reconnect()
            else:
                self.connect()
        return self._channel

    @property
    def is_connected(self) -> bool:

        return (
            self._connection is not None and
            self._connection.is_open and
            self._channel is not None
        )

    @property
    def is_degraded(self) -> bool:

        return self._degraded_mode

    def declare_queue(self, name: str, durable: bool = True) -> bool:

        if self._degraded_mode:
            logger.debug(f"Modo degradado: fila '{name}' não declarada")
            return False

        try:
            ch = self.channel
            if ch:
                ch.queue_declare(queue=name, durable=durable)
                logger.debug("Fila declarada: %s", name)
                return True
        except Exception as e:
            logger.warning(f"Erro ao declarar fila {name}: {e}")

        return False

    def publish(self, queue: str, body: str) -> bool:

        if self._degraded_mode:
            logger.debug(f"⚠️  Modo degradado: mensagem descartada [{queue}]: {body}")
            return False

        try:
            ch = self.channel
            if ch:
                ch.basic_publish(
                    exchange="",
                    routing_key=queue,
                    body=body,
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                    )
                )
                logger.debug("Publicado em %s: %s", queue, body)
                return True
        except Exception as e:
            logger.warning(f"Erro ao publicar em {queue}: {e}")
            if self._enable_resilience:
                self._auto_reconnect()

        return False

    def consume(self, queue: str, callback: Callable[[str], None]):

        ch = self.channel
        if not ch:
            logger.error(f"Não foi possível configurar consumidor para {queue}")
            return

        def _wrapper(ch_, method, properties, body):
            try:
                msg = body.decode()
                callback(msg)
            except Exception as e:
                logger.error(f"Erro ao processar mensagem: {e}")
            finally:
                try:
                    ch_.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    logger.warning(f"Erro ao confirmar mensagem: {e}")

        ch.basic_qos(prefetch_count=1)
        ch.basic_consume(queue=queue, on_message_callback=_wrapper)
        logger.info("Consumindo fila: %s", queue)

    def process_data_events(self, time_limit=0):

        if not self.is_connected and self._enable_resilience:
            self._auto_reconnect()

        if self._connection and self._connection.is_open:
            try:
                self._connection.process_data_events(time_limit=time_limit)
            except Exception as e:
                logger.warning(f"Erro ao processar eventos: {e}")
                if self._enable_resilience:
                    self._auto_reconnect()

    def start_consuming(self):

        if self._channel:
            try:
                self._channel.start_consuming()
            except Exception as e:
                logger.error(f"Erro ao consumir mensagens: {e}")
                if self._enable_resilience:
                    self._auto_reconnect()

    def stop_consuming(self):

        if self._channel:
            try:
                self._channel.stop_consuming()
            except Exception as e:
                logger.warning(f"Erro ao parar consumo: {e}")

    def close(self):

        try:
            if self._connection and self._connection.is_open:
                self._connection.close()
                logger.info("Conexão RabbitMQ fechada")
        except Exception as e:
            logger.warning("Erro ao fechar conexão RabbitMQ: %s", e)

    def get_health_status(self) -> dict:

        return {
            "connected": self.is_connected,
            "degraded": self.is_degraded,
            "circuit_breaker_state": self._circuit_breaker.state.value,
            "connection_failures": self._connection_failures,
            "host": self._host
        }
