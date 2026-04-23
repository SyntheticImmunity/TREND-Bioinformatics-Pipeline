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
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend import __version__, config, preflight
from backend.library import queries
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


@app.get("/library/constructs/{construct_id}")
def library_construct_detail(construct_id: str) -> JSONResponse:
    try:
        result = queries.get_construct(construct_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail=f"Construct '{construct_id}' not found.")
    return JSONResponse(result)


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


@app.get("/results/selectivity_scatter")
def results_selectivity_scatter(
    project: str = Query(default="ovarian_cancer"),
    selectivity_threshold: float = Query(default=2.0, description="log2 fold-change cutoff for highlighting cancer-selective enhancers."),
    min_activity: float = Query(default=0.1, description="Minimum tumor RD ratio to include."),
) -> dict:
    """Panel F source data: cancer-selectivity volcano-style scatter for OvCa.

    For each promoter we compute:
      x = log2(mean_OV8_to_IOSE_RD_ratio)
      y = log10(mean_OV8_RD_ratio)
    Promoters where log2(selectivity) >= threshold AND OV8 activity > 0 are
    flagged 'selective' so the frontend can highlight them in red.
    """
    import math
    import pandas as pd

    if project != "ovarian_cancer":
        raise HTTPException(status_code=400, detail="Selectivity scatter is currently OvCa-specific.")

    target = (
        config.PROJECT_DATA_ROOT
        / "final_enhancer_activity_results"
        / "ovarian_cancer"
        / "ovca_sensor_activity_result_concise.csv"
    )
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Result file not found: {target}")

    df = pd.read_csv(target)
    df = df.dropna(subset=["mean_OV8_RD_ratio", "mean_OV8_to_IOSE_RD_ratio"])
    df = df[(df["mean_OV8_RD_ratio"] > min_activity) & (df["mean_OV8_to_IOSE_RD_ratio"] > 0)]

    # Compute axes; cap log values to keep the chart legible.
    df["log2_selectivity"] = df["mean_OV8_to_IOSE_RD_ratio"].apply(
        lambda v: math.log2(v) if v > 0 else None
    )
    df["log10_activity"] = df["mean_OV8_RD_ratio"].apply(
        lambda v: math.log10(v) if v > 0 else None
    )
    df = df.dropna(subset=["log2_selectivity", "log10_activity"])

    df["selective"] = df["log2_selectivity"] >= selectivity_threshold

    # Sort by selectivity desc so highlighted points draw on top in the SVG.
    df = df.sort_values("log2_selectivity", ascending=True).reset_index(drop=True)

    # Keep payload small — rounding to 3 decimals.
    rows = [
        {
            "promoter_name": str(r.promoter_name),
            "tf": str(r.TF_name_human_curated) if pd.notna(r.TF_name_human_curated) else "",
            "x": round(float(r.log2_selectivity), 3),
            "y": round(float(r.log10_activity), 3),
            "selectivity_ratio": round(float(r.mean_OV8_to_IOSE_RD_ratio), 3),
            "ov8_activity": round(float(r.mean_OV8_RD_ratio), 3),
            "iose_activity": round(float(r.mean_IOSE_RD_ratio), 3) if pd.notna(r.mean_IOSE_RD_ratio) else None,
            "selective": bool(r.selective),
        }
        for r in df.itertuples()
    ]
    n_selective = sum(1 for r in rows if r["selective"])

    # Top-10 most selective for a sidebar list.
    top10 = sorted(rows, key=lambda r: -r["x"])[:10]

    return {
        "project": project,
        "selectivity_threshold": selectivity_threshold,
        "min_activity": min_activity,
        "n_total": len(rows),
        "n_selective": n_selective,
        "x_label": "log2(OV8 / IOSE) RD ratio",
        "y_label": "log10(OV8 RD ratio)",
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
