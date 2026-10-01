"""Keyboard stand-in for BLE when MOCK_BLE=1."""

from __future__ import annotations

import pygame

from players import PlayerManager


class MockBleInput:
    """P1: Space jump, Down duck, A/D sidestep, B/G hero. J = hot-join P2."""

    def __init__(self, players: PlayerManager, auto_connect_p0: bool = True) -> None:
        self.players = players
        self._duck_keys_down: set[int] = set()
        if auto_connect_p0:
            self.players.connect("MOCK-P0", hero_girl=False)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._on_key_down(event.key)
        elif event.type == pygame.KEYUP:
            self._on_key_up(event.key)

    def _on_key_down(self, key: int) -> None:
        if key == pygame.K_j and self.players.active_count() < 2:
            self.players.connect("MOCK-P1", hero_girl=True)
            return

        slot = self._slot()

        if key == pygame.K_SPACE:
            self.players.pulse_jump(slot)
        elif key == pygame.K_DOWN:
            self._duck_keys_down.add(key)
            self.players.set_duck_held(slot, True)
        elif key == pygame.K_a:
            self.players.pulse_step_left(slot)
        elif key == pygame.K_d:
            self.players.pulse_step_right(slot)
        elif key == pygame.K_b:
            self.players.set_hero_girl(slot, False)
        elif key == pygame.K_g:
            self.players.set_hero_girl(slot, True)

    def _slot(self) -> int:
        if self.players.active_count() >= 2 and (pygame.key.get_mods() & pygame.KMOD_SHIFT):
            return 1
        return 0

    def _on_key_up(self, key: int) -> None:
        if key == pygame.K_DOWN:
            self._duck_keys_down.discard(key)
            if not self._duck_keys_down:
                self.players.set_duck_held(self._slot(), False)
