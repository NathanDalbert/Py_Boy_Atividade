import os
import pytest
from app.config import load_config

def test_defaults():
    cfg = load_config()
    assert cfg.rom_path == "roms/pokemon_red.gb"
    assert cfg.queue_commands == "fila_comandos"
    assert cfg.queue_events == "fila_eventos"

@pytest.mark.parametrize(
    "rom,cmd_q,evt_q",
    [
        ("custom.gb","q_cmd","q_evt"),
        ("another.gb","commands","events"),
    ]
)
def test_overrides(rom, cmd_q, evt_q):
    os.environ["PYBOY_ROM"] = rom
    os.environ["QUEUE_COMMANDS"] = cmd_q
    os.environ["QUEUE_EVENTS"] = evt_q
    cfg = load_config()
    assert cfg.rom_path == rom
    assert cfg.queue_commands == cmd_q
    assert cfg.queue_events == evt_q
