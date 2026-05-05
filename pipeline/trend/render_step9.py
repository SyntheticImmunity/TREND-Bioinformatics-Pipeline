"""Render the project-specific Step-9 R script from a samplesheet.yaml.

The runner generates a per-run R script tailored to the user's samples,
DNA thresholds, and contrasts — preserving the manuscript R analysis verbatim
inside a template, with the sample-list and contrast-list bits substituted in.
The rendered script is saved to the run directory as `step9_rendered.R`, both
for execution and for human inspection (the bioinformatician path: open the
rendered script in RStudio and run cell-by-cell).
"""

from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Any

import yaml


# Per-template configuration. Each entry maps the project template name (as
# referenced by samplesheet.project) to its output filename prefix and the
# template file used for rendering.
_PROJECT_CONFIG: dict[str, dict[str, str]] = {
    "ovarian_cancer": {
        "template_file": "ovarian_cancer.R.template",
        "output_prefix": "ovca",
    },
}

DEFAULT_DNA_THRESHOLD = 3
DEFAULT_BC_THRESHOLD = 3

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates" / "r_scripts"


def load_samplesheet(path: Path) -> dict[str, Any]:
    """Read samplesheet.yaml and return the parsed dict."""
    with open(path) as f:
        return yaml.safe_load(f)


def render_step9(samplesheet: dict[str, Any]) -> str:
    """Return rendered R script text for the given parsed samplesheet."""
    project = samplesheet.get("project")
    if project not in _PROJECT_CONFIG:
        raise ValueError(
            f"Unknown project {project!r}. Known projects: "
            f"{sorted(_PROJECT_CONFIG)}"
        )
    cfg = _PROJECT_CONFIG[project]
    template_path = _TEMPLATES_DIR / cfg["template_file"]
    if not template_path.exists():
        raise FileNotFoundError(f"R template not found: {template_path}")

    samples = samplesheet.get("samples") or []
    if not samples:
        raise ValueError("samplesheet has no `samples:` entries")

    analysis = samplesheet.get("analysis") or {}
    contrasts = analysis.get("contrasts") or []
    if not contrasts:
        raise ValueError("samplesheet has no `analysis.contrasts:` entries")
    bc_threshold = int(analysis.get("bc_threshold", DEFAULT_BC_THRESHOLD))

    # Per-sample fields: every row becomes one (cell_line, replicate) pair.
    sample_name_vector = [f"{s['cell_line']}_r{s['replicate']}" for s in samples]
    dna_threshold_vector = [
        int(s.get("dna_threshold", DEFAULT_DNA_THRESHOLD)) for s in samples
    ]

    # Column-name list, grouped per cell line: all RNA reps, then all DNA reps,
    # matching the order the manuscript script's explicit-name select uses.
    cell_lines_in_order: list[str] = []
    samples_by_cell: dict[str, list[dict]] = {}
    for s in samples:
        if s["cell_line"] not in cell_lines_in_order:
            cell_lines_in_order.append(s["cell_line"])
        samples_by_cell.setdefault(s["cell_line"], []).append(s)

    column_lines: list[str] = []
    for cell in cell_lines_in_order:
        cell_samples = sorted(samples_by_cell[cell], key=lambda s: int(s["replicate"]))
        rna_cols = ", ".join(s["rna_fastq"] for s in cell_samples)
        dna_cols = ", ".join(s["dna_fastq"] for s in cell_samples)
        column_lines.append(f"    {rna_cols}, {dna_cols},")
    # Strip trailing comma from the last line (R won't accept dangling args).
    if column_lines:
        column_lines[-1] = column_lines[-1].rstrip(",")
    column_selector_names = "\n".join(column_lines)

    # mean_<cell>_RD_ratio block, one entry per cell line.
    mean_entries: list[str] = []
    for cell in cell_lines_in_order:
        cell_samples = sorted(samples_by_cell[cell], key=lambda s: int(s["replicate"]))
        median_cols = ",\n               ".join(
            f"median_{cell}_Lib4_RD_ratio_r{s['replicate']}" for s in cell_samples
        )
        mean_entries.append(
            f"      mean_{cell}_RD_ratio = rowMeans(\n"
            f"        select(., {median_cols}),\n"
            f"        na.rm = TRUE\n"
            f"      )"
        )
    mean_ratio_block = ",\n".join(mean_entries)

    # mean_<exp>_to_<ctrl>_RD_ratio per contrast.
    contrast_entries: list[str] = []
    for c in contrasts:
        exp = c["experimental"]
        ctrl = c["control"]
        col_name = f"mean_{exp}_to_{ctrl}_RD_ratio"
        contrast_entries.append(
            f"      {col_name} = mean_{exp}_RD_ratio / mean_{ctrl}_RD_ratio"
        )
    contrast_block = ",\n".join(contrast_entries)

    # First contrast drives arrange(); last contrast bounds the select(NA_count:...)
    primary_exp = contrasts[0]["experimental"]
    primary_ctrl = contrasts[0]["control"]
    primary_contrast_col = f"mean_{primary_exp}_to_{primary_ctrl}_RD_ratio"

    last_exp = contrasts[-1]["experimental"]
    last_ctrl = contrasts[-1]["control"]
    primary_contrast_col_last = f"mean_{last_exp}_to_{last_ctrl}_RD_ratio"

    template = Template(template_path.read_text())
    return template.substitute(
        COLUMN_SELECTOR_NAMES=column_selector_names,
        SAMPLE_NAME_VECTOR=_to_r_char_vector(sample_name_vector),
        DNA_THRESHOLD_VECTOR=_to_r_num_vector(dna_threshold_vector),
        MEAN_RATIO_BLOCK=mean_ratio_block,
        CONTRAST_BLOCK=contrast_block,
        PRIMARY_CONTRAST_COL=primary_contrast_col,
        PRIMARY_CONTRAST_COL_LAST=primary_contrast_col_last,
        BC_THRESHOLD=bc_threshold,
        OUTPUT_PREFIX=cfg["output_prefix"],
    )


def thresholds_supplied(samplesheet: dict[str, Any]) -> bool:
    """True iff every sample row has an explicit dna_threshold (no defaults used)."""
    for s in samplesheet.get("samples") or []:
        if "dna_threshold" not in s:
            return False
    return True


def _to_r_char_vector(values: list[str]) -> str:
    quoted = ", ".join(f'"{v}"' for v in values)
    return f"c({quoted})"


def _to_r_num_vector(values: list[int]) -> str:
    return f"c({', '.join(str(v) for v in values)})"
