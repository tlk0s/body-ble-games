"""Minimal Lane Race playground (sidestep). Full game in Phase 2."""

from __future__ import annotations

import pygame

from games.base_game import BaseGame
from input_events import FrameInput, Hero
from motion_profiles import MotionProfile


class LaneRaceGame(BaseGame):
    profile = MotionProfile.LANE
    title = "Lane Race"

    LANES = (160, 320, 480)

    def __init__(self, players, screen) -> None:
        super().__init__(players, screen)
        self.lane_idx = [1, 1]

    def on_player_left(self, slot: int) -> None:
        if 0 <= slot < 2:
            self.lane_idx[slot] = 1

    def update(self, inputs: list[FrameInput], dt: float) -> None:
        for slot, inp in enumerate(inputs):
            if not inp.connected:
                continue
            if inp.step_left and self.lane_idx[slot] > 0:
                self.lane_idx[slot] -= 1
            if inp.step_right and self.lane_idx[slot] < 2:
                self.lane_idx[slot] += 1

    def draw(self, inputs: list[FrameInput]) -> None:
        w, h = self.screen.get_size()
        self.screen.fill((40, 40, 50))
        for x in self.LANES:
            pygame.draw.line(self.screen, (80, 80, 90), (x, 0), (x, h), 2)

        for slot, inp in enumerate(inputs):
            if not inp.connected:
                continue
            cx = self.LANES[self.lane_idx[slot]]
            cy = 200 + slot * 80
            color = (255, 105, 180) if inp.hero == Hero.GIRL else (60, 120, 220)
            pygame.draw.rect(self.screen, color, (cx - 22, cy - 16, 44, 32), border_radius=4)

        title = self.font_lg.render("Lane Race (playground)", True, (255, 255, 255))
        self.screen.blit(title, (8, 8))
