import os
from dataclasses import dataclass

@dataclass
class AppConfig:
    rom_path: str
    queue_commands: str
    queue_events: str


def load_config() -> AppConfig:
    rom = os.environ.get("PYBOY_ROM", "roms/pokemon_red.gb")
    q_cmd = os.environ.get("QUEUE_COMMANDS", "fila_comandos")
    q_evt = os.environ.get("QUEUE_EVENTS", "fila_eventos")
    return AppConfig(rom_path=rom, queue_commands=q_cmd, queue_events=q_evt)
