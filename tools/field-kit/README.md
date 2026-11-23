# MVRP Field Kit · Edge-Test Blind Assistant (v1.2)

Runs the MVRP edge test (white paper §5.1) alone, with the PiezoPhire blinded by script. It also holds the single decision rule and the cell-test analysis (§4.5, §6). Start with `INDEX.md`.

| File | What it is |
|---|---|
| `blind_assistant.py` | Session runner and analysis: maskcheck, walk, fixed, summary, coverage |
| `mvrp_rules.py` | Exclusive pass/kill/inconclusive rule; S1 and C0 analysis; power simulation; `selftest` |
| `striker/striker.ino` | Arduino sketch: two identical servos, one strikes the bowl, one a cushion |
| `FIELD_CARD.md`, `LOG_SHEETS.md`, `INDEX.md` | Printable bench pack (also as `MVRP_field_pack.pdf`) |
| `pilot_corrected.csv` | Pilot table: duplicate flagged, battery readings excluded |

## Setup

```
pip install numpy sounddevice soundfile pyserial
python mvrp_rules.py selftest
python blind_assistant.py devices
```

**Hardware**

- **Audio.** The PiezoPhire's cables are 56" long, so its audio comes from a USB sound dongle at the *device station*, 30" right of the midpoint. An active USB extension runs to the laptop (`--device-out`). The masking speaker gets its own output (`--room-out`).
- **Mic** for the masking gate and the room-quiet check (`--mic`). A USB mic or the laptop mic.
- **Arduino** with two servos on pins 9 and 10, a separate 5 V supply and a common ground. Upload `striker.ino` and set `HIT_BOWL` and `HIT_CUSH`.
- **Wireless number pad** for answers from up to 13 ft away. Keypad codes are on the field card.

## Run

```
COMMON="--device-out 3 --room-out 1 --mic 2 --cascade cascade.wav --serial /dev/tty.usbmodem101 --line 1 --theta0 25"
python blind_assistant.py maskcheck $COMMON                     # must read MASKED
python blind_assistant.py walk $COMMON --fix-round1             # exploratory
python blind_assistant.py fixed $COMMON --marks <8 pre-registered marks> --maskcheck edge_sessions/<maskcheck>_header.json
python blind_assistant.py summary edge_sessions/<session>.csv
```

## The rule (both scripts)

A smallest effect of interest (SESOI) and an interval give exactly one outcome:

- **KILL:** the upper bound is below the SESOI.
- **PASS:** the lower bound is above 0, the estimate is at or above the SESOI, and the extra conditions hold.
- **INCONCLUSIVE:** anything else.

For the edge test, SESOI = 50 cm on both ΔDB and ΔDC. The extra conditions are: the masking gate passed, and the edges for B, C and D can all be estimated within 0–4 m. Guesses about the device are reported as a diagnostic only.

## Validation (simulated; the marks used are 4 6 8 10 11 12 14 16)

| Check | Result |
|---|---|
| `mvrp_rules.py selftest` | 880 boundary cases, each with exactly one outcome |
| S1 with no effect (200 sweeps, 10 blocks, SD 3 mV) | 0 PASS |
| S1 with a true +10 mV excess (100 sweeps) | 100 PASS |
| Edge test with no effect (30 sessions) | 0 PASS |
| Edge test with a true +100 cm push (15 sessions) | 12 PASS |
| Edge interval coverage, 99.9% percentile, 120 sessions | 97.5% without drift, 95.8% with serial drift (SD 30 cm, ρ 0.5) |
| Leaking device (simulated) | Flagged NOT MASKED; cannot PASS |

These simulations test the pipeline and the rules, not perception. Rerun `coverage` with the drift estimated from your own Phase 1 data before the confirmatory session. If coverage is below 95%, use `--blocks 6`.
