import pygame
import sys
import random
import math

# ─── Constants ────────────────────────────────────────────────────────────────
GRID_SIZE = 10
TILE_PX = 56
GRID_PX = GRID_SIZE * TILE_PX
PANEL_W = 260
SCREEN_W = GRID_PX + PANEL_W
SCREEN_H = GRID_PX
FPS = 30

MAX_TURNS = 20
AP_PER_TURN = 2
BURN_THRESHOLD = 18  # lose if burned tiles exceed this

# Tile states
FOREST = 0
BURNING = 1
BURNED = 2
FIREBREAK = 3

# Action modes
MODE_FIREBREAK = "firebreak"
MODE_SCAN = "scan"
MODE_CREW = "crew"

# Colours
COL_FOREST = (34, 139, 34)
COL_BURNING = (220, 50, 20)
COL_BURNED = (60, 60, 60)
COL_FIREBREAK = (160, 120, 60)
COL_PENDING_LOW = (255, 255, 100)   # low risk overlay
COL_PENDING_HIGH = (255, 140, 0)    # high risk overlay
COL_BG = (20, 20, 30)
COL_PANEL = (30, 30, 45)
COL_TEXT = (220, 220, 220)
COL_HIGHLIGHT = (255, 255, 255)
COL_GRID_LINE = (50, 50, 60)
COL_SCAN_PREVIEW = (0, 180, 255, 100)
COL_BTN = (60, 60, 90)
COL_BTN_ACTIVE = (90, 90, 150)
COL_WIN = (50, 200, 50)
COL_LOSE = (200, 50, 50)


# ─── Game State ───────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.grid = [[FOREST for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        # Pending risk per tile (quantum superposition of fire spread)
        self.pending_risk = [[0.0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.turn = 1
        self.ap = AP_PER_TURN
        self.mode = MODE_FIREBREAK
        self.burned_count = 0
        self.game_over = False
        self.win = False
        self.message = ""
        self.scan_preview = None  # (row, col) centre for scan preview

        # Place initial fires (2-3 random spots)
        starts = random.sample(
            [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)],
            k=3,
        )
        for r, c in starts:
            self.grid[r][c] = BURNING

        self._count_burned()

    # ── helpers ───────────────────────────────────────────────────────────
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

    # ── Player Actions ────────────────────────────────────────────────────
    def build_firebreak(self, r, c):
        if self.ap < 1:
            self.message = "Not enough AP!"
            return False
        if self.grid[r][c] != FOREST:
            self.message = "Can only build on forest tiles."
            return False
        self.grid[r][c] = FIREBREAK
        self.pending_risk[r][c] = 0.0
        self.ap -= 1
        self.message = f"Firebreak built at ({r},{c})."
        return True

    def scan_area(self, r, c):
        """Scan a 3×3 area centred on (r,c). Collapses pending risk."""
        if self.ap < 1:
            self.message = "Not enough AP!"
            return False
        collapsed_fire = 0
        collapsed_safe = 0
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                nr, nc = r + dr, c + dc
                if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                    risk = self.pending_risk[nr][nc]
                    if risk > 0 and self.grid[nr][nc] == FOREST:
                        # Collapse: probability = risk value
                        if random.random() < risk:
                            self.grid[nr][nc] = BURNING
                            collapsed_fire += 1
                        else:
                            collapsed_safe += 1
                        self.pending_risk[nr][nc] = 0.0
        self.ap -= 1
        self.message = (
            f"Scan at ({r},{c}): {collapsed_fire} caught fire, "
            f"{collapsed_safe} safe."
        )
        self._count_burned()
        self._check_lose()
        return True

    def deploy_crew(self, r, c):
        if self.ap < 2:
            self.message = "Need 2 AP for crew!"
            return False
        if self.grid[r][c] != BURNING:
            self.message = "Crew can only extinguish burning tiles."
            return False
        self.grid[r][c] = BURNED  # extinguished but scorched
        self.ap -= 2
        self.message = f"Crew deployed at ({r},{c}). Fire extinguished."
        self._count_burned()
        return True

    # ── End‑of‑turn logic ─────────────────────────────────────────────────
    def end_turn(self):
        if self.game_over:
            return

        # 1. Burning tiles spread pending risk to forest neighbours
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] == BURNING:
                    for nr, nc in self._neighbours(r, c):
                        if self.grid[nr][nc] == FOREST:
                            # Add risk (capped at 1.0)
                            spread = random.uniform(0.15, 0.35)
                            self.pending_risk[nr][nc] = min(
                                1.0, self.pending_risk[nr][nc] + spread
                            )

        # 2. Decoherence: existing pending risk drifts upward
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.pending_risk[r][c] > 0 and self.grid[r][c] == FOREST:
                    self.pending_risk[r][c] = min(
                        1.0, self.pending_risk[r][c] + 0.05
                    )

        # 3. Auto‑collapse: risk at 1.0 → tile catches fire (full decoherence)
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.pending_risk[r][c] >= 1.0 and self.grid[r][c] == FOREST:
                    self.grid[r][c] = BURNING
                    self.pending_risk[r][c] = 0.0

        # 4. Burning tiles that already burned for a full previous turn → Burned
        #    (fire exhausts fuel after one turn of burning)
        # We mark currently burning tiles; they'll become BURNED next turn.
        # Implementation: tiles that were BURNING before spread stay BURNING
        # for one more turn then become BURNED.
        # Simple approach: each burning tile has a 40 % chance to burn out.
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] == BURNING:
                    if random.random() < 0.30:
                        self.grid[r][c] = BURNED

        # 5. Advance turn
        self.turn += 1
        self.ap = AP_PER_TURN
        self._count_burned()
        self._check_lose()

        # 6. Check win (survived all turns)
        if self.turn > MAX_TURNS and not self.game_over:
            self.game_over = True
            if self.burned_count <= BURN_THRESHOLD:
                self.win = True
                self.message = "You saved the community! Wildfire contained."
            else:
                self.win = False
                self.message = "Too many tiles burned. The region is devastated."

    def _check_lose(self):
        if self.burned_count > BURN_THRESHOLD and not self.game_over:
            self.game_over = True
            self.win = False
            self.message = "Fire overwhelmed the region! You lose."


