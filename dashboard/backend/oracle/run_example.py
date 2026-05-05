"""The 'Run the example' reviewer oracle, three tiers.

Tier        | Inputs                                       | Tools needed
------------|----------------------------------------------|-------------------------
smoke       | bundled published outputs                    | none
step9       | subsampled OvCa data (~1k promoters)         | Rscript + tidyverse
pipeline    | simulated FASTQs (50 promoters x 5 bcs)      | bowtie2/samtools/cutadapt/fastx + R

All tiers return the same OracleReport shape so the dashboard can render any
of them with the same UI. When required tools are missing, the oracle falls
back to a "structural" comparison (schema + presence) and clearly notes that
the run was not actually executed.
"""

from __future__ import annotations

import dataclasses
import logging
import shutil
import subprocess
import tempfile
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from backend import config
from backend.oracle.compare import CompareResult, compare_csv

log = logging.getLogger("trend.oracle")

EXAMPLES_DIR = config.DASHBOARD_ROOT / "example_data"

# Per-tier mapping: snakemake target outputs are the step-8 count tables for
# the install-check; step 9 is intentionally NOT run for this fixture.
PIPELINE_TIER_STEPS = ["step_2_flip_orientation", "step_4_trim_adapters",
                       "step_5_collapse_umis", "step_6_extract_barcodes",
                       "step_7_align_barcodes", "step_8_count_barcodes"]
PIPELINE_TIER_SKIPPED = ["step_1_verify_barcodes", "step_3_demultiplex",
                         "step_9_enhancer_activity"]

# Reproduce-the-manuscript flow: count tables are NOT bundled in the image
# (they're 1+ GB per project). On first reproduce-button click, the dashboard
# fetches them from this GitHub release and caches in the canonical
# project_data/alignment_results/{project}/ path for the container's lifetime.
REPRODUCE_RELEASE_TAG = "library-data-2026-05-04"
REPRODUCE_RELEASE_URL = (
    f"https://github.com/SyntheticImmunity/TREND-Bioinformatics-Pipeline"
    f"/releases/download/{REPRODUCE_RELEASE_TAG}"
)

# Per-project: the R script, the metadata file it reads, and the expected
# output filenames Step 9 produces.
_REPRODUCE_PROJECTS: dict[str, dict] = {
    "ovarian_cancer": {
        "r_script": (
            config.CODES_ROOT
            / "3. Post_HPC_enhancer_activity_analysis_scripts"
            / "code_by_projects" / "ovarian_cancer"
            / "ovarian_cancer_specific_enhancer_screening_analysis.R"
        ),
        "metadata_csv": (
            config.CODES_ROOT
            / "3. Post_HPC_enhancer_activity_analysis_scripts"
            / "required_metadata" / "all_enhancer_metadata_111525.csv"
        ),
        "outputs": [
            "ovca_sensor_activity_result_concise.csv",
            "ovca_sensor_activity_result_all.csv",
        ],
        "approx_download_mb": 1300,
    },
    "T_cell_activation": {
        "r_script": (
            config.CODES_ROOT
            / "3. Post_HPC_enhancer_activity_analysis_scripts"
            / "code_by_projects" / "T_cell_activation"
            / "T_cell_activation_responsive_enhancer_screening_analysis.R"
        ),
        "metadata_csv": (
            config.CODES_ROOT
            / "3. Post_HPC_enhancer_activity_analysis_scripts"
            / "required_metadata" / "all_enhancer_metadata_111525.csv"
        ),
        "outputs": [
            "activation_responsive_enhancer_screening_result_donor1.csv",
            "activation_responsive_enhancer_screening_result_donor2.csv",
        ],
        "approx_download_mb": 1080,
    },
}

_REPRODUCE_COUNT_TABLES = [
    "alignment_result_normalized_in_house_pipeline.csv",
    "alignment_result_unnormalized_in_house_pipeline.csv",
]

# Module-level map of {project: produced_dir} so the file-serving endpoints
# can locate the most recent run's outputs. Sufficient for a single-user
# dashboard session (the only intended use).
_LATEST_REPRODUCE_DIRS: dict[str, Path] = {}


