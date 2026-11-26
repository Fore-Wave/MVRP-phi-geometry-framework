#!/usr/bin/env python3
"""
MVRP Edge-Test Blind Assistant · v1.2 (revised after XReview 29771c7e, 24 Nov 2026)
===================================================================================
Runs the edge test (paper section 5.1) alone, with the PiezoPhire blinded by script.

  * KICK-OFF timestamp and a SHA-256 seal of the trial order; the order itself goes
    to a sealed file you open only after the summary.
  * PiezoPhire on/off by playing your cascade or equal-length silence into its input.
  * Arduino striker hits the bowl or a matched cushion at the start beep.
  * Pink noise from a separate speaker masks device sound.
  * MASKING GATE (instrument, not your guesses): with --mic, the masking check records
    the room at the nearest mark with the device on vs off. Masking holds when no 1/3-octave
    band from 50 Hz to 20 kHz differs by 1 dB or more, both in the steady state and in the
    1 s right after the device switches (switching transients). This is an operational
    acoustic check, not proof that no cue exists. Your on/off guesses are logged as a
    diagnostic only, because a real sensation could legitimately inform them.
  * Before the next trial the room must fall back to within 1 dB of the noise floor
    (mic), or a fixed wait is used (30 s after bowl trials, 15 s otherwise).
  * `summary` applies the pre-registered rule (paper 4.5 and 5.1) and prints the verdict.

Modes
  devices    list audio devices
  maskcheck  masking gate (mic) + 20-trial guess diagnostic, no bowl
  walk       Phase 1, exploratory: 4 Latin-square rounds x 4 conditions x Out/In = 32 trials
  fixed      Phase 2, confirmatory: 4 blocks x 4 conditions x 8 marks = 128 trials (fixed design)
  summary    python blind_assistant.py summary <session.csv>
  calibrate  joint simulation of the complete Phase 2 decision rule, with Monte Carlo error
  selftest   every gate x contrast-outcome combination through the Phase 2 hierarchy

Conditions: A nothing on | B device only | C bowl only | D both.
Mark k = k x 25 cm (k x 9.84 in).
"""
import argparse, csv, datetime as dt, hashlib, json, math, os, random, sys, time, threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mvrp_rules

CONDS = {"A": (False, False), "B": (True, False), "C": (False, True), "D": (True, True)}  # (device_on, bowl)
LATIN = ["ACBD", "DBCA", "CADB", "BDAC"]
CENSOR_CM = 425
SESOI_EDGE_CM = 50.0     # smallest edge push of interest
MAX_CM = 400.0           # 4 m: edges beyond this are censored
FAIL_FRAC = 0.05         # more than 5% flat bootstrap fits -> INCONCLUSIVE
FIXED_BLOCKS = 4         # registered block count (no adaptive change)
BOOT_REPS = 500          # bootstrap replicates for the standard error (identical in calibration and analysis)
Z_EDGE = 3.06            # interval = estimate +/- Z_EDGE x bootstrap SE; from CALIBRATION.json (97.5% joint quantile, worst structure)
CAL_Q = 0.975            # calibration quantile for z (margin over the 95% coverage target)
STRUCTS = {              # serial-dependence structures the decision rule is validated across
    "none":   (0.0, 0.0),        # (drift SD cm, AR(1) rho)
    "ar_mid": (30.0, 0.5),
    "ar_high": (50.0, 0.9),
}

def now_iso():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")

# ============================================================ hardware
class Hardware:
    def __init__(self, a):
        self.sim = a.simulate; self.on = False; self.mic = None; self.sr = 48000
        if self.sim: return
        import numpy as np, sounddevice as sd
        self.np, self.sd = np, sd
        if not a.cascade: sys.exit("--cascade <file.wav> is required unless --simulate")
        import soundfile as sf
        data, sr = sf.read(a.cascade, dtype="float32", always_2d=True)
        self.dev_sr = sr; self.cascade = data[:, 0].copy() * a.cascade_gain; self.cpos = 0
        self.dev_stream = sd.OutputStream(device=a.device_out, samplerate=self.dev_sr, channels=1,
                                          callback=self._dev_cb, blocksize=1024)
        n = self.sr * 30
        spec = np.fft.rfft(np.random.default_rng(1).standard_normal(n)); f = np.fft.rfftfreq(n, 1 / self.sr); f[0] = f[1]
        pink = np.fft.irfft(spec / np.sqrt(f), n).astype("float32")
        self.pink = pink / np.max(np.abs(pink)) * a.noise_gain; self.ppos = 0
        self.beeps, self.lock = [], threading.Lock()
        self.room_stream = sd.OutputStream(device=a.room_out, samplerate=self.sr, channels=1,
                                           callback=self._room_cb, blocksize=1024)
        self.dev_stream.start(); self.room_stream.start()
        self.mic = a.mic; self.ser = None
        if a.serial:
            import serial
            self.ser = serial.Serial(a.serial, 115200, timeout=2); time.sleep(2.0); self.ser.reset_input_buffer()

    def _dev_cb(self, out, frames, t, status):
        if not self.on: out[:] = 0; return
        c = self.cascade; idx = (self.np.arange(frames) + self.cpos) % len(c)
        out[:, 0] = c[idx]; self.cpos = (self.cpos + frames) % len(c)

    def _room_cb(self, out, frames, t, status):
        np = self.np; idx = (np.arange(frames) + self.ppos) % len(self.pink)
        buf = self.pink[idx].copy(); self.ppos = (self.ppos + frames) % len(self.pink)
        with self.lock:
            keep = []
            for b in self.beeps:
                k = min(frames, len(b)); buf[:k] += b[:k]
                if len(b) > frames: keep.append(b[frames:])
            self.beeps = keep
        out[:, 0] = np.clip(buf, -1, 1)

    def device(self, on): self.on = bool(on)

    def beep(self, hz=1000, ms=150, vol=0.5):
        if self.sim: return
        np = self.np; t = np.arange(int(self.sr * ms / 1000)) / self.sr
        b = (vol * np.sin(2 * np.pi * hz * t) * np.hanning(len(t))).astype("float32")
        with self.lock: self.beeps.append(b)

    def strike(self, bowl):
        if self.sim: return
        if self.ser: self.ser.write(b"B" if bowl else b"C"); self.ser.readline()
        else: print("  >>> MANUAL STRIKE:", "BOWL" if bowl else "CUSHION")

    def record(self, seconds):
        if self.sim or self.mic is None: return None
        x = self.sd.rec(int(seconds * self.sr), samplerate=self.sr, channels=1, device=self.mic); self.sd.wait()
        return x[:, 0]

    def level_db(self, seconds=1.0):
        x = self.record(seconds)
        return None if x is None else 10 * math.log10(float(self.np.mean(x ** 2)) + 1e-20)

    def close(self):
        if self.sim: return
        self.device(False); time.sleep(0.2); self.dev_stream.stop(); self.room_stream.stop()
        if self.ser: self.ser.close()