# ─── Drawing helpers ──────────────────────────────────────────────────────────
def tile_colour(state):
    return {FOREST: COL_FOREST, BURNING: COL_BURNING, BURNED: COL_BURNED, FIREBREAK: COL_FIREBREAK}[state]


def lerp_colour(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_grid(surface, game, font_sm):
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            x = c * TILE_PX
            y = r * TILE_PX
            rect = pygame.Rect(x, y, TILE_PX, TILE_PX)

            # Base tile colour
            base = tile_colour(game.grid[r][c])
            pygame.draw.rect(surface, base, rect)

            # Pending‑risk overlay (shimmer for quantum uncertainty)
            risk = game.pending_risk[r][c]
            if risk > 0 and game.grid[r][c] == FOREST:
                overlay = pygame.Surface((TILE_PX, TILE_PX), pygame.SRCALPHA)
                # Pulsing alpha based on risk
                pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 300 + r + c)
                alpha = int((80 + 100 * risk) * pulse)
                col = lerp_colour(COL_PENDING_LOW, COL_PENDING_HIGH, risk)
                overlay.fill((*col, alpha))
                surface.blit(overlay, rect)
                # Show risk number
                txt = font_sm.render(f"{risk:.0%}", True, (0, 0, 0))
                surface.blit(txt, (x + TILE_PX // 2 - txt.get_width() // 2,
                                   y + TILE_PX // 2 - txt.get_height() // 2))

            # Fire emoji‑like symbol
            if game.grid[r][c] == BURNING:
                txt = font_sm.render("F", True, (255, 255, 200))
                surface.blit(txt, (x + TILE_PX // 2 - txt.get_width() // 2,
                                   y + TILE_PX // 2 - txt.get_height() // 2))

            # Grid lines
            pygame.draw.rect(surface, COL_GRID_LINE, rect, 1)

    # Scan preview (3×3 blue outline)
    if game.mode == MODE_SCAN and game.scan_preview is not None:
        pr, pc = game.scan_preview
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                nr, nc = pr + dr, pc + dc
                if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                    rect = pygame.Rect(nc * TILE_PX, nr * TILE_PX, TILE_PX, TILE_PX)
                    overlay = pygame.Surface((TILE_PX, TILE_PX), pygame.SRCALPHA)
                    overlay.fill((0, 180, 255, 60))
                    surface.blit(overlay, rect)
                    pygame.draw.rect(surface, (0, 180, 255), rect, 2)


def draw_panel(surface, game, font, font_sm):
    panel_rect = pygame.Rect(GRID_PX, 0, PANEL_W, SCREEN_H)
    pygame.draw.rect(surface, COL_PANEL, panel_rect)

    x = GRID_PX + 16
    y = 16

    def text(txt, colour=COL_TEXT, f=font, yy=None):
        nonlocal y
        if yy is not None:
            y = yy
        rendered = f.render(txt, True, colour)
        surface.blit(rendered, (x, y))
        y += rendered.get_height() + 6

    text("QUANTUM FIREBREAK", COL_HIGHLIGHT)
    y += 4
    text(f"Turn: {game.turn} / {MAX_TURNS}")
    text(f"AP:   {game.ap} / {AP_PER_TURN}")
    text(f"Burned: {game.burned_count} / {BURN_THRESHOLD}")
    y += 8

    # Mode buttons
    modes = [
        (MODE_FIREBREAK, "1: Firebreak (1 AP)", "Place barrier on forest"),
        (MODE_SCAN, "2: Scan (1 AP)", "Collapse 3x3 risk area"),
        (MODE_CREW, "3: Deploy Crew (2 AP)", "Extinguish one fire"),
    ]
    for mode_id, label, desc in modes:
        btn_rect = pygame.Rect(x, y, PANEL_W - 32, 44)
        col = COL_BTN_ACTIVE if game.mode == mode_id else COL_BTN
        pygame.draw.rect(surface, col, btn_rect, border_radius=6)
        pygame.draw.rect(surface, COL_HIGHLIGHT if game.mode == mode_id else COL_GRID_LINE, btn_rect, 2, border_radius=6)
        lbl = font_sm.render(label, True, COL_TEXT)
        surface.blit(lbl, (x + 8, y + 4))
        d = font_sm.render(desc, True, (160, 160, 180))
        surface.blit(d, (x + 8, y + 22))
        y += 52

    y += 8
    text("E / Space: End Turn", (180, 180, 200), font_sm)
    text("R: Restart", (180, 180, 200), font_sm)
    y += 8

    # Legend
    text("— Legend —", COL_HIGHLIGHT, font_sm)
    legend = [
        (COL_FOREST, "Forest"),
        (COL_BURNING, "Burning"),
        (COL_BURNED, "Burned"),
        (COL_FIREBREAK, "Firebreak"),
        (COL_PENDING_HIGH, "Pending Risk (quantum)"),
    ]
    for col, label in legend:
        pygame.draw.rect(surface, col, (x, y + 2, 14, 14))
        lbl = font_sm.render(label, True, COL_TEXT)
        surface.blit(lbl, (x + 22, y))
        y += 20

    # Message log
    y += 12
    if game.message:
        # Word‑wrap message
        words = game.message.split()
        lines = []
        line = ""
        for w in words:
            test = f"{line} {w}".strip()
            if font_sm.size(test)[0] < PANEL_W - 40:
                line = test
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
        for ln in lines:
            text(ln, (255, 220, 100), font_sm)

    # Game over overlay
    if game.game_over:
        y += 16
        result_col = COL_WIN if game.win else COL_LOSE
        result_txt = "VICTORY!" if game.win else "DEFEAT"
        text(result_txt, result_col, font)
        text("Press R to restart", COL_TEXT, font_sm)


# ─── Main Loop ────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Quantum Firebreak")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 18, bold=True)
    font_sm = pygame.font.SysFont("consolas", 14)

    game = Game()

    running = True
    while running:
        # ── Events ────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    game.mode = MODE_FIREBREAK
                elif event.key == pygame.K_2:
                    game.mode = MODE_SCAN
                elif event.key == pygame.K_3:
                    game.mode = MODE_CREW
                elif event.key in (pygame.K_e, pygame.K_SPACE):
                    if not game.game_over:
                        game.end_turn()
                elif event.key == pygame.K_r:
                    game.reset()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if mx < GRID_PX and my < GRID_PX and not game.game_over:
                    c = mx // TILE_PX
                    r = my // TILE_PX
                    if game.mode == MODE_FIREBREAK:
                        game.build_firebreak(r, c)
                    elif game.mode == MODE_SCAN:
                        game.scan_area(r, c)
                    elif game.mode == MODE_CREW:
                        game.deploy_crew(r, c)

        # ── Scan preview on hover ─────────────────────────────────────
        mx, my = pygame.mouse.get_pos()
        if mx < GRID_PX and my < GRID_PX:
            game.scan_preview = (my // TILE_PX, mx // TILE_PX)
        else:
            game.scan_preview = None

        # ── Draw ──────────────────────────────────────────────────────
        screen.fill(COL_BG)
        draw_grid(screen, game, font_sm)
        draw_panel(screen, game, font, font_sm)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