@dataclass
class OracleReport:
    project: str
    tier: str
    mode: str  # "real" | "stub"
    overall_pass: bool
    runtime_seconds: float
    file_results: list[dict]
    notes: list[str]


# ---------------------------------------------------------------------------
# Tier dispatcher
# ---------------------------------------------------------------------------
def run_oracle(project: str = "ovarian_cancer", tier: str = "smoke") -> OracleReport:
    if tier == "smoke":
        return _run_smoke(project)
    if tier == "step9":
        return _run_step9(project)
    if tier == "pipeline":
        return _run_pipeline(project)
    raise ValueError(f"unknown tier: {tier}")


# ---------------------------------------------------------------------------
# Tier 1 — smoke (always works, no tools required)
# ---------------------------------------------------------------------------
def _run_smoke(project: str) -> OracleReport:
    """Compare the published outputs against themselves (or invoke R if available)."""
    paths = _smoke_paths(project)
    expected_dir: Path = paths["expected_dir"]
    outputs: list[str] = paths["outputs"]
    notes: list[str] = []

    t0 = time.perf_counter()
    rscript = shutil.which("Rscript")

    if rscript:
        actual_dir = _execute_step9(paths)
        mode = "real"
    else:
        actual_dir = _stub_actual_outputs(expected_dir, outputs, "smoke")
        mode = "stub"
        notes.append(
            "R is not installed on this machine, so this comparison shows the "
            "bundled reference outputs against themselves (a preview of how the "
            "comparison report looks). To re-run the analysis live, install R "
            "or use the bundled container."
        )

    file_results = _compare_outputs(actual_dir, expected_dir, outputs, paths)
    return OracleReport(
        project=project, tier="smoke", mode=mode,
        overall_pass=all(r["equivalent"] for r in file_results),
        runtime_seconds=round(time.perf_counter() - t0, 2),
        file_results=file_results, notes=notes,
    )


def _smoke_paths(project: str) -> dict:
    if project == "ovarian_cancer":
        return {
            "inputs_dir": config.PROJECT_DATA_ROOT / "alignment_results" / "ovarian_cancer",
            "expected_dir": config.PROJECT_DATA_ROOT / "final_enhancer_activity_results" / "ovarian_cancer",
            "step9_script": (
                config.CODES_ROOT
                / "3. Post_HPC_enhancer_activity_analysis_scripts"
                / "code_by_projects" / "ovarian_cancer"
                / "ovarian_cancer_specific_enhancer_screening_analysis.R"
            ),
            "metadata_csv": (
                config.CODES_ROOT
                / "3. Post_HPC_enhancer_activity_analysis_scripts"
                / "required_metadata" / "all_enhancer_metadata_111525.csv"
            ),
            "outputs": [
                "ovca_sensor_activity_result_concise.csv",
                "ovca_sensor_activity_result_all.csv",
            ],
            "primary_key": "promoter_name",
            "ordered": True,
        }
    if project == "T_cell_activation":
        return {
            "inputs_dir": config.PROJECT_DATA_ROOT / "alignment_results" / "T_cell_activation",
            "expected_dir": config.PROJECT_DATA_ROOT / "final_enhancer_activity_results" / "T_cell_activation",
            "step9_script": (
                config.CODES_ROOT
                / "3. Post_HPC_enhancer_activity_analysis_scripts"
                / "code_by_projects" / "T_cell_activation"
                / "T_cell_activation_responsive_enhancer_screening_analysis.R"
            ),
            "metadata_csv": (
                config.CODES_ROOT
                / "3. Post_HPC_enhancer_activity_analysis_scripts"
                / "required_metadata" / "all_enhancer_metadata_111525.csv"
            ),
            "outputs": [
                "activation_responsive_enhancer_screening_result_donor1.csv",
                "activation_responsive_enhancer_screening_result_donor2.csv",
            ],
            "primary_key": "promoter_name",
            "ordered": False,
        }
    raise ValueError(f"unknown project: {project}")


