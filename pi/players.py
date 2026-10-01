"""Up to two players; BLE or mock feeds motion flags."""

from __future__ import annotations

import time
from typing import Optional

PULSE_HOLD_S = 0.15

from input_events import FrameInput, Hero, PlayerState, SessionEvent, SessionEventType
from motion_profiles import MotionFlags, MotionProfile, filter_flags


class PlayerManager:
    MAX_SLOTS = 2

    def __init__(self) -> None:
        self._slots: list[Optional[PlayerState]] = [None, None]
        self._session_events: list[SessionEvent] = []
        self._mac_to_slot: dict[str, int] = {}

    def active_count(self) -> int:
        return sum(1 for s in self._slots if s is not None)

    def slot_mac(self, slot: int) -> str:
        p = self._slots[slot]
        return p.mac if p else ""

    def hero_girl(self, slot: int) -> bool:
        p = self._slots[slot]
        return bool(p and p.hero_girl)

    def consume_session_events(self) -> list[SessionEvent]:
        out = self._session_events[:]
        self._session_events.clear()
        return out

    def _emit(self, ev: SessionEvent) -> None:
        self._session_events.append(ev)

    def _find_slot_for_mac(self, mac: str) -> Optional[int]:
        if mac in self._mac_to_slot:
            idx = self._mac_to_slot[mac]
            if self._slots[idx] is not None:
                return idx
        for i, s in enumerate(self._slots):
            if s is None:
                return i
        return None

    def connect(self, mac: str, hero_girl: bool = False) -> Optional[int]:
        if mac in self._mac_to_slot and self._slots[self._mac_to_slot[mac]] is not None:
            slot = self._mac_to_slot[mac]
            self._slots[slot].hero_girl = hero_girl  # type: ignore[union-attr]
            return slot
        slot = self._find_slot_for_mac(mac)
        if slot is None:
            return None
        self._slots[slot] = PlayerState(mac=mac, hero_girl=hero_girl)
        self._mac_to_slot[mac] = slot
        self._emit(SessionEvent(SessionEventType.PLAYER_JOINED, slot, mac))
        self._sync_mode_event()
        return slot

    def disconnect(self, mac: str) -> None:
        if mac not in self._mac_to_slot:
            return
        slot = self._mac_to_slot.pop(mac)
        if self._slots[slot] is not None:
            self._slots[slot] = None
            self._emit(SessionEvent(SessionEventType.PLAYER_LEFT, slot, mac))
            self._sync_mode_event()

    def disconnect_slot(self, slot: int) -> None:
        p = self._slots[slot]
        if p is None:
            return
        self.disconnect(p.mac)

    def _sync_mode_event(self) -> None:
        n = self.active_count()
        if n >= 2:
            self._emit(SessionEvent(SessionEventType.MODE_2P))
        elif n == 1:
            self._emit(SessionEvent(SessionEventType.MODE_1P))

    def apply_flags(self, slot: int, raw_flags: int) -> None:
        p = self._slots[slot]
        if p is None:
            return
        flags = raw_flags & 0xFF
        motion = flags & (
            MotionFlags.JUMP | MotionFlags.DUCK | MotionFlags.STEP_L | MotionFlags.STEP_R
        )
        if not motion or (flags & MotionFlags.HERO_GIRL):
            p.hero_girl = bool(flags & MotionFlags.HERO_GIRL)
        pulses = flags & (
            MotionFlags.JUMP | MotionFlags.STEP_L | MotionFlags.STEP_R
        )
        if flags & MotionFlags.DUCK:
            p.duck_held = True
        elif not pulses:
            p.duck_held = bool(flags & MotionFlags.DUCK)
        now = time.monotonic()
        if flags & MotionFlags.JUMP:
            p.jump_pulse = True
            p.jump_until = now + PULSE_HOLD_S
        if flags & MotionFlags.STEP_L:
            p.step_l_pulse = True
            p.step_l_until = now + PULSE_HOLD_S
        if flags & MotionFlags.STEP_R:
            p.step_r_pulse = True
            p.step_r_until = now + PULSE_HOLD_S

    def set_hero_girl(self, slot: int, girl: bool) -> None:
        p = self._slots[slot]
        if p:
            p.hero_girl = girl

    def pulse_jump(self, slot: int) -> None:
        if self._slots[slot]:
            self._slots[slot].jump_pulse = True  # type: ignore[union-attr]

    def pulse_step_left(self, slot: int) -> None:
        if self._slots[slot]:
            self._slots[slot].step_l_pulse = True  # type: ignore[union-attr]

    def pulse_step_right(self, slot: int) -> None:
        if self._slots[slot]:
            self._slots[slot].step_r_pulse = True  # type: ignore[union-attr]

    def set_duck_held(self, slot: int, held: bool) -> None:
        if self._slots[slot]:
            self._slots[slot].duck_held = held  # type: ignore[union-attr]

    def consume_frame_inputs(self, profile: MotionProfile) -> list[FrameInput]:
        out: list[FrameInput] = []
        for slot in range(self.MAX_SLOTS):
            p = self._slots[slot]
            if p is None:
                out.append(FrameInput(connected=False))
                continue
            now = time.monotonic()
            raw = 0
            if p.jump_pulse or now < p.jump_until:
                raw |= MotionFlags.JUMP
            if p.duck_held:
                raw |= MotionFlags.DUCK
            if p.step_l_pulse or now < p.step_l_until:
                raw |= MotionFlags.STEP_L
            if p.step_r_pulse or now < p.step_r_until:
                raw |= MotionFlags.STEP_R
            if p.hero_girl:
                raw |= MotionFlags.HERO_GIRL
            filtered = filter_flags(profile, raw)
            fi = FrameInput(
                connected=True,
                hero=Hero.GIRL if (filtered & MotionFlags.HERO_GIRL) else Hero.BOY,
                jump=bool(filtered & MotionFlags.JUMP),
                duck_held=bool(filtered & MotionFlags.DUCK),
                step_left=bool(filtered & MotionFlags.STEP_L),
                step_right=bool(filtered & MotionFlags.STEP_R),
            )
            out.append(fi)
            p.jump_pulse = False
            p.step_l_pulse = False
            p.step_r_pulse = False
        return out
