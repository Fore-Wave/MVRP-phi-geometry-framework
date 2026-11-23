# MVRP Field Kit · Index (v1.2, 23 Nov 2026)

Everything for the bench works offline. Print items 2 and 3 before each session.

| # | File | What it is | When |
|---|---|---|---|
| 1 | `INDEX.md` | This list | — |
| 2 | `FIELD_CARD.md` | Floor layout in inches, keypad codes, order of the day, safety | Setup and each session |
| 3 | `LOG_SHEETS.md` | Session header, masking gate, Phase 1 walk sheet, Phase 2 block sheet (print 4) | Each session |
| 4 | `blind_assistant.py` | Runs maskcheck, walk and fixed sessions, and writes the summary and verdict | Each session |
| 5 | `mvrp_rules.py` | The single pass/kill/inconclusive rule; S1 and C0 analysis; power simulation; `selftest` | Before data (selftest) and after cell runs |
| 6 | `striker/striker.ino` | Arduino sketch for the bowl and cushion servos | Once, at setup |
| 7 | `pilot_corrected.csv` | Pilot table with the duplicate flagged and the battery readings excluded | Reference |
| 8 | `README.md` | Install, wiring and validation results | Once, at setup |
| 9 | White paper v1.2 | The protocol: download it as a PDF from the doc | Reference |

## Install once (needs internet; the sessions themselves are offline)

```
pip install numpy sounddevice soundfile pyserial
python mvrp_rules.py selftest
python blind_assistant.py fixed --simulate --marks 4 6 8 10 11 12 14 16
python blind_assistant.py devices
```

## Checks before the first real session

- [ ] Layout taped and photographed (field card, section 1)
- [ ] Striker reaches the bowl rim and the cushion with the same travel
- [ ] Keypad types digits into the terminal from mark 16
- [ ] Masking gate reads MASKED
- [ ] The 8 Phase 2 marks are pre-registered (dated commit)