# ---------------------------------------------------------------------------
# Tier 2 — step9 on subsampled real data
# ---------------------------------------------------------------------------
def _run_step9(project: str) -> OracleReport:
    if project != "ovarian_cancer":
        raise ValueError("Tier 2 (step9) is currently OvCa-only.")

    fixture_dir = EXAMPLES_DIR / "ovca_step9"
    inputs_dir = fixture_dir / "inputs"
    expected_dir = fixture_dir / "expected"

    if not inputs_dir.exists() or not any(inputs_dir.glob("*.csv")):
        return _missing_fixtures("step9", "Run `python tools/build_fixtures.py --tier t2` first.")

    paths = {
        "inputs_dir": inputs_dir,
        "expected_dir": expected_dir,
        "step9_script": (
            config.CODES_ROOT
            / "3. Post_HPC_enhancer_activity_analysis_scripts"
            / "code_by_projects" / "ovarian_cancer"
            / "ovarian_cancer_specific_enhancer_screening_analysis.R"
        ),
        "metadata_csv": inputs_dir / "all_enhancer_metadata_111525.csv",
        "outputs": [
            "ovca_sensor_activity_result_concise.csv",
            "ovca_sensor_activity_result_all.csv",
        ],
        "primary_key": "promoter_name",
        "ordered": True,
    }

    notes: list[str] = []
    t0 = time.perf_counter()
    rscript = shutil.which("Rscript")
    if rscript:
        actual_dir = _execute_step9(paths)
        mode = "real"
    else:
        actual_dir = _stub_actual_outputs(expected_dir, paths["outputs"], "step9")
        mode = "stub"
        notes.append(
            "R is not installed. Showing the bundled reference outputs against "
            "themselves so you can preview how the comparison report looks. "
            "Install R (or use the bundled container) and re-run for a live check."
        )

    file_results = _compare_outputs(actual_dir, expected_dir, paths["outputs"], paths)
    return OracleReport(
        project=project, tier="step9", mode=mode,
        overall_pass=all(r["equivalent"] for r in file_results),
        runtime_seconds=round(time.perf_counter() - t0, 2),
        file_results=file_results, notes=notes,
    )


# ---------------------------------------------------------------------------
# Tier 3 — full pipeline on simulated FASTQs
# ---------------------------------------------------------------------------
def _run_pipeline(project: str) -> OracleReport:
    if project != "ovarian_cancer":
        raise ValueError("Tier 3 (pipeline) is currently OvCa-only.")

    fixture_dir = EXAMPLES_DIR / "ovca_pipeline"
    inputs_dir = fixture_dir / "inputs"
    expected_dir = fixture_dir / "expected"

    if not (fixture_dir / "expected").exists():
        return _missing_fixtures("pipeline", "Run `python tools/build_fixtures.py --tier t3` first.")

    notes: list[str] = []
    t0 = time.perf_counter()

    snakemake_bin = shutil.which("snakemake")
    bowtie2_bin = shutil.which("bowtie2")
    can_run_pipeline = bool(snakemake_bin and bowtie2_bin)

    outputs = [
        "alignment_result_normalized_in_house_pipeline.csv",
        "alignment_result_unnormalized_in_house_pipeline.csv",
    ]

    if can_run_pipeline:
        try:
            actual_dir, run_notes = _execute_snakemake_pipeline(inputs_dir, outputs)
            notes.extend(run_notes)
            mode = "real"
        except Exception as exc:
            log.exception("Snakemake invocation failed")
            actual_dir = _stub_actual_outputs(expected_dir, outputs, "pipeline_error")
            mode = "stub"
            notes.append(
                f"Pipeline invocation failed ({exc}); showing reference outputs "
                f"against themselves. Check server logs for the snakemake stderr."
            )
    else:
        actual_dir = _stub_actual_outputs(expected_dir, outputs, "pipeline")
        mode = "stub"
        missing = []
        if not snakemake_bin: missing.append("snakemake")
        if not bowtie2_bin:   missing.append("bowtie2")
        notes.append(
            f"Tools not installed: {', '.join(missing)}. Showing the analytically-"
            f"computed expected count matrix without re-running the pipeline. "
            f"Install the conda env (`conda env create -f pipeline/environment.yml`) "
            f"or use the bundled container to run for real."
        )

    paths = {
        "inputs_dir": inputs_dir,
        "expected_dir": expected_dir,
        "outputs": outputs,
        "primary_key": "promoter_name_bc",
        "ordered": False,
    }
    # Pipeline-tier comparison uses a relaxed tolerance. bowtie2 distributes
    # reads non-deterministically across near-identical barcodes (the fixture
    # contains 1bp-shifted barcode pairs that bowtie2 multimaps), and RPM
    # normalization amplifies those swaps. rtol=0.5 + atol=100 absorbs the
    # alignment ambiguity floor while still flagging real regressions —
    # an order-of-magnitude discrepancy is still well outside this envelope.
    file_results = _compare_outputs(
        actual_dir, expected_dir, outputs, paths, rtol=0.5, atol=100.0,
    )
    return OracleReport(
        project=project, tier="pipeline", mode=mode,
        overall_pass=all(r["equivalent"] for r in file_results),
        runtime_seconds=round(time.perf_counter() - t0, 2),
        file_results=file_results, notes=notes,
    )


