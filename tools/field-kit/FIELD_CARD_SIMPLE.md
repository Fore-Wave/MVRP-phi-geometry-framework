# MVRP Edge Test · Simple Field Card (transducers 86" apart)

**M** is the midpoint between the transducers. Face *forward*, square to the transducer line. Every position is measured from M. **3-4-5 check:** 30" along the transducer line and 40" along the forward line should be **50"** apart.

| Put this | Right (+) / Left (−) of M | Forward (+) / Back (−) of M |
|---|---|---|
| Left transducer (faces right one, on pad) | −43" | 0" |
| Right transducer (faces left one, on pad) | +43" | 0" |
| Dongle (device station, on pad) | 0" | −6" |
| Bowl center (tape a circle) | 0" | −19.7" |
| Masking speaker (facing M) | +74.6" | +29.0" |

**Cords (56"):** each runs about 43" from the dongle to its transducer, with 12½" spare. Tape them flat. Each crosses its line about 7" from M, before mark 1.

| Line | Direction | Mark 4 | Mark 8 | Mark 12 | Mark 16 (end) |
|---|---|---|---|---|---|
| **Line 1 (core)** | back-left, 42.5° off back | 26.6" L, 29.0" back | 53.2" L, 58.1" back | 79.8" L, 87.1" back | 106.4" L, 116.1" back |
| Line 2 | straight forward | 39.4" fwd | 78.7" fwd | 118.1" fwd | 157.5" fwd |
| Line 3 | back-right, 42.5° off back | 26.6" R, 29.0" back | 53.2" R, 58.1" back | 79.8" R, 87.1" back | 106.4" R, 116.1" back |

**Marks along any line** (measured along the tape from M): 1 = 9.8" · 2 = 1' 7.7" · 3 = 2' 5.5" · 4 = 3' 3.4" · 5 = 4' 1.2" · 6 = 4' 11.1" · 7 = 5' 8.9" · 8 = 6' 6.7" · 9 = 7' 4.6" · 10 = 8' 2.4" · 11 = 9' 0.3" · 12 = 9' 10.1" · 13 = 10' 8.0" · 14 = 11' 5.8" · 15 = 12' 3.6" · 16 = 13' 1.5"

## Each session

1. **Check:** Wi-Fi off · laptop on battery · pads under the transducers and striker · bowl in its circle · masking speaker on.
2. **Masking gate:** `maskcheck`, with the mic at the nearest mark. It must say **MASKED**.
3. **Copy** the KICK-OFF time and the first 16 characters of the SEAL onto the log sheet.
4. **Run** `walk` (exploratory) or `fixed` (confirmatory, with the 8 pre-registered marks).
5. **Run** `summary`, copy the VERDICT line, and upload the 4 session files to GitHub the same day.

| Keypad | Type |
|---|---|
| Masking gate | `1` = on · `0` = off |
| Walk | the mark you called, `1`–`16`; `17` means 16+ |
| Fixed | 3 digits: `1`/`0` present/absent · `1`–`3` confidence · `1`/`0` guess on/off (e.g. `121`) |

Safety: forks used as electrodes are lab-only from now on. Tape cords flat. Keep noise ≤ 70 dBA at M.
