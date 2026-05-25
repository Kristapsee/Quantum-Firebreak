# -----------------------------------------------------------------------------
# Quantum Firebreak - a turn-based strategy game with quantum-inspired mechanics
#
# The player tries to contain a wildfire on a 10x10 grid over configurable turns.
# Each turn the player gets configurable Action Points (AP) to spend on three actions:
#   - Build a firebreak (barrier) on a forest tile
#   - Scan a 3x3 area to perform quantum measurement and collapse superposition
#   - Deploy a crew to extinguish a burning tile
#
# Core quantum idea:
# Forest tiles are represented by two amplitudes:
#   Tile = safe_amp * |safe> + fire_amp * |fire>
#
# Fire spread increases fire_amp in nearby forest tiles.
# Scanning measures tiles and collapses each uncertain tile to either fire or safe,
# based on probabilities from squared amplitudes.
# -----------------------------------------------------------------------------

import math
import os
import random
import sys

import pygame

# --- Constants ----------------------------------------------------------------

# Grid dimensions
GRID_SIZE = 10
TILE_PX = 84
GRID_PX = GRID_SIZE * TILE_PX
PANEL_W = 320
SCREEN_W = GRID_PX + PANEL_W
SCREEN_H = GRID_PX
FPS = 30

# Gameplay rules
MAX_TURNS = 20
AP_PER_TURN = 3
BURN_THRESHOLD = 18
INITIAL_FIRES = 4
AUTO_IGNITE_PROBABILITY = 0.88
BURNOUT_CHANCE = 0.21

DIFFICULTY_SETTINGS = [
    ("initial_fires", "Starting fires", 1, 12, 1),
    ("max_turns", "Turns to survive", 5, 40, 1),
    ("ap_per_turn", "Action points / turn", 1, 6, 1),
    ("entangled_pairs", "Entangled pairs", 0, 12, 1),
    ("burn_threshold", "Burn limit", 5, 40, 1),
    ("auto_ignite_percent", "Auto-ignite threshold", 65, 98, 1),
]
DIFFICULTY_PRESETS = {
    "Easy": {
        "initial_fires": 2,
        "max_turns": 15,
        "ap_per_turn": 4,
        "entangled_pairs": 1,
        "burn_threshold": 25,
        "auto_ignite_percent": 94,
    },
    "Standard": {
        "initial_fires": INITIAL_FIRES,
        "max_turns": MAX_TURNS,
        "ap_per_turn": AP_PER_TURN,
        "entangled_pairs": 3,
        "burn_threshold": BURN_THRESHOLD,
        "auto_ignite_percent": int(AUTO_IGNITE_PROBABILITY * 100),
    },
    "Hard": {
        "initial_fires": 6,
        "max_turns": 25,
        "ap_per_turn": 2,
        "entangled_pairs": 6,
        "burn_threshold": 14,
        "auto_ignite_percent": 80,
    },
}

# Tile states
FOREST = 0
BURNING = 1
BURNED = 2
FIREBREAK = 3

# Action modes
MODE_FIREBREAK = "firebreak"
MODE_SCAN = "scan"
MODE_CREW = "crew"

# App screens
SCREEN_MENU = "menu"
SCREEN_GAME = "game"

# Colors (RGB)
COL_FOREST = (71, 148, 92)
COL_BURNING = (227, 96, 50)
COL_BURNED = (74, 74, 82)
COL_FIREBREAK = (176, 134, 84)
COL_AMP_LOW = (255, 236, 150)
COL_AMP_HIGH = (255, 151, 74)
COL_BG_TOP = (17, 41, 47)
COL_BG_BOTTOM = (8, 22, 26)
COL_PANEL_TOP = (29, 56, 64)
COL_PANEL_BOTTOM = (18, 37, 44)
COL_CARD = (34, 69, 79)
COL_TEXT = (234, 241, 239)
COL_MUTED = (176, 200, 198)
COL_HIGHLIGHT = (255, 255, 255)
COL_FACT_TITLE = (255, 214, 153)
COL_FACT_TEXT = (255, 240, 204)
COL_GRID_LINE = (32, 70, 78)
COL_SCAN_PREVIEW = (112, 223, 255, 90)
COL_BTN = (43, 84, 95)
COL_BTN_ACTIVE = (76, 132, 146)
COL_WIN = (119, 231, 119)
COL_LOSE = (240, 113, 113)
COL_GLOW = (117, 212, 239)
COL_ENTANGLE = (196, 158, 255)
COL_DANGER = (255, 91, 67)
COL_MODAL = (8, 22, 26, 226)
COL_MODAL_CARD = (24, 53, 61)
COL_SAFE_FLASH = (132, 244, 169)
COL_SMOKE = (163, 171, 169)

FACTS_FILE = os.path.join(os.path.dirname(__file__), "fire_safety_facts.txt")
DEFAULT_FACTS = [
    "Install smoke alarms on every level and test them monthly.",
    "Keep cooking areas clear of towels, packaging, and other flammables.",
    "Plan two exits from every room and practice your home fire drill.",
    "If smoke appears, get out, stay out, and call emergency services.",
    "Create defensible space by clearing dry vegetation near structures.",
]
WIN_FACTS = [
    "Real firebreaks remove or separate burnable vegetation, helping slow a fire and giving crews a safer line from which to respond.",
    "Reducing dry leaves, branches, and other fuels near a protected area can lower flame intensity and support containment work.",
    "A fire line is strongest when responders also watch for embers that may land beyond the break and start spot fires.",
]
LOSS_FACTS = [
    "Wind-driven embers can travel ahead of a wildfire and start spot fires beyond roads, streams, or constructed firebreaks.",
    "When fire behavior changes quickly, early warnings and prompt evacuation protect lives even when vegetation cannot be saved.",
    "Dense dry fuel and strong wind can allow wildfire growth to outpace containment, which is why prevention and early detection matter.",
]


def load_fire_safety_facts():
    """Load facts from an external text file; each non-empty line is one fact."""
    try:
        with open(FACTS_FILE, "r", encoding="utf-8") as f:
            facts = [line.strip() for line in f if line.strip()]
            if facts:
                return facts
    except OSError:
        pass
    return DEFAULT_FACTS


