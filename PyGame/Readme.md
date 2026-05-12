# Quantum Firebreak

**Developer:** Kristaps Licis, kl23081

## What has been implemented

A fully playable turn-based strategy game built with Python 3 and Pygame. The game combines wildfire containment with quantum-inspired mechanics: superposition, measurement, decoherence, interference, and entanglement.

## Core gameplay

- **10x10 grid** representing a wildfire region with forest, burning, burned, and firebreak tiles
- **20-turn game loop** with **2 Action Points per turn**
- **4 starting fires** placed randomly at the beginning of each game
- **Three player actions:**
  - **Build Firebreak (1 AP):** place a firebreak on a forest tile and stabilize nearby quantum fire amplitudes
  - **Scan / Measure (1 AP):** perform quantum measurement on a 3x3 area and collapse uncertain tiles into definite outcomes
  - **Deploy Crew (2 AP):** extinguish one burning tile
- **Win/Lose conditions:** win if 18 or fewer tiles are burned after 20 turns; lose immediately if burned count exceeds 18
- **Faster fire spread:** fire can now spread through cardinal neighbors and weaker diagonal ember drift
- **Wind system:** wind changes during the game and increases fire spread in its current direction
- **Natural burnout:** burning tiles may burn out on their own, but this is limited so the player cannot rely on it

## Quantum concept: Superposition, Measurement, and Decoherence

The fire spread system uses quantum-inspired amplitude mechanics instead of a normal pending-risk percentage.

1. **Superposition:**

   Each forest tile has two amplitudes:

   ```text
   Tile = safe_amp |safe> + fire_amp |fire>
   ```

   A tile with fire amplitude is uncertain. It is not burning yet, but it has a measurable chance to collapse into fire. The fire chance is calculated from squared amplitudes:

   ```text
   fire_probability = fire_amp^2 / (safe_amp^2 + fire_amp^2)
   ```

2. **Measurement / Collapse:**

   The player's Scan action performs quantum measurement on a 3x3 area. Each uncertain forest tile in that area collapses based on its `fire_probability`.

   - If measurement collapses to fire, the tile becomes burning.
   - If measurement collapses to safe, the tile remains forest.
   - After collapse, the tile resets to a safe basis state:

   ```text
   safe_amp = 1.0
   fire_amp = 0.0
   ```

   This makes scanning a strategic choice: observing an area can reveal danger early, but it can also force uncertain fire states to become real.

3. **Decoherence:**

   Unobserved forest tiles with fire amplitude slowly become less stable each turn, so their displayed fire percentage rises over time.

   - `fire_amp` increases slightly.
   - `safe_amp` decreases slightly.
   - If the calculated fire probability reaches the auto-ignite threshold, the tile becomes burning without a scan.

   This represents the superposition drifting toward a classical burning state when left unmeasured.

4. **Interference:**

   Firebreaks do more than physically block fire. They create destructive interference in nearby forest tiles.

   - Nearby `fire_amp` is reduced.
   - Nearby `safe_amp` is slightly increased.

   This makes firebreaks a quantum-inspired stabilization tool, not just a wall.

5. **Entanglement:**

   Some forest tiles are created as simple entangled pairs. Measuring one tile can also affect or collapse its partner.

   - If one tile collapses to fire, its partner becomes more likely to collapse to fire.
   - If one tile collapses safe, its partner becomes more likely to collapse safe.

   This keeps entanglement understandable while adding a small amount of non-local strategy.

## Wind system

Wind is shown in the side panel as **North**, **South**, **East**, or **West**.

Each turn, the wind may change direction. When a burning tile spreads fire amplitude to nearby forest tiles, the tile in the wind direction receives a stronger spread boost. For example:

- **Wind: East** means fire is more likely to push into the tile to the right of a burning tile.
- **Wind: North** means fire is more likely to push into the tile above a burning tile.

Wind does not instantly set tiles on fire. It increases `fire_amp`, which raises the displayed fire probability. If that probability keeps rising through spread and decoherence, the tile can later ignite or collapse into fire when scanned.

## UI

- Color-coded grid with pulsing shimmer effect on tiles with quantum fire amplitude
- Fire probability displayed on uncertain tiles
- Probability rings around uncertain tiles show risk at a glance
- High-risk uncertain tiles receive a pulsing red danger border
- Heat rings flash on tiles that receive a strong spread increase
- Burning tiles use animated flame shapes and ember effects
- Wind-driven ember streaks move across the board in the active wind direction
- Entangled forest tiles are marked with a purple `E` badge
- Active entangled pairs are connected by faint animated purple lines
- Particle bursts appear when building firebreaks, scanning, extinguishing, or when auto-ignition happens
- Scan actions create an expanding measurement wave and collapse flashes
- Side panel showing turn count, AP, burned tile count, wind direction, wind compass, action mode selector, and legend
- Action buttons in the side panel are clickable
- Victory and defeat use a centered game-over overlay with final stats
- Random fire-safety fact shown in the side panel on each game restart
- Scan preview with a blue 3x3 measurement highlight on hover
- Info/help overlay explaining controls and quantum concepts

## Fire safety facts data

- Facts are loaded from a separate file: `fire_safety_facts.txt`
- Each non-empty line is treated as one fact
- You can edit that file to add or replace facts without changing code

## Suggested reference sources

- U.S. Fire Administration (USFA): https://www.usfa.fema.gov/prevention/home-fires/
- National Fire Protection Association (NFPA): https://www.nfpa.org/public-education
- American Red Cross (fire safety): https://www.redcross.org/get-help/how-to-prepare-for-emergencies/types-of-emergencies/fire.html
- Ready.gov (wildfire and home fire preparedness): https://www.ready.gov/wildfires

## How to run

```bash
pip install pygame
python quantum_firebreak.py
```

## Controls

| Input | Action |
| --- | --- |
| `1` | Select Firebreak mode |
| `2` | Select Measure Scan mode |
| `3` | Select Crew mode |
| Left click grid | Use the selected action on a tile |
| Left click side-panel action button | Select that action mode |
| `E` or `Space` | End turn |
| `R` | Restart with a new random map and safety fact |
| `H`, `I`, or `?` | Open or close the info overlay |
| `Esc` | Close the info overlay |

## Strategy notes

- Build firebreaks ahead of the wind direction, not only next to current flames.
- Scan when a cluster of tiles has high fire probability, because unmeasured tiles decohere toward fire over time.
- Use crews on fires with many open forest neighbors, because those fires have the highest spread potential.
- Watch entangled `E` tiles before scanning: measuring one can also collapse or influence its partner.
