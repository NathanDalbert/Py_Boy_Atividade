
from __future__ import annotations
import pika
import logging
import os
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class RabbitMQClient:
    def __init__(self, host: str = None):
        default_host = os.environ.get("RABBITMQ_HOST", "127.0.0.1")
        self._host = host or default_host
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.channel.Channel] = None

    def connect(self):
        if self._connection and self._connection.is_open:
            return
        try:
            params = pika.ConnectionParameters(
                host=self._host,
                connection_attempts=3,
                retry_delay=2,
                socket_timeout=10,
                blocked_connection_timeout=300
            )
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()
            logger.info("Conectado ao RabbitMQ em %s", self._host)
        except Exception as e:
            logger.error("Falha ao conectar RabbitMQ: %s", e)
            raise

    @property
    def channel(self):
        if not self._channel:
            self.connect()
        return self._channel

    def declare_queue(self, name: str):
        ch = self.channel
        ch.queue_declare(queue=name)
        logger.debug("Fila declarada: %s", name)

    def publish(self, queue: str, body: str):
        ch = self.channel
        ch.basic_publish(exchange="", routing_key=queue, body=body)
        logger.debug("Publicado em %s: %s", queue, body)

    def consume(self, queue: str, callback: Callable[[str], None]):
        ch = self.channel

        def _wrapper(ch_, method, properties, body):
            try:
                msg = body.decode()
                callback(msg)
            finally:
                ch_.basic_ack(delivery_tag=method.delivery_tag)
        ch.basic_qos(prefetch_count=1)
        ch.basic_consume(queue=queue, on_message_callback=_wrapper)
        logger.info("Consumindo fila: %s", queue)

    def process_data_events(self, time_limit=0):
        if self._connection:
            self._connection.process_data_events(time_limit=time_limit)

    def start_consuming(self):
        if self._channel:
            self._channel.start_consuming()

    def stop_consuming(self):
        if self._channel:
            self._channel.stop_consuming()

    def close(self):
        try:
            if self._connection and self._connection.is_open:
                self._connection.close()
                logger.info("Conexão RabbitMQ fechada")
        except Exception as e:
            logger.warning("Erro ao fechar conexão RabbitMQ: %s", e)