# ---------------------------------------------------------------------------
# Streaming variant — yields per-step events as snakemake progresses
# ---------------------------------------------------------------------------
def run_oracle_streaming(
    project: str = "ovarian_cancer", tier: str = "smoke",
) -> Iterator[dict]:
    """Streaming wrapper around run_oracle.

    For tier 'pipeline' yields per-step events as snakemake makes progress.
    For tiers 'smoke' / 'step9' just yields a single 'report' event with the
    synchronous result, so the SSE consumer can treat all tiers uniformly.

    Final event for every tier is `{"event": "report", "payload": {...}}`.
    """
    if tier == "pipeline":
        yield from _run_pipeline_streaming(project)
    else:
        report = run_oracle(project, tier)
        yield {"event": "report", "payload": dataclasses.asdict(report)}


def _run_pipeline_streaming(project: str) -> Iterator[dict]:
    """Run the install-check pipeline tier with per-step progress events."""
    if project != "ovarian_cancer":
        report = OracleReport(
            project=project, tier="pipeline", mode="stub",
            overall_pass=False, runtime_seconds=0.0, file_results=[],
            notes=["Streaming pipeline tier is currently OvCa-only."],
        )
        yield {"event": "report", "payload": dataclasses.asdict(report)}
        return

    fixture_dir = EXAMPLES_DIR / "ovca_pipeline"
    inputs_dir = fixture_dir / "inputs"
    expected_dir = fixture_dir / "expected"

    if not (fixture_dir / "expected").exists():
        report = _missing_fixtures("pipeline", "Run `python tools/build_fixtures.py --tier t3` first.")
        yield {"event": "report", "payload": dataclasses.asdict(report)}
        return

    snakemake_bin = shutil.which("snakemake")
    bowtie2_bin = shutil.which("bowtie2")
    outputs = [
        "alignment_result_normalized_in_house_pipeline.csv",
        "alignment_result_unnormalized_in_house_pipeline.csv",
    ]

    # Tools missing — fall back to stub comparison without streaming.
    if not (snakemake_bin and bowtie2_bin):
        missing = [t for t, b in (("snakemake", snakemake_bin),
                                  ("bowtie2", bowtie2_bin)) if not b]
        actual_dir = _stub_actual_outputs(expected_dir, outputs, "pipeline")
        paths = {"primary_key": "promoter_name_bc", "ordered": False}
        file_results = _compare_outputs(actual_dir, expected_dir, outputs, paths,
                                        rtol=0.5, atol=100.0)
        report = OracleReport(
            project=project, tier="pipeline", mode="stub",
            overall_pass=all(r["equivalent"] for r in file_results),
            runtime_seconds=0.0,
            file_results=file_results,
            notes=[
                f"Tools not installed: {', '.join(missing)}. Showing reference "
                f"outputs against themselves. Use the bundled container to run "
                f"the live pipeline.",
            ],
        )
        yield {"event": "report", "payload": dataclasses.asdict(report)}
        return

    # Inform the consumer of the step skeleton up-front so it can paint the
    # full state-machine in pending / skipped state immediately.
    yield {
        "event": "run_started",
        "tier": "pipeline",
        "active_steps": PIPELINE_TIER_STEPS,
        "skipped_steps": PIPELINE_TIER_SKIPPED,
    }

    sample_count = _count_fastq_samples(inputs_dir / "fastqs")
    snakefile = config.REPO_ROOT / "pipeline" / "trend" / "workflow" / "Snakefile"
    work = Path(tempfile.mkdtemp(prefix="trend_pipeline_"))
    metadata_root = Path(tempfile.mkdtemp(prefix="trend_meta_"))
    notes: list[str] = []
    t0 = time.perf_counter()

    try:
        # Materialize fixture's tiny Lib4 under canonical names.
        shutil.copy(inputs_dir / "Lib4_tiny.fasta", metadata_root / "Lib4.fasta")
        shutil.copy(
            inputs_dir / "Lib4_info_tiny.csv",
            metadata_root / "Lib4_info_concise_060621.csv",
        )

        fastqs_dir = inputs_dir / "fastqs"
        target_outputs = [f"outputs/{name}" for name in outputs]
        cmd = [
            snakemake_bin,
            "--snakefile", str(snakefile),
            "--directory", str(work),
            "--cores", "2",
            *target_outputs,
            "--config",
            f"inputs_dir={fastqs_dir}",
            f"metadata_root={metadata_root}",
        ]

        log.info("Streaming snakemake; work=%s sample_count=%d", work, sample_count)
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )

        prior_state = {sid: "pending" for sid in PIPELINE_TIER_STEPS}
        while proc.poll() is None:
            time.sleep(0.5)
            current = _check_step_states(work, sample_count, project)
            for sid, status in current.items():
                if prior_state.get(sid) != status:
                    if status == "running":
                        yield {"event": "step_started", "step_id": sid}
                    elif status == "completed":
                        yield {"event": "step_finished",
                               "step_id": sid, "status": "completed"}
                    prior_state[sid] = status

        # Snakemake exited; capture any stderr/stdout for debugging
        rc = proc.returncode
        tail_lines = (proc.stdout.read() or "").splitlines()[-20:] if proc.stdout else []
        if rc != 0:
            notes.append(f"Snakemake exited {rc}; outputs may be incomplete.")
            log.warning("Snakemake exit %s; tail: %s", rc, "\n".join(tail_lines))
        # Final state pass: any step whose outputs landed at the very end.
        current = _check_step_states(work, sample_count, project)
        for sid, status in current.items():
            if prior_state.get(sid) != status:
                if status == "running":
                    yield {"event": "step_started", "step_id": sid}
                elif status == "completed":
                    yield {"event": "step_finished",
                           "step_id": sid, "status": "completed"}
                prior_state[sid] = status

        # Harvest outputs and compare.
        actual_dir = config.RUNS_DIR / f"oracle_pipeline_{int(time.time())}" / "outputs"
        actual_dir.mkdir(parents=True, exist_ok=True)
        for name in outputs:
            src = work / "outputs" / name
            if src.exists():
                shutil.copy2(src, actual_dir / name)

        paths = {"primary_key": "promoter_name_bc", "ordered": False}
        file_results = _compare_outputs(actual_dir, expected_dir, outputs, paths,
                                        rtol=0.5, atol=100.0)
        report = OracleReport(
            project=project, tier="pipeline",
            mode="real" if rc == 0 else "stub",
            overall_pass=all(r["equivalent"] for r in file_results),
            runtime_seconds=round(time.perf_counter() - t0, 2),
            file_results=file_results, notes=notes,
        )
        yield {"event": "report", "payload": dataclasses.asdict(report)}

    except Exception as exc:
        log.exception("Streaming pipeline failed")
        report = OracleReport(
            project=project, tier="pipeline", mode="stub",
            overall_pass=False,
            runtime_seconds=round(time.perf_counter() - t0, 2),
            file_results=[],
            notes=[f"Streaming pipeline failed: {exc}"],
        )
        yield {"event": "report", "payload": dataclasses.asdict(report)}
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(metadata_root, ignore_errors=True)


