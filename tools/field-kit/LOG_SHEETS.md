# MVRP Edge Test · Log Sheets (v1.2)

The script's CSV is the record of truth. These sheets back it up, hold what the script can't know, and catch anything the keypad missed.

## A · Session header (one per session)

| Field | Entry |
|---|---|
| Date · room · room temperature | |
| Mode (maskcheck / walk / fixed) · line · θ₀ | |
| KICK-OFF timestamp | |
| Seal (first 16 characters) · seed | |
| PiezoPhire pair · audio file · volume step · transducer height | |
| Noise gain · masking gate (largest band difference dB · MASKED Y/N) | |
| Striker (servo / manual) · isolation pads Y/N · device source | |
| Electrodes (rods / forks) · polarity · block number (cell tests only) | |
| Anything different from last session | |

## B · Masking gate (20 trials)

| # | Guess 1/0 | # | Guess 1/0 | # | Guess 1/0 | # | Guess 1/0 |
|---|---|---|---|---|---|---|---|
| 1 | | 6 | | 11 | | 16 | |
| 2 | | 7 | | 12 | | 17 | |
| 3 | | 8 | | 13 | | 18 | |
| 4 | | 9 | | 14 | | 19 | |
| 5 | | 10 | | 15 | | 20 | |

Screen result: largest band difference ____ dB · MASKED Y / N · guesses correct ____ / 20

## C · Phase 1 walk (Line ___)

The script shows round and direction; the condition stays sealed.

| # | Round | Dir | Mark | # | Round | Dir | Mark |
|---|---|---|---|---|---|---|---|
| 1 | | | | 17 | | | |
| 2 | | | | 18 | | | |
| 3 | | | | 19 | | | |
| 4 | | | | 20 | | | |
| 5 | | | | 21 | | | |
| 6 | | | | 22 | | | |
| 7 | | | | 23 | | | |
| 8 | | | | 24 | | | |
| 9 | | | | 25 | | | |
| 10 | | | | 26 | | | |
| 11 | | | | 27 | | | |
| 12 | | | | 28 | | | |
| 13 | | | | 29 | | | |
| 14 | | | | 30 | | | |
| 15 | | | | 31 | | | |
| 16 | | | | 32 | | | |

Suggested Phase 2 marks from the summary: __ __ __ __ __ __ __ __ · pre-registered at (commit / date): ________

## D · Phase 2 block sheet (print 4: block ___ of 4)

| # | Mark | Answer | # | Mark | Answer |
|---|---|---|---|---|---|
| 1 | | | 17 | | |
| 2 | | | 18 | | |
| 3 | | | 19 | | |
| 4 | | | 20 | | |
| 5 | | | 21 | | |
| 6 | | | 22 | | |
| 7 | | | 23 | | |
| 8 | | | 24 | | |
| 9 | | | 25 | | |
| 10 | | | 26 | | |
| 11 | | | 27 | | |
| 12 | | | 28 | | |
| 13 | | | 29 | | |
| 14 | | | 30 | | |
| 15 | | | 31 | | |
| 16 | | | 32 | | |

## E · Verdict line (copy from the summary)

| d50 A | d50 B | d50 C | d50 D | ΔDB [interval] | ΔDC [interval] | Masking | VERDICT |
|---|---|---|---|---|---|---|---|
| | | | | | | | PASS / KILL / INCONCLUSIVE |

Notes and anything unusual (with time):

&nbsp;

&nbsp;
