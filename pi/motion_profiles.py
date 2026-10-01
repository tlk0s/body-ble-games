"""Filter controller events per game (BLE layer will use the same rules)."""

from enum import Enum, auto


class MotionProfile(Enum):
    DINO = auto()  # jump + duck
    LANE = auto()  # sidestep only
    TEST_ALL = auto()


GAME_PROFILE: dict[str, MotionProfile] = {
    "blob_jump": MotionProfile.DINO,
    "lane_race": MotionProfile.LANE,
}


class MotionFlags:
    JUMP = 0x01
    DUCK = 0x02
    STEP_L = 0x04
    STEP_R = 0x08
    HERO_GIRL = 0x10


def filter_flags(profile: MotionProfile, flags: int) -> int:
    """Return flags allowed for this game (hero bit always passes)."""
    hero = flags & MotionFlags.HERO_GIRL
    if profile == MotionProfile.DINO:
        allowed = MotionFlags.JUMP | MotionFlags.DUCK
    elif profile == MotionProfile.LANE:
        allowed = MotionFlags.STEP_L | MotionFlags.STEP_R
    else:
        allowed = (
            MotionFlags.JUMP
            | MotionFlags.DUCK
            | MotionFlags.STEP_L
            | MotionFlags.STEP_R
        )
    return (flags & allowed) | hero