class Game:
    """Holds all game data and logic."""

    def __init__(self):
        self.fire_safety_facts = load_fire_safety_facts()
        self.settings = DIFFICULTY_PRESETS["Standard"].copy()
        self.difficulty_name = "Standard"
        self.reset()

    def apply_difficulty_preset(self, name):
        """Apply a named difficulty configuration for the next new game."""
        self.settings.update(DIFFICULTY_PRESETS[name])
        self.difficulty_name = name

    def adjust_setting(self, key, amount):
        """Adjust one configurable rule while keeping its allowed range."""
        for setting_key, _label, minimum, maximum, step in DIFFICULTY_SETTINGS:
            if setting_key == key:
                value = self.settings[key] + amount * step
                self.settings[key] = max(minimum, min(maximum, value))
                self.difficulty_name = "Custom"
                return

    def reset(self):
        """Initialize (or re-initialize) game state for a new game."""
        self.grid = [[FOREST for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        # Quantum amplitudes for each tile.
        # For forest tiles we start in mostly safe state: 1.0|safe> + 0.0|fire>.
        self.safe_amp = [[1.0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.fire_amp = [[0.0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        self.turn = 1
        self.ap = self.settings["ap_per_turn"]
        self.mode = MODE_FIREBREAK
        self.burned_count = 0
        self.game_over = False
        self.win = False
        self.message = ""
        self.outcome_fact = ""
        self.scan_preview = None
        self.current_fact = random.choice(self.fire_safety_facts)
        self.particles = []
        self.heat_flashes = []
        self.scan_waves = []
        self.collapse_flashes = []
        self.show_info = False
        self.show_social_good = False
        self.show_settings = False
        self.ui_buttons = {}
        self.wind_dir = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
        self.stats = {"firebreaks": 0, "scans": 0, "crews": 0}

        # Simple optional entanglement map: (r, c) -> (r2, c2), symmetric.
        self.entangled_partner = {}
        self.entangled_pairs = []

        starts = random.sample(
            [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)],
            k=self.settings["initial_fires"],
        )
        for r, c in starts:
            self.grid[r][c] = BURNING
            self.safe_amp[r][c] = 0.0
            self.fire_amp[r][c] = 1.0

        self._create_entangled_pairs(pair_count=self.settings["entangled_pairs"])
        self._count_burned()

    # --- Internal helpers -----------------------------------------------------

    def _count_burned(self):
        self.burned_count = sum(
            1
            for r in range(GRID_SIZE)
            for c in range(GRID_SIZE)
            if self.grid[r][c] in (BURNED, BURNING)
        )

    def _neighbours(self, r, c):
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                yield nr, nc

    def _spread_neighbours(self, r, c):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                    yield nr, nc, dr, dc

    def _spawn_particle_burst(self, r, c, colours, count=24, speed=140):
        """Create a short-lived burst centered on a grid tile."""
        cx = c * TILE_PX + TILE_PX * 0.5
        cy = r * TILE_PX + TILE_PX * 0.5
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            vel = random.uniform(speed * 0.45, speed)
            life = random.uniform(0.35, 0.75)
            self.particles.append(
                {
                    "x": cx + random.uniform(-8, 8),
                    "y": cy + random.uniform(-8, 8),
                    "vx": math.cos(ang) * vel,
                    "vy": math.sin(ang) * vel,
                    "life": life,
                    "max_life": life,
                    "size": random.randint(2, 4),
                    "col": random.choice(colours),
                }
            )

    def update_particles(self, dt):
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 180 * dt
            p["vx"] *= 0.985
            p["vy"] *= 0.985
            alive.append(p)
        self.particles = alive

        self.heat_flashes = [
            {"r": h["r"], "c": h["c"], "life": h["life"] - dt, "max_life": h["max_life"]}
            for h in self.heat_flashes
            if h["life"] - dt > 0
        ]
        self.scan_waves = [
            {"r": w["r"], "c": w["c"], "life": w["life"] - dt, "max_life": w["max_life"]}
            for w in self.scan_waves
            if w["life"] - dt > 0
        ]
        self.collapse_flashes = [
            {
                "r": f["r"],
                "c": f["c"],
                "life": f["life"] - dt,
                "max_life": f["max_life"],
                "col": f["col"],
            }
            for f in self.collapse_flashes
            if f["life"] - dt > 0
        ]

    def fire_probability(self, r, c):
        """Compute fire probability from squared amplitudes.

        p(fire) = fire_amp^2 / (safe_amp^2 + fire_amp^2)
        """
        sa = self.safe_amp[r][c]
        fa = self.fire_amp[r][c]
        denom = sa * sa + fa * fa
        if denom <= 1e-12:
            return 0.0
        return (fa * fa) / denom

    def _reset_to_safe_state(self, r, c):
        """Reset amplitudes to the default collapsed safe basis values."""
        self.safe_amp[r][c] = 1.0
        self.fire_amp[r][c] = 0.0

    def _collapse_tile(self, r, c, force_probability=None):
        """Measure one forest tile and collapse it to BURNING or safe FOREST.

        Returns True if the tile collapses to fire, False if it collapses safe.
        """
        if self.grid[r][c] != FOREST:
            return False

        p_fire = self.fire_probability(r, c) if force_probability is None else force_probability
        p_fire = max(0.0, min(1.0, p_fire))

        became_fire = random.random() < p_fire
        if became_fire:
            self.grid[r][c] = BURNING
        self.collapse_flashes.append(
            {
                "r": r,
                "c": c,
                "life": 0.55,
                "max_life": 0.55,
                "col": COL_DANGER if became_fire else COL_SAFE_FLASH,
            }
        )

        # After measurement, reset amplitudes as requested.
        self._reset_to_safe_state(r, c)
        return became_fire

    def _create_entangled_pairs(self, pair_count=4):
        """Create a few simple entangled tile pairs among forest tiles."""
        self.entangled_partner.clear()
        self.entangled_pairs.clear()
        available = [
            (r, c)
            for r in range(GRID_SIZE)
            for c in range(GRID_SIZE)
            if self.grid[r][c] == FOREST
        ]
        random.shuffle(available)

        made = 0
        while len(available) >= 2 and made < pair_count:
            a = available.pop()
            b = available.pop()
            self.entangled_partner[a] = b
            self.entangled_partner[b] = a
            self.entangled_pairs.append((a, b))
            made += 1

    # --- Player actions -------------------------------------------------------

    def build_firebreak(self, r, c):
        """Build a firebreak on a forest tile. Costs 1 AP.

        Quantum interference: firebreaks locally suppress fire amplitude.
        """
        if self.ap < 1:
            self.message = "Not enough AP!"
            return False
        if self.grid[r][c] != FOREST:
            self.message = "Can only build on forest tiles."
            return False

        self.grid[r][c] = FIREBREAK
        self._reset_to_safe_state(r, c)

        # Immediate local destructive interference around new firebreak.
        for nr, nc in self._neighbours(r, c):
            if self.grid[nr][nc] == FOREST:
                self.fire_amp[nr][nc] *= 0.78
                self.safe_amp[nr][nc] = min(1.4, self.safe_amp[nr][nc] + 0.08)

        self.ap -= 1
        self.stats["firebreaks"] += 1
        self._spawn_particle_burst(
            r,
            c,
            [(212, 179, 128), (164, 122, 73), (238, 209, 156)],
            count=20,
            speed=120,
        )
        self.message = f"Firebreak built at ({r},{c}) - interference stabilized nearby amplitudes."
        return True

    def scan_area(self, r, c):
        """Perform quantum measurement in a 3x3 area centered on (r, c)."""
        if self.ap < 1:
            self.message = "Not enough AP!"
            return False

        collapsed_fire = 0
        collapsed_safe = 0
        entangled_triggered = 0
        measured = set()

        for dr in range(-1, 2):
            for dc in range(-1, 2):
                nr, nc = r + dr, c + dc
                if not (0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE):
                    continue
                if self.grid[nr][nc] != FOREST:
                    continue
                if self.fire_amp[nr][nc] <= 0.0:
                    continue

                became_fire = self._collapse_tile(nr, nc)
                measured.add((nr, nc))
                if became_fire:
                    collapsed_fire += 1
                else:
                    collapsed_safe += 1

                # Optional simple entanglement: measuring a tile influences partner.
                partner = self.entangled_partner.get((nr, nc))
                if partner is None or partner in measured:
                    continue

                pr, pc = partner
                if self.grid[pr][pc] != FOREST:
                    continue

                entangled_triggered += 1
                partner_base = self.fire_probability(pr, pc)
                if became_fire:
                    partner_p = min(0.98, partner_base + 0.25)
                else:
                    partner_p = max(0.02, partner_base - 0.20)

                partner_burn = self._collapse_tile(pr, pc, force_probability=partner_p)
                measured.add((pr, pc))
                if partner_burn:
                    collapsed_fire += 1
                else:
                    collapsed_safe += 1

        self.ap -= 1
        self.stats["scans"] += 1
        self.scan_waves.append({"r": r, "c": c, "life": 0.75, "max_life": 0.75})
        self._spawn_particle_burst(
            r,
            c,
            [(115, 227, 255), (165, 236, 255), (211, 245, 255)],
            count=30,
            speed=165,
        )
        self.message = (
            f"Measurement at ({r},{c}): {collapsed_fire} collapsed to fire, "
            f"{collapsed_safe} collapsed safe"
            + (f", {entangled_triggered} entangled link(s) collapsed." if entangled_triggered else ".")
        )
        self._count_burned()
        self._check_lose()
        return True

    def deploy_crew(self, r, c):
        """Deploy a crew to extinguish one burning tile. Costs 2 AP."""
        if self.ap < 2:
            self.message = "Need 2 AP for crew!"
            return False
        if self.grid[r][c] != BURNING:
            self.message = "Crew can only extinguish burning tiles."
            return False

        self.grid[r][c] = BURNED
        self._reset_to_safe_state(r, c)
        self.ap -= 2
        self.stats["crews"] += 1
        self._spawn_particle_burst(
            r,
            c,
            [(181, 238, 255), (123, 208, 255), (225, 247, 255)],
            count=32,
            speed=180,
        )
        self.message = f"Crew deployed at ({r},{c}). Fire extinguished."
        self._count_burned()
        return True

    # --- End-of-turn mechanics -----------------------------------------------

    def _finish_game(self, win, message):
        self.game_over = True
        self.win = win
        self.message = message
        fact_pool = WIN_FACTS if win else LOSS_FACTS
        self.outcome_fact = random.choice(fact_pool)

    def end_turn(self):
        """Advance one turn and run quantum spread mechanics."""
        if self.game_over:
            return

        if random.random() < 0.45:
            self.wind_dir = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])

        # Step 1: Fire spread injects fire amplitude into neighbouring forest.
        spread_delta = [[0.0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] == BURNING:
                    for nr, nc, dr, dc in self._spread_neighbours(r, c):
                        if self.grid[nr][nc] == FOREST:
                            diagonal = dr != 0 and dc != 0
                            base = random.uniform(0.16, 0.32)
                            if diagonal:
                                base *= 0.52
                            if (dr, dc) == self.wind_dir:
                                base *= 1.38
                            spread_delta[nr][nc] += base

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] == FOREST and spread_delta[r][c] > 0:
                    self.fire_amp[r][c] = min(2.2, self.fire_amp[r][c] + spread_delta[r][c])
                    if spread_delta[r][c] >= 0.24:
                        self.heat_flashes.append({"r": r, "c": c, "life": 0.65, "max_life": 0.65})

        # Step 2: Firebreak interference suppresses nearby fire amplitude.
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] == FIREBREAK:
                    for nr, nc in self._neighbours(r, c):
                        if self.grid[nr][nc] == FOREST:
                            self.fire_amp[nr][nc] *= 0.86
                            self.safe_amp[nr][nc] = min(1.5, self.safe_amp[nr][nc] + 0.05)

        # Step 3: Decoherence on unobserved superposition drifts toward fire.
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] == FOREST and self.fire_amp[r][c] > 0.0:
                    before_p = self.fire_probability(r, c)
                    self.fire_amp[r][c] = min(2.7, self.fire_amp[r][c] + 0.085)
                    self.safe_amp[r][c] = max(0.05, self.safe_amp[r][c] - 0.04)

                    # Make decoherence visible: unmeasured uncertainty should
                    # drift upward by at least 7 percentage points each turn.
                    target_p = min(0.97, before_p + 0.07)
                    if self.fire_probability(r, c) < target_p:
                        ratio = math.sqrt(target_p / max(0.001, 1.0 - target_p))
                        self.fire_amp[r][c] = self.safe_amp[r][c] * ratio

        # Step 4: Strongly decohered tiles can classically ignite.
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] == FOREST and self.fire_amp[r][c] > 0.0:
                    if self.fire_probability(r, c) >= self.settings["auto_ignite_percent"] / 100.0:
                        self.grid[r][c] = BURNING
                        self._reset_to_safe_state(r, c)
                        self._spawn_particle_burst(
                            r,
                            c,
                            [(255, 127, 73), (255, 191, 93), (255, 88, 58)],
                            count=22,
                            speed=145,
                        )

        # Step 5: Some burning tiles burn out naturally.
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] == BURNING and random.random() < BURNOUT_CHANCE:
                    self.grid[r][c] = BURNED
                    self._reset_to_safe_state(r, c)

        self.turn += 1
        self.ap = self.settings["ap_per_turn"]
        self._count_burned()
        self._check_lose()

        if self.turn > self.settings["max_turns"] and not self.game_over:
            if self.burned_count <= self.settings["burn_threshold"]:
                self._finish_game(True, "You saved the community! Wildfire contained.")
            else:
                self._finish_game(False, "Too many tiles burned. The region is devastated.")

    def _check_lose(self):
        if self.burned_count > self.settings["burn_threshold"] and not self.game_over:
            self._finish_game(False, "Fire overwhelmed the region! You lose.")


