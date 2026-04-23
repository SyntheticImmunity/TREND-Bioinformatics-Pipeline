/** Typed fetch helpers for the FastAPI backend.
 *
 * The Vite dev server proxies /healthz, /library, /run, /results, /preflight to
 * http://127.0.0.1:8000 (see vite.config.ts).
 */

export interface Health {
  status: string;
  version: string;
  library_ingested: boolean;
  container_mode: boolean;
}

export interface HistogramJSON {
  bin_edges: number[];
  counts: number[];
}

export interface ConstructsPerTfRow {
  tf: string;
  count: number;
}

export interface LibrarySummary {
  schema_version: number;
  total_constructs: number;
  total_promoters: number;
  total_tfs_in_library: number;
  total_tfs_curated: number;
  total_variable_regions: number;
  mean_barcodes_per_promoter: number;
  median_barcodes_per_promoter: number;
  barcodes_per_promoter_histogram: HistogramJSON;
  enhancers_per_tf: ConstructsPerTfRow[];
  constructs_per_tf: ConstructsPerTfRow[];
  variable_region_length_histogram: HistogramJSON;
  classifications?: {
    totals: {
      n_classified_tfs: number;
      n_dbd_families_chart: number;
      n_dbd_families_total: number;
      cacts: { n_in: number; n_total: number; pct: number };
      dalessio: { n_in: number; n_total: number; pct: number };
    };
    composition_breakdown: CompositionBreakdown;
  };
}

export interface CompositionLeaf {
  label: string;
  count: number;
  color: string;
}

export interface CompositionBranch extends CompositionLeaf {
  children?: CompositionLeaf[];
}

export interface CompositionBreakdown {
  total: number;
  branches: CompositionBranch[];
}

export interface ConstructRow {
  promoter_name_bc: string;
  promoter_name: string;
  TFBS_random_bc: string;
  TFBS: string;
  TF: string;
  by_ppm_name: string;
  rank: number;
}

export interface ConstructPage {
  total: number;
  offset: number;
  limit: number;
  rows: ConstructRow[];
}

export interface EnhancerRow {
  TF: string;
  TF_name_by_PPM: string;
  TFBS_sequence: string;
  variable_region: string;
  by_ppm_name: string;
  rank: number;
  Lambert_DBD_family: string | null;
  Lambert_TF_assessment: string | null;
  Lambert_matched: string | null;
  n_barcodes: number;
}

export interface EnhancerPage {
  total: number;
  offset: number;
  limit: number;
  sort_by?: EnhancerSortColumn;
  sort_dir?: "asc" | "desc";
  rows: EnhancerRow[];
}

export type EnhancerSortColumn =
  | "TF"
  | "TFBS_sequence"
  | "variable_region"
  | "by_ppm_name"
  | "rank"
  | "n_barcodes";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export interface PipelineStep {
  id: string;
  name: string;
  short_purpose: string;
  tool: string;
  optional: boolean;
  inputs: string[];
  outputs: string[];
}

export interface RunHistoryRow {
  run_id: string;
  project: string;
  status: string;
  mode: string;
  created_at: string;
  finished_at: string | null;
}

export interface OracleFileResult {
  filename: string;
  equivalent: boolean;
  summary: string;
  column_diff?: { only_in_actual?: string[]; only_in_expected?: string[] } | null;
  row_count_diff?: [number, number] | null;
  numeric_mismatches?: { column: string; row: number; actual: number | string; expected: number | string }[];
  string_mismatches?: { column: string; row: number; actual: string; expected: string }[];
}

export type ExampleTier = "smoke" | "step9" | "pipeline";

export interface OracleReport {
  project: string;
  tier: ExampleTier;
  mode: "real" | "stub";
  overall_pass: boolean;
  runtime_seconds: number;
  file_results: OracleFileResult[];
  notes: string[];
}

export interface ResultsColumn {
  name: string;
  type: string;
  description: string | null;
}

export interface ResultsFile {
  project: string;
  filename: string;
  schema_description: string | null;
  total: number;
  offset: number;
  limit: number;
  columns: ResultsColumn[];
  rows: Record<string, unknown>[];
}

export interface RunStartRequest {
  project?: string;
  mode?: "dry_run" | "real";
  inputs?: Record<string, string>;
  parameters?: Record<string, unknown>;
  step_filter?: string[];
}

