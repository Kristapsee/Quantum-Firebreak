# Quantum Concepts in Quantum Firebreak

This file explains how the game implements quantum-inspired ideas. The goal is not to simulate real quantum physics perfectly, but to use simplified mechanics that make the concepts understandable through gameplay.

## Overview

In the game, wildfire risk is represented as an uncertain quantum-like state. A forest tile can be safe, burning, burned, or protected by a firebreak. Some forest tiles are also uncertain: they are not burning yet, but they have a probability of becoming fire.

The main quantum-inspired ideas are:

- Superposition
- Probability amplitudes
- Measurement and collapse
- Decoherence
- Interference
- Entanglement

## Superposition

In quantum mechanics, superposition means a system can exist as a combination of multiple possible states before it is measured.

In the game, a forest tile can be treated as a combination of:

```text
|safe>
|fire>
```

The game represents this with two values:

```text
safe_amp
fire_amp
```

Conceptually:

```text
Tile = safe_amp |safe> + fire_amp |fire>
```

This means a tile can be uncertain. It is still drawn as forest, but it may have a displayed fire percentage. That percentage means the tile has some chance of becoming fire if measured or if it decoheres enough over time.

Code locations:

- `safe_amp` and `fire_amp` grids are created in `quantum_firebreak.py`, lines 122-123.
- Initial burning tiles are forced into the fire state on lines 153-154.
- Uncertain forest tiles are displayed with fire probability on lines 783-808.

## Probability Amplitudes

In real quantum mechanics, probabilities come from squared amplitudes. The game uses the same basic idea.

For each uncertain forest tile, the fire probability is calculated as:

```text
fire_probability = fire_amp^2 / (safe_amp^2 + fire_amp^2)
```

This is why the game stores amplitudes instead of directly storing a simple fire percentage.

Example:

- A tile with low `fire_amp` has a low chance of becoming fire.
- A tile with high `fire_amp` has a high chance of becoming fire.
- The displayed percentage on the grid is this calculated fire probability.

Code locations:

- The probability formula is implemented in `fire_probability()` on lines 241-251.
- The grid display calls `fire_probability()` when drawing uncertain tiles on lines 783-808.

## Measurement and Collapse

In quantum mechanics, measurement forces an uncertain system into one definite state.

In the game, the **Measure Scan** action is the measurement mechanic.

When the player scans a 3x3 area:

- Every uncertain forest tile in that area is measured.
- The tile collapses into either safe forest or active fire.
- The result is random, but weighted by the tile's fire probability.

If a tile collapses to fire:

```text
FOREST -> BURNING
```

If a tile collapses safe:

```text
FOREST -> FOREST
```

After collapse, the tile is reset to a definite safe basis state:

```text
safe_amp = 1.0
fire_amp = 0.0
```

This makes scanning useful but risky. Scanning gives information and can remove uncertainty, but it can also cause a dangerous uncertain tile to become real fire.

Code locations:

- `_collapse_tile()` performs the actual measurement collapse on lines 258-284.
- `_reset_to_safe_state()` resets a collapsed tile's amplitudes on lines 253-256.
- `scan_area()` applies measurement to a 3x3 area on lines 342-409.

## Decoherence

In real quantum physics, decoherence describes how a quantum system loses its fragile quantum behavior through interaction with the environment and starts behaving more classically.

In the game, decoherence means unmeasured fire risk becomes more real over time.

At the end of each turn, uncertain forest tiles drift toward fire:

- `fire_amp` increases.
- `safe_amp` decreases.
- The displayed fire probability rises.

If the probability becomes high enough, the tile can auto-ignite without being scanned.

Gameplay meaning:

- Ignoring uncertain tiles is dangerous.
- A small fire probability can become a serious threat after several turns.
- Scanning and firebreaks are ways to manage decoherence.

Code locations:

- End-of-turn decoherence is implemented on lines 479-490.
- Auto-ignition after high probability is implemented on lines 494-504.
- The auto-ignite threshold constant is on line 42.

## Interference

In quantum mechanics, interference happens when wave-like states combine. They can reinforce each other or cancel each other out.

The game uses firebreaks as a form of destructive interference.

When the player builds a firebreak:

- The selected forest tile becomes a firebreak.
- Nearby forest tiles have their `fire_amp` reduced.
- Nearby forest tiles have their `safe_amp` slightly increased.

This represents destructive interference against the fire state.

Gameplay meaning:

