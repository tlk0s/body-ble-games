"""Common game loop helpers."""

from __future__ import annotations

import time

import pygame

from input_events import FrameInput, SessionEventType
from motion_profiles import MotionProfile
from players import PlayerManager


class BaseGame:
    profile: MotionProfile = MotionProfile.TEST_ALL
    title: str = "Game"

    def __init__(self, players: PlayerManager, screen: pygame.Surface) -> None:
        self.players = players
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        self.font = pygame.font.SysFont(None, 22)
        self.font_lg = pygame.font.SysFont(None, 28)
        self.exit_to: str = "menu"

    def handle_event(self, event: pygame.event.Event, ble=None) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.running = False
            self.exit_to = "menu" if ble is not None else "quit"

    def update(self, inputs: list[FrameInput], dt: float) -> None:
        raise NotImplementedError

    def draw(self, inputs: list[FrameInput]) -> None:
        raise NotImplementedError

    def draw_debug_hud(self, inputs: list[FrameInput], y: int = 8, ble=None) -> None:
        for slot, inp in enumerate(inputs):
            if not inp.connected:
                continue
            from input_events import Hero

            hero = "girl" if inp.hero == Hero.GIRL else "boy"
            bits = []
            if inp.jump:
                bits.append("JUMP")
            if inp.duck_held:
                bits.append("DUCK")
            if inp.step_left:
                bits.append("L")
            if inp.step_right:
                bits.append("R")
            ev = " ".join(bits) if bits else "—"
            color = (255, 120, 180) if inp.hero == Hero.GIRL else (100, 160, 255)
            line = self.font.render(f"P{slot + 1} {hero}: {ev}", True, color)
            self.screen.blit(line, (8, y + slot * 22))
        if ble is not None:
            dbg = self.font.render(
                f"BLE last=0x{ble.last_flags:02X} n={ble.notify_count}", True, (180, 180, 180)
            )
            self.screen.blit(dbg, (8, y + 48))

    def on_player_left(self, slot: int) -> None:
        """Override to reset per-player state when a controller drops."""

    def _draw_exit_hint(self, ble=None) -> None:
        if ble is None:
            return
        hint_font = pygame.font.SysFont(None, 16)
        s = hint_font.render("Power off remotes to return to menu", True, (95, 100, 110))
        self.screen.blit(s, s.get_rect(midtop=(self.screen.get_width() // 2, 5)))

    def run(self, mock_input=None, ble=None) -> str:
        empty_after_play_s = 2.5
        had_player = self.players.active_count() > 0
        no_player_since: float | None = None

        while self.running:
            dt = self.clock.tick(60) / 1000.0
            if ble is not None:
                ble.poll()
            for ev in self.players.consume_session_events():
                if ev.kind == SessionEventType.PLAYER_LEFT:
                    self.on_player_left(ev.slot)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.exit_to = "quit"
                elif mock_input is not None:
                    mock_input.handle_event(event)
                self.handle_event(event, ble=ble)

            inputs = self.players.consume_frame_inputs(self.profile)

            if self.players.active_count() > 0:
                had_player = True
                no_player_since = None
            elif had_player and ble is not None:
                now = time.monotonic()
                if no_player_since is None:
                    no_player_since = now
                elif now - no_player_since >= empty_after_play_s:
                    self.running = False
                    self.exit_to = "menu"

            self.update(inputs, dt)
            self.screen.fill((30, 30, 40))
            self.draw(inputs)
            self.draw_debug_hud(inputs, y=self.screen.get_height() - 76, ble=ble)
            self._draw_exit_hint(ble)
            pygame.display.flip()

        return self.exit_to
