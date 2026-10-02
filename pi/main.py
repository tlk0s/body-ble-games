#!/usr/bin/env python3
"""Body BLE Games launcher."""

from __future__ import annotations

import os
import sys

try:
    import pygame
except ModuleNotFoundError:
    print("pygame not found for this Python:", sys.executable, file=sys.stderr)
    print("Use the project venv:  cd pi && ./run", file=sys.stderr)
    print("Or:  .venv/bin/pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

from ble_manager import BleManager
from display import create_game_surface, present
from mock_input import MockBleInput
from motion_profiles import GAME_PROFILE, MotionProfile
from players import PlayerManager

WIDTH, HEIGHT = 640, 360
FPS = max(15, min(60, int(os.environ.get("BODY_FPS", "60"))))

MOCK_BLE = os.environ.get("MOCK_BLE", "1") not in ("0", "false", "False")
# Optional kiosk: skip menu — BODY_GAME=blob_jump or lane_race
BODY_GAME = os.environ.get("BODY_GAME", "").strip()
BODY_FULLSCREEN = os.environ.get("BODY_FULLSCREEN", "0") not in ("0", "false", "False")
LANE_RACE_SELECTABLE = False  # show on menu, jump-only select for now


def create_screen() -> pygame.Surface:
    return create_game_surface(WIDTH, HEIGHT, BODY_FULLSCREEN)


def draw_centered(screen: pygame.Surface, lines: list[str], y_start: int, color=(240, 240, 240)) -> None:
    font = pygame.font.SysFont(None, 26)
    for i, text in enumerate(lines):
        surf = font.render(text, True, color)
        rect = surf.get_rect(center=(screen.get_width() // 2, y_start + i * 32))
        screen.blit(surf, rect)


def run_game_select(
    screen: pygame.Surface,
    players: PlayerManager,
    mock: MockBleInput | None,
    ble: BleManager | None,
) -> str | None:
    """Keyboard 1/2 in dev; belt Jump = BlobJump, Sidestep = Lane on Pi."""
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 22)
    while True:
        clock.tick(FPS)
        if ble is not None:
            ble.poll()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None
            if mock is not None:
                mock.handle_event(event)
            if event.type == pygame.KEYDOWN and MOCK_BLE:
                if event.key == pygame.K_1:
                    return "blob_jump"
                if event.key == pygame.K_2 and LANE_RACE_SELECTABLE:
                    return "lane_race"

        if players.active_count() >= 1:
            inputs = players.consume_frame_inputs(MotionProfile.TEST_ALL)
            for inp in inputs:
                if not inp.connected:
                    continue
                if inp.jump:
                    return "blob_jump"
                if LANE_RACE_SELECTABLE and (inp.step_left or inp.step_right):
                    return "lane_race"

        screen.fill((20, 24, 32))
        cx = screen.get_width() // 2
        gray = (120, 120, 130)

        def menu_line(text: str, y: int, color=(240, 240, 240)) -> None:
            surf = font.render(text, True, color)
            screen.blit(surf, surf.get_rect(center=(cx, y)))

        if MOCK_BLE:
            menu_line("Body BLE Games", 60)
            menu_line("1 — BlobJump  (Jump)", 96)
            menu_line("2 — Lane Race  (coming soon)", 128, gray)
        elif players.active_count() < 1:
            msg = ble.status if ble and ble.status else "Waiting for controller…"
            if ble and ble.last_error:
                msg = ble.last_error
            draw_centered(
                screen,
                ["Body BLE Games", "", msg, "", "Power on a belt remote"],
                80,
                color=(255, 220, 120),
            )
        else:
            menu_line("Choose a game", 64)
            menu_line("Jump  →  BlobJump", 104)
            menu_line("Lane Race  (coming soon)", 136, gray)
        if ble is not None and players.active_count() >= 1:
            hint = font.render(f"BLE 0x{ble.last_flags:02X}", True, (140, 140, 140))
            screen.blit(hint, hint.get_rect(center=(screen.get_width() // 2, HEIGHT - 24)))
        present(screen)


def load_game(game_id: str, players: PlayerManager, screen: pygame.Surface):
    if game_id in ("blob_jump", "dino_run"):  # dino_run: legacy id
        from games.blob_jump import BlobJumpGame

        return BlobJumpGame(players, screen)
    if game_id == "lane_race":
        from games.lane_race import LaneRaceGame

        return LaneRaceGame(players, screen)
    raise ValueError(game_id)


def main() -> int:
    pygame.init()
    pygame.display.set_caption("Body BLE Games")
    screen = create_screen()

    players = PlayerManager()
    mock: MockBleInput | None = None
    ble: BleManager | None = None

    if MOCK_BLE:
        mock = MockBleInput(players, auto_connect_p0=True)
    else:
        ble = BleManager(players)
        ble.start()

    while True:
        if BODY_GAME in GAME_PROFILE:
            game_id = BODY_GAME
        else:
            game_id = run_game_select(screen, players, mock, ble)
        if not game_id:
            break

        game = load_game(game_id, players, screen)
        _ = GAME_PROFILE.get(game_id)
        when_done = game.run(mock_input=mock, ble=ble)
        if when_done == "quit":
            break
        # "menu" → loop back to game select (jump / sidestep)

    if ble:
        ble.stop()
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