def third_octave_db(x, sr):
    import numpy as np
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2; f = np.fft.rfftfreq(len(x), 1 / sr)
    out = []
    nb = 27 if sr >= 44100 else 25                     # 50 Hz .. 20 kHz centres (12.7 kHz if sr < 44.1 kHz)
    for c in [50 * 2 ** (i / 3) for i in range(nb)]:
        m = (f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6)); out.append(10 * np.log10(spec[m].sum() + 1e-20))
    return np.array(out)

# ============================================================ session plumbing
def ask(prompt, valid, log_note, sim_answer=None):
    if sim_answer is not None: return sim_answer
    while True:
        s = input(prompt).strip().lower()
        if s.startswith("n ") or s == "n": log_note(s[1:].strip()); print("  note saved"); continue
        if valid(s): return s
        print("  ?")

def header(a, mode):
    return {"mode": mode, "kickoff": now_iso(), "version": "1.1", "line": a.line, "theta0_deg": a.theta0,
            "room_temp": a.room_temp, "piezo_pair": a.pair, "cascade_file": os.path.basename(a.cascade or "sim"),
            "volume_step": a.volume, "noise_gain": a.noise_gain, "mic": a.mic, "isolation_pads": a.pads,
            "device_audio_source": a.device_source,
            "striker": "servo" if a.serial else ("sim" if a.simulate else "manual"), "seed": a.seed}

def seal(trials, path, seed):
    blob = json.dumps({"seed": seed, "trials": trials}, sort_keys=True).encode()
    with open(path, "w") as f: f.write(blob.decode())
    return hashlib.sha256(blob).hexdigest()

