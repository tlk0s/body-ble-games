"""Fullscreen letterbox for TV / Pi (avoids pygame SCALED crop on some displays)."""

from __future__ import annotations

import os

import pygame

_virtual: pygame.Surface | None = None
_real: pygame.Surface | None = None


def uses_letterbox() -> bool:
    return _real is not None


def create_game_surface(width: int, height: int, fullscreen: bool) -> pygame.Surface:
    global _virtual, _real
    _virtual = None
    _real = None

    if not fullscreen:
        return pygame.display.set_mode((width, height))

    pygame.mouse.set_visible(False)
    # Legacy: FULLSCREEN|SCALED (can look "zoomed" on Pi + HDMI)
    if os.environ.get("BODY_FS_SCALED", "").lower() in ("1", "true", "yes"):
        return pygame.display.set_mode((width, height), pygame.FULLSCREEN | pygame.SCALED)

    _real = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    _virtual = pygame.Surface((width, height))
    return _virtual


def present(virtual: pygame.Surface) -> None:
    if _real is None:
        pygame.display.flip()
        return

    gw, gh = _real.get_size()
    vw, vh = virtual.get_size()
    scale = min(gw / vw, gh / vh)
    nw, nh = max(1, int(vw * scale)), max(1, int(vh * scale))
    if (nw, nh) == (vw, vh):
        scaled = virtual
    elif nw == vw * 2 and nh == vh * 2:
        scaled = pygame.transform.scale2x(virtual)
    else:
        # scale (not smoothscale) — much cheaper on Pi Zero 2 W
        scaled = pygame.transform.scale(virtual, (nw, nh))
    x, y = (gw - nw) // 2, (gh - nh) // 2
    _real.fill((0, 0, 0))
    _real.blit(scaled, (x, y))
    pygame.display.flip()
