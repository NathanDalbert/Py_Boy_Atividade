import time
import logging
from typing import Dict, Optional, Callable
from datetime import datetime
from threading import Thread, Lock
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.start_time = time.time()
        self._checks: Dict[str, Callable] = {}
        self._status: Dict[str, HealthStatus] = {}
        self._last_check_time: Dict[str, float] = {}
        self._errors: Dict[str, str] = {}
        self._lock = Lock()

    def register_check(self, name: str, check_func: Callable[[], bool]):
        with self._lock:
            self._checks[name] = check_func
            self._status[name] = HealthStatus.HEALTHY
            logger.debug(f"Health check registrado: {name}")

    def check(self, name: str) -> HealthStatus:
        if name not in self._checks:
            return HealthStatus.UNHEALTHY

        try:
            is_healthy = self._checks[name]()
            with self._lock:
                self._last_check_time[name] = time.time()
                if is_healthy:
                    self._status[name] = HealthStatus.HEALTHY
                    if name in self._errors:
                        del self._errors[name]
                else:
                    self._status[name] = HealthStatus.UNHEALTHY
                    self._errors[name] = "Check retornou False"

        except Exception as e:
            with self._lock:
                self._status[name] = HealthStatus.UNHEALTHY
                self._errors[name] = str(e)
                logger.warning(f"Health check falhou [{name}]: {e}")

        return self._status[name]

    def check_all(self) -> HealthStatus:
        if not self._checks:
            return HealthStatus.HEALTHY

        results = [self.check(name) for name in self._checks.keys()]

        healthy_count = sum(1 for s in results if s == HealthStatus.HEALTHY)
        total = len(results)

        if healthy_count == total:
            return HealthStatus.HEALTHY
        elif healthy_count >= total / 2:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY

    def get_status(self) -> Dict[str, any]:
        with self._lock:
            uptime = time.time() - self.start_time
            overall_status = self.check_all()

            status = {
                "service": self.service_name,
                "status": overall_status.value,
                "uptime_seconds": int(uptime),
                "timestamp": datetime.now().isoformat(),
                "checks": {}
            }

            for name in self._checks.keys():
                check_status = self._status.get(name, HealthStatus.UNHEALTHY)
                status["checks"][name] = {
                    "status": check_status.value,
                    "last_check": self._last_check_time.get(name, 0),
                    "error": self._errors.get(name)
                }

            return status

    def print_status(self):
        status = self.get_status()
        uptime_min = status["uptime_seconds"] // 60

        print(f"\n{'='*60}")
        print(f"🏥 Health Status - {status['service']}")
        print(f"{'='*60}")
        print(f"Status Geral: {self._format_status(status['status'])}")
        print(f"Uptime: {uptime_min} minutos")
        print(f"\nComponentes:")

        for name, check in status["checks"].items():
            status_icon = self._get_status_icon(check["status"])
            print(f"  {status_icon} {name:20} - {check['status']}")
            if check.get("error"):
                print(f"      ⚠️  Erro: {check['error']}")

        print(f"{'='*60}\n")

    @staticmethod
    def _format_status(status_str: str) -> str:
        icons = {
            "healthy": "✅ SAUDÁVEL",
            "degraded": "⚠️  DEGRADADO",
            "unhealthy": "❌ CRÍTICO"
        }
        return icons.get(status_str, status_str)

    @staticmethod
    def _get_status_icon(status_str: str) -> str:
        icons = {
            "healthy": "✅",
            "degraded": "⚠️",
            "unhealthy": "❌"
        }
        return icons.get(status_str, "❓")


class HealthCheckMonitor:
    def __init__(self, health_check: HealthCheck, interval: float = 30.0):
        self.health_check = health_check
        self.interval = interval
        self._running = False
        self._thread: Optional[Thread] = None

    def start(self):
        if self._running:
            return

        self._running = True
        self._thread = Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"Health check monitor iniciado (intervalo: {self.interval}s)")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Health check monitor parado")

    def _monitor_loop(self):
        while self._running:
            try:
                status = self.health_check.check_all()
                if status != HealthStatus.HEALTHY:
                    logger.warning(
                        f"Serviço em estado {status.value}: "
                        f"{self.health_check.service_name}"
                    )
            except Exception as e:
                logger.error(f"Erro no health check monitor: {e}")

            time.sleep(self.interval)