def open_log(a, mode):
    base = os.path.join(a.outdir, f"edge_{mode}_{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(a.outdir, exist_ok=True)
    f = open(base + ".csv", "w", newline=""); w = csv.writer(f)
    w.writerow(["session", "mode", "trial", "block_or_round", "line", "mark", "distance_cm", "direction", "condition",
                "device_on", "bowl", "answer", "confidence", "device_guess", "t_start", "t_answer", "wait_s", "note"])
    notes = open(base + "_notes.txt", "a")
    def log_note(text): notes.write(f"{now_iso()}\t{text}\n"); notes.flush()
    return base, f, w, log_note

def save_header(base, h):
    with open(base + "_header.json", "w") as f: json.dump(h, f, indent=2)

def kickoff(h):
    print("=" * 66); print(f"MVRP edge test · {h['mode']}")
    print(f"KICK-OFF   {h['kickoff']}"); print(f"SEAL       sha256 {h['seal'][:16]}…")
    print("Copy both onto the field log. Do not open *_SEALED_order.json until after the summary."); print("=" * 66)

def wait_for_quiet(hw, a, bowl):
    """Next trial only when the room is back at the noise floor (mic), else a fixed wait."""
    if a.simulate: return 0.0
    t0 = time.monotonic()
    if hw.mic is not None and a.floor_db is not None:
        time.sleep(a.rest)
        while time.monotonic() - t0 < 120:
            lv = hw.level_db(1.0)
            if lv is None or lv <= a.floor_db + 1.0: break
    else:
        time.sleep(30.0 if bowl else 15.0)
    return round(time.monotonic() - t0, 1)


# keypad answers: a wireless number pad works from 13 ft away
#   fixed:  3 digits  [1 present | 0 absent][confidence 1-3][1 on | 0 off]   e.g. 121 = present, fairly sure, guess on
#   walk:   the mark number, 17 for "16+"      maskcheck: 1 on, 0 off
def valid_fixed(s):
    if len(s) == 3 and s[0] in "pa" and s[1] in "123" and s[2] in "of": return True
    return len(s) == 3 and s[0] in "10" and s[1] in "123" and s[2] in "10"

def keypad_fixed(s):
    if s[0] in "10": return ("p" if s[0] == "1" else "a") + s[1] + ("o" if s[2] == "1" else "f")
    return s

# ============================================================ modes
def run_maskcheck(a, hw):
    rng = random.Random(a.seed)
    states = [True] * 10 + [False] * 10; rng.shuffle(states)
    trials = [{"trial": i + 1, "device_on": s} for i, s in enumerate(states)]
    h = header(a, "maskcheck"); base, f, w, note = open_log(a, "maskcheck")
    h["seal"] = seal(trials, base + "_SEALED_order.json", a.seed); kickoff(h)
    print(f"Mic at mark {a.check_mark}, head height, no bowl. You stand there and guess: o = on, f = off.")
    on_b, off_b, on_t, off_t, correct = [], [], [], [], 0
    for t in trials:
        hw.device(t["device_on"]); xt = hw.record(1.0)          # switching-transient window
        time.sleep(max(0.0, a.settle - 1.0)); t0 = now_iso()
        x = hw.record(4.0)                                       # steady-state window
        if x is not None: (on_b if t["device_on"] else off_b).append(third_octave_db(x, hw.sr))
        if xt is not None: (on_t if t["device_on"] else off_t).append(third_octave_db(xt, hw.sr))
        hw.beep()
        sim = ("o" if (t["device_on"] if rng.random() < 0.5 + a.sim_leak else not t["device_on"]) else "f") if a.simulate else None
        g = ask(f"[{t['trial']:2d}/20] device on or off? (o/f, or keypad 1/0) ", lambda s: s in ("o", "f", "1", "0"), note, sim)
        g = {"1": "o", "0": "f"}.get(g, g)
        hw.device(False); correct += (g == "o") == t["device_on"]
        w.writerow([os.path.basename(base), "maskcheck", t["trial"], "", a.line, a.check_mark, a.check_mark * 25, "",
                    "B" if t["device_on"] else "A", int(t["device_on"]), 0, "", "", g, t0, now_iso(), "", ""]); f.flush()
        if not a.simulate: time.sleep(a.rest)
    masking = {"method": "none", "masked": None}
    if on_b and off_b:
        import numpy as np
        diff = np.mean(on_b, axis=0) - np.mean(off_b, axis=0); mx = float(np.max(np.abs(diff)))
        mt = float(np.max(np.abs(np.mean(on_t, axis=0) - np.mean(off_t, axis=0)))) if on_t and off_t else float("nan")
        floor = float(np.mean([10 * np.log10(np.sum(10 ** (b / 10))) for b in off_b]))
        masking = {"method": "mic", "max_band_diff_db": round(mx, 2), "max_transient_band_diff_db": round(mt, 2),
                   "top_band_hz": round(50 * 2 ** ((len(diff) - 1) / 3)),
                   "masked": bool(mx < 1.0 and mt < 1.0), "noise_floor_db": round(floor, 2)}
    elif a.simulate:
        masking = {"method": "sim", "masked": a.sim_leak < 0.2, "max_band_diff_db": 0.3 if a.sim_leak < 0.2 else 3.0}
    p = mvrp_rules_binom(correct, 20)
    masking["guess_diagnostic"] = {"correct": correct, "n": 20, "p_one_sided": round(p, 4)}
    h["masking"] = masking; save_header(base, h)
    if masking["masked"] is None:
        print("\nNo mic: masking UNVERIFIED. A fixed session can still run, but it cannot PASS.")
    else:
        print(f"\nMASKING GATE ({masking['method']}): largest band difference {masking['max_band_diff_db']} dB steady, "
              f"{masking.get('max_transient_band_diff_db', 'n/a')} dB in the switching window -> "
              + ("MASKED" if masking["masked"] else "NOT MASKED: raise --noise-gain, check isolation pads, recheck"))
    print(f"Guess diagnostic (not a gate): {correct}/20 correct, one-sided p = {p:.3f}")
    note(f"MASKCHECK {json.dumps(masking)}")
    print(f"For the fixed session add:  --maskcheck {base}_header.json")
    return base + ".csv"

def run_walk(a, hw):
    rng = random.Random(a.seed); rows = LATIN[:]
    first = rows.pop(0) if a.fix_round1 else None; rng.shuffle(rows); order = ([first] if first else []) + rows
    trials, n = [], 0
    for r, row in enumerate(order, 1):
        dirs = ["Out", "In"] if rng.random() < 0.5 else ["In", "Out"]
        for c in row:
            for d in dirs: n += 1; trials.append({"trial": n, "round": r, "cond": c, "dir": d})
    h = header(a, "walk"); base, f, w, note = open_log(a, "walk")
    h["seal"] = seal(trials, base + "_SEALED_order.json", a.seed); save_header(base, h); kickoff(h)
    print("EXPLORATORY. Answer with the mark number 1–16, or 16+. Metronome: one mark every 2 s.")
    for t in trials:
        dev, bowl = CONDS[t["cond"]]
        if not a.simulate:
            start = "the midpoint" if t["dir"] == "Out" else "mark 16"
            input(f"\n[{t['trial']:2d}/32] round {t['round']} · walk {t['dir'].upper()} from {start}. Enter when in place… ")
        hw.device(dev); time.sleep(a.settle); t0 = now_iso(); hw.beep(); hw.strike(bowl)
        if not a.simulate:
            for _ in range(17): time.sleep(2.0); hw.beep(hz=1500, ms=40, vol=0.25)
        sim = sim_walk(t, rng) if a.simulate else None
        m = ask("  mark called (1–16, or 16+ / 17): ", lambda s: s in ("16+", "17") or (s.isdigit() and 1 <= int(s) <= 16), note, sim)
        if m == "17": m = "16+"
        hw.device(False); dist = CENSOR_CM if m == "16+" else int(m) * 25
        ws = wait_for_quiet(hw, a, bowl)
        w.writerow([os.path.basename(base), "walk", t["trial"], t["round"], a.line, m, dist, t["dir"], t["cond"],
                    int(dev), int(bowl), m, "", "", t0, now_iso(), ws, ""]); f.flush()
    print("\nWalk complete. Run:  python blind_assistant.py summary", base + ".csv"); return base + ".csv"

def run_fixed(a, hw):
    if not a.marks or len(a.marks) != 8: sys.exit("--marks needs the 8 pre-registered marks")
    if a.blocks != FIXED_BLOCKS and not a.simulate: sys.exit(f"the registered design uses {FIXED_BLOCKS} blocks")
    masking = {"method": "none", "masked": None}
    if a.maskcheck:
        masking = json.load(open(a.maskcheck)).get("masking", masking); a.floor_db = masking.get("noise_floor_db")
    elif a.simulate:
        masking = {"method": "sim", "masked": a.sim_leak < 0.2}
    rng = random.Random(a.seed); trials, n = [], 0
    for b in range(1, a.blocks + 1):
        block = [(c, m) for c in "ABCD" for m in a.marks]; rng.shuffle(block)
        for c, m in block: n += 1; trials.append({"trial": n, "block": b, "cond": c, "mark": m})
    h = header(a, "fixed"); h.update(marks=a.marks, blocks=a.blocks, masking=masking)
    base, f, w, note = open_log(a, "fixed")
    h["seal"] = seal(trials, base + "_SEALED_order.json", a.seed); save_header(base, h); kickoff(h)
    if masking.get("masked") is not True:
        print("WARNING: masking not verified by mic for this session; it can be reported but cannot PASS.")
    print("Answer: p/a · confidence 1–3 · guess o/f  (e.g. p2f)  or keypad: 1/0 · 1–3 · 1/0  (e.g. 121)")
    drift = 0.0
    for t in trials:
        dev, bowl = CONDS[t["cond"]]
        if not a.simulate:
            input(f"\n[{t['trial']:3d}/{len(trials)}] block {t['block']} · go to MARK {t['mark']} "
                  f"({t['mark'] * 9.84:.0f} in), face away. Enter when ready… ")
        hw.device(dev); time.sleep(a.settle); t0 = now_iso(); hw.beep(); hw.strike(bowl)
        if not a.simulate: time.sleep(3.0)
        hw.beep(hz=600)
        sim = None
        if a.simulate:
            drift = a.sim_rho * drift + math.sqrt(1 - a.sim_rho ** 2) * rng.gauss(0, a.sim_drift_cm)
            sim = sim_fixed(t, dev, rng, a, drift)
        s = ask("  answer: ", valid_fixed, note, sim); s = keypad_fixed(s)
        hw.device(False); ws = wait_for_quiet(hw, a, bowl)
        w.writerow([os.path.basename(base), "fixed", t["trial"], t["block"], a.line, t["mark"], t["mark"] * 25, "",
                    t["cond"], int(dev), int(bowl), s[0], s[1], s[2], t0, now_iso(), ws, ""]); f.flush()
    print("\nFixed session complete. Run:  python blind_assistant.py summary", base + ".csv"); return base + ".csv"

# ============================================================ simulation (pipeline testing only)
def sim_walk(t, rng):
    base = {"A": 3, "B": 6, "C": 8, "D": 8}[t["cond"]] + rng.choice([-1, 0, 1]) + (1 if t["dir"] == "Out" else -1)
    return "16+" if base > 16 else str(max(1, base))

def sim_fixed(t, dev, rng, a, drift):
    d50 = {"A": 60, "B": 150, "C": 200, "D": 200 + a.sim_effect}[t["cond"]] + drift
    p = 1 / (1 + math.exp((t["mark"] * 25 - d50) / 25))
    ans = "p" if rng.random() < p else "a"
    guess = "o" if (dev if rng.random() < 0.5 + a.sim_leak else not dev) else "f"
    return f"{ans}2{guess}"

# ============================================================ statistics
def mvrp_rules_binom(k, n, p=0.5):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))

