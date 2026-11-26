# MVRP Edge Test · Field Card (v1.2.1, one session)

The script logs every answer. By hand you write only the session header, the kick-off line and anything unusual. Use with `LOG_SHEETS.md`.

## 1 · Floor layout in inches (transducers 86" apart; tape once, photograph, leave it down)

**Directions.** Stand on the midpoint **M**, halfway between the transducers, facing *forward*: square to the transducer line, along Line 2. "Right" means toward the right-hand transducer. Every position below is measured from M.

**Square the floor.** Tape the *transducer line* through M. Tape the *forward line* square to it, using 3-4-5: a point 30" along one and a point 40" along the other should be exactly **50"** apart.

| What | Right of M | Forward of M | Notes |
|---|---|---|---|
| Left transducer | −43" | 0" | Faces the right one; on a foam pad. Height: ____" |
| Right transducer | +43" | 0" | 86" apart in total |
| **Device station** (USB dongle) | 0" | −6" | On a foam pad. USB extension runs to the laptop desk. |
| Bowl center | 0" | −19.7" | 50 cm straight back. Tape a circle around its base. Striker beside it, on a pad, away from the lines. |
| Masking speaker | +74.6" | +29.0" | 80" out, facing M; separate power |
| Mic (masking gate) | at the nearest Phase 2 mark | | Head height |

**Cords (56" long).** Each runs about 43" from the dongle to its transducer, with 12½" spare. Tape both flat. The left cord crosses Line 1 and the right cord crosses Line 3, each about 7" from M, before mark 1. With the transducers 86" apart there is no route that avoids every line, because the lines fan out from M between them; this one crosses them nearest M.

**Walking lines.** Line 2 *is* the forward line. Lines 1 and 3 run back-left and back-right, each 42.5° off the back line. Every line stays at least 31.7" from both transducers.

| Line (bearing from forward) | Mark 4 | Mark 8 | Mark 12 | Mark 16 (end) |
|---|---|---|---|---|
| **Line 1 (222.5°, core)** | 26.6" L, 29.0" back | 53.2" L, 58.1" back | 79.8" L, 87.1" back | 106.4" L, 116.1" back |
| Line 2 (0°) | 39.4" fwd | 78.7" fwd | 118.1" fwd | 157.5" fwd |
| Line 3 (137.5°) | 26.6" R, 29.0" back | 53.2" R, 58.1" back | 79.8" R, 87.1" back | 106.4" R, 116.1" back |

**Marks along each line** (mark k = k × 9.84", measured along the tape from M):

| Mark | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| from M | 9.8" | 1' 7.7" | 2' 5.5" | 3' 3.4" | 4' 1.2" | 4' 11.1" | 5' 8.9" | 6' 6.7" |
| **Mark** | **9** | **10** | **11** | **12** | **13** | **14** | **15** | **16** |
| from M | 7' 4.6" | 8' 2.4" | 9' 0.3" | 9' 10.1" | 10' 8.0" | 11' 5.8" | 12' 3.6" | 13' 1.5" |

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
