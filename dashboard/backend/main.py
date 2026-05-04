"""FastAPI app for the TREND Dashboard.

Phase 1 / Week 1 surface:
    GET /healthz                       Liveness + ingest status
    GET /library/summary               FR-6 summary cards + histograms (cached JSON)
    GET /library/constructs            Paginated/filterable construct table
    GET /library/constructs/{id}       Construct detail with metadata join
    GET /                              Static frontend bundle (in container mode)

Future weeks:
    /run/*       Pipeline runner + state machine + SSE  (Week 3-4)
    /results/*   Output explorer with column tooltips    (Week 4)
    /preflight   Environment check                       (Week 5)
"""

from __future__ import annotations

import logging
from pathlib import Path

import asyncio
import json as _json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend import __version__, config, preflight
from backend.library import queries
from backend.library.pwms import load_pwms
from backend.library.summary import SummaryNotBuilt, load_summary
from backend.oracle.run_example import run_oracle
from backend.pipeline import error_hints, runner
from backend.schemas import _loader as schema_loader

log = logging.getLogger("trend.dashboard")

app = FastAPI(
    title="TREND Dashboard",
    description="Local-first wrapper around the TREND bioinformatics pipeline.",
    version=__version__,
)

# Vite dev server runs on :5173; FastAPI on :8000. Permit local cross-origin during dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict:
    """Liveness probe + report whether the library has been ingested."""
    return {
        "status": "ok",
        "version": __version__,
        "library_ingested": config.LIBRARY_DB.exists() and config.LIBRARY_SUMMARY_JSON.exists(),
        "container_mode": config.is_container_mode(),
    }


@app.get("/library/summary")
def library_summary() -> dict:
    """Library summary: cards + histograms + per-TF stacked bar."""
    try:
        return load_summary()
    except SummaryNotBuilt as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@app.get("/library/dbd_families")
def library_dbd_families() -> dict:
    """Panel B + C source data: per-DBD-family TF count and sensor count.
    Each row also carries a stable color used by both panels."""
    try:
        summary = load_summary()
    except SummaryNotBuilt as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    cls = summary.get("classifications", {})
    return {
        "families": cls.get("dbd_families", []),
        "n_classified_tfs": cls.get("totals", {}).get("n_classified_tfs", 0),
    }


@app.get("/library/pwms")
def library_pwms() -> dict:
    """All position probability matrices, keyed by motif name.

    Each value is a 4×W matrix as [[A...], [C...], [G...], [T...]] giving the
    probability of each base at each position. Used by the frontend to render
    sequence logos for every cancer-selective enhancer.
    """
    return {"pwms": load_pwms()}


@app.get("/library/cacts_coverage")
def library_cacts_coverage() -> dict:
    """Panel D source data: TREND coverage of cancer master TFs (Reddy CaCTS)
    across TCGA tumor types."""
    try:
        summary = load_summary()
    except SummaryNotBuilt as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return summary.get("classifications", {}).get(
        "cacts_coverage", {"per_tumor": [], "totals": {}}
    )


@app.get("/library/dalessio_coverage")
def library_dalessio_coverage() -> dict:
    """Panel E source data: TREND coverage of cell identity TFs (D'Alessio)
    across anatomical systems."""
    try:
        summary = load_summary()
    except SummaryNotBuilt as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return summary.get("classifications", {}).get(
        "dalessio_coverage", {"per_system": [], "totals": {}}
    )