def firth_logit(X, y, iters=60):
    """Firth-penalized logistic regression: finite estimates even under complete separation."""
    import numpy as np
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        eta = np.clip(X @ b, -30, 30); mu = 1 / (1 + np.exp(-eta)); W = mu * (1 - mu) + 1e-10
        Xw = X * np.sqrt(W)[:, None]; inv = np.linalg.pinv(X.T @ (X * W[:, None]))
        h = np.einsum("ij,jk,ik->i", Xw, inv, Xw)
        step = inv @ (X.T @ (y - mu + h * (0.5 - mu)))
        sm = float(np.max(np.abs(step)))
        if sm > 5: step *= 5 / sm
        b = b + step
        if sm < 1e-7: break
    return b

def edge_fit(rows):
    """Condition-specific intercept and slope (per metre); block effects in sum-to-zero coding.
    Edge d50 = distance where the BLOCK-AVERAGED P(present) is 0.5, searched on 0–400 cm.
    Returns {cond: (cm, status)}, status in ok | above (>4 m) | below (<0) | flat (does not fall with distance)."""
    import numpy as np
    blocks = sorted({r["block"] for r in rows}); K = len(blocks); X, y = [], []
    for r in rows:
        x = []
        for c in "ABCD": on = 1.0 if r["cond"] == c else 0.0; x += [on, on * r["dist"] / 100]
        for b in blocks[:-1]: x.append(1.0 if r["block"] == b else (-1.0 if r["block"] == blocks[-1] else 0.0))
        X.append(x); y.append(1.0 if r["ans"] == "p" else 0.0)
    X, y = np.array(X), np.array(y); beta = firth_logit(X, y)
    beff = (list(beta[8:]) + [-float(np.sum(beta[8:]))]) if K > 1 else [0.0]
    grid = np.arange(0, MAX_CM + 1, 1.0); out = {}
    for i, c in enumerate("ABCD"):
        a0, a1 = beta[2 * i], beta[2 * i + 1]
        if a1 >= -1e-6: out[c] = (float("nan"), "flat"); continue
        P = np.mean([1 / (1 + np.exp(-(a0 + be + a1 * grid / 100))) for be in beff], axis=0)
        if P[0] < 0.5: out[c] = (0.0, "below")
        elif P[-1] > 0.5: out[c] = (MAX_CM, "above")
        else:
            j = int(np.argmax(P < 0.5)); x0, x1, p0, p1 = grid[j - 1], grid[j], P[j - 1], P[j]
            out[c] = (float(x0 + (p0 - 0.5) / (p0 - p1) * (x1 - x0)), "ok")
    return out