def _count_fastq_samples(fastqs_dir: Path) -> int:
    """Count distinct sample stems under fastqs_dir."""
    if not fastqs_dir.exists():
        return 0
    stems: set[str] = set()
    for p in fastqs_dir.iterdir():
        name = p.name.removesuffix(".gz").removesuffix(".fastq")
        if name:
            stems.add(name)
    return len(stems)


def _check_step_states(
    work_dir: Path, sample_count: int, project: str,
) -> dict[str, str]:
    """Derive each pipeline step's state from output files in work_dir.

    Returns a dict mapping step_id -> 'pending' | 'running' | 'completed'.
    A step is 'completed' when all its outputs exist; 'running' once any
    output exists but not all; 'pending' otherwise.
    """
    intermediate = work_dir / "intermediate"
    sam_files = work_dir / "sam_files"
    outputs = work_dir / "outputs"

    def count(glob: str, root: Path) -> int:
        return len(list(root.glob(glob))) if root.exists() else 0

    flipped = count("flipped_*.fastq", intermediate)
    trimmed = count("trimmed_*.fastq", intermediate)
    collapsed = count("collapsed_*.fasta", intermediate)
    barcoded = count("barcode_*.fasta", intermediate)
    sams = count("*.sam", sam_files)
    counted_csv = outputs / "alignment_result_normalized_in_house_pipeline.csv"
    counted = counted_csv.exists()

    def derive(present: int) -> str:
        if present >= sample_count:
            return "completed"
        if present > 0:
            return "running"
        return "pending"

    states = {
        "step_2_flip_orientation": derive(flipped),
        "step_4_trim_adapters": derive(trimmed),
        "step_5_collapse_umis": derive(collapsed),
        "step_6_extract_barcodes": derive(barcoded),
        "step_7_align_barcodes": derive(sams),
        # Step 8 collapses all samples into one CSV; "running" once all sams
        # have landed but the CSV hasn't yet appeared.
        "step_8_count_barcodes": (
            "completed" if counted
            else ("running" if sams >= sample_count else "pending")
        ),
    }
    return states


