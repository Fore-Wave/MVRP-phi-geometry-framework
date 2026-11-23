# MVRP Edge Test · Field Card (v1.2, one session)

The script logs every answer. By hand you write only the session header, the kick-off line and anything unusual. Use with `LOG_SHEETS.md`.

## 1 · Floor layout in inches (tape once, photograph, leave it down)

**Directions.** Stand on the midpoint **M**, facing *forward*: square to the line between the transducers, toward Line 1. "Right" means toward the right-hand transducer. Every position below is measured from M: so many inches right (or left), then so many inches forward (or back).

**Square the floor.** Tape the *transducer line* through M. Tape the *forward line* square to it, using 3-4-5: a point 30" along one and a point 40" along the other should be exactly **50"** apart.

| What | Right of M | Forward of M | Notes |
|---|---|---|---|
| Left transducer | −6" | 0" | Faces the right one; on a foam pad. Height: ____" |
| Right transducer | +6" | 0" | ≤ 12" apart in total |
| **Device station** (USB dongle) | +30" | 0" | On a foam pad. USB extension runs to the laptop desk. |
| Bowl center | −5.9" | +18.8" | 19.7" straight-line. Tape a circle around its base. Striker beside it on a pad. |
| Masking speaker | −46.6" | −37.8" | 60" out, back-left, facing M; separate power |
| Mic (masking gate) | at the nearest Phase 2 mark | | Head height |

**Cables (56" long).** Right transducer to the station: 24" along the transducer line. Left transducer: 4" back, across behind M, then along the line, about 44" with 12" spare. Tape both flat. The only line they cross is Line 2, within its first 4".

**Walking lines.** Run the tape from M straight through each line's end point (mark 16):

| Line (bearing from forward) | Mark 4 | Mark 8 | Mark 12 | Mark 16 (end) |
|---|---|---|---|---|
| Line 1 (25°) | 16.6" R, 35.7" fwd | 33.3" R, 71.4" fwd | 49.9" R, 107.0" fwd | 66.6" R, 142.7" fwd |
| Line 2 (162.5°) | 11.8" R, 37.5" back | 23.7" R, 75.1" back | 35.5" R, 112.6" back | 47.4" R, 150.2" back |
| Line 3 (300°) | 34.1" L, 19.7" fwd | 68.2" L, 39.4" fwd | 102.3" L, 59.1" fwd | 136.4" L, 78.7" fwd |

**Marks along each line** (mark k = k × 9.84", measured along the tape from M):

| Mark | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| from M | 9.8" | 1' 7.7" | 2' 5.5" | 3' 3.4" | 4' 1.2" | 4' 11.1" | 5' 8.9" | 6' 6.7" |
| **Mark** | **9** | **10** | **11** | **12** | **13** | **14** | **15** | **16** |
| from M | 7' 4.6" | 8' 2.4" | 9' 0.3" | 9' 10.1" | 10' 8.0" | 11' 5.8" | 12' 3.6" | 13' 1.5" |

If a transducer disc blocks Line 3, rotate all three lines together by the same angle and write down the new θ₀.

## 2 · Before each session (5 min)

Wi-Fi off · phone in airplane mode · laptop on battery · bowl in its circle · pads under the transducers and striker · masking speaker on · striker aimed · keypad paired · nobody else moving. Fill in the session header on the log sheet.

## 3 · Kick-off

Copy the **KICK-OFF timestamp** and the first 16 characters of the **SEAL** from the screen onto the log sheet. Leave `*_SEALED_order.json` unopened until the summary has run.

## 4 · Keypad codes

| Mode | Type | Example |
|---|---|---|
| Masking gate | 1 = on, 0 = off | `1` |
| Walk | the mark you called, 1–16; `17` means 16+ | `9` |
| Fixed | three digits: present 1 / absent 0 · confidence 1–3 · guess on 1 / off 0 | `121` = present, fairly sure, guess on |
| Any prompt (keyboard) | `n` plus a note: saved with a timestamp | `n dog barked` |

Always guess on/off, even with no idea. Guesses are a diagnostic, never a gate.

## 5 · Order of a full day

1. `maskcheck` (mic gate): must read **MASKED**. If not, raise `--noise-gain`, check the pads, and run it again.
2. `walk` on Line 1 (exploratory). The summary prints 8 suggested marks.
3. Pre-register those 8 marks with a dated GitHub commit or Zenodo note **before** step 4.
4. `fixed` with those marks and `--maskcheck <header.json>`: 128 trials, about 60–70 min with breaks between blocks.
5. `summary` → copy the verdict line onto the log sheet.
6. Upload the `.csv`, `_header.json`, `_notes.txt` and `_SEALED_order.json` to GitHub `data/prospective/` the same day, unedited.

## 6 · Safety

Forks or rods used as electrodes are lab-only from then on. Ventilate during cell tests, since electrolysis gives off hydrogen and chlorine. Use a battery or a bench supply at ≤ 9 V only. Tape cables flat. Keep masking noise ≤ 70 dBA at M.
