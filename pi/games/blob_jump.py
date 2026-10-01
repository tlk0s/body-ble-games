"""BlobJump — 1P full screen or 2P horizontal split; jump / duck obstacles; score."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto

import pygame

from games.base_game import BaseGame
from games.blob_music import BlobJumpMusic
from input_events import FrameInput, Hero
from motion_profiles import MotionProfile


class ObsKind(Enum):
    GROUND = auto()
    AIR = auto()


@dataclass
class Obstacle:
    kind: ObsKind
    x: float
    w: int
    h: int
    wave_id: int
    hit: bool = False
    resolved: bool = False


@dataclass
class LaneState:
    obstacles: list[Obstacle] = field(default_factory=list)
    score: int = 0
    jump_v: float = 0.0
    y_off: float = 0.0
    duck: bool = False
    invincible_until: float = 0.0


class _Sprites:
    """Procedural sprites; collision uses sprite rect (with small inset)."""

    HIT_INSET = 5

    @staticmethod
    def load() -> _Sprites:
        s = _Sprites()
        s.blob_stand_boy = s._blob((60, 120, 220), 42, 44)
        s.blob_stand_girl = s._blob((255, 105, 180), 42, 44)
        s.blob_duck_boy = s._blob((60, 120, 220), 42, 26)
        s.blob_duck_girl = s._blob((255, 105, 180), 42, 26)
        s.cactus = s._cactus(22, 48)
        s.bird = s._bird(44, 26)
        return s

    def _blob(self, color: tuple[int, int, int], w: int, h: int) -> pygame.Surface:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, color, surf.get_rect())
        pygame.draw.ellipse(surf, (255, 255, 255, 80), (w // 4, h // 5, w // 3, h // 4))
        return surf

    def _cactus(self, w: int, h: int) -> pygame.Surface:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        r = surf.get_rect()
        pygame.draw.rect(surf, (35, 110, 45), (w // 2 - 4, 0, 8, h), border_radius=2)
        pygame.draw.rect(surf, (45, 130, 55), (2, h // 3, 8, h // 3), border_radius=2)
        pygame.draw.rect(surf, (45, 130, 55), (w - 10, h // 4, 8, h // 3), border_radius=2)
        return surf

    def _bird(self, w: int, h: int) -> pygame.Surface:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (90, 80, 100), surf.get_rect())
        pygame.draw.polygon(surf, (120, 100, 110), [(w - 4, h // 2), (w + 6, h // 2 - 4), (w + 6, h // 2 + 4)])
        return surf

    def hitbox(self, rect: pygame.Rect) -> pygame.Rect:
        r = rect.inflate(-self.HIT_INSET * 2, -self.HIT_INSET * 2)
        return r if r.w > 0 and r.h > 0 else rect

    @staticmethod
    def air_obs_hitbox(rect: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(rect.x + 3, rect.y + 2, max(6, rect.w - 6), max(6, rect.h - 4))


class BlobJumpGame(BaseGame):
    profile = MotionProfile.DINO
    title = "BlobJump"

    BLOB_X = 96
    BASE_SPEED = 88.0
    GRAVITY = 980.0
    JUMP_V = 420.0
    INVINCIBLE_S = 1.0
    RECOVERY_AFTER_OBS_S = 0.9
    # Bottom of air sprite sits this many px above ground (duck blob is 26px tall)
    AIR_OBS_BOTTOM = 30

    def __init__(self, players, screen) -> None:
        super().__init__(players, screen)
        self.elapsed = 0.0
        self.game_rng = random.Random(random.randint(0, 2_000_000))
        self.spawn_timer = 1.6
        self.wave_counter = 0
        self.recovery_applied: set[int] = set()
        self.lanes: list[LaneState] = [LaneState(), LaneState()]
        self.sprites = _Sprites.load()
        self._sp_phase = "ramp"
        self._sp_phase_start = 0.0
        self._sp_peak_hold_s = 0.0
        self._music = BlobJumpMusic()

    def on_player_left(self, slot: int) -> None:
        if 0 <= slot < 2:
            self.lanes[slot] = LaneState()

    SPEED_PEAK = 3.0
    SPEED_VALLEY = 2.5
    SPEED_RAMP_S = 28.0
    SPEED_TRANSITION_S = 11.0
    SPEED_PEAK_HOLD_MAX_S = 45.0

    def _next_peak_hold_s(self) -> float:
        return self.game_rng.uniform(0.0, self.SPEED_PEAK_HOLD_MAX_S)

    def _advance_speed_phase(self) -> None:
        e = self.elapsed
        t = e - self._sp_phase_start
        if self._sp_phase == "ramp":
            if e >= self.SPEED_RAMP_S:
                self._sp_phase = "hold_peak"
                self._sp_phase_start = e
                self._sp_peak_hold_s = self._next_peak_hold_s()
            return
        if self._sp_phase == "hold_peak":
            if t >= self._sp_peak_hold_s:
                self._sp_phase = "fall"
                self._sp_phase_start = e
            return
        if self._sp_phase == "fall":
            if t >= self.SPEED_TRANSITION_S:
                self._sp_phase = "rise"
                self._sp_phase_start = e
            return
        if self._sp_phase == "rise":
            if t >= self.SPEED_TRANSITION_S:
                self._sp_phase = "hold_peak"
                self._sp_phase_start = e
                self._sp_peak_hold_s = self._next_peak_hold_s()

    def _speed_mult(self) -> float:
        hi, lo = self.SPEED_PEAK, self.SPEED_VALLEY
        e = self.elapsed
        if self._sp_phase == "ramp":
            u = min(1.0, e / self.SPEED_RAMP_S)
            return 1.0 + (hi - 1.0) * u
        if self._sp_phase == "hold_peak":
            return hi
        t = e - self._sp_phase_start
        if self._sp_phase == "fall":
            u = min(1.0, t / self.SPEED_TRANSITION_S)
            return hi + (lo - hi) * u
        if self._sp_phase == "rise":
            u = min(1.0, t / self.SPEED_TRANSITION_S)
            return lo + (hi - lo) * u
        return hi

    def _speed(self) -> float:
        return self.BASE_SPEED * self._speed_mult()

    def _music_intensity(self) -> float:
        """0 at start → 1 when obstacles are hardest (peak speed / hold)."""
        sm = self._speed_mult()
        base = (sm - 1.0) / (self.SPEED_PEAK - 1.0)
        if self._sp_phase == "hold_peak":
            return min(1.0, max(base, 0.92))
        if self._sp_phase == "rise":
            t = min(1.0, (self.elapsed - self._sp_phase_start) / self.SPEED_TRANSITION_S)
            return min(1.0, max(base, 0.35 + 0.55 * t))
        if self._sp_phase == "fall":
            return base * 0.85
        return min(1.0, max(0.0, base))

    def run(self, mock_input=None, ble=None) -> str:
        self._music.start()
        try:
            return super().run(mock_input, ble)
        finally:
            self._music.stop()

    def _active_slots(self, inputs: list[FrameInput]) -> list[int]:
        return [i for i, inp in enumerate(inputs) if inp.connected]

    def _lane_surface_rect(self, slot: int, two_player: bool) -> pygame.Rect:
        w, h = self.screen.get_size()
        if not two_player:
            return pygame.Rect(0, 0, w, h)
        mid = h // 2
        if slot == 0:
            return pygame.Rect(0, 0, w, mid)
        return pygame.Rect(0, mid, w, h - mid)

    def _split_mid_y(self) -> int:
        return self.screen.get_height() // 2

    def _ground_y(self, lane: pygame.Rect) -> int:
        return lane.bottom - 12

    def _schedule_spawn(self) -> None:
        speed = max(self._speed(), self.BASE_SPEED)
        self.spawn_timer = self.game_rng.uniform(1.2, 2.4) * (self.BASE_SPEED / speed)

    def _apply_obstacle_recovery(self, wave_id: int) -> None:
        if wave_id in self.recovery_applied:
            return
        self.recovery_applied.add(wave_id)
        self.spawn_timer += self.RECOVERY_AFTER_OBS_S
        if len(self.recovery_applied) > 64:
            self.recovery_applied.clear()

    def _spawn_shared_obstacles(self, inputs: list[FrameInput], two: bool) -> None:
        active = self._active_slots(inputs)
        if not active:
            return
        ref = self._lane_surface_rect(active[0], two)
        w = ref.width
        self.wave_counter += 1
        wid = self.wave_counter
        kind = ObsKind.GROUND if self.game_rng.random() < 0.55 else ObsKind.AIR
        if kind == ObsKind.GROUND:
            oh, ow = 48, 22
        else:
            oh, ow = 26, 44
        x = float(w + ow + 8)
        for slot in active:
            self.lanes[slot].obstacles.append(Obstacle(kind, x, ow, oh, wid))
        self._schedule_spawn()

    def _blob_sprite(self, inp: FrameInput, ls: LaneState) -> pygame.Surface:
        girl = inp.hero == Hero.GIRL
        if ls.duck:
            return self.sprites.blob_duck_girl if girl else self.sprites.blob_duck_boy
        return self.sprites.blob_stand_girl if girl else self.sprites.blob_stand_boy

    def _blob_draw_rect(self, slot: int, lane_rect: pygame.Rect, sprite: pygame.Surface) -> pygame.Rect:
        gy = self._ground_y(lane_rect)
        ls = self.lanes[slot]
        top = gy - sprite.get_height() - int(ls.y_off)
        return pygame.Rect(lane_rect.left + self.BLOB_X, top, sprite.get_width(), sprite.get_height())

    def _obs_sprite(self, obs: Obstacle) -> pygame.Surface:
        if obs.kind == ObsKind.GROUND:
            return pygame.transform.smoothscale(self.sprites.cactus, (obs.w, obs.h))
        return pygame.transform.smoothscale(self.sprites.bird, (obs.w, obs.h))

    def _obs_draw_rect(self, obs: Obstacle, lane_rect: pygame.Rect) -> pygame.Rect:
        gy = self._ground_y(lane_rect)
        sprite = self._obs_sprite(obs)
        if obs.kind == ObsKind.GROUND:
            return pygame.Rect(int(obs.x), gy - obs.h, sprite.get_width(), sprite.get_height())
        bottom = gy - self.AIR_OBS_BOTTOM
        top = bottom - obs.h
        return pygame.Rect(int(obs.x), top, sprite.get_width(), sprite.get_height())

    def _update_lane(self, slot: int, inp: FrameInput, dt: float, lane_rect: pygame.Rect) -> None:
        ls = self.lanes[slot]
        speed = self._speed()
        now = time.monotonic()
        invincible = now < ls.invincible_until

        ls.duck = inp.duck_held
        if inp.jump and ls.y_off <= 0 and ls.jump_v <= 0:
            ls.jump_v = self.JUMP_V
        ls.jump_v -= self.GRAVITY * dt
        ls.y_off += ls.jump_v * dt
        if ls.y_off < 0:
            ls.y_off = 0
            ls.jump_v = 0

        stand_sprite = self.sprites.blob_stand_girl if inp.hero == Hero.GIRL else self.sprites.blob_stand_boy
        blob_sprite = self._blob_sprite(inp, ls)
        blob_rect = self._blob_draw_rect(slot, lane_rect, blob_sprite)
        stand_rect = self._blob_draw_rect(slot, lane_rect, stand_sprite)
        blob_hit = self.sprites.hitbox(blob_rect)
        stand_hit = self.sprites.hitbox(stand_rect)

        for obs in ls.obstacles:
            obs.x -= speed * dt
            orect = self._obs_draw_rect(obs, lane_rect)

            if obs.kind == ObsKind.AIR:
                ducked = ls.duck and ls.y_off < 10
                if ducked or invincible:
                    collides = False
                else:
                    obs_hit = self.sprites.air_obs_hitbox(orect)
                    collides = stand_hit.colliderect(obs_hit)
            else:
                obs_hit = self.sprites.hitbox(orect)
                collides = not invincible and blob_hit.colliderect(obs_hit)

            if not obs.resolved and collides:
                obs.hit = True
                obs.resolved = True
                ls.score = max(0, ls.score - 1)
                ls.invincible_until = now + self.INVINCIBLE_S
                self._apply_obstacle_recovery(obs.wave_id)

            if not obs.resolved and obs.x + obs.w < lane_rect.left + self.BLOB_X - 6:
                obs.resolved = True
                if not obs.hit:
                    ls.score += 1
                self._apply_obstacle_recovery(obs.wave_id)

        ls.obstacles = [o for o in ls.obstacles if o.x + o.w > lane_rect.left - 40]

    def update(self, inputs: list[FrameInput], dt: float) -> None:
        self.elapsed += dt
        self._advance_speed_phase()
        self._music.update(self._music_intensity(), dt)
        two = len(self._active_slots(inputs)) >= 2
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self._spawn_shared_obstacles(inputs, two)
        for slot, inp in enumerate(inputs):
            if not inp.connected:
                continue
            self._update_lane(slot, inp, dt, self._lane_surface_rect(slot, two))

    def _draw_lane_bg(self, lane_rect: pygame.Rect) -> None:
        sky_h = max(1, lane_rect.height // 2)
        pygame.draw.rect(self.screen, (135, 206, 235), (lane_rect.x, lane_rect.y, lane_rect.w, sky_h))
        pygame.draw.rect(
            self.screen,
            (222, 186, 120),
            (lane_rect.x, lane_rect.y + sky_h, lane_rect.w, lane_rect.height - sky_h),
        )
        gy = self._ground_y(lane_rect)
        pygame.draw.line(
            self.screen,
            (90, 70, 40),
            (lane_rect.left, gy + 1),
            (lane_rect.right, gy + 1),
            3,
        )

    def draw_debug_hud(self, inputs: list[FrameInput], y: int = 8, ble=None) -> None:
        two = len(self._active_slots(inputs)) >= 2
        for slot, inp in enumerate(inputs):
            if not inp.connected:
                continue
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
            if two:
                lane = self._lane_surface_rect(slot, True)
                self.screen.blit(line, (lane.left + 8, lane.bottom - 24))
            else:
                self.screen.blit(line, (8, y + slot * 22))
        if ble is not None and not two:
            dbg = self.font.render(
                f"BLE last=0x{ble.last_flags:02X} n={ble.notify_count}", True, (180, 180, 180)
            )
            self.screen.blit(dbg, (8, y + 48))

    def draw(self, inputs: list[FrameInput]) -> None:
        w, h = self.screen.get_size()
        two = len(self._active_slots(inputs)) >= 2
        self.screen.fill(30)
        now = time.monotonic()

        if two:
            mid = self._split_mid_y()
            pygame.draw.line(self.screen, (70, 75, 85), (0, mid), (w, mid), 2)

        for slot, inp in enumerate(inputs):
            if not inp.connected:
                continue
            lane = self._lane_surface_rect(slot, two)
            self._draw_lane_bg(lane)
            ls = self.lanes[slot]

            for obs in ls.obstacles:
                sprite = self._obs_sprite(obs)
                orect = self._obs_draw_rect(obs, lane)
                self.screen.blit(sprite, orect.topleft)

            blob_sprite = self._blob_sprite(inp, ls)
            blob_rect = self._blob_draw_rect(slot, lane, blob_sprite)
            inv = now < ls.invincible_until
            if inv and int(now * 8) % 2 == 0:
                blob_sprite = blob_sprite.copy()
                blob_sprite.set_alpha(120)
            self.screen.blit(blob_sprite, blob_rect.topleft)

            tag = self.font.render(f"P{slot + 1}", True, (230, 230, 235))
            self.screen.blit(tag, (lane.left + 8, lane.top + 22))
            score_s = self.font.render(str(ls.score), True, (255, 255, 255))
            self.screen.blit(score_s, (lane.right - score_s.get_width() - 10, lane.top + 22))

        spd = self.font.render(f"speed x{self._speed_mult():.2f}", True, (180, 185, 195))
        if two:
            self.screen.blit(spd, spd.get_rect(midtop=(w // 2, 22)))
        else:
            title = self.font_lg.render("BlobJump", True, (255, 255, 255))
            self.screen.blit(title, (8, 8))
            self.screen.blit(spd, (w - spd.get_width() - 8, 8))