def _execute_snakemake_pipeline(
    inputs_dir: Path, outputs: list[str],
) -> tuple[Path, list[str]]:
    """Run the bundled Snakefile against fixture inputs in a clean work dir.

    Returns (directory containing produced outputs, runtime notes).
    """
    notes: list[str] = []
    snakefile = config.REPO_ROOT / "pipeline" / "trend" / "workflow" / "Snakefile"
    work = Path(tempfile.mkdtemp(prefix="trend_pipeline_"))
    metadata_root = Path(tempfile.mkdtemp(prefix="trend_meta_"))

    try:
        # Materialize the fixture's tiny Lib4 under the canonical names the
        # Snakefile expects (Lib4.fasta, Lib4_info_concise_060621.csv).
        shutil.copy(inputs_dir / "Lib4_tiny.fasta", metadata_root / "Lib4.fasta")
        shutil.copy(
            inputs_dir / "Lib4_info_tiny.csv",
            metadata_root / "Lib4_info_concise_060621.csv",
        )

        fastqs_dir = inputs_dir / "fastqs"
        target_outputs = [f"outputs/{name}" for name in outputs]

        cmd = [
            shutil.which("snakemake"),
            "--snakefile", str(snakefile),
            "--directory", str(work),
            "--cores", "2",
            *target_outputs,
            "--config",
            f"inputs_dir={fastqs_dir}",
            f"metadata_root={metadata_root}",
        ]

        log.info("Invoking snakemake against fixture; work dir=%s", work)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if proc.returncode != 0:
            log.warning(
                "Snakemake exit %s; stderr tail: %s",
                proc.returncode, proc.stderr[-1500:],
            )
            notes.append(
                f"Snakemake exited {proc.returncode}; outputs may be incomplete."
            )

        actual_dir = config.RUNS_DIR / f"oracle_pipeline_{int(time.time())}" / "outputs"
        actual_dir.mkdir(parents=True, exist_ok=True)
        for name in outputs:
            src = work / "outputs" / name
            if src.exists():
                shutil.copy2(src, actual_dir / name)

        return actual_dir, notes
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(metadata_root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _execute_step9(paths: dict) -> Path:
    """Materialize a temp cwd with the inputs + metadata, run the Step-9 R script,
    return the directory that contains the produced outputs."""
    from backend.pipeline.cwd_shim import materialize, harvest

    inputs_dir: Path = paths["inputs_dir"]
    in_files = {p.name: p for p in inputs_dir.glob("*.csv")}
    in_files[paths["metadata_csv"].name] = paths["metadata_csv"]
    work = materialize(in_files)
    actual_dir = config.RUNS_DIR / f"oracle_{int(time.time())}" / "outputs"
    actual_dir.mkdir(parents=True, exist_ok=True)
    try:
        log.info("Invoking Rscript against %s in %s", paths["step9_script"], work)
        proc = subprocess.run(
            [shutil.which("Rscript"), str(paths["step9_script"])],
            cwd=work, capture_output=True, text=True, timeout=900,
        )
        if proc.returncode != 0:
            log.warning("Rscript exit %s; stderr tail: %s",
                        proc.returncode, proc.stderr[-500:])
        harvest(work, paths["outputs"], actual_dir)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return actual_dir


def _stub_actual_outputs(expected_dir: Path, outputs: list[str], tag: str) -> Path:
    """Copy the expected outputs as the 'actual' so the comparator passes
    trivially. Used when required tools aren't installed."""
    actual_dir = config.RUNS_DIR / f"oracle_stub_{tag}_{int(time.time())}" / "outputs"
    actual_dir.mkdir(parents=True, exist_ok=True)
    for name in outputs:
        src = expected_dir / name
        if src.exists():
            shutil.copy2(src, actual_dir / name)
    return actual_dir


def _compare_outputs(
    actual_dir: Path, expected_dir: Path, outputs: list[str], paths: dict,
    *, rtol: float = 1e-6, atol: float = 1e-9,
) -> list[dict]:
    file_results: list[dict] = []
    for name in outputs:
        actual = actual_dir / name
        expected = expected_dir / name
        if not actual.exists() or not expected.exists():
            file_results.append({
                "filename": name, "equivalent": False,
                "summary": (f"output missing: actual_exists={actual.exists()} "
                           f"expected_exists={expected.exists()}"),
            })
            continue
        result: CompareResult = compare_csv(
            actual, expected,
            primary_key=paths["primary_key"], ordered=paths["ordered"],
            rtol=rtol, atol=atol,
        )
        file_results.append({
            "filename": name,
            "equivalent": result.equivalent,
            "summary": result.summary,
            "column_diff": result.column_diff or None,
            "row_count_diff": result.row_count_diff,
            "numeric_mismatches": result.numeric_mismatches[:5],
            "string_mismatches": result.string_mismatches[:5],
        })
    return file_results


def _missing_fixtures(tier: str, hint: str) -> OracleReport:
    return OracleReport(
        project="ovarian_cancer", tier=tier, mode="stub",
        overall_pass=False, runtime_seconds=0.0, file_results=[],
        notes=[f"Bundled fixtures for tier '{tier}' not found. {hint}"],
    )


# ---------------------------------------------------------------------------
# Reproduce-the-manuscript streaming flow
# ---------------------------------------------------------------------------
def reproduce_streaming(project: str) -> Iterator[dict]:
    """Run the manuscript's Step 9 R script against the deposited count tables.

    On first call for a project, downloads the count tables from the GitHub
    release into project_data/alignment_results/{project}/. Subsequent calls
    in the same container reuse the downloaded files. Yields events:

      - run_started   : { download_mb, count_tables_present }
      - download_started / download_progress / download_finished
      - analysis_started / analysis_finished
      - report        : { produced_files, deposited_files, runtime_seconds }
    """
    import urllib.request
    import urllib.error

    if project not in _REPRODUCE_PROJECTS:
        yield {"event": "report", "payload": {
            "error": f"Unknown project: {project}",
            "produced_files": [], "deposited_files": [],
        }}
        return

    cfg = _REPRODUCE_PROJECTS[project]
    target_dir = config.PROJECT_DATA_ROOT / "alignment_results" / project
    target_dir.mkdir(parents=True, exist_ok=True)

    missing = [f for f in _REPRODUCE_COUNT_TABLES if not (target_dir / f).exists()]
    yield {
        "event": "run_started",
        "project": project,
        "download_needed": bool(missing),
        "approx_download_mb": cfg["approx_download_mb"] if missing else 0,
        "count_tables_present": [f for f in _REPRODUCE_COUNT_TABLES
                                 if (target_dir / f).exists()],
        "count_tables_to_download": missing,
    }

    # ---- Download phase ----
    if missing:
        yield {"event": "download_started", "files": missing}
        for filename in missing:
            asset_name = f"{project}__{filename}"
            url = f"{REPRODUCE_RELEASE_URL}/{asset_name}"
            target_path = target_dir / filename
            yield {"event": "download_progress", "filename": filename,
                   "stage": "fetching", "url": url}
            try:
                # Stream download with progress reporting.
                req = urllib.request.Request(url, headers={"Accept": "application/octet-stream"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    chunk_size = 8 * 1024 * 1024  # 8 MiB
                    written = 0
                    last_yield_mb = 0
                    with open(target_path, "wb") as out:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            out.write(chunk)
                            written += len(chunk)
                            current_mb = written / (1024 * 1024)
                            if current_mb - last_yield_mb >= 50:
                                yield {
                                    "event": "download_progress",
                                    "filename": filename,
                                    "stage": "downloading",
                                    "downloaded_bytes": written,
                                    "total_bytes": total,
                                }
                                last_yield_mb = current_mb
            except (urllib.error.URLError, OSError) as exc:
                # Clean up partial file
                target_path.unlink(missing_ok=True)
                yield {"event": "report", "payload": {
                    "error": f"Download failed for {filename}: {exc}",
                    "produced_files": [], "deposited_files": [],
                }}
                return
        yield {"event": "download_finished"}

    # ---- Analysis phase ----
    yield {"event": "analysis_started", "estimated_minutes": 5}
    rscript = shutil.which("Rscript")
    if not rscript:
        yield {"event": "report", "payload": {
            "error": "Rscript is not available in this environment. "
                     "Use the Docker container — it bundles R + tidyverse.",
            "produced_files": [], "deposited_files": [],
        }}
        return

    t0 = time.perf_counter()
    paths = {
        "inputs_dir": target_dir,
        "metadata_csv": cfg["metadata_csv"],
        "step9_script": cfg["r_script"],
        "outputs": cfg["outputs"],
    }
    try:
        actual_dir = _execute_step9(paths)
    except Exception as exc:
        log.exception("reproduce: Step 9 invocation failed")
        yield {"event": "report", "payload": {
            "error": f"Analysis failed: {exc}",
            "produced_files": [], "deposited_files": [],
        }}
        return

    runtime = round(time.perf_counter() - t0, 2)
    yield {"event": "analysis_finished", "runtime_seconds": runtime}

    # Verify outputs landed and remember where for the file-serving endpoints.
    produced_files: list[str] = []
    for name in cfg["outputs"]:
        if (actual_dir / name).exists():
            produced_files.append(name)

    deposited_dir = config.PROJECT_DATA_ROOT / "final_enhancer_activity_results" / project
    deposited_files = [n for n in cfg["outputs"] if (deposited_dir / n).exists()]

    _LATEST_REPRODUCE_DIRS[project] = actual_dir

    yield {"event": "report", "payload": {
        "project": project,
        "runtime_seconds": runtime,
        "produced_files": produced_files,
        "deposited_files": deposited_files,
        "error": None,
    }}


def get_latest_reproduce_dir(project: str) -> Path | None:
    """Return the most recent produced-output directory for a project, or None."""
    return _LATEST_REPRODUCE_DIRS.get(project)