def edge_contrasts(rows, reps=1000, seed=7):
    """Bootstrap: resample trials within each condition x mark cell, across blocks.
    Replicates with a censored edge keep the censored value (0 or 400 cm); flat fits are counted as failures."""
    import numpy as np
    rng = np.random.default_rng(seed); est = edge_fit(rows); cells = {}
    for r in rows: cells.setdefault((r["cond"], r["dist"]), []).append(r)
    bDB, bDC, fails = [], [], 0
    for _ in range(reps):
        sample = []
        for cell in cells.values(): sample += [cell[i] for i in rng.integers(len(cell), size=len(cell))]
        e = edge_fit(sample)
        if any(e[c][1] == "flat" for c in "BCD"): fails += 1; continue
        bDB.append(e["D"][0] - e["B"][0]); bDC.append(e["D"][0] - e["C"][0])
    return est, np.array(bDB), np.array(bDC), fails / reps

def edge_interval(est, boot):
    """Stable interval: estimate +/- Z_EDGE x bootstrap SE (no extreme-tail order statistics)."""
    import numpy as np
    if len(boot) < 2: return float("nan"), float("nan")
    se = float(np.std(boot, ddof=1)); return est - Z_EDGE * se, est + Z_EDGE * se

def edge_decide(est, bDB, bDC, failfrac, masked):
    """Single Phase 2 decision hierarchy (paper §4.5 and §5.1). Applied in order; the first step that fires decides.
      1  Gate: masking verified by mic, else INCONCLUSIVE (reason 'masking').
      2  Gate: edges for B, C and D all 'ok' and <= 5% flat bootstrap fits, else INCONCLUSIVE (reason 'estimability').
      3  KILL if either contrast's upper bound < SESOI.
      4  PASS if both contrasts have lower bound > 0 and estimate >= SESOI.
      5  INCONCLUSIVE otherwise."""
    dDB = est["D"][0] - est["B"][0]; dDC = est["D"][0] - est["C"][0]
    ciDB, ciDC = edge_interval(dDB, bDB), edge_interval(dDC, bDC)
    o = dict(dDB=dDB, dDC=dDC, ciDB=ciDB, ciDC=ciDC, oDB="—", oDC="—")
    if not masked: return dict(o, verdict="INCONCLUSIVE", reason="gate 1: masking not verified by mic")
    if not (all(est[c][1] == "ok" for c in "BCD") and failfrac <= FAIL_FRAC and len(bDC) >= 100):
        return dict(o, verdict="INCONCLUSIVE", reason="gate 2: an edge for B, C or D not estimable in 0–4 m, or >5% flat bootstrap fits")
    o["oDB"] = mvrp_rules.classify(dDB, ciDB[0], ciDB[1], SESOI_EDGE_CM)
    o["oDC"] = mvrp_rules.classify(dDC, ciDC[0], ciDC[1], SESOI_EDGE_CM)
    return dict(o, verdict=mvrp_rules.combine_all([o["oDB"], o["oDC"]]), reason="")

