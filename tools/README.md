# tools/

Maintenance and audit utilities. Not shipped to adopters — used by the maintainer to build fixtures, regenerate derived references, and spot-check the dashboard's analyses.

Contents:

- **`build_fixtures.py`** — deterministic regenerator for the bundled subsampled fixtures under `dashboard/example_data/`. Used to refresh the inputs and expected outputs that drive the dashboard's *Install check* tab.
- **`audit_ppm_ic.py`** — sanity audit of the PPM library: information content per position, total length distribution, and mismatch rate against the manuscript's quoted statistics.
- **`audit_variant_rank_vs_pwm.py`** — diagnostic for the per-variant rank-vs-PPM relationship — produced figures supporting the manuscript's variant-rank disclosure.
- **`score_e2f8_variants.py`** — one-off scoring script for the E2F8 case study, retained for the maintainer's reference.

Most readers can ignore this directory. To regenerate fixtures after the manuscript R script or library state changes, see the docstring at the top of `build_fixtures.py`.
