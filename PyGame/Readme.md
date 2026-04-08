# Quantum Firebreak — Prototype 1

**Developer:** Kristaps Licis, kl23081

## What has been implemented

A fully playable turn-based strategy game built with Python 3 and Pygame.

## AI Usage

AI was used to implement parts of code, fix bugs. First version was not playable so GitHub Copilot with Claude Opus 4.6 was used to make it playable.

### Core gameplay

- **10×10 grid** representing a wildfire region (forest, burning, burned, firebreak tiles)
- **20-turn game loop** with **2 Action Points per turn**
- **Three player actions:**
  - **Build Firebreak (1 AP):** place a barrier on a forest tile to block fire spread
  - **Scan (1 AP):** collapse a 3×3 area of uncertain fire risk into definite outcomes
  - **Deploy Crew (2 AP):** extinguish one burning tile
- **Win/Lose conditions:** win if ≤18 tiles burned after 20 turns; lose immediately if burned count exceeds 18

### Quantum concept: Superposition, Measurement, and Decoherence

The fire spread system implements quantum-inspired mechanics:

1. **Superposition (state uncertainty):** When fire is adjacent to forest, the neighboring tiles do not immediately catch fire. Instead, they accumulate a _pending risk_ value (0%–100%), representing an uncertain quantum state — the tile is neither burning nor safe until observed.

2. **Measurement / Collapse (Scan action):** The player's Scan action forces a 3×3 area of pending-risk tiles to collapse into a definite state. Each tile's risk value becomes the probability that it catches fire upon measurement. This is the core strategic decision — _when_ and _where_ to observe determines what becomes real.

3. **Decoherence:** Each turn, unscanned pending risk drifts upward (+5% per turn). If risk reaches 100%, the tile auto-collapses into fire without player observation. This models the loss of control over uncertain systems when left unobserved.

### UI

- Color-coded grid with pulsing shimmer effect on tiles with pending quantum risk
- Risk percentage displayed on uncertain tiles
- Side panel showing turn count, AP, burned tile count, action mode selector, legend
- Scan preview (blue 3×3 highlight on hover)
- Keyboard controls: 1/2/3 for action modes, E/Space to end turn, R to restart

## How to run

```
pip install pygame
python quantum_firebreak.py
```
