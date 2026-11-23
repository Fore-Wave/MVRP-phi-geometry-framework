# Corrections log

Last updated: 2026-11-23 (revised after XReview cross-review 6f0dbb63, 23 Nov 2026). These corrections supersede the listed statements wherever they appear in earlier documents, READMEs or posts in this repository, on Zenodo or elsewhere. The raw data files are unchanged.

| # | Earlier statement | Correction |
|---|---|---|
| C1 | "N = 10, t = 9.8, p < 0.001, Cohen's d = 4.5" (Master Synthesis v3.1; phi-finder README) | **Withdrawn.** There are 7 trials, with one run per control condition (baseline, acoustic-only, φ-only), so no significance test is possible. |
| C2 | "0.09 ± 0.02 V vs 0.03 ± 0.01 V, N = 5, p = 0.008" and "+22.2 dB at 854 Hz" (July 2026 review) | **Withdrawn.** No data file contains these values. The logged spectra show a 7–10 dB difference, and their source runs are undocumented (see C6). |
| C3 | 9.36 V "fork ring" voltage, 9.34 V "bonus charge", 14 V transient (trials 6–7) | **Reclassified** as battery and instrument readings. The 9 V battery already reads above 9 V on its own before any test, as fresh 9 V cells do. These are not effects in the water. |
| C4 | "0.810 V beam spike, replicated" | **n = 1 at most.** Trials 4 and 5 are identical rows sharing one video, and each is a single 10 s reading. Now an exploratory (T2.5) item with its own test (edge test E3). |
| C5 | Baseline voltage given as 0.02, 0.01 or 0.0 V in different files | The raw CSV (`data/historical/`, 0.02 V) is authoritative. Ratios such as "3.5×" depend on which baseline is used, so we no longer quote them. |
| C6 | 854 Hz peaks, a 264 Hz subharmonic and HRV values (tracker EXP001–007) | **Excluded** until the source audio and video files are posted. |
| C7 | Q ≈ 200,000 from Q = 2πfτ (f = 528 Hz, τ = 60 s) | **Invalid.** τ is DC voltage relaxation, not acoustic ring-down. Q will be measured acoustically (piezo bowl test B2). |
| C8 | "854 Hz harmonic = time-crystal signature" | **Withdrawn as a claim.** A discrete time crystal responds at a fraction of the drive (f/2), and a vessel has its own modes. Now a T2.5 question with a test (A2). |
| C9 | "Seven pioneers independently converged on φ" | Restated as **inspiration (T3)**. The φ spacings are our own designs, not the pioneers' specifications. |
| C10 | φ-Finder LIGO p = 0.014 | **Withdrawn.** The v3 null drew ratios uniformly up to 8, which undercounts chance matches near 1.6. Replaced by a GWTC-3 population null and a φ-masked smoothed null, each calibrated on simulated φ-free data, plus a decoy gate. Bootstrap resampling is used for uncertainty only, not as a null, since it reproduces any clustering already at φ. Events examined in v3 are exploratory; confirmation uses events released after pre-registration. |

**Honest current status:** one pilot series of 7 unblinded trials, with suggestive differences and known confounds. No prospective, blinded or pre-registered trial has been run yet, and there is no independent replication.

See the white paper *Golden-Ratio Geometry as an Imposed Variable: An Open Benchtop Programme (MVRP)* for the full test plan, including the edge test and the piezo bowl.