@app.get("/library/constructs")
def library_constructs(
    tf: str | None = Query(default=None, description="Exact TF (e.g., 'A1CF')."),
    promoter_prefix: str | None = Query(default=None, description="Prefix match on promoter_name."),
    by_ppm_name: str | None = Query(default=None, description="Exact PPM identifier."),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict:
    try:
        page = queries.list_constructs(
            tf=tf,
            promoter_prefix=promoter_prefix,
            by_ppm_name=by_ppm_name,
            limit=limit,
            offset=offset,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "total": page.total,
        "offset": page.offset,
        "limit": page.limit,
        "rows": [r.__dict__ for r in page.rows],
    }


@app.get("/library/enhancers")
def library_enhancers(
    q: str | None = Query(default=None, description="Free-text substring match across TF, TFBS, PPM, and variable region."),
    tf: str | None = Query(default=None, description="Exact TF name (e.g., 'MYC')."),
    tfbs_prefix: str | None = Query(default=None, description="Prefix match on TFBS sequence."),
    by_ppm_name: str | None = Query(default=None, description="Exact PPM identifier."),
    dbd_family: str | None = Query(default=None, description="Lambert DBD family (Panel B/C bar)."),
    cacts_tumor: str | None = Query(default=None, description="TCGA tumor type code (Panel D bar)."),
    dalessio_system: str | None = Query(default=None, description="D'Alessio anatomical system (Panel E bar)."),
    tf_contains: str | None = Query(default=None, description="Substring filter on TF (case-insensitive)."),
    tfbs_contains: str | None = Query(default=None, description="Substring filter on TFBS sequence."),
    ppm_contains: str | None = Query(default=None, description="Substring filter on PPM identifier."),
    vr_contains: str | None = Query(default=None, description="Substring filter on variable region."),
    dbd_contains: str | None = Query(default=None, description="Substring filter on Lambert DBD family."),
    sort_by: str = Query(default="TF", description="Column to sort by."),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Enhancer-level paginated table: one row per designed enhancer
    (multibarcode-collapsed), with n_barcodes attached."""
    try:
        page = queries.list_enhancers(
            q=q,
            tf=tf,
            tfbs_prefix=tfbs_prefix,
            by_ppm_name=by_ppm_name,
            dbd_family=dbd_family,
            cacts_tumor=cacts_tumor,
            dalessio_system=dalessio_system,
            tf_contains=tf_contains,
            tfbs_contains=tfbs_contains,
            ppm_contains=ppm_contains,
            vr_contains=vr_contains,
            dbd_contains=dbd_contains,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "total": page.total,
        "offset": page.offset,
        "limit": page.limit,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "rows": [r.__dict__ for r in page.rows],
    }


@app.get("/library/enhancers/export")
def library_enhancers_export(
    q: str | None = Query(default=None),
    tf: str | None = Query(default=None),
    tfbs_prefix: str | None = Query(default=None),
    by_ppm_name: str | None = Query(default=None),
    dbd_family: str | None = Query(default=None),
    cacts_tumor: str | None = Query(default=None),
    dalessio_system: str | None = Query(default=None),
    tf_contains: str | None = Query(default=None),
    tfbs_contains: str | None = Query(default=None),
    ppm_contains: str | None = Query(default=None),
    vr_contains: str | None = Query(default=None),
    dbd_contains: str | None = Query(default=None),
    sort_by: str = Query(default="TF"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> StreamingResponse:
    """Stream the full filtered enhancer set as CSV. Same filter/sort params as
    /library/enhancers, no pagination — the user gets every row matching their
    current narrowing in the dashboard's enhancer table."""
    import csv
    import io
    from datetime import date

    # Header labels mirror the dashboard table columns the user is looking at.
    columns = [
        ("TF", "TF"),
        ("Lambert_DBD_family", "DBD Family"),
        ("TFBS_sequence", "TFBS"),
        ("variable_region", "Variable Region"),
        ("by_ppm_name", "PPM Name"),
        ("rank", "Rank"),
        ("n_barcodes", "# Barcodes"),
    ]

    try:
        row_iter = queries.iter_enhancers_for_export(
            q=q, tf=tf, tfbs_prefix=tfbs_prefix, by_ppm_name=by_ppm_name,
            dbd_family=dbd_family, cacts_tumor=cacts_tumor, dalessio_system=dalessio_system,
            tf_contains=tf_contains, tfbs_contains=tfbs_contains, ppm_contains=ppm_contains,
            vr_contains=vr_contains, dbd_contains=dbd_contains,
            sort_by=sort_by, sort_dir=sort_dir,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    def gen():
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow([label for _, label in columns])
        n = 0
        BATCH = 500
        for row in row_iter:
            d = row.__dict__
            writer.writerow([d.get(field, "") if d.get(field) is not None else "" for field, _ in columns])
            n += 1
            if n >= BATCH:
                yield buf.getvalue()
                buf.seek(0)
                buf.truncate(0)
                n = 0
        if buf.tell():
            yield buf.getvalue()

    filename = f"trend_library_enhancers_{date.today().isoformat()}.csv"
    return StreamingResponse(
        gen(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/library/constructs/{construct_id}")
def library_construct_detail(construct_id: str) -> JSONResponse:
    try:
        result = queries.get_construct(construct_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail=f"Construct '{construct_id}' not found.")
    return JSONResponse(result)


@app.get("/library/constructs/{construct_id}/performance")
def library_construct_performance(construct_id: str) -> dict:
    """Per-project activity for a single promoter, across every project that has one.

    Scans the same result CSVs that drive the strip plot. Returns a list of
    `{project, title, metrics: {label: value}}` entries — empty list if the
    promoter doesn't appear in any project.
    """
    import pandas as pd

    out: list[dict] = []
    for project, cfg in _SELECTIVITY_PROJECTS.items():
        target = (
            config.PROJECT_DATA_ROOT / "final_enhancer_activity_results" / project / cfg["csv"]
        )
        if not target.exists():
            continue
        df = pd.read_csv(target)
        match = df[df["promoter_name"] == construct_id]
        if match.empty:
            continue
        row = match.iloc[0]

        def _val(col: str) -> float | None:
            if col not in row or pd.isna(row[col]):
                return None
            return round(float(row[col]), 4)

        exp_label, ctrl_label = cfg["title"].split("/")
        metrics: dict[str, float | None] = {
            f"{exp_label} activity": _val(cfg["exp_col"]),
            f"{ctrl_label} activity": _val(cfg["ctrl_col"]),
            f"{cfg['title']} ratio": _val(cfg["ratio_col"]),
        }
        out.append({
            "project": project,
            "title": cfg["title"],
            "tf": (str(row[cfg["tf_col"]]) if cfg["tf_col"] in row and pd.notna(row[cfg["tf_col"]]) else None),
            "by_ppm_name": _normalize_pwm_name(row["by_ppm_name"]) if "by_ppm_name" in row and pd.notna(row["by_ppm_name"]) else None,
            "rank": int(row["rank"]) if "rank" in row and pd.notna(row["rank"]) else None,
            "metrics": metrics,
        })

    return {"promoter_name": construct_id, "projects": out}


@app.get("/preflight")
def preflight_check(force: bool = False) -> dict:
    """FR-2 environment check. Cached for 30s; pass ?force=true to refresh."""
    return preflight.report_dict(force=force)


@app.get("/run/{run_id}/hint")
def run_hint(run_id: str) -> dict:
    """FR-9 plain-language hint for the failed step in a run, if any."""
    try:
        manifest = runner.get_manifest_dict(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    failed = next((s for s in manifest["steps"] if s["status"] == "failed"), None)
    if not failed:
        return {"failed_step": None, "hint": None}
    hint = error_hints.classify(failed.get("stderr_tail") or [])
    return {
        "failed_step": failed["id"],
        "step_name": failed["name"],
        "exit_code": failed.get("exit_code"),
        "stderr_tail": failed.get("stderr_tail", [])[-10:],
        "hint": hint,
    }


@app.get("/run/steps")
def run_steps() -> dict:
    """Static description of the 9 pipeline steps for the FR-1 state machine view."""
    steps = runner.load_steps()
    return {
        "schema_version": 1,
        "steps": [
            {
                "id": s["id"],
                "name": s["name"],
                "short_purpose": s.get("short_purpose", ""),
                "tool": s.get("tool", ""),
                "optional": s.get("optional", False),
                "inputs": s.get("inputs", []),
                "outputs": s.get("outputs", []),
            }
            for s in steps
        ],
    }


class StartRunRequest(BaseModel):
    project: str = "ovarian_cancer"
    mode: str = "dry_run"  # "real" requires bowtie2/cutadapt/Rscript on PATH (Docker)
    inputs: dict[str, str] = {}  # in-run filename -> source path
    parameters: dict[str, object] = {}
    step_filter: list[str] | None = None


@app.post("/run/start")
def start_run(req: StartRunRequest) -> dict:
    """Stream pipeline status events as SSE.

    The endpoint launches the run synchronously (in this thread) but emits
    each step's start/finish event over Server-Sent Events. The browser
    progressively renders the FR-1 state-machine view from those events.
    """
    inputs_resolved = {name: Path(path) for name, path in req.inputs.items()}
    iterator = runner.run_pipeline(
        project=req.project,
        inputs=inputs_resolved,
        parameters=req.parameters,
        mode=req.mode,
        step_filter=req.step_filter,
    )

    async def event_source():
        # runner.run_pipeline is sync; bridge it into the asyncio loop step-by-step.
        loop = asyncio.get_running_loop()
        sentinel = object()

        def _next():
            try:
                return next(iterator)
            except StopIteration:
                return sentinel

        while True:
            event = await loop.run_in_executor(None, _next)
            if event is sentinel:
                break
            yield {"event": event.get("event", "message"), "data": _json.dumps(event)}

    return EventSourceResponse(event_source())


@app.post("/run/example")
def run_example(
    project: str = Query(default="ovarian_cancer"),
    tier: str = Query(default="smoke", pattern="^(smoke|step9|pipeline)$"),
) -> dict:
    """Reviewer oracle. Three tiers:
       smoke    — stub against published outputs (no tools required)
       step9    — bundled subsampled OvCa data (requires R)
       pipeline — simulated FASTQs through full pipeline (requires bowtie2 + R)
    """
    report = run_oracle(project=project, tier=tier)
    return {
        "project": report.project,
        "tier": report.tier,
        "mode": report.mode,
        "overall_pass": report.overall_pass,
        "runtime_seconds": report.runtime_seconds,
        "file_results": report.file_results,
        "notes": report.notes,
    }


_PWM_VERSION_SUFFIX = __import__("re").compile(r"_v\d+$")


def _normalize_pwm_name(raw: object) -> str:
    """Match the CSV's by_ppm_name to the canonical key in the PPM file.

    The CSV stores either the original FASTA header line (`NAME description...`)
    or `NAME` with a trailing `_vN` revision suffix. The PPM file is keyed by
    NAME alone. Splitting on whitespace and stripping the version suffix
    recovers the canonical name in both formats.
    """
    first = str(raw).split()[0] if raw is not None else ""
    return _PWM_VERSION_SUFFIX.sub("", first)


# Project-agnostic schema: the strip plot endpoint maps each project's
# experimental/control columns onto the same OVR/IOSE shape so the frontend
# renders identically regardless of dataset.
_SELECTIVITY_PROJECTS: dict[str, dict[str, str]] = {
    "ovarian_cancer": {
        "csv": "ovca_sensor_activity_result_concise.csv",
        "exp_col": "mean_OV8_RD_ratio",
        "ctrl_col": "mean_IOSE_RD_ratio",
        "ratio_col": "mean_OV8_to_IOSE_RD_ratio",
        "tf_col": "TF_name_human_curated",
        "title": "OV8/IOSE",
    },
    "T_cell_activation": {
        "csv": "activation_responsive_enhancer_screening_result_donor1.csv",
        "exp_col": "median_stim_Lib4_RD_ratio_r1",
        "ctrl_col": "median_rest_Lib4_RD_ratio_r1",
        "ratio_col": "stim_to_rest_RD_ratio_r1",
        "tf_col": "TF_name_human_curated",
        "title": "Stim/Rest",
    },
}


@app.get("/results/selectivity_scatter")
def results_selectivity_scatter(
    project: str = Query(default="ovarian_cancer"),
    selectivity_threshold: float = Query(default=2.0, description="log2 fold-change cutoff for highlighting selective enhancers."),
    min_activity: float = Query(default=0.1, description="Minimum experimental RD ratio to include."),
) -> dict:
    """Strip-plot source data, project-agnostic.

    Each project supplies its own experimental/control columns; we map them
    onto a single OVR/IOSE shape:
      x = log2(experimental / control)
      y = log10(experimental)
    """
    import math
    import pandas as pd

    cfg = _SELECTIVITY_PROJECTS.get(project)
    if not cfg:
        raise HTTPException(
            status_code=400,
            detail=f"No strip-plot config for project '{project}'.",
        )

    target = (
        config.PROJECT_DATA_ROOT / "final_enhancer_activity_results" / project / cfg["csv"]
    )
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Result file not found: {target}")

    exp_col, ctrl_col, ratio_col, tf_col = cfg["exp_col"], cfg["ctrl_col"], cfg["ratio_col"], cfg["tf_col"]

    df = pd.read_csv(target)
    df = df.dropna(subset=[exp_col, ratio_col])
    df = df[(df[exp_col] > min_activity) & (df[ratio_col] > 0)]

    df["log2_selectivity"] = df[ratio_col].apply(lambda v: math.log2(v) if v > 0 else None)
    df["log10_activity"] = df[exp_col].apply(lambda v: math.log10(v) if v > 0 else None)
    df = df.dropna(subset=["log2_selectivity", "log10_activity"])

    df["selective"] = df["log2_selectivity"] >= selectivity_threshold
    df = df.sort_values("log2_selectivity", ascending=True).reset_index(drop=True)

    rows = [
        {
            "promoter_name": str(r.promoter_name),
            "tf": str(getattr(r, tf_col)) if pd.notna(getattr(r, tf_col)) else "",
            "by_ppm_name": _normalize_pwm_name(r.by_ppm_name) if pd.notna(r.by_ppm_name) else "",
            "rank": int(r.rank) if pd.notna(r.rank) else None,
            "tfbs_sequence": str(r.TFBS_sequence) if pd.notna(getattr(r, "TFBS_sequence", None)) else None,
            "x": round(float(r.log2_selectivity), 3),
            "y": round(float(r.log10_activity), 3),
            "selectivity_ratio": round(float(getattr(r, ratio_col)), 3),
            "ov8_activity": round(float(getattr(r, exp_col)), 3),
            "iose_activity": round(float(getattr(r, ctrl_col)), 3) if pd.notna(getattr(r, ctrl_col)) else None,
            "selective": bool(r.selective),
        }
        for r in df.itertuples()
    ]
    n_selective = sum(1 for r in rows if r["selective"])
    top10 = sorted(rows, key=lambda r: -r["x"])[:10]

    return {
        "project": project,
        "selectivity_threshold": selectivity_threshold,
        "min_activity": min_activity,
        "n_total": len(rows),
        "n_selective": n_selective,
        "title": cfg["title"],
        "x_label": f"log2({cfg['title']}) RD ratio",
        "y_label": f"log10({cfg['title'].split('/')[0]} RD ratio)",
        "rows": rows,
        "top_selective": top10,
    }


@app.get("/results/projects")
def results_projects() -> dict:
    """Enumerate the projects with bundled published results."""
    base = config.PROJECT_DATA_ROOT / "final_enhancer_activity_results"
    projects = []
    if base.exists():
        for d in sorted(p for p in base.iterdir() if p.is_dir()):
            files = sorted(p.name for p in d.glob("*.csv"))
            projects.append({"name": d.name, "files": files})
    return {"projects": projects}


@app.get("/results/file")
def results_file(
    project: str = Query(...),
    filename: str = Query(...),
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Read a result CSV with column tooltips from the schema YAML."""
    import pandas as pd

    base = config.PROJECT_DATA_ROOT / "final_enhancer_activity_results" / project
    target = base / filename
    if not target.exists():
        # Try filename normalization (e.g., the double-dot quirk).
        candidate = next((p for p in base.glob(filename + "*") if p.is_file()), None)
        if candidate is None:
            raise HTTPException(status_code=404, detail=f"Result file not found: {target}")
        target = candidate

    # Read paginated rows.
    df = pd.read_csv(target, skiprows=range(1, 1 + offset) if offset else None, nrows=limit)
    # Total row count for paginator (cheap line-count, minus header).
    with open(target, "rb") as f:
        total = sum(1 for _ in f) - 1

    schema = schema_loader.schema_for(filename) or {}
    columns_meta = {c["name"]: c for c in schema.get("columns", [])}
    columns = [
        {
            "name": col,
            "type": columns_meta.get(col, {}).get("type", "string"),
            "description": columns_meta.get(col, {}).get("description"),
        }
        for col in df.columns
    ]
    rows = [
        {col: (None if pd.isna(v) else (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)) for col, v in row.items()}
        for row in df.to_dict(orient="records")
    ]
    return {
        "project": project,
        "filename": target.name,
        "schema_description": schema.get("description"),
        "total": total,
        "offset": offset,
        "limit": limit,
        "columns": columns,
        "rows": rows,
    }


@app.get("/run/history")
def run_history(limit: int = Query(default=50, ge=1, le=500)) -> dict:
    return {"runs": runner.list_runs(limit=limit)}


@app.get("/run/{run_id}/manifest")
def run_manifest(run_id: str) -> dict:
    try:
        return runner.get_manifest_dict(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# Mount the built frontend bundle if it exists (container mode). In native dev,
# `npm run dev` serves the frontend on :5173 instead.
#
# StaticFiles with html=True serves index.html for `/` but not for client-side
# routes like `/library`. Mount static assets under `/assets` and add an SPA
# fallback that returns index.html for any GET that didn't match an API route.
if config.FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=config.FRONTEND_DIST / "assets"),
        name="frontend-assets",
    )

    INDEX_HTML = config.FRONTEND_DIST / "index.html"
    _STATIC_PASSTHROUGH = {"vite.svg", "favicon.ico", "robots.txt"}

    @app.get("/{spa_path:path}", include_in_schema=False)
    def spa_fallback(spa_path: str, request: Request):
        # Pass through any real file at the root of the dist (e.g., favicon).
        if spa_path in _STATIC_PASSTHROUGH:
            file_path = config.FRONTEND_DIST / spa_path
            if file_path.exists():
                return FileResponse(file_path)
        # Everything else is a React Router route — serve the SPA shell.
        return FileResponse(INDEX_HTML)


def run() -> None:
    """Console-script entry: `trend-dashboard`."""
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)


