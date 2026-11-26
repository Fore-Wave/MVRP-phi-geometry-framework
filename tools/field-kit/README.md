# MVRP Field Kit · Edge-Test Blind Assistant (v1.2)

Runs the MVRP edge test (white paper §5.1) alone, with the PiezoPhire blinded by script. It also holds the single decision rule and the cell-test analysis (§4.5, §6). Start with `INDEX.md`.

| File | What it is |
|---|---|
| `blind_assistant.py` | Session runner and analysis: maskcheck, walk, fixed, summary, calibrate, selftest |
| `mvrp_rules.py` | The single decision hierarchy; schedules; S1, S1c and C0 analysis; deterministic sample-size algorithm; `selftest` |
| `striker/striker.ino` | Arduino sketch: two identical servos, one strikes the bowl, one a cushion |
| `FIELD_CARD.md`, `LOG_SHEETS.md`, `INDEX.md` | Printable bench pack (also as `MVRP_field_pack.pdf`) |
| `pilot_corrected.csv` | Pilot table: duplicate flagged, battery readings excluded |

## Setup

```
pip install numpy sounddevice soundfile pyserial
python mvrp_rules.py selftest
python blind_assistant.py selftest
python blind_assistant.py devices
```

**Hardware**

- **Audio.** The PiezoPhire's cables are 56" long, so its audio comes from a USB sound dongle at the *device station*, 6" behind the midpoint (transducers 86" apart). An active USB extension runs to the laptop (`--device-out`). The masking speaker gets its own output (`--room-out`).
- **Mic** for the masking gate and the room-quiet check (`--mic`). A USB mic or the laptop mic.
- **Arduino** with two servos on pins 9 and 10, a separate 5 V supply and a common ground. Upload `striker.ino` and set `HIT_BOWL` and `HIT_CUSH`.
- **Wireless number pad** for answers from up to 13 ft away. Keypad codes are on the field card.

## Run

```
COMMON="--device-out 3 --room-out 1 --mic 2 --cascade cascade.wav --serial /dev/tty.usbmodem101 --line 1 --theta0 222.5"
python blind_assistant.py maskcheck $COMMON                     # must read MASKED
python blind_assistant.py walk $COMMON --fix-round1             # exploratory
python blind_assistant.py fixed $COMMON --marks <8 pre-registered marks> --maskcheck edge_sessions/<maskcheck>_header.json
python blind_assistant.py summary edge_sessions/<session>.csv
```

## The rule (both scripts, paper §4.6)

One hierarchy, applied in order; the first step that fires decides:

1. **Gates.** Any failed eligibility gate gives INCONCLUSIVE. For the edge test: masking verified by mic, and edges for B, C and D estimable within 0–4 m with ≤ 5% flat bootstrap fits.
2. **KILL:** an upper bound is below the SESOI.
3. **PASS:** every lower bound is above 0 and every estimate is at or above the SESOI (plus any extra conditions).
4. **INCONCLUSIVE:** anything else.

For the edge test, SESOI = 50 cm on both ΔDB and ΔDC, and both must pass. Intervals are estimate ± z × bootstrap SE (500 replicates), with z from `CALIBRATION.json`. The design is fixed at 4 blocks. Guesses about the device are reported as a diagnostic only.

## Validation (simulated; marks 4 6 8 10 11 12 14 16)

| Check | Result |
|---|---|
| `mvrp_rules.py selftest` | 440 boundary cases + every outcome combination × gate state; schedules; S1, S1c, C0 cases |
| `blind_assistant.py selftest` | 300 gate × contrast combinations through the edge hierarchy |
| S1, no effect (200 sweeps, 10 blocks, SD 3 mV) | 0 PASS, 198 KILL, 2 INCONCLUSIVE |
| S1, true +10 mV excess, tone on only (100 sweeps) | 100 PASS |
| C0, clean 12 mV tone effect (100 runs of 10 blocks, SD 2 mV) | 75 PASS, 25 INCONCLUSIVE, 0 KILL |
| C0, no tone effect | 100 KILL |
| C0, artefact at 75% of the tone effect | 98 KILL, 2 INCONCLUSIVE, 0 PASS |
| Edge test calibration (`CALIBRATION.json`) | z = 3.06; 1,200 calibration + 1,800 validation sessions over 3 drift structures |
| Edge joint coverage, both contrasts | 97.3–98.3% in every cell (lowest 95% CP bound 94.8%) |
| Edge false PASS, no effect | 0.3–0.7% (highest 95% CP bound 2.4%) |
| Edge power at +100 cm | 95.3% (no drift), 85.0% (ρ 0.5), 71.3% (ρ 0.9) |
| Leaking device (simulated) | Fails the masking gate → INCONCLUSIVE |

A first calibration at the 95% quantile (z = 2.52) validated at 94.0% joint coverage, below the 95% tolerance, so it was replaced. Its log is kept as `calib_run1_z95.log`. These simulations test the pipeline and the rules, not perception. The design is fixed at 4 blocks; there is no adaptive block count.