def summary_fixed(rows, h, reps=BOOT_REPS):
    import numpy as np
    est, bDB, bDC, failfrac = edge_contrasts(rows, reps)
    masked = (h or {}).get("masking", {}).get("masked") is True
    d = edge_decide(est, bDB, bDC, failfrac, masked)
    dDB, dDC, ciDB, ciDC, oDB, oDC = d["dDB"], d["dDC"], d["ciDB"], d["ciDC"], d["oDB"], d["oDC"]
    verdict, reason = d["verdict"], (f" ({d['reason']})" if d["reason"] else "")
    print("\nPHASE 2 · stationary detection"); print("-" * 66)
    marks = sorted({r["dist"] for r in rows})
    print("% present by distance (cm):".ljust(28) + " ".join(f"{m:>5}" for m in marks))
    for c in "ABCD":
        sub = [r for r in rows if r["cond"] == c]
        print(f"  {c}".ljust(28) + " ".join(f"{100 * np.mean([r['ans'] == 'p' for r in sub if r['dist'] == m]):5.0f}" for m in marks))
    print("-" * 66)
    for c in "ABCD":
        v, s = est[c]
        txt = {"ok": f"{v:6.0f} cm ({v / 2.54:.0f} in)", "above": "> 400 cm (beyond 4 m)",
               "below": "< nearest mark (rarely or never felt)", "flat": "not estimable (no fall with distance)"}[s]
        print(f"  edge d50 {c}: {txt}")
    print(f"  ΔDB = {dDB:6.0f} cm   interval (est ± {Z_EDGE:.2f} SE) {ciDB[0]:6.0f} to {ciDB[1]:6.0f}   -> {oDB}")
    print(f"  ΔDC = {dDC:6.0f} cm   interval (est ± {Z_EDGE:.2f} SE) {ciDC[0]:6.0f} to {ciDC[1]:6.0f}   -> {oDC}")
    print(f"  flat bootstrap fits: {failfrac:.1%} (limit {FAIL_FRAC:.0%})")
    m = (h or {}).get("masking", {})
    print(f"  masking gate: {m.get('method', 'none')} · " + {True: "MASKED", False: "NOT MASKED", None: "UNVERIFIED"}[m.get("masked")])
    def acc(sel):
        s = [r for r in rows if sel(r)]; k = sum((r["guess"] == "o") == bool(r["dev"]) for r in s)
        return k, len(s), (mvrp_rules_binom(k, len(s)) if s else float("nan"))
    k1, n1, p1 = acc(lambda r: True); k2, n2, p2 = acc(lambda r: r["ans"] == "a")
    print(f"  guess diagnostic (not a gate): all {k1}/{n1} p={p1:.3f} · when 'absent' {k2}/{n2} p={p2:.3f}")
    print("    above-chance guessing on 'absent' trials suggests a leaking cue (sound, floor vibration, electrical)")
    print("-" * 66); print(f"  VERDICT (pre-registered, §4.5 and §5.1): {verdict}{reason}")
    print(f"  Hierarchy: gate 1 masking · gate 2 estimability · KILL if either upper bound < {SESOI_EDGE_CM:.0f} cm · "
          "PASS if both lower bounds > 0 and both estimates ≥ SESOI · else INCONCLUSIVE")
    return verdict

def summary_walk(rows, n=2000, seed=7):
    import numpy as np
    rng = np.random.default_rng(seed); by = {}
    for r in rows: by.setdefault((r["block"], r["cond"]), []).append(r["dist"])
    rm = {k: float(np.mean(v)) for k, v in by.items()}; rounds = sorted({k[0] for k in rm})
    print("\nPHASE 1 · walk (EXPLORATORY: path-dependent; never used for pass/kill)"); print("-" * 66)
    for c in "ABCD":
        v = [rm[(r, c)] for r in rounds if (r, c) in rm]
        cens = sum(1 for r in rows if r["cond"] == c and r["dist"] == CENSOR_CM)
        print(f"  {c}: round means {['%.0f' % x for x in v]}  median {np.median(v):.0f} cm ({np.median(v) / 2.54:.0f} in)"
              f"  range {min(v):.0f}–{max(v):.0f}  16+ {cens}")
    for c1, c2 in (("D", "B"), ("D", "C")):
        def stat(m): return np.median([m[(r, c1)] for r in rounds]) - np.median([m[(r, c2)] for r in rounds])
        obs = stat(rm); hits = 0
        for _ in range(n):
            m = dict(rm)
            for r in rounds:
                if rng.random() < 0.5: m[(r, c1)], m[(r, c2)] = rm[(r, c2)], rm[(r, c1)]
            hits += stat(m) >= obs
        print(f"  {c1}−{c2} median difference {obs:+.0f} cm   within-round permutation p {(hits + 1) / (n + 1):.3f} (exploratory)")
    mB = np.median([rm[(r, "B")] for r in rounds if (r, "B") in rm])
    lo, hi = max(1, round(mB / 2 / 25)), min(16, round(mB * 2 / 25))
    if hi - lo < 7: hi = min(16, lo + 7); lo = max(1, hi - 7)
    print("  Suggested Phase 2 marks (½× to 2× the median B edge):", sorted({int(round(x)) for x in np.linspace(lo, hi, 8)}))

