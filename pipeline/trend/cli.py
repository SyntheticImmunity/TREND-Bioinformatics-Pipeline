"""trend - command-line entry point.

Subcommands:
    init        Scaffold a new project directory from a reference template.
    run         Execute the 9-step TREND pipeline on a sample sheet.
    dashboard   Launch the web dashboard pointed at a runs directory.
    status      Print a one-screen summary of a manifest.
    preflight   Show the FR-2 environment check and exit.

Design: stdlib argparse only — no new dependencies. The CLI is a thin wrapper
around the pipeline runner library that already ships with the dashboard
backend; this file is the user-facing entry point.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import trend

# Templates ship inside the package (pipeline/templates/) and as a fallback
# we honor a sibling directory at repo root (pipeline/templates/) for editable
# installs.
_TEMPLATES_DIR_CANDIDATES = [
    Path(__file__).resolve().parent / "templates",
    Path(__file__).resolve().parents[1] / "templates",
]


def _templates_dir() -> Path:
    for cand in _TEMPLATES_DIR_CANDIDATES:
        if cand.exists() and cand.is_dir():
            return cand
    raise FileNotFoundError(
        "trend templates/ directory not found. "
        "Reinstall trend-pipeline or run from a checkout that includes pipeline/templates/."
    )


def _list_templates() -> list[str]:
    try:
        return sorted(p.name for p in _templates_dir().iterdir() if p.is_dir())
    except FileNotFoundError:
        return []


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------
def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.name).resolve()
    if target.exists() and any(target.iterdir()):
        print(f"error: target directory exists and is not empty: {target}", file=sys.stderr)
        return 2

    templates = _templates_dir()
    src = templates / args.template
    if not src.exists():
        print(
            f"error: unknown template '{args.template}'. Available: "
            f"{', '.join(_list_templates()) or '(none found)'}",
            file=sys.stderr,
        )
        return 2

    target.mkdir(parents=True, exist_ok=True)
    for entry in src.rglob("*"):
        rel = entry.relative_to(src)
        dest = target / rel
        if entry.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry, dest)

    print(f"Scaffolded {target} from template '{args.template}'.")
    print(f"Next: edit {target / 'samplesheet.yaml'}, then run:")
    print(f"  cd {target.name}")
    print(f"  trend run --inputs <fastq_dir> --output runs/$(date +%Y-%m-%d)/")
    return 0


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------
def cmd_run(args: argparse.Namespace) -> int:
    # --resume <dir> --rerun-from step9: skip alignment, re-render and re-run
    # the Step-9 R against the existing alignment outputs in <dir>. Used for
    # fast threshold-tuning iteration after the user inspects the DNA-distribution PDF.
    if args.resume and args.rerun_from == "step9":
        return _cmd_rerun_step9(args)

    if trend.pipeline is None:
        print(
            "error: trend.pipeline backend is not importable. The CLI expects to "
            "find dashboard/backend/pipeline/runner.py at the repo root, or to be "
            "installed alongside the dashboard. See README for details.",
            file=sys.stderr,
        )
        return 3

    inputs_dir = Path(args.inputs).resolve() if args.inputs else None
    output_dir = Path(args.output).resolve() if args.output else None

    if args.example:
        # Quick reproducer path: skip --inputs/--output requirements; use the
        # bundled OvCa fixtures.
        if trend.oracle is None:
            print("error: trend.oracle not importable; cannot run --example.", file=sys.stderr)
            return 3
        from backend.oracle import run_example as _re
        report = _re.run_oracle(project=args.example, tier=args.tier)
        print()
        print(f"  project:      {report.project}")
        print(f"  tier:         {report.tier}")
        print(f"  mode:         {report.mode}")
        print(f"  overall_pass: {report.overall_pass}")
        print(f"  runtime:      {report.runtime_seconds}s")
        for fr in report.file_results:
            badge = "[MATCH]" if fr["equivalent"] else "[DIFFERS]"
            print(f"  {badge} {fr['filename']}: {fr['summary']}")
        for n in report.notes:
            print(f"  note: {n}")
        return 0 if report.overall_pass else 1

    if inputs_dir is None or output_dir is None:
        print("error: --inputs and --output are required (or use --example).", file=sys.stderr)
        return 2
    if not inputs_dir.exists():
        print(f"error: --inputs directory does not exist: {inputs_dir}", file=sys.stderr)
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.profile == "snakemake" or args.profile == "slurm":
        return _run_via_snakemake(inputs_dir, output_dir, args)

    # Fall through: --profile local uses the dashboard-backend runner below.
    # B-Slim samplesheet-driven Step 9 is wired to the snakemake/slurm path
    # only; --profile local still uses the manuscript R script as-is.

    # Local execution path: invoke the existing runner directly.
    # Tell the dashboard backend to write manifests into the user's chosen
    # output directory rather than the dashboard's bundled runs/ tree.
    os.environ["TREND_RUNS_DIR"] = str(output_dir)
    if trend.config is not None:
        trend.config.RUNS_DIR = output_dir  # type: ignore[attr-defined]

    inputs_map = {p.name: p for p in inputs_dir.iterdir() if p.is_file()}
    print(f"Running pipeline (mode={args.mode}) on {len(inputs_map)} input file(s); "
          f"output -> {output_dir}")
    last_status = "completed"
    for event in trend.pipeline.runner.run_pipeline(
        project=args.project,
        inputs=inputs_map,
        mode=args.mode,
    ):
        kind = event.get("event")
        if kind == "run_started":
            print(f"  run_id: {event['run_id']}")
        elif kind == "step_started":
            print(f"  -> {event['step_id']}", end="", flush=True)
        elif kind == "step_finished":
            print(f"  [{event['status']:9s}]  {event.get('runtime_seconds', 0):.2f}s")
            if event["status"] == "failed":
                last_status = "failed"
        elif kind == "run_finished":
            last_status = event["status"]
            print(f"  run_finished: {event['status']}")
    return 0 if last_status == "completed" else 1


def _run_via_snakemake(inputs_dir: Path, output_dir: Path, args: argparse.Namespace) -> int:
    """Invoke Snakemake against the bundled workflow.

    If `args.samplesheet` (or an auto-discovered samplesheet.yaml) is supplied,
    Snakemake is restricted to Steps 1-8 (alignment) and Step 9 is run
    afterwards by the B-Slim samplesheet-driven renderer. Otherwise the
    classic flow runs (Snakemake also handles Step 9 via the manuscript R).
    """
    snakefile = Path(__file__).resolve().parent / "workflow" / "Snakefile"
    if not snakefile.exists():
        print(f"error: bundled Snakefile not found at {snakefile}", file=sys.stderr)
        return 3
    if shutil.which("snakemake") is None:
        print(
            "error: snakemake not on PATH. Install with `conda install -c bioconda snakemake` "
            "or `pip install snakemake`.",
            file=sys.stderr,
        )
        return 127

    samplesheet_path, samplesheet = _resolve_samplesheet(args, inputs_dir)

    cmd = [
        "snakemake",
        "--snakefile", str(snakefile),
        "--directory", str(output_dir),
    ]
    if samplesheet is not None:
        # B-Slim flow: ask Snakemake only for Step-8 alignment outputs; Step 9
        # runs in Python below from the user's samplesheet.
        cmd += [
            "outputs/alignment_result_normalized_in_house_pipeline.csv",
            "outputs/alignment_result_unnormalized_in_house_pipeline.csv",
        ]
    cmd += [
        "--config",
        f"inputs_dir={inputs_dir}",
        f"project={args.project}",
        "--cores", str(args.cores),
    ]
    if args.profile == "slurm":
        profile_dir = snakefile.parent / "profiles" / "slurm"
        cmd += ["--profile", str(profile_dir)]
    if args.dry_run:
        cmd += ["--dry-run"]
    if args.verbose:
        cmd += ["--verbose"]
    print("running:", " ".join(cmd))
    import subprocess
    rc = subprocess.call(cmd)
    if rc != 0 or args.dry_run:
        return rc

    if samplesheet is None:
        # Backwards-compat: no samplesheet means Snakemake also ran Step 9
        # with the manuscript R. Nothing more to do.
        return 0

    # B-Slim Step 9: render and run.
    return _render_and_invoke_step9(samplesheet, samplesheet_path, output_dir)


def _resolve_samplesheet(
    args: argparse.Namespace, inputs_dir: Path,
) -> tuple[Path | None, dict | None]:
    """Find samplesheet.yaml from --samplesheet flag or by auto-discovery.

    Returns (path, parsed_dict) or (None, None) if no samplesheet is found.
    Auto-discovery searches: explicit --samplesheet flag, then
    inputs_dir/../samplesheet.yaml, then ./samplesheet.yaml.
    """
    from .render_step9 import load_samplesheet

    candidates: list[Path] = []
    if getattr(args, "samplesheet", None):
        candidates.append(Path(args.samplesheet).resolve())
    candidates.append((inputs_dir.parent / "samplesheet.yaml").resolve())
    candidates.append(Path.cwd() / "samplesheet.yaml")

    for p in candidates:
        if p.is_file():
            try:
                return p, load_samplesheet(p)
            except Exception as exc:
                print(f"warning: failed to parse {p}: {exc}", file=sys.stderr)
    return None, None


def _render_and_invoke_step9(
    samplesheet: dict, samplesheet_path: Path | None, run_dir: Path,
) -> int:
    """Run B-Slim Step 9 in `run_dir`. Returns 0 on success, nonzero otherwise."""
    from . import step9_runner

    # Locate the design-metadata directory. In the bundled image / repo it is
    # at codes/3. .../required_metadata/.
    repo_root = Path(__file__).resolve().parents[2]
    metadata_root = (
        repo_root
        / "codes"
        / "3. Post_HPC_enhancer_activity_analysis_scripts"
        / "required_metadata"
    )
    if not metadata_root.is_dir():
        print(
            f"error: design metadata directory not found: {metadata_root}",
            file=sys.stderr,
        )
        return 3

    if samplesheet_path is not None:
        step9_runner.save_samplesheet_copy(samplesheet_path, run_dir)

    print(f"running Step 9 from samplesheet (output -> {run_dir})")
    result = step9_runner.render_and_run(samplesheet, run_dir, metadata_root)
    print(f"  rendered R: {result.rendered_path}")
    if result.used_default_thresholds:
        print(
            "  note: one or more samples had no dna_threshold; default of 3 was used.\n"
            "        Inspect DNA_threshold_for_samples.pdf, edit samplesheet.yaml,\n"
            f"        and re-run with: trend run --resume {run_dir} --rerun-from step9"
        )
    if result.rc != 0:
        print(f"error: Step-9 R exited with code {result.rc}", file=sys.stderr)
        if result.log_tail:
            print(f"stderr tail:\n{result.log_tail}", file=sys.stderr)
        return result.rc
    if not result.output_files:
        print(
            "error: Step-9 R produced no *_sensor_activity_result_*.csv files.",
            file=sys.stderr,
        )
        return 1
    print("  outputs:")
    for p in result.output_files:
        print(f"    {p.name}")
    return 0


def _cmd_rerun_step9(args: argparse.Namespace) -> int:
    """`--resume <dir> --rerun-from step9` — re-render and re-run Step 9 only."""
    from .render_step9 import load_samplesheet

    resume_dir = Path(args.resume).resolve()
    if not resume_dir.is_dir():
        print(f"error: --resume dir not found: {resume_dir}", file=sys.stderr)
        return 2

    samplesheet_path = resume_dir / "samplesheet.yaml"
    if not samplesheet_path.is_file():
        print(
            f"error: no samplesheet.yaml in {resume_dir}. The original `trend run`\n"
            f"       drops a samplesheet.yaml here; if missing, point --samplesheet\n"
            f"       at your samplesheet explicitly.",
            file=sys.stderr,
        )
        return 2

    samplesheet = load_samplesheet(samplesheet_path)
    return _render_and_invoke_step9(samplesheet, samplesheet_path, resume_dir)


# ---------------------------------------------------------------------------
# dashboard
# ---------------------------------------------------------------------------
def cmd_dashboard(args: argparse.Namespace) -> int:
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        print(
            "error: dashboard requires the optional 'dashboard' extra. Install with:\n"
            "  pip install 'trend-pipeline[dashboard]'\n"
            "or:\n"
            "  pip install fastapi uvicorn pydantic duckdb sse-starlette",
            file=sys.stderr,
        )
        return 3

    if args.runs:
        os.environ["TREND_RUNS_DIR"] = str(Path(args.runs).resolve())

    # The dashboard FastAPI app already lives at backend.main:app. The bind in
    # trend/__init__.py adds dashboard/ to sys.path so this import works.
    print(f"trend dashboard - serving on http://{args.host}:{args.port}")
    if args.runs:
        print(f"  reading runs from: {os.environ['TREND_RUNS_DIR']}")
    print("  Ctrl-C to stop")
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=args.reload,
    )
    return 0


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------
def cmd_status(args: argparse.Namespace) -> int:
    if trend.provenance is None:
        print("error: trend.provenance not importable.", file=sys.stderr)
        return 3

    runs_dir = Path(args.runs_dir or os.environ.get("TREND_RUNS_DIR") or "runs").resolve()
    manifest_path = runs_dir / args.run_id / "manifest.json"
    if not manifest_path.exists():
        print(f"error: manifest not found: {manifest_path}", file=sys.stderr)
        return 2

    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"run_id:        {raw['run_id']}")
    print(f"project:       {raw['project']}")
    print(f"status:        {raw['status']}")
    print(f"started:       {raw['created_at']}")
    print(f"finished:      {raw.get('finished_at') or '(not finished)'}")
    print(f"work_dir:      {raw['work_dir']}")
    print()
    print("software:")
    for k, v in (raw.get("software") or {}).items():
        if v != "missing":
            print(f"  {k:18s} {v}")
    print()
    print("steps:")
    for s in raw.get("steps", []):
        runtime = (
            f"{s['runtime_seconds']:>6.2f}s"
            if s.get("runtime_seconds") is not None else "    --"
        )
        exit_code = s.get("exit_code")
        ec = f"exit={exit_code:>3d}" if exit_code is not None else "exit=  -"
        print(f"  [{s['status']:9s}] {runtime}  {ec}  {s['id']}")
    return 0


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------
def cmd_preflight(args: argparse.Namespace) -> int:
    if trend.preflight is None:
        print("error: trend.preflight not importable.", file=sys.stderr)
        return 3
    report = trend.preflight.run_preflight(force=True)
    print(f"OS:             {report.os_name}")
    print(f"Container mode: {report.container_mode}")
    print(f"Overall:        {report.overall}")
    print(f"Summary:        {report.summary}")
    print()
    print("Checks:")
    for c in report.checks:
        icon = "OK" if c.found else "--"
        ver = (c.version or "")[:55]
        print(f"  [{icon}] {c.name:18s} [{c.category:15s}] {ver}")
        if not c.found and c.hint:
            print(f"         install: {c.hint}")
    return 0 if report.overall != "blocked" else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trend",
        description="TREND enhancer-screening pipeline + dashboard",
    )
    parser.add_argument("--version", action="version", version=f"trend {trend.__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    p_init = sub.add_parser("init", help="Scaffold a new project from a template.")
    p_init.add_argument("name", help="Project directory to create.")
    p_init.add_argument(
        "--template", default="ovarian_cancer",
        help=f"Template to copy from. Available: {', '.join(_list_templates()) or 'ovarian_cancer, T_cell_activation'}",
    )
    p_init.set_defaults(func=cmd_init)

    p_run = sub.add_parser("run", help="Execute the 9-step pipeline on a sample sheet.")
    p_run.add_argument("--project", default="ovarian_cancer", help="Project name (matches a project.yaml).")
    p_run.add_argument("--inputs", help="Directory containing per-sample input files (FASTQ or post-alignment).")
    p_run.add_argument("--output", help="Run output directory (will contain manifest.json + outputs/).")
    p_run.add_argument(
        "--mode", choices=("dry_run", "real"), default="real",
        help="dry_run = stub steps for orchestration testing; real = invoke the actual tools.",
    )
    p_run.add_argument(
        "--profile", choices=("local", "snakemake", "slurm"), default="local",
        help="Execution backend. local = run steps in this process; snakemake = use the bundled Snakefile; slurm = snakemake + cluster profile.",
    )
    p_run.add_argument("--cores", type=int, default=4, help="Cores for snakemake/slurm profiles.")
    p_run.add_argument(
        "--example", choices=("ovarian_cancer", "T_cell_activation"), default=None,
        help="Run the bundled reviewer oracle for the named project.",
    )
    p_run.add_argument(
        "--tier", choices=("smoke", "step9", "pipeline"), default="smoke",
        help=(
            "Reviewer-oracle tier: "
            "smoke = bundled output comparator (no tools); "
            "step9 = R Step-9 on subsampled real data (~1k promoters; ~30s); "
            "pipeline = simulated FASTQs through full pipeline (requires conda env; ~3 min)."
        ),
    )
    p_run.add_argument("--dry-run", action="store_true", help="Snakemake DAG dry-run; print what would happen.")
    p_run.add_argument("--verbose", "-v", action="store_true")
    p_run.add_argument(
        "--samplesheet",
        help=(
            "Path to samplesheet.yaml. If provided (or auto-discovered next to "
            "--inputs), Step 9 is run from this samplesheet via the rendered R "
            "template instead of the manuscript script's hardcoded sample list."
        ),
    )
    p_run.add_argument(
        "--resume",
        help=(
            "Path to a previous run directory. Combined with --rerun-from, "
            "re-runs only the named stage against the existing outputs (e.g., "
            "fast threshold tuning after inspecting the DNA-distribution PDF)."
        ),
    )
    p_run.add_argument(
        "--rerun-from",
        choices=("step9",),
        help=(
            "Used with --resume: which stage to re-run. Currently only `step9` "
            "is supported, which re-renders and re-runs the Step-9 R against "
            "the already-produced alignment outputs."
        ),
    )
    p_run.set_defaults(func=cmd_run)

    p_dash = sub.add_parser("dashboard", help="Launch the web dashboard.")
    p_dash.add_argument("--runs", help="Directory of run manifests to display (default: ./runs).")
    p_dash.add_argument("--host", default="127.0.0.1")
    p_dash.add_argument("--port", type=int, default=8000)
    p_dash.add_argument("--log-level", default="info", choices=("debug", "info", "warning", "error"))
    p_dash.add_argument("--reload", action="store_true", help="Auto-reload on backend file changes (dev).")
    p_dash.set_defaults(func=cmd_dashboard)

    p_st = sub.add_parser("status", help="Summarize a single run's manifest.")
    p_st.add_argument("run_id", help="Run id (the directory name under runs/).")
    p_st.add_argument("--runs-dir", help="Override the runs directory.")
    p_st.set_defaults(func=cmd_status)

    p_pf = sub.add_parser("preflight", help="Check that all required tools and packages are installed.")
    p_pf.set_defaults(func=cmd_preflight)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