- Firebreaks are not just physical barriers.
- They also stabilize nearby uncertain tiles.
- A well-placed firebreak can lower fire probability before the tile ignites.

Code locations:

- `build_firebreak()` places a firebreak and applies immediate interference on lines 309-340.
- End-of-turn firebreak interference is applied again on lines 470-475.

## Entanglement

In quantum mechanics, entanglement means two systems are linked so that measuring one affects the other, even if they are separated.

In the game, some forest tiles are randomly assigned as entangled pairs. They are shown with a purple `E` marker and connected by animated purple lines.

When one entangled tile is measured:

- Its partner may also be affected.
- If the measured tile collapses to fire, the partner becomes more likely to collapse to fire.
- If the measured tile collapses safe, the partner becomes more likely to collapse safe.

This is a simplified version of entanglement. It is not a full physics simulation, but it demonstrates the idea of linked measurement outcomes.

Gameplay meaning:

- Scanning one tile can affect a distant tile.
- Entangled pairs create non-local consequences.
- Players should pay attention to purple `E` markers before scanning.

Code locations:

- Entangled pair storage is initialized on lines 144-145.
- `_create_entangled_pairs()` creates the linked pairs on lines 286-304.
- `scan_area()` applies partner influence during measurement on lines 371-387.
- Entangled links and `E` markers are drawn on lines 733-776.

## Fire Spread as Quantum Risk

Normal fire spread would simply turn nearby tiles into fire. This game instead spreads fire amplitude.

At the end of each turn:

- Burning tiles inject `fire_amp` into nearby forest tiles.
- Cardinal neighbors receive stronger spread than diagonal neighbors.
- Wind increases spread in its current direction.

The affected tiles usually remain forest at first, but their fire probability rises. This means the fire is represented as uncertainty before it becomes visible.

Code locations:

- `_spread_neighbours()` includes cardinal and diagonal spread targets on lines 175-181.
- End-of-turn fire spread creates `spread_delta` on lines 447-459.
- Spread is added to `fire_amp` on lines 463-466.

## Wind and Quantum Probability

Wind is not a quantum concept by itself. It is a classical environmental factor that changes how fire amplitude spreads.

For example:

- **Wind: East** means burning tiles push more `fire_amp` into eastern neighbors.
- **Wind: North** means burning tiles push more `fire_amp` into northern neighbors.

Wind increases the probability that certain nearby tiles will later become fire. It does not instantly ignite them.

This helps connect the quantum model to a wildfire simulation:

```text
burning tile + wind direction -> more fire_amp -> higher fire probability
```

Code locations:

- Initial wind direction is chosen on line 140.
- Wind may change at the start of `end_turn()` on lines 443-444.
- Wind increases spread strength on lines 457-458.
- The wind label and compass are shown in the side panel on lines 916-917.

## Quick Code Reference

| Concept | Main code locations in `quantum_firebreak.py` |
| --- | --- |
| Superposition state | Lines 122-123, 153-154 |
| Probability amplitudes | Lines 241-251 |
| Measurement / collapse | Lines 258-284, 342-409 |
| Decoherence | Lines 479-490 |
| Auto-ignition | Lines 42, 494-504 |
| Interference / firebreaks | Lines 309-340, 470-475 |
| Entanglement | Lines 144-145, 286-304, 371-387, 733-776 |
| Quantum fire spread | Lines 175-181, 447-466 |
| Wind | Lines 140, 443-444, 457-458, 916-917 |

## How to Explain the Game Simply

A short explanation:

> Quantum Firebreak represents wildfire risk as a quantum-inspired probability system. Forest tiles can be in a superposition of safe and fire states. Fire spread increases the fire amplitude, which raises the chance that a tile will collapse into fire. Scanning is measurement: it collapses uncertain tiles into either safe forest or burning fire. Firebreaks create destructive interference by lowering nearby fire amplitude. Unmeasured tiles decohere over time, becoming more likely to ignite. Some tiles are entangled, so measuring one can affect its partner elsewhere on the map.

## What Is Simplified

The game is inspired by quantum mechanics, but it is not a physically accurate quantum simulation.

Simplifications include:

- Tiles use two simple amplitudes instead of real quantum wavefunctions.
- Measurement uses random probability collapse, not a full quantum measurement model.
- Entanglement is implemented as paired tile influence, not real quantum state correlation.
- Firebreak interference is a gameplay analogy for destructive interference.
- Wind is a classical wildfire mechanic layered on top of the quantum-inspired probability system.

These simplifications make the concepts easier to understand and playable as a strategy game.