def load_rows(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append({"block": int(r["block_or_round"] or 0), "cond": r["condition"], "dist": int(r["distance_cm"]),
                         "ans": r["answer"], "guess": r["device_guess"], "dev": int(r["device_on"]), "mode": r["mode"]})
    return rows

def run_summary(path):
    rows = load_rows(path); hp = path[:-4] + "_header.json"
    h = json.load(open(hp)) if os.path.exists(hp) else {}
    print(f"Summary of {os.path.basename(path)} · {len(rows)} trials · {now_iso()}")
    mode = rows[0]["mode"] if rows else ""
    if mode == "fixed": return summary_fixed(rows, h)
    if mode == "walk": return summary_walk(rows)
    if mode == "maskcheck": print(json.dumps(h.get("masking", {}), indent=2))

def run_selftest():
    """Every combination of gate states and contrast positions goes through edge_decide; checks the hierarchy."""
    import numpy as np
    n = 0
    for masked in (True, False):
        for status in ("ok", "above", "flat"):
            for ff in (0.0, 0.10):
                for dDB in (-100.0, 0.0, 30.0, 60.0, 150.0):
                    for dDC in (-100.0, 0.0, 30.0, 60.0, 150.0):
                        est = {"A": (50.0, "ok"), "B": (100.0, status), "C": (100.0, "ok")}
                        est["D"] = (100.0 + dDC, "ok"); est["B"] = (100.0 + dDC - dDB, status)
                        boot = np.random.default_rng(1).normal(0, 10, 500)
                        d = edge_decide(est, dDB + boot, dDC + boot, ff, masked); n += 1
                        gate_ok = masked and status == "ok" and ff <= FAIL_FRAC
                        if not gate_ok: assert d["verdict"] == "INCONCLUSIVE", (masked, status, ff, d)
                        else:
                            exp = mvrp_rules.combine_all([mvrp_rules.classify(d["dDB"], *d["ciDB"], SESOI_EDGE_CM),
                                                          mvrp_rules.classify(d["dDC"], *d["ciDC"], SESOI_EDGE_CM)])
                            assert d["verdict"] == exp
    print(f"edge selftest OK: {n} combinations; failed gates always INCONCLUSIVE, else the conjunctive rule")

def _sim_session(args):
    """One simulated Phase 2 session through the complete pipeline. Returns estimates, SEs and the verdict."""
    import numpy as np
    seed, eff, sd, rho, marks, z = args
    a = argparse.Namespace(sim_effect=eff, sim_leak=0.0, sim_drift_cm=sd, sim_rho=rho)
    rng = random.Random(seed); drift = 0.0; rows = []
    for b in range(1, FIXED_BLOCKS + 1):
        block = [(c, m) for c in "ABCD" for m in marks]; rng.shuffle(block)
        for c, m in block:
            drift = rho * drift + math.sqrt(1 - rho ** 2) * rng.gauss(0, sd)
            ans = sim_fixed({"cond": c, "mark": m}, CONDS[c][0], rng, a, drift)
            rows.append({"block": b, "cond": c, "dist": m * 25, "ans": ans[0], "guess": ans[2], "dev": int(CONDS[c][0])})
    est, bDB, bDC, ff = edge_contrasts(rows, reps=BOOT_REPS, seed=seed)
    global Z_EDGE; Z_EDGE = z
    d = edge_decide(est, bDB, bDC, ff, True)
    sDB = float(np.std(bDB, ddof=1)) if len(bDB) > 1 else float("nan")
    sDC = float(np.std(bDC, ddof=1)) if len(bDC) > 1 else float("nan")
    return dict(eDB=d["dDB"], eDC=d["dDC"], sDB=sDB, sDC=sDC, verdict=d["verdict"], gate=bool(d["reason"]))

def _cp(k, n, conf=0.95):
    """Clopper-Pearson interval for a simulated rate (its Monte Carlo error)."""
    from math import comb
    def cdf(x, p): return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(x + 1))
    def solve(f, lo=0.0, hi=1.0):
        for _ in range(60):
            mid = (lo + hi) / 2
            if f(mid): hi = mid
            else: lo = mid
        return (lo + hi) / 2
    a = (1 - conf) / 2
    lo = 0.0 if k == 0 else solve(lambda p: 1 - cdf(k - 1, p) >= a)
    hi = 1.0 if k == n else solve(lambda p: cdf(k, p) <= a)
    return round(k / n, 4), round(lo, 4), round(hi, 4)