# --- Drawing helpers ----------------------------------------------------------

def tile_colour(state):
    return {
        FOREST: COL_FOREST,
        BURNING: COL_BURNING,
        BURNED: COL_BURNED,
        FIREBREAK: COL_FIREBREAK,
    }[state]


def lerp_colour(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_vertical_gradient(surface, rect, top_col, bottom_col):
    height = max(rect.height, 1)
    for i in range(height):
        t = i / (height - 1) if height > 1 else 0
        col = lerp_colour(top_col, bottom_col, t)
        pygame.draw.line(surface, col, (rect.x, rect.y + i), (rect.right - 1, rect.y + i))


def draw_animated_backdrop(surface, ticks):
    draw_vertical_gradient(surface, pygame.Rect(0, 0, SCREEN_W, SCREEN_H), COL_BG_TOP, COL_BG_BOTTOM)

    fx = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    for i in range(7):
        phase = ticks / 2200 + i * 0.9
        cx = int((SCREEN_W * (0.15 + i * 0.12) + 65 * math.sin(phase)) % SCREEN_W)
        cy = int((SCREEN_H * (0.2 + (i % 4) * 0.22) + 45 * math.cos(phase * 1.3)) % SCREEN_H)
        radius = 70 + i * 10
        alpha = 24 + (i % 3) * 10
        pygame.draw.circle(fx, (*COL_GLOW, alpha), (cx, cy), radius)
    surface.blit(fx, (0, 0))


def wrap_text_lines(font_obj, text, max_width):
    words = text.split()
    if not words:
        return []
    lines = []
    current = words[0]
    for w in words[1:]:
        test = f"{current} {w}"
        if font_obj.size(test)[0] <= max_width:
            current = test
        else:
            lines.append(current)
            current = w
    lines.append(current)
    return lines


def wind_label(wind_dir):
    return {
        (-1, 0): "North",
        (1, 0): "South",
        (0, -1): "West",
        (0, 1): "East",
    }.get(wind_dir, "Calm")


def wind_pixel_vector(wind_dir):
    dr, dc = wind_dir
    return dc, dr


def draw_tile_detail(surface, state, rect, r, c, ticks):
    if state == FOREST:
        for i in range(4):
            ox = 13 + ((r * 17 + c * 11 + i * 19) % max(1, rect.width - 26))
            oy = 13 + ((r * 13 + c * 23 + i * 15) % max(1, rect.height - 26))
            pygame.draw.circle(surface, (52, 123, 72), (rect.x + ox, rect.y + oy), 9)
            pygame.draw.circle(surface, (91, 171, 103), (rect.x + ox - 2, rect.y + oy - 2), 4)
    elif state == BURNED:
        for i in range(3):
            sx = rect.x + 14 + ((r * 21 + c * 9 + i * 17) % max(1, rect.width - 28))
            sy = rect.y + 18 + ((r * 8 + c * 19 + i * 13) % max(1, rect.height - 30))
            ex = sx + 9 + ((i * 7 + c) % 12)
            ey = sy + 4 + ((r + i * 5) % 12)
            pygame.draw.line(surface, (40, 40, 46), (sx, sy), (ex, ey), 2)
        smoke = 0.5 + 0.5 * math.sin(ticks / 900 + r + c)
        pygame.draw.circle(surface, (*COL_SMOKE, int(24 + 20 * smoke)), rect.center, 18)
    elif state == FIREBREAK:
        pygame.draw.line(surface, (112, 77, 46), (rect.left + 10, rect.centery), (rect.right - 10, rect.centery), 5)
        pygame.draw.line(surface, (218, 183, 125), (rect.left + 12, rect.centery - 7), (rect.right - 12, rect.centery - 14), 2)
        for i in range(5):
            x = rect.left + 13 + i * 12
            pygame.draw.line(surface, (130, 92, 55), (x, rect.top + 18), (x + 8, rect.bottom - 17), 2)


def draw_flame(surface, rect, r, c, ticks):
    cx = rect.centerx
    base_y = rect.bottom - 12
    flicker = math.sin(ticks / 110 + r * 0.8 + c * 0.5)
    flame_h = 42 + int(6 * flicker)
    outer = [
        (cx - 21, base_y),
        (cx - 14, base_y - 22),
        (cx - 4, base_y - flame_h),
        (cx + 7, base_y - 25),
        (cx + 20, base_y),
    ]
    mid = [
        (cx - 13, base_y - 2),
        (cx - 7, base_y - 20),
        (cx + 3, base_y - flame_h + 10),
        (cx + 11, base_y - 18),
        (cx + 14, base_y - 2),
    ]
    inner = [
        (cx - 6, base_y - 1),
        (cx - 2, base_y - 14),
        (cx + 4, base_y - flame_h + 19),
        (cx + 8, base_y - 1),
    ]
    pygame.draw.polygon(surface, (205, 52, 39), outer)
    pygame.draw.polygon(surface, (255, 132, 48), mid)
    pygame.draw.polygon(surface, (255, 229, 113), inner)


def draw_probability_ring(surface, rect, p_fire, ticks):
    center = rect.center
    radius = min(rect.width, rect.height) // 2 - 8
    col = lerp_colour(COL_AMP_LOW, COL_DANGER, p_fire)
    pygame.draw.circle(surface, (28, 45, 45), center, radius, 4)
    start = -math.pi / 2
    end = start + math.tau * p_fire
    points = [center]
    steps = max(5, int(36 * p_fire))
    for i in range(steps + 1):
        a = start + (end - start) * (i / steps)
        points.append((center[0] + math.cos(a) * radius, center[1] + math.sin(a) * radius))
    if len(points) > 2:
        pygame.draw.lines(surface, col, False, points[1:], 5)
    pulse = int(35 + 30 * (0.5 + 0.5 * math.sin(ticks / 180)))
    pygame.draw.circle(surface, (*col, pulse), center, radius + 3, 2)


def draw_wind_embers(surface, wind_dir, ticks):
    dx, dy = wind_pixel_vector(wind_dir)
    if dx == 0 and dy == 0:
        return
    length = 34
    for i in range(28):
        seed_x = (i * 97) % GRID_PX
        seed_y = (i * 53) % GRID_PX
        speed = 35 + (i % 5) * 10
        x = int((seed_x + dx * ticks * speed / 1000) % GRID_PX)
        y = int((seed_y + dy * ticks * speed / 1000) % GRID_PX)
        alpha = 28 + (i % 4) * 12
        start = (int(x - dx * length), int(y - dy * length))
        end = (x, y)
        pygame.draw.line(surface, (255, 159, 82, alpha), start, end, 2)


def draw_wind_compass(surface, rect, wind_dir, font_sm):
    pygame.draw.rect(surface, (20, 46, 53), rect, border_radius=8)
    pygame.draw.rect(surface, (*COL_GLOW, 90), rect, 1, border_radius=8)
    center = rect.center
    dx, dy = wind_pixel_vector(wind_dir)
    arrow_len = 24
    tip = (center[0] + dx * arrow_len, center[1] + dy * arrow_len)
    tail = (center[0] - dx * 11, center[1] - dy * 11)
    pygame.draw.line(surface, COL_FACT_TITLE, tail, tip, 4)
    if dx != 0:
        head = [(tip[0], tip[1]), (tip[0] - dx * 10, tip[1] - 7), (tip[0] - dx * 10, tip[1] + 7)]
    else:
        head = [(tip[0], tip[1]), (tip[0] - 7, tip[1] - dy * 10), (tip[0] + 7, tip[1] - dy * 10)]
    pygame.draw.polygon(surface, COL_FACT_TITLE, head)
    lbl = font_sm.render("WIND", True, COL_MUTED)
    surface.blit(lbl, (rect.centerx - lbl.get_width() // 2, rect.bottom - lbl.get_height() - 3))


def draw_grid(surface, game, font_sm, ticks):
    board = pygame.Rect(6, 6, GRID_PX - 12, GRID_PX - 12)
    pulse = 0.5 + 0.5 * math.sin(ticks / 700)
    glow_pad = int(6 + 4 * pulse)
    board_glow = pygame.Rect(
        board.x - glow_pad,
        board.y - glow_pad,
        board.width + glow_pad * 2,
        board.height + glow_pad * 2,
    )
    glow = pygame.Surface((board_glow.width, board_glow.height), pygame.SRCALPHA)
    pygame.draw.rect(glow, (*COL_GLOW, 22), glow.get_rect(), border_radius=24)
    surface.blit(glow, board_glow.topleft)
    pygame.draw.rect(surface, (16, 49, 56), board, border_radius=18)

    wind_fx = pygame.Surface((GRID_PX, GRID_PX), pygame.SRCALPHA)
    draw_wind_embers(wind_fx, game.wind_dir, ticks)
    surface.blit(wind_fx, (0, 0))

    ember_fx = pygame.Surface((GRID_PX, GRID_PX), pygame.SRCALPHA)
    entangle_fx = pygame.Surface((GRID_PX, GRID_PX), pygame.SRCALPHA)
    entangle_pulse = 0.5 + 0.5 * math.sin(ticks / 420)

    # Draw entangled links first so tile states remain readable above them.
    for (r1, c1), (r2, c2) in game.entangled_pairs:
        if game.grid[r1][c1] != FOREST or game.grid[r2][c2] != FOREST:
            continue

        x1 = int(c1 * TILE_PX + TILE_PX * 0.5)
        y1 = int(r1 * TILE_PX + TILE_PX * 0.5)
        x2 = int(c2 * TILE_PX + TILE_PX * 0.5)
        y2 = int(r2 * TILE_PX + TILE_PX * 0.5)
        alpha = int(48 + 54 * entangle_pulse)

        pygame.draw.line(entangle_fx, (*COL_ENTANGLE, alpha), (x1, y1), (x2, y2), 2)

        # Moving dots make the non-local link easier to notice without dominating.
        for offset in (0.0, 0.5):
            t = (ticks / 1200 + offset) % 1.0
            px = int(x1 + (x2 - x1) * t)
            py = int(y1 + (y2 - y1) * t)
            pygame.draw.circle(entangle_fx, (*COL_ENTANGLE, alpha + 45), (px, py), 4)

    surface.blit(entangle_fx, (0, 0))

    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            x = c * TILE_PX
            y = r * TILE_PX
            rect = pygame.Rect(x + 4, y + 4, TILE_PX - 8, TILE_PX - 8)

            base = tile_colour(game.grid[r][c])
            pygame.draw.rect(surface, base, rect, border_radius=12)
            draw_tile_detail(surface, game.grid[r][c], rect, r, c, ticks)
            pygame.draw.rect(surface, COL_GRID_LINE, rect, 1, border_radius=12)

            # Visualize uncertain superposition using fire probability overlay.
            if game.grid[r][c] == FOREST and game.fire_amp[r][c] > 0.0:
                p_fire = game.fire_probability(r, c)
                overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 300 + r + c)
                alpha = int((80 + 100 * p_fire) * pulse)
                col = lerp_colour(COL_AMP_LOW, COL_AMP_HIGH, p_fire)
                pygame.draw.rect(overlay, (*col, alpha), overlay.get_rect(), border_radius=12)
                surface.blit(overlay, rect.topleft)
                draw_probability_ring(surface, rect, p_fire, ticks)

                if p_fire >= 0.55:
                    danger_alpha = int(95 + 85 * pulse)
                    pygame.draw.rect(surface, (*COL_DANGER, danger_alpha), rect, 3, border_radius=12)

                txt = font_sm.render(f"{p_fire:.0%}", True, (31, 44, 42))
                surface.blit(
                    txt,
                    (
                        x + TILE_PX // 2 - txt.get_width() // 2,
                        y + TILE_PX // 2 - txt.get_height() // 2,
                    ),
                )

            # Entangled forest tiles get a high-contrast linked-state marker.
            if game.grid[r][c] == FOREST and (r, c) in game.entangled_partner:
                marker_alpha = int(190 + 55 * entangle_pulse)
                marker = pygame.Surface((31, 29), pygame.SRCALPHA)
                marker_rect = marker.get_rect()
                pygame.draw.rect(marker, (43, 27, 67, 238), marker_rect, border_radius=7)
                pygame.draw.rect(marker, (*COL_ENTANGLE, marker_alpha), marker_rect, 3, border_radius=7)
                pygame.draw.rect(marker, (247, 239, 255, 70), marker_rect.inflate(-7, -7), 1, border_radius=4)
                shadow = font_sm.render("E", True, (11, 8, 16))
                label = font_sm.render("E", True, (250, 242, 255))
                label_x = marker.get_width() // 2 - label.get_width() // 2
                label_y = marker.get_height() // 2 - label.get_height() // 2 - 1
                marker.blit(shadow, (label_x + 1, label_y + 1))
                marker.blit(label, (label_x, label_y))
                surface.blit(marker, (x + TILE_PX - 38, y + 8))

            if game.grid[r][c] == BURNING:
                draw_flame(surface, rect, r, c, ticks)

                for i in range(5):
                    phase = ((ticks / 1300) + (r * 0.31 + c * 0.19 + i * 0.22)) % 1.0
                    ex = int(x + 18 + i * 10 + 6 * math.sin(ticks / 260 + i + c))
                    ey = int(y + TILE_PX - 12 - phase * (TILE_PX - 24))
                    radius = 2 + (i % 2)
                    alpha = int(180 * (1.0 - phase))
                    col = (255, 180 + i * 10, 90)
                    pygame.draw.circle(ember_fx, (*col, alpha), (ex, ey), radius)

    surface.blit(ember_fx, (0, 0))

    heat_fx = pygame.Surface((GRID_PX, GRID_PX), pygame.SRCALPHA)
    for h in game.heat_flashes:
        progress = 1.0 - h["life"] / h["max_life"]
        cx = int(h["c"] * TILE_PX + TILE_PX * 0.5)
        cy = int(h["r"] * TILE_PX + TILE_PX * 0.5)
        radius = int(8 + 38 * progress)
        alpha = int(150 * (1.0 - progress))
        pygame.draw.circle(heat_fx, (*COL_DANGER, alpha), (cx, cy), radius, 3)
    surface.blit(heat_fx, (0, 0))

    collapse_fx = pygame.Surface((GRID_PX, GRID_PX), pygame.SRCALPHA)
    for f in game.collapse_flashes:
        progress = 1.0 - f["life"] / f["max_life"]
        rect = pygame.Rect(f["c"] * TILE_PX + 4, f["r"] * TILE_PX + 4, TILE_PX - 8, TILE_PX - 8)
        alpha = int(190 * (1.0 - progress))
        inset = int(18 * progress)
        flash_rect = rect.inflate(-inset, -inset)
        pygame.draw.rect(collapse_fx, (*f["col"], alpha), flash_rect, 4, border_radius=12)
    surface.blit(collapse_fx, (0, 0))

    burst_fx = pygame.Surface((GRID_PX, GRID_PX), pygame.SRCALPHA)
    for p in game.particles:
        alpha = int(255 * (p["life"] / p["max_life"]))
        if alpha <= 0:
            continue
        x = int(p["x"])
        y = int(p["y"])
        if 0 <= x < GRID_PX and 0 <= y < GRID_PX:
            pygame.draw.circle(burst_fx, (*p["col"], alpha), (x, y), p["size"])
    surface.blit(burst_fx, (0, 0))

    if game.mode == MODE_SCAN and game.scan_preview is not None:
        pr, pc = game.scan_preview
        pulse_border = 2 + int((math.sin(ticks / 140) + 1) * 1.2)
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                nr, nc = pr + dr, pc + dc
                if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                    rect = pygame.Rect(nc * TILE_PX + 4, nr * TILE_PX + 4, TILE_PX - 8, TILE_PX - 8)
                    overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                    pygame.draw.rect(overlay, COL_SCAN_PREVIEW, overlay.get_rect(), border_radius=12)
                    surface.blit(overlay, rect.topleft)
                    pygame.draw.rect(surface, (87, 213, 255), rect, pulse_border, border_radius=12)

    scan_fx = pygame.Surface((GRID_PX, GRID_PX), pygame.SRCALPHA)
    for w in game.scan_waves:
        progress = 1.0 - w["life"] / w["max_life"]
        cx = int(w["c"] * TILE_PX + TILE_PX * 0.5)
        cy = int(w["r"] * TILE_PX + TILE_PX * 0.5)
        radius = int(10 + progress * TILE_PX * 1.9)
        alpha = int(180 * (1.0 - progress))
        pygame.draw.circle(scan_fx, (113, 225, 255, alpha), (cx, cy), radius, 3)
        pygame.draw.circle(scan_fx, (210, 247, 255, max(0, alpha - 80)), (cx, cy), max(4, radius // 2), 1)
    surface.blit(scan_fx, (0, 0))


def draw_panel(surface, game, font, font_sm, font_fact, ticks):
    panel_rect = pygame.Rect(GRID_PX, 0, PANEL_W, SCREEN_H)
    draw_vertical_gradient(surface, panel_rect, COL_PANEL_TOP, COL_PANEL_BOTTOM)
    game.ui_buttons.clear()

    x = GRID_PX + 16
    y = 16

    def text(txt, colour=COL_TEXT, f=font, yy=None):
        nonlocal y
        if yy is not None:
            y = yy
        rendered = f.render(txt, True, colour)
        surface.blit(rendered, (x, y))
        y += rendered.get_height() + 6

    shadow = font.render("QUANTUM FIREBREAK", True, (10, 26, 31))
    surface.blit(shadow, (x + 1, y + 1))
    text("QUANTUM FIREBREAK", COL_HIGHLIGHT)

    info_rect = pygame.Rect(GRID_PX + PANEL_W - 46, 14, 30, 30)
    game.ui_buttons["info"] = info_rect
    pygame.draw.rect(surface, COL_BTN_ACTIVE if game.show_info else COL_BTN, info_rect, border_radius=6)
    pygame.draw.rect(surface, (*COL_GLOW, 110), info_rect, 1, border_radius=6)
    info_txt = font.render("?", True, COL_HIGHLIGHT)
    surface.blit(
        info_txt,
        (
            info_rect.centerx - info_txt.get_width() // 2,
            info_rect.centery - info_txt.get_height() // 2,
        ),
    )
    y += 4

    stats_rect = pygame.Rect(x - 8, y, PANEL_W - 40, 106)
    pygame.draw.rect(surface, COL_CARD, stats_rect, border_radius=10)
    pygame.draw.rect(surface, (*COL_GLOW, 80), stats_rect, 1, border_radius=10)
    text(f"Turn: {game.turn} / {game.settings['max_turns']}", COL_TEXT, font_sm, yy=y + 10)
    text(f"AP: {game.ap} / {game.settings['ap_per_turn']}", COL_TEXT, font_sm)
    text(f"Burned: {game.burned_count} / {game.settings['burn_threshold']}", COL_TEXT, font_sm)
    text(f"Wind: {wind_label(game.wind_dir)}", COL_MUTED, font_sm)
    draw_wind_compass(surface, pygame.Rect(stats_rect.right - 70, stats_rect.y + 12, 54, 74), game.wind_dir, font_sm)
    y = stats_rect.bottom + 18

    modes = [
        (MODE_FIREBREAK, "1: Firebreak (1 AP)", "Create destructive interference"),
        (MODE_SCAN, "2: Measure Scan (1 AP)", "Collapse 3x3 superposition"),
        (MODE_CREW, "3: Deploy Crew (2 AP)", "Extinguish one fire"),
    ]
    for mode_id, label, desc in modes:
        btn_rect = pygame.Rect(x, y, PANEL_W - 32, 44)
        game.ui_buttons[mode_id] = btn_rect
        col = COL_BTN_ACTIVE if game.mode == mode_id else COL_BTN
        pygame.draw.rect(surface, col, btn_rect, border_radius=6)
        border_col = COL_HIGHLIGHT if game.mode == mode_id else COL_GRID_LINE
        border_w = 2 + int((math.sin(ticks / 220) + 1) * 0.5) if game.mode == mode_id else 1
        pygame.draw.rect(surface, border_col, btn_rect, border_w, border_radius=6)
        lbl = font_sm.render(label, True, COL_TEXT)
        surface.blit(lbl, (x + 8, y + 4))
        d = font_sm.render(desc, True, COL_MUTED)
        surface.blit(d, (x + 8, y + 22))
        y += 52

    y += 8
    text("E / Space: End Turn", COL_MUTED, font_sm)
    text("R: Restart (new random fact)", COL_MUTED, font_sm)
    text("H / ?: Info", COL_MUTED, font_sm)
    y += 6

    menu_rect = pygame.Rect(x, y, PANEL_W - 32, 38)
    game.ui_buttons["main_menu"] = menu_rect
    pygame.draw.rect(surface, COL_BTN, menu_rect, border_radius=6)
    pygame.draw.rect(surface, (*COL_GLOW, 105), menu_rect, 1, border_radius=6)
    menu_txt = font_sm.render("Main Menu", True, COL_HIGHLIGHT)
    surface.blit(
        menu_txt,
        (
            menu_rect.centerx - menu_txt.get_width() // 2,
            menu_rect.centery - menu_txt.get_height() // 2,
        ),
    )
    y = menu_rect.bottom + 12

    if game.message:
        for ln in wrap_text_lines(font_sm, game.message, PANEL_W - 40):
            text(ln, (255, 220, 100), font_sm)
        y += 6

    if game.game_over:
        result_col = COL_WIN if game.win else COL_LOSE
        result_txt = "VICTORY!" if game.win else "DEFEAT"
        text(result_txt, result_col, font)
        text("Press R to restart", COL_TEXT, font_sm)
        y += 4

    text("Legend", COL_HIGHLIGHT, font_sm)
    legend = [
        (COL_FOREST, "Forest"),
        (COL_BURNING, "Burning"),
        (COL_BURNED, "Burned"),
        (COL_FIREBREAK, "Firebreak"),
        (COL_AMP_HIGH, "Quantum fire amplitude"),
        (COL_ENTANGLE, "Entangled pair (E)"),
    ]
    for col, label in legend:
        pygame.draw.rect(surface, col, (x, y + 2, 14, 14), border_radius=3)
        lbl = font_sm.render(label, True, COL_TEXT)
        surface.blit(lbl, (x + 22, y))
        y += 20

    fact_y = y + 10
    fact_h = SCREEN_H - fact_y - 16
    if fact_h < 150:
        fact_h = 150
        fact_y = SCREEN_H - fact_h - 16
    fact_rect = pygame.Rect(x - 8, fact_y, PANEL_W - 40, fact_h)
    pygame.draw.rect(surface, COL_CARD, fact_rect, border_radius=10)
    pygame.draw.rect(surface, (*COL_GLOW, 95), fact_rect, 1, border_radius=10)

    text("Safety Fact", COL_FACT_TITLE, font, yy=fact_y + 10)
    lines = wrap_text_lines(font_fact, game.current_fact, PANEL_W - 54)
    line_h = font_fact.get_height() + 7
    max_lines = max(1, (fact_h - 30) // line_h)
    for ln in lines[:max_lines]:
        text(ln, COL_FACT_TEXT, font_fact)


def draw_info_overlay(surface, game, font, font_sm, font_fact):
    shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    shade.fill(COL_MODAL)
    surface.blit(shade, (0, 0))

    card = pygame.Rect(170, 82, SCREEN_W - 340, SCREEN_H - 164)
    pygame.draw.rect(surface, COL_MODAL_CARD, card, border_radius=10)
    pygame.draw.rect(surface, (*COL_GLOW, 120), card, 2, border_radius=10)

    x = card.x + 28
    y = card.y + 24
    max_w = card.width - 56

    title = font.render("Controls and Quantum Concepts", True, COL_HIGHLIGHT)
    surface.blit(title, (x, y))
    y += title.get_height() + 18

    sections = [
        (
            "Actions",
            [
                "1 or Firebreak: spend 1 AP to turn forest into a barrier. Nearby fire amplitude is reduced by destructive interference.",
                "2 or Measure Scan: spend 1 AP to measure a 3x3 area. Uncertain tiles collapse into either safe forest or active fire.",
                "3 or Crew: spend 2 AP to extinguish one burning tile. The tile is saved from spreading but counts as burned ground.",
                "E or Space: end the turn. R restarts. H, I, or ? opens and closes this panel.",
            ],
        ),
        (
            "Quantum Fire Model",
            [
                "Yellow-orange percentages are the chance that a forest tile collapses into fire when measured.",
                "Unmeasured tiles decohere each turn, so uncertainty drifts toward real fire if ignored.",
                "Purple E markers are entangled pairs. Measuring one can instantly influence its partner elsewhere.",
                f"Wind currently blows {wind_label(game.wind_dir).lower()}, making fire more likely to spread that way.",
            ],
        ),
        (
            "Goal",
            [
                f"Survive {game.settings['max_turns']} turns while keeping burned and burning tiles at {game.settings['burn_threshold']} or fewer.",
                "Scan when risk is concentrated, build firebreaks ahead of wind, and save crews for fires that can spread into open forest.",
            ],
        ),
    ]

    for heading, lines in sections:
        h = font_sm.render(heading, True, COL_FACT_TITLE)
        surface.blit(h, (x, y))
        y += h.get_height() + 6
        for line in lines:
            wrapped = wrap_text_lines(font_fact, line, max_w - 16)
            for idx, ln in enumerate(wrapped):
                prefix = "- " if idx == 0 else "  "
                rendered = font_fact.render(prefix + ln, True, COL_TEXT)
                surface.blit(rendered, (x + 8, y))
                y += rendered.get_height() + 3
        y += 11

    close = font_sm.render("Click anywhere outside this panel, press Esc, or press H to close.", True, COL_MUTED)
    surface.blit(close, (x, card.bottom - close.get_height() - 18))


def draw_social_good_overlay(surface, font, font_sm, font_fact):
    shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    shade.fill(COL_MODAL)
    surface.blit(shade, (0, 0))

    card = pygame.Rect(170, 82, SCREEN_W - 340, SCREEN_H - 164)
    pygame.draw.rect(surface, COL_MODAL_CARD, card, border_radius=10)
    pygame.draw.rect(surface, (*COL_GLOW, 120), card, 2, border_radius=10)

    x = card.x + 28
    y = card.y + 24
    max_w = card.width - 56

    title = font.render("UNESCO Social Good Connection", True, COL_HIGHLIGHT)
    surface.blit(title, (x, y))
    y += title.get_height() + 18

    sections = [
        (
            "Education for climate resilience",
            [
                "The game turns wildfire risk into an active learning system: players test prevention, detection, and response choices instead of only reading about them.",
                "It supports environmental awareness by showing how wind, dry fuel, delayed action, and containment planning can change outcomes.",
            ],
        ),
        (
            "Risk literacy and decision-making",
            [
                "Players compare tradeoffs under limited action points, which mirrors real disaster-risk decisions where time and resources are constrained.",
                "The scan mechanic teaches uncertainty: hidden risk is not the same as no risk, and better information can improve response planning.",
            ],
        ),
        (
            "Community benefit",
            [
                "Short safety facts reinforce practical preparedness messages while the simulation keeps learners engaged.",
                "The project can be used in classrooms or public-awareness demos to discuss forests, fire safety, climate adaptation, and responsible technology.",
            ],
        ),
    ]

    for heading, lines in sections:
        h = font_sm.render(heading, True, COL_FACT_TITLE)
        surface.blit(h, (x, y))
        y += h.get_height() + 6
        for line in lines:
            for idx, ln in enumerate(wrap_text_lines(font_fact, line, max_w - 16)):
                prefix = "- " if idx == 0 else "  "
                rendered = font_fact.render(prefix + ln, True, COL_TEXT)
                surface.blit(rendered, (x + 8, y))
                y += rendered.get_height() + 3
        y += 11

    close = font_sm.render("Click outside this panel or press Esc to close.", True, COL_MUTED)
    surface.blit(close, (x, card.bottom - close.get_height() - 18))


def draw_settings_overlay(surface, game, font, font_sm, font_fact):
    shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    shade.fill(COL_MODAL)
    surface.blit(shade, (0, 0))

    card = pygame.Rect(284, 70, 532, 700)
    pygame.draw.rect(surface, COL_MODAL_CARD, card, border_radius=10)
    pygame.draw.rect(surface, (*COL_GLOW, 120), card, 2, border_radius=10)

    x = card.x + 30
    y = card.y + 24
    title = font.render("Difficulty Settings", True, COL_HIGHLIGHT)
    surface.blit(title, (x, y))
    preset_text = font_sm.render(f"Profile: {game.difficulty_name}", True, COL_FACT_TITLE)
    surface.blit(preset_text, (card.right - preset_text.get_width() - 30, y + 4))
    y += 48

    for name in DIFFICULTY_PRESETS:
        rect = pygame.Rect(x, y, 144, 42)
        game.ui_buttons[f"preset:{name}"] = rect
        active = game.difficulty_name == name
        pygame.draw.rect(surface, COL_BTN_ACTIVE if active else COL_BTN, rect, border_radius=6)
        pygame.draw.rect(surface, COL_HIGHLIGHT if active else COL_GRID_LINE, rect, 1, border_radius=6)
        label = font_sm.render(name, True, COL_HIGHLIGHT)
        surface.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))
        x += 154
    x = card.x + 30
    y += 65

    rule_hints = {
        "initial_fires": "More is harder",
        "max_turns": "More is harder",
        "ap_per_turn": "More is easier",
        "entangled_pairs": "More uncertainty",
        "burn_threshold": "More is easier",
        "auto_ignite_percent": "Lower is harder",
    }
    for key, label, _minimum, _maximum, _step in DIFFICULTY_SETTINGS:
        rendered = font_fact.render(label, True, COL_TEXT)
        surface.blit(rendered, (x, y + 10))
        hint = font_sm.render(rule_hints[key], True, COL_MUTED)
        surface.blit(hint, (x + 168, y + 13))

        minus = pygame.Rect(card.right - 156, y + 4, 38, 38)
        plus = pygame.Rect(card.right - 48, y + 4, 38, 38)
        game.ui_buttons[f"setting:-:{key}"] = minus
        game.ui_buttons[f"setting:+:{key}"] = plus
        for rect, glyph in ((minus, "-"), (plus, "+")):
            pygame.draw.rect(surface, COL_BTN, rect, border_radius=6)
            pygame.draw.rect(surface, COL_GRID_LINE, rect, 1, border_radius=6)
            txt = font.render(glyph, True, COL_HIGHLIGHT)
            surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

        value = f"{game.settings[key]}%" if key == "auto_ignite_percent" else str(game.settings[key])
        value_txt = font.render(value, True, COL_FACT_TITLE)
        surface.blit(value_txt, (card.right - 96 - value_txt.get_width() // 2, y + 11))
        y += 58

    footer = (
        "Settings apply when starting or restarting a game. "
        "Entanglement controls linked tile pairs."
    )
    fy = card.bottom - 66
    for line in wrap_text_lines(font_sm, footer, card.width - 60):
        surface.blit(font_sm.render(line, True, COL_MUTED), (card.x + 30, fy))
        fy += 20
    close = font_sm.render("Esc: close", True, COL_MUTED)
    surface.blit(close, (card.right - close.get_width() - 30, card.bottom - 30))


def draw_main_menu(surface, game, font_title, font, font_sm, font_fact, ticks):
    draw_animated_backdrop(surface, ticks)
    game.ui_buttons.clear()

    left = 76
    top = 66
    max_w = 560

    title_shadow = font_title.render("QUANTUM FIREBREAK", True, (6, 18, 22))
    title = font_title.render("QUANTUM FIREBREAK", True, COL_HIGHLIGHT)
    surface.blit(title_shadow, (left + 2, top + 3))
    surface.blit(title, (left, top))

    subtitle = font.render("A turn-based wildfire containment strategy game", True, COL_FACT_TITLE)
    surface.blit(subtitle, (left + 2, top + 62))

    y = top + 112
    intro_lines = [
        "Forest fires can move fast when wind, dry fuel, and heat line up. In this game, each turn is a short emergency response window: build firebreaks, scan uncertain areas, and send crews before small ignitions become a regional disaster.",
        "The quantum-inspired fire model turns hidden risk into strategy. Unmeasured forest tiles can hold a fire probability, scans collapse that uncertainty into safe forest or active flame, and firebreaks reduce nearby fire amplitude.",
        f"Goal: survive {game.settings['max_turns']} turns while keeping burned and burning tiles at {game.settings['burn_threshold']} or fewer.",
    ]
    for paragraph in intro_lines:
        for line in wrap_text_lines(font_fact, paragraph, max_w):
            rendered = font_fact.render(line, True, COL_TEXT)
            surface.blit(rendered, (left, y))
            y += rendered.get_height() + 4
        y += 14

    fact_rect = pygame.Rect(left - 10, y + 2, max_w + 20, 132)
    pygame.draw.rect(surface, COL_CARD, fact_rect, border_radius=8)
    pygame.draw.rect(surface, (*COL_GLOW, 95), fact_rect, 1, border_radius=8)
    fact_title = font.render("Forest Fire Reality", True, COL_FACT_TITLE)
    surface.blit(fact_title, (fact_rect.x + 16, fact_rect.y + 12))
    fact_text = (
        "Firebreaks work by removing or separating fuel, while early detection gives crews time "
        "to contain flame fronts before wind-driven embers spread into new forest."
    )
    fy = fact_rect.y + 46
    line_h = font_fact.get_height() + 4
    max_fact_lines = max(1, (fact_rect.bottom - fy - 14) // line_h)
    for line in wrap_text_lines(font_fact, fact_text, fact_rect.width - 44)[:max_fact_lines]:
        rendered = font_fact.render(line, True, COL_FACT_TEXT)
        surface.blit(rendered, (fact_rect.x + 22, fy))
        fy += line_h

    button_y = SCREEN_H - 170
    start_rect = pygame.Rect(left, button_y, 176, 54)
    info_rect = pygame.Rect(left + 188, button_y, 168, 54)
    settings_rect = pygame.Rect(left + 368, button_y, 172, 54)
    social_rect = pygame.Rect(left, button_y + 66, 306, 46)
    quit_rect = pygame.Rect(left + 328, button_y + 66, 120, 46)
    game.ui_buttons["start_game"] = start_rect
    game.ui_buttons["menu_info"] = info_rect
    game.ui_buttons["menu_settings"] = settings_rect
    game.ui_buttons["social_good"] = social_rect
    game.ui_buttons["quit_game"] = quit_rect

    for rect, label, active in (
        (start_rect, "Start Game", True),
        (info_rect, "How to Play", False),
        (settings_rect, "Settings", False),
        (social_rect, "UNESCO Social Good", False),
        (quit_rect, "Quit", False),
    ):
        col = COL_BTN_ACTIVE if active else COL_BTN
        pygame.draw.rect(surface, col, rect, border_radius=6)
        pygame.draw.rect(surface, COL_HIGHLIGHT if active else (*COL_GLOW, 110), rect, 2, border_radius=6)
        label_txt = font.render(label, True, COL_HIGHLIGHT)
        surface.blit(
            label_txt,
            (
                rect.centerx - label_txt.get_width() // 2,
                rect.centery - label_txt.get_height() // 2,
            ),
        )

    hint = font_sm.render("Enter: start   H / ?: info   Settings: difficulty   Esc: quit", True, COL_MUTED)
    surface.blit(hint, (left, button_y + 126))

    preview = pygame.Rect(SCREEN_W - 412, 88, 316, 560)
    pygame.draw.rect(surface, (16, 49, 56), preview, border_radius=16)
    pygame.draw.rect(surface, (*COL_GLOW, 90), preview, 2, border_radius=16)
    cell = 54
    grid_x = preview.x + 23
    grid_y = preview.y + 24
    sample_states = [
        [FOREST, FOREST, BURNING, FOREST, FOREST],
        [FOREST, FIREBREAK, FOREST, BURNING, FOREST],
        [FOREST, FIREBREAK, FOREST, FOREST, FOREST],
        [FOREST, FOREST, FOREST, FIREBREAK, BURNING],
        [BURNED, FOREST, FOREST, FOREST, FOREST],
    ]
    for r, row in enumerate(sample_states):
        for c, state in enumerate(row):
            rect = pygame.Rect(grid_x + c * cell, grid_y + r * cell, cell - 8, cell - 8)
            pygame.draw.rect(surface, tile_colour(state), rect, border_radius=8)
            pygame.draw.rect(surface, COL_GRID_LINE, rect, 1, border_radius=8)
            draw_tile_detail(surface, state, rect, r, c, ticks)
            if state == BURNING:
                draw_flame(surface, rect, r, c, ticks)
    draw_wind_compass(surface, pygame.Rect(preview.x + 34, preview.y + 330, 66, 82), game.wind_dir, font_sm)
    wind = font.render(f"Wind: {wind_label(game.wind_dir)}", True, COL_FACT_TITLE)
    surface.blit(wind, (preview.x + 116, preview.y + 342))
    preview_text_x = preview.x + 34
    preview_text_w = preview.width - 68
    preview_y = preview.y + 432
    for line in wrap_text_lines(font_fact, "Watch wind, fuel, and hidden fire probability.", preview_text_w):
        rendered = font_fact.render(line, True, COL_TEXT)
        surface.blit(rendered, (preview_text_x, preview_y))
        preview_y += rendered.get_height() + 4
    preview_y += 8
    for idx, line in enumerate(wrap_text_lines(font_sm, "Build barriers ahead of the fire, scan risky clusters, and use crews where spread potential is highest.", preview_text_w)):
        rendered = font_sm.render(line, True, COL_MUTED)
        surface.blit(rendered, (preview_text_x, preview_y + idx * 21))


def draw_game_over_overlay(surface, game, font_title, font, font_sm, font_fact):
    shade = pygame.Surface((GRID_PX, SCREEN_H), pygame.SRCALPHA)
    shade.fill((8, 18, 20, 186))
    surface.blit(shade, (0, 0))

    card = pygame.Rect(86, 116, GRID_PX - 172, 586)
    pygame.draw.rect(surface, COL_MODAL_CARD, card, border_radius=10)
    pygame.draw.rect(surface, (*COL_GLOW, 130), card, 2, border_radius=10)

    result_col = COL_WIN if game.win else COL_LOSE
    result_txt = "WILDFIRE CONTAINED" if game.win else "CONTAINMENT FAILED"
    title = font_title.render(result_txt, True, result_col)
    surface.blit(title, (card.centerx - title.get_width() // 2, card.y + 26))

    outcome = (
        "Your response held the burned area within the safety limit."
        if game.win
        else "The burned area exceeded the containment limit."
    )
    outcome_txt = font_fact.render(outcome, True, COL_TEXT)
    surface.blit(outcome_txt, (card.centerx - outcome_txt.get_width() // 2, card.y + 76))

    stats = [
        ("Turns", f"{min(game.turn - 1, game.settings['max_turns'])} / {game.settings['max_turns']}"),
        ("Burned / Limit", f"{game.burned_count} / {game.settings['burn_threshold']}"),
        ("Firebreaks", str(game.stats["firebreaks"])),
        ("Scans", str(game.stats["scans"])),
        ("Crews", str(game.stats["crews"])),
    ]
    stat_y = card.y + 122
    stat_w = 112
    stat_gap = 10
    total_w = len(stats) * stat_w + (len(stats) - 1) * stat_gap
    stat_x = card.centerx - total_w // 2
    for idx, (label, value) in enumerate(stats):
        stat_rect = pygame.Rect(stat_x + idx * (stat_w + stat_gap), stat_y, stat_w, 78)
        pygame.draw.rect(surface, COL_CARD, stat_rect, border_radius=7)
        pygame.draw.rect(surface, (*COL_GLOW, 75), stat_rect, 1, border_radius=7)
        value_txt = font.render(value, True, COL_HIGHLIGHT)
        label_txt = font_sm.render(label, True, COL_MUTED)
        surface.blit(value_txt, (stat_rect.centerx - value_txt.get_width() // 2, stat_rect.y + 15))
        surface.blit(label_txt, (stat_rect.centerx - label_txt.get_width() // 2, stat_rect.y + 48))

    lesson_rect = pygame.Rect(card.x + 34, card.y + 228, card.width - 68, 172)
    pygame.draw.rect(surface, COL_CARD, lesson_rect, border_radius=8)
    pygame.draw.rect(surface, (*result_col, 125), lesson_rect, 2, border_radius=8)
    lesson_heading = "Why containment worked" if game.win else "Real-world wildfire lesson"
    lesson_title = font.render(lesson_heading, True, COL_FACT_TITLE)
    surface.blit(lesson_title, (lesson_rect.x + 20, lesson_rect.y + 17))
    lesson = game.outcome_fact or random.choice(WIN_FACTS if game.win else LOSS_FACTS)
    lesson_y = lesson_rect.y + 57
    for line in wrap_text_lines(font_fact, lesson, lesson_rect.width - 40):
        rendered = font_fact.render(line, True, COL_FACT_TEXT)
        surface.blit(rendered, (lesson_rect.x + 20, lesson_y))
        lesson_y += rendered.get_height() + 7

    prompt = "Try another response plan or return to the menu."
    prompt_txt = font_sm.render(prompt, True, COL_MUTED)
    surface.blit(prompt_txt, (card.centerx - prompt_txt.get_width() // 2, card.y + 430))

    restart_rect = pygame.Rect(card.centerx - 212, card.bottom - 82, 196, 48)
    menu_rect = pygame.Rect(card.centerx + 16, card.bottom - 82, 196, 48)
    game.ui_buttons["restart_game"] = restart_rect
    game.ui_buttons["main_menu"] = menu_rect
    for rect, label, emphasized in (
        (restart_rect, "Play Again", True),
        (menu_rect, "Main Menu", False),
    ):
        pygame.draw.rect(surface, COL_BTN_ACTIVE if emphasized else COL_BTN, rect, border_radius=6)
        pygame.draw.rect(surface, COL_HIGHLIGHT if emphasized else (*COL_GLOW, 110), rect, 2, border_radius=6)
        label_txt = font.render(label, True, COL_HIGHLIGHT)
        surface.blit(
            label_txt,
            (
                rect.centerx - label_txt.get_width() // 2,
                rect.centery - label_txt.get_height() // 2,
            ),
        )


def main():
    pygame.init()

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Quantum Firebreak")

    clock = pygame.time.Clock()

    font = pygame.font.SysFont("georgia", 20, bold=True)
    font_title = pygame.font.SysFont("georgia", 38, bold=True)
    font_sm = pygame.font.SysFont("trebuchetms", 15)
    font_fact = pygame.font.SysFont("trebuchetms", 18)

    game = Game()
    app_screen = SCREEN_MENU

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if app_screen == SCREEN_MENU:
                    if (game.show_info or game.show_social_good or game.show_settings) and event.key == pygame.K_ESCAPE:
                        game.show_info = False
                        game.show_social_good = False
                        game.show_settings = False
                    elif game.show_settings:
                        continue
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        game.reset()
                        app_screen = SCREEN_GAME
                    elif event.key in (pygame.K_h, pygame.K_i) or event.unicode == "?":
                        game.show_info = not game.show_info
                        game.show_social_good = False
                        game.show_settings = False
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                    continue

                if event.key == pygame.K_1:
                    game.mode = MODE_FIREBREAK
                elif event.key == pygame.K_2:
                    game.mode = MODE_SCAN
                elif event.key == pygame.K_3:
                    game.mode = MODE_CREW
                elif event.key in (pygame.K_h, pygame.K_i) or event.unicode == "?":
                    game.show_info = not game.show_info
                    game.show_social_good = False
                elif event.key == pygame.K_ESCAPE and game.show_info:
                    game.show_info = False
                elif event.key == pygame.K_ESCAPE and game.show_social_good:
                    game.show_social_good = False
                elif event.key in (pygame.K_e, pygame.K_SPACE):
                    if not game.game_over:
                        game.end_turn()
                elif event.key == pygame.K_r:
                    game.reset()
                elif event.key == pygame.K_ESCAPE:
                    app_screen = SCREEN_MENU
                    game.show_info = False
                    game.show_social_good = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if game.show_settings:
                    settings_card = pygame.Rect(284, 70, 532, 700)
                    if not settings_card.collidepoint(mx, my):
                        game.show_settings = False
                    else:
                        for name, rect in game.ui_buttons.items():
                            if not rect.collidepoint(mx, my):
                                continue
                            if name.startswith("preset:"):
                                game.apply_difficulty_preset(name.split(":", 1)[1])
                            elif name.startswith("setting:"):
                                _kind, direction, key = name.split(":")
                                game.adjust_setting(key, 1 if direction == "+" else -1)
                            break
                    continue
                if game.show_info or game.show_social_good:
                    info_card = pygame.Rect(170, 82, SCREEN_W - 340, SCREEN_H - 164)
                    if not info_card.collidepoint(mx, my):
                        game.show_info = False
                        game.show_social_good = False
                    continue

                if app_screen == SCREEN_MENU:
                    clicked_menu_button = False
                    for name, rect in game.ui_buttons.items():
                        if rect.collidepoint(mx, my):
                            clicked_menu_button = True
                            if name == "start_game":
                                game.reset()
                                app_screen = SCREEN_GAME
                            elif name == "menu_info":
                                game.show_info = True
                                game.show_social_good = False
                                game.show_settings = False
                            elif name == "menu_settings":
                                game.show_settings = True
                                game.show_info = False
                                game.show_social_good = False
                            elif name == "social_good":
                                game.show_social_good = True
                                game.show_info = False
                                game.show_settings = False
                            elif name == "quit_game":
                                running = False
                            break
                    if clicked_menu_button:
                        continue

                clicked_button = False
                for name, rect in game.ui_buttons.items():
                    if rect.collidepoint(mx, my):
                        clicked_button = True
                        if name == "info":
                            game.show_info = True
                            game.show_social_good = False
                        elif name == "restart_game":
                            game.reset()
                        elif name == "main_menu":
                            app_screen = SCREEN_MENU
                            game.show_info = False
                            game.show_social_good = False
                        elif name in (MODE_FIREBREAK, MODE_SCAN, MODE_CREW):
                            game.mode = name
                        break
                if clicked_button:
                    continue

                if mx < GRID_PX and my < GRID_PX and not game.game_over:
                    c = mx // TILE_PX
                    r = my // TILE_PX
                    if game.mode == MODE_FIREBREAK:
                        game.build_firebreak(r, c)
                    elif game.mode == MODE_SCAN:
                        game.scan_area(r, c)
                    elif game.mode == MODE_CREW:
                        game.deploy_crew(r, c)

        mx, my = pygame.mouse.get_pos()
        if app_screen == SCREEN_GAME and mx < GRID_PX and my < GRID_PX:
            game.scan_preview = (my // TILE_PX, mx // TILE_PX)
        else:
            game.scan_preview = None

        ticks = pygame.time.get_ticks()
        dt = 1.0 / FPS
        game.update_particles(dt)
        if app_screen == SCREEN_MENU:
            draw_main_menu(screen, game, font_title, font, font_sm, font_fact, ticks)
        else:
            draw_animated_backdrop(screen, ticks)
            draw_grid(screen, game, font_sm, ticks)
            draw_panel(screen, game, font, font_sm, font_fact, ticks)
            if game.game_over:
                draw_game_over_overlay(screen, game, font_title, font, font_sm, font_fact)
        if game.show_info:
            draw_info_overlay(screen, game, font, font_sm, font_fact)
        if game.show_social_good:
            draw_social_good_overlay(screen, font, font_sm, font_fact)
        if game.show_settings:
            draw_settings_overlay(screen, game, font, font_sm, font_fact)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
