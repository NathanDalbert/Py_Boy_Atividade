""""""
from __future__ import annotations
import os
import sys
from typing import Optional

try:
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    import comtypes
except Exception:
    AudioUtilities = None
    ISimpleAudioVolume = None


class VolumeService:
    def __init__(self, initial_percent: int = 50):
        self._current_percent = max(0, min(100, initial_percent))
        
        self._last_non_zero = self._current_percent / 100.0 if self._current_percent > 0 else 0.0
        self._iface = None
        self._attempts = 0
        self._max_attempts = 5
        self._acquire_interface(initial_sync=True)
        self._debug = os.getenv("PYBOY_VOLUME_DEBUG", "0") in {"1", "true", "TRUE"}
        if self._debug:
            print(f"[VolumeService] Inicializado (pycaw {'OK' if AudioUtilities else 'INDISPONÍVEL'})", file=sys.stderr)

    def _get_interface(self):
        if AudioUtilities is None:
            return None
        try:
            pid = os.getpid()
            for session in AudioUtilities.GetAllSessions():
                proc = session.Process
                if proc and proc.pid == pid:
                    return session._ctl.QueryInterface(ISimpleAudioVolume)
        except Exception:
            return None
        return None

    def _acquire_interface(self, initial_sync: bool = False):
        if self._iface is not None:
            return
        if self._attempts >= self._max_attempts:
            if os.getenv("PYBOY_VOLUME_DEBUG", "0") in {"1", "true", "TRUE"}:
                print(f"[VolumeService] Limite de tentativas atingido ({self._attempts})", file=sys.stderr)
            return
        self._attempts += 1
        iface = self._get_interface()
        if iface:
            self._iface = iface
            if initial_sync:
                try:
                    self._iface.SetMasterVolume(self._current_percent / 100.0, None)
                except Exception:
                    self._iface = None
            if os.getenv("PYBOY_VOLUME_DEBUG", "0") in {"1", "true", "TRUE"}:
                print(f"[VolumeService] Interface pycaw obtida na tentativa {self._attempts}", file=sys.stderr)
        else:
            if os.getenv("PYBOY_VOLUME_DEBUG", "0") in {"1", "true", "TRUE"}:
                print(f"[VolumeService] Falha em obter interface (tentativa {self._attempts})", file=sys.stderr)

    def is_available(self) -> bool:
        return self._iface is not None

    def get_percent(self) -> int:
        return self._current_percent

    def set_percent(self, percent: int):
        
        if self._iface is None:
            self._acquire_interface()
        percent = max(0, min(100, percent))
        self._current_percent = percent
        if percent > 0:
            self._last_non_zero = percent / 100.0
        if self._iface:
            try:
                self._iface.SetMasterVolume(percent / 100.0, None)
            except Exception:
                pass
        elif self._debug:
            print(f"[VolumeService] set_percent lógico (sem interface) -> {percent}%", file=sys.stderr)

    def increase(self, step: int = 10):
        self.set_percent(self._current_percent + step)
        return self._current_percent

    def decrease(self, step: int = 10):
        self.set_percent(self._current_percent - step)
        return self._current_percent

    def mute(self):
        if self._iface is None:
            self._acquire_interface()
        if self._current_percent > 0:
            self._last_non_zero = self._current_percent / 100.0
        if self._iface:
            try:
                self._iface.SetMasterVolume(0.0, None)
            except Exception:
                pass
        self._current_percent = 0
        if self._debug and self._iface is None:
            print("[VolumeService] mute lógico (sem interface)", file=sys.stderr)

    def unmute(self, default_percent: int = 50):
        if self._iface is None:
            self._acquire_interface()
        target = self._last_non_zero if self._last_non_zero > 0.01 else default_percent / 100.0
        percent = int(target * 100)
        self._current_percent = percent
        if self._iface:
            try:
                self._iface.SetMasterVolume(target, None)
            except Exception:
                pass
        if percent > 0:
            self._last_non_zero = target
        if self._debug and self._iface is None:
            print(f"[VolumeService] unmute lógico -> {percent}% (sem interface)", file=sys.stderr)
        return percent
