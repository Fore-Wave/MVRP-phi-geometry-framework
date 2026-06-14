# Contributing to MVRP

Welcome! Every contribution — replication, critique, data, or code — improves the framework. Here's how to participate.

## Ways to Contribute

### 1. Replicate the Experiment
The most valuable contribution. Equipment costs < $150, one trial takes ~10 minutes.

- Read: [MVRP Onboarding Protocol v1.1](docs/protocols/)
- Run: All 4 conditions (Baseline, Acoustic Only, φ-Spacing, φ+Acoustic)
- Log: Use the [MVRP Data Dashboard](tools/mvrp_data_entry_dashboard_v2.html)
- Submit: Open a [Replication Report issue](.github/ISSUE_TEMPLATE/replication_report.md)

**Null results are equally valuable.** Please submit them.

### 2. Improve the Code
All tools are single-file HTML — easy to fork and modify.

```bash
git clone https://github.com/Fore-Wave/MVRP-phi-geometry-framework.git
cd MVRP-phi-geometry-framework
# Open any .html file in your browser — no build step needed
```

Submit improvements via Pull Request with a clear description of what changed and why.

### 3. Critique the Methodology
Open an issue with the `methodology` label. We welcome:
- Statistical challenges
- Confound identification
- Protocol improvement suggestions
- Theoretical framework critiques

### 4. Add Data
If you have measurement data relevant to φ-geometry effects, open a `data-contribution` issue with your dataset (CSV preferred).

## Tier System

All contributions must respect the Tier classification:

| Tier | Description | Claim Standard |
|------|-------------|----------------|
| **Tier 1** | Established physics | Citable, peer-reviewed, measurement-confirmed |
| **Tier 2** | Testable hypotheses | Experiment design attached, measurement-only claims |
| **Tier 3** | Speculation | Clearly labeled, never claimed as fact |

**Never mix tiers without explicit labeling.**

## Code Style

- Single-file HTML preferred (no build tools)
- Vanilla JS only (no framework dependencies unless critical)
- Comments explaining the science, not just the code
- Export functions for any data the tool generates

## Pull Request Checklist

- [ ] HTML validates without errors
- [ ] Works fully offline (no required internet connections for core features)
- [ ] New features have a clear Tier classification
- [ ] Data export still works (CSV at minimum)
- [ ] Tested in Chrome and Firefox

## Questions?

Open an issue or reach out via [X/@EvanTheHowell](https://x.com/EvanTheHowell).

---
*Open Science · Measurement-Only Claims · All Feedback Welcome*
