"""Shared input types for games and BLE layer."""

from dataclasses import dataclass, field
from enum import Enum, auto


class Hero(Enum):
    BOY = auto()
    GIRL = auto()


class SessionEventType(Enum):
    PLAYER_JOINED = auto()
    PLAYER_LEFT = auto()
    MODE_1P = auto()
    MODE_2P = auto()


@dataclass
class SessionEvent:
    kind: SessionEventType
    slot: int = -1
    mac: str = ""


@dataclass
class FrameInput:
    """One frame of input for a player slot (after profile filter)."""

    connected: bool = False
    hero: Hero = Hero.BOY
    jump: bool = False
    duck_held: bool = False
    step_left: bool = False
    step_right: bool = False


@dataclass
class PlayerState:
    mac: str
    hero_girl: bool = False
    duck_held: bool = False
    jump_pulse: bool = False
    step_l_pulse: bool = False
    step_r_pulse: bool = False
    jump_until: float = 0.0
    step_l_until: float = 0.0
    step_r_until: float = 0.0

    @property
    def hero(self) -> Hero:
        return Hero.GIRL if self.hero_girl else Hero.BOY