export const api = {
  health: () => getJson<Health>("/healthz"),
  librarySummary: () => getJson<LibrarySummary>("/library/summary"),
  listConstructs: (params: {
    tf?: string;
    promoter_prefix?: string;
    by_ppm_name?: string;
    limit?: number;
    offset?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params.tf) qs.set("tf", params.tf);
    if (params.promoter_prefix) qs.set("promoter_prefix", params.promoter_prefix);
    if (params.by_ppm_name) qs.set("by_ppm_name", params.by_ppm_name);
    if (params.limit !== undefined) qs.set("limit", String(params.limit));
    if (params.offset !== undefined) qs.set("offset", String(params.offset));
    return getJson<ConstructPage>(`/library/constructs?${qs.toString()}`);
  },
  getConstruct: (id: string) =>
    getJson<{ construct: ConstructRow & Record<string, unknown>; metadata: Record<string, unknown> | null }>(
      `/library/constructs/${encodeURIComponent(id)}`,
    ),
  listEnhancers: (params: {
    q?: string;
    tf?: string;
    tfbs_prefix?: string;
    by_ppm_name?: string;
    dbd_family?: string;
    cacts_tumor?: string;
    dalessio_system?: string;
    sort_by?: EnhancerSortColumn;
    sort_dir?: "asc" | "desc";
    limit?: number;
    offset?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.tf) qs.set("tf", params.tf);
    if (params.tfbs_prefix) qs.set("tfbs_prefix", params.tfbs_prefix);
    if (params.by_ppm_name) qs.set("by_ppm_name", params.by_ppm_name);
    if (params.dbd_family) qs.set("dbd_family", params.dbd_family);
    if (params.cacts_tumor) qs.set("cacts_tumor", params.cacts_tumor);
    if (params.dalessio_system) qs.set("dalessio_system", params.dalessio_system);
    if (params.sort_by) qs.set("sort_by", params.sort_by);
    if (params.sort_dir) qs.set("sort_dir", params.sort_dir);
    if (params.limit !== undefined) qs.set("limit", String(params.limit));
    if (params.offset !== undefined) qs.set("offset", String(params.offset));
    return getJson<EnhancerPage>(`/library/enhancers?${qs.toString()}`);
  },
  pipelineSteps: () => getJson<{ schema_version: number; steps: PipelineStep[] }>("/run/steps"),
  runHistory: (limit = 50) => getJson<{ runs: RunHistoryRow[] }>(`/run/history?limit=${limit}`),
  runExample: (project = "ovarian_cancer", tier: ExampleTier = "smoke") =>
    fetch(
      `/run/example?project=${encodeURIComponent(project)}&tier=${encodeURIComponent(tier)}`,
      { method: "POST" },
    ).then((r) => {
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      return r.json() as Promise<OracleReport>;
    }),
  resultsProjects: () =>
    getJson<{ projects: { name: string; files: string[] }[] }>("/results/projects"),
  resultsFile: (project: string, filename: string, limit = 200, offset = 0) =>
    getJson<ResultsFile>(
      `/results/file?project=${encodeURIComponent(project)}&filename=${encodeURIComponent(filename)}&limit=${limit}&offset=${offset}`,
    ),
  runManifest: (runId: string) =>
    getJson<{
      run_id: string;
      project: string;
      status: string;
      created_at: string;
      finished_at: string | null;
      software: Record<string, string>;
      steps: Array<{
        id: string;
        name: string;
        status: string;
        exit_code: number | null;
        runtime_seconds: number | null;
        stderr_tail: string[];
      }>;
    }>(`/run/${runId}/manifest`),
  preflight: (force = false) =>
    getJson<PreflightReport>(`/preflight${force ? "?force=true" : ""}`),
  dbdFamilies: () =>
    getJson<{ families: DbdFamily[]; n_classified_tfs: number }>("/library/dbd_families"),
  cactsCoverage: () => getJson<CoverageBundle<CactsRow>>("/library/cacts_coverage"),
  dalessioCoverage: () => getJson<CoverageBundle<DalessioRow>>("/library/dalessio_coverage"),
  selectivityScatter: (project = "ovarian_cancer") =>
    getJson<SelectivityScatter>(
      `/results/selectivity_scatter?project=${encodeURIComponent(project)}`,
    ),
};

export interface SelectivityPoint {
  promoter_name: string;
  tf: string;
  x: number;
  y: number;
  selectivity_ratio: number;
  ov8_activity: number;
  iose_activity: number | null;
  selective: boolean;
}

export interface SelectivityScatter {
  project: string;
  selectivity_threshold: number;
  min_activity: number;
  n_total: number;
  n_selective: number;
  x_label: string;
  y_label: string;
  rows: SelectivityPoint[];
  top_selective: SelectivityPoint[];
}

export interface DbdFamily {
  family: string;
  n_tfs: number;
  n_sensors: number;
  color: string;
}

interface CoverageRowBase {
  n_total: number;
  n_in: number;
  n_missing: number;
  pct: number;
  in_tfs: string[];
  missing_tfs: string[];
}

export interface CactsRow extends CoverageRowBase {
  tumor: string;
}

export interface DalessioRow extends CoverageRowBase {
  system: string;
}

export interface CoverageBundle<R> {
  totals: { n_in: number; n_total: number; pct: number };
  per_tumor?: R[];
  per_system?: R[];
}

export interface PreflightCheck {
  name: string;
  category: "binary" | "python_package" | "r_package";
  found: boolean;
  version: string | null;
  purpose: string;
  hint: string;
  severity: "info" | "warning" | "error";
}

export interface PreflightReport {
  container_mode: boolean;
  os_name: string;
  os_version: string;
  overall: "ok" | "degraded" | "blocked";
  checks: PreflightCheck[];
  summary: string;
}

/**
 * SSE consumer for /run/start. fetch() with text/event-stream parsing because
 * EventSource can't issue POST requests.
 */
export async function startRun(
  body: RunStartRequest,
  onEvent: (event: { event: string } & Record<string, unknown>) => void,
): Promise<void> {
  const res = await fetch("/run/start", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    throw new Error(`Run failed to start: ${res.status} ${res.statusText}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const dataLine = block
        .split("\n")
        .find((line) => line.startsWith("data:"));
      if (!dataLine) continue;
      try {
        const payload = JSON.parse(dataLine.slice(5).trim());
        onEvent(payload);
      } catch {
        /* ignore malformed lines */
      }
    }
  }
}