def run_calibrate(a):
    """Two stages, separate seeds. Stage 1 sets Z_EDGE to the CAL_Q (97.5%) quantile of the joint |t| statistic under the
    worst dependence structure; the margin above 95% absorbs Monte Carlo error in z (a 95% quantile gave 94.0%
    validated coverage in run 1, see calib_run1_z95.log). Stage 2 validates the complete decision rule on fresh sessions and reports every
    rate with its Clopper-Pearson Monte Carlo interval."""
    import numpy as np
    from multiprocessing import Pool
    marks = a.marks or [4, 6, 8, 10, 11, 12, 14, 16]; n1, n2 = a.sessions, a.val_sessions
    truth = lambda eff: (50.0 + eff, eff)                      # simulator: d50 B=150, C=200, D=200+eff
    out = {"design": dict(cal_quantile=CAL_Q, blocks=FIXED_BLOCKS, marks=marks, boot_reps=BOOT_REPS, sesoi_cm=SESOI_EDGE_CM,
                          structures=STRUCTS, calibration_sessions_per_structure_and_effect=n1,
                          validation_sessions_per_cell=n2, tolerance=dict(joint_coverage_min=0.95,
                          joint_coverage_cp_lower_min=0.93, false_pass_max=0.025, false_pass_cp_upper_max=0.05))}
    with Pool(a.procs) as pool:
        zs = {}
        for name, (sd, rho) in STRUCTS.items():
            t = []
            for eff in (0.0, 100.0):
                res = pool.map(_sim_session, [(10_000 + 7919 * i + int(eff), eff, sd, rho, marks, 3.0) for i in range(n1)])
                tDB, tDC = truth(eff)
                t += [max(abs(r["eDB"] - tDB) / r["sDB"], abs(r["eDC"] - tDC) / r["sDC"]) for r in res
                      if r["sDB"] > 0 and r["sDC"] > 0 and not math.isnan(r["sDB"])]
            zs[name] = float(np.quantile(t, CAL_Q)); print(f"stage 1 {name}: {CAL_Q:.1%} quantile of joint |t| = {zs[name]:.3f} (n={len(t)})", flush=True)
        z = round(max(zs.values()) + 0.005, 2); out["stage1_joint_t95"] = zs; out["Z_EDGE"] = z
        val = {}
        for name, (sd, rho) in STRUCTS.items():
            for eff in (0.0, 100.0):
                res = pool.map(_sim_session, [(9_000_000 + 104729 * i + int(eff), eff, sd, rho, marks, z) for i in range(n2)])
                tDB, tDC = truth(eff); n = len(res)
                cov = sum(1 for r in res if r["sDB"] > 0 and abs(r["eDB"] - tDB) <= z * r["sDB"] and abs(r["eDC"] - tDC) <= z * r["sDC"])
                v = {o: sum(r["verdict"] == o for r in res) for o in ("PASS", "KILL", "INCONCLUSIVE")}
                val[f"{name}/effect_{int(eff)}cm"] = dict(n=n, joint_coverage=_cp(cov, n),
                    PASS=_cp(v["PASS"], n), KILL=_cp(v["KILL"], n), INCONCLUSIVE=_cp(v["INCONCLUSIVE"], n),
                    gate2_inconclusive=sum(r["gate"] for r in res))
                print(f"stage 2 {name} effect {eff:.0f}: {val[f'{name}/effect_{int(eff)}cm']}", flush=True)
        out["stage2_validation"] = val
        tol = out["design"]["tolerance"]
        out["tolerance_met"] = all(v["joint_coverage"][0] >= tol["joint_coverage_min"] and
                                   v["joint_coverage"][1] >= tol["joint_coverage_cp_lower_min"] for v in val.values()) and \
                               all(v["PASS"][0] <= tol["false_pass_max"] and v["PASS"][2] <= tol["false_pass_cp_upper_max"]
                                   for k, v in val.items() if k.endswith("effect_0cm"))
        print("TOLERANCE MET" if out["tolerance_met"] else "TOLERANCE NOT MET", flush=True)
    json.dump(out, open(a.out or "CALIBRATION.json", "w"), indent=2); print("written", a.out or "CALIBRATION.json")

# ============================================================ CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["devices", "maskcheck", "walk", "fixed", "summary", "calibrate", "selftest"])
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--device-out", type=int); ap.add_argument("--room-out", type=int); ap.add_argument("--mic", type=int)
    ap.add_argument("--cascade"); ap.add_argument("--cascade-gain", type=float, default=1.0)
    ap.add_argument("--noise-gain", type=float, default=0.15); ap.add_argument("--serial")
    ap.add_argument("--marks", type=int, nargs="*"); ap.add_argument("--blocks", type=int, default=4)
    ap.add_argument("--maskcheck", help="the *_header.json written by maskcheck")
    ap.add_argument("--fix-round1", action="store_true"); ap.add_argument("--check-mark", type=int, default=2)
    ap.add_argument("--settle", type=float, default=3.0); ap.add_argument("--rest", type=float, default=5.0)
    ap.add_argument("--line", default="1"); ap.add_argument("--theta0", default=""); ap.add_argument("--room-temp", default="")
    ap.add_argument("--pair", default="piezo"); ap.add_argument("--volume", default="")
    ap.add_argument("--pads", default="yes", help="isolation pads under PiezoPhire and striker: yes/no")
    ap.add_argument("--device-source", default="laptop on battery", help="what plays the cascade (logged)")
    ap.add_argument("--seed", type=int); ap.add_argument("--outdir", default="edge_sessions")
    ap.add_argument("--simulate", action="store_true"); ap.add_argument("--sim-effect", type=float, default=0.0)
    ap.add_argument("--sim-leak", type=float, default=0.0); ap.add_argument("--sim-rho", type=float, default=0.0)
    ap.add_argument("--sim-drift-cm", type=float, default=0.0)
    ap.add_argument("--sessions", type=int, default=300, help="calibrate: stage-1 sessions per structure and effect")
    ap.add_argument("--val-sessions", type=int, default=400, help="calibrate: stage-2 sessions per structure and effect")
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--out")
    a = ap.parse_args(); a.floor_db = None
    if a.mode == "summary":
        if not a.csv: sys.exit("usage: summary <session.csv>")
        return run_summary(a.csv)
    if a.mode == "devices":
        import sounddevice as sd; print(sd.query_devices()); return
    if a.mode == "calibrate": return run_calibrate(a)
    if a.mode == "selftest": return run_selftest()
    if a.seed is None: a.seed = random.SystemRandom().randrange(1, 2 ** 31)
    if a.simulate: a.settle = 0.0; a.rest = 0.0
    hw = Hardware(a)
    try: path = {"maskcheck": run_maskcheck, "walk": run_walk, "fixed": run_fixed}[a.mode](a, hw)
    finally: hw.close()
    if a.simulate: run_summary(path)

if __name__ == "__main__":
    main()
