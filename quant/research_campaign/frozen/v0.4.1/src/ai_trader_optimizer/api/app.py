"""HTTP API v1 of the quant engine — React talks ONLY to this.

React → FastAPI (this module) → services.py → engine / risk / analytics / catalog.

Guarantees
* No order route, no credential field, no broker import (``tests/test_api.py`` enumerates routes).
* Every number in a response was computed by the engine and read back from the catalog.
* Inputs are validated by the domain pydantic models (extra fields refused); ids are
  16-hex fingerprints (no path traversal); uploads are size-limited and parsed in memory.
* Errors are mapped to 4xx with a French message; unexpected errors return a generic 500
  (details only in the server log).
"""

from __future__ import annotations

import io
import logging
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, Path, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from .. import ENGINE_VERSION, __version__
from ..analytics.metrics import drawdown_series_pct
from ..backtest.codehash import code_fingerprint
from ..data import import_csv, synthetic_dataset
from ..research import (
    RegistryIntegrityError,
    StudyIntegrityError,
    StudySettings,
    list_studies,
    load_study,
    run_edge_study,
    run_robustness,
)
from ..risk.guardian import REJECTION_LABELS_FR
from ..safety import DEMO_TRADING_ENABLED, LIVE_TRADING_ENABLED, DataKind
from ..services import (
    RiskPolicyViolation,
    default_config,
    policy_mode,
    reproduce,
    resolve_risk_policy,
    run_and_store,
)
from ..storage import (
    CorruptRunError,
    LabCatalog,
    ProvenanceConflictError,
    ReproducibilityError,
    RunNotFoundError,
)
from ..strategies import IMPLEMENTATIONS, StrategyNotRunnableError, load_catalog
from .schemas import (
    ID_PATTERN,
    BacktestRequest,
    DemoDatasetRequest,
    EdgeStudyRequest,
    Health,
    ReproduceResult,
    frame_records,
    to_jsonable,
)
from .security import LocalRequestGuard, max_upload_bytes

log = logging.getLogger("ai_trader_optimizer.api")

DEFAULT_ORIGINS = "http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173"
ENGINE_REASON_LABELS_FR = {
    "OUTSIDE_TEST_WINDOW": "Avant le début de la période testée",
    "EXITED_THIS_BAR": "Une position vient de se fermer dans cette bougie",
    "NON_TRADING_DAY": "Jour non tradé par la stratégie",
    "OUTSIDE_SESSION": "Hors des horaires de trading",
    "INVALID_PRICES": "Prix de stop / objectif invalides",
}
EXPORTS = {
    "trades.csv": ("trades.csv", "text/csv"),
    "decisions.csv": ("decisions.csv", "text/csv"),
    "equity.csv.gz": ("equity.csv.gz", "application/gzip"),
    "metrics.json": ("metrics.json", "application/json"),
    "manifest.json": ("manifest.json", "application/json"),
}
RunId = Annotated[str, Path(pattern=ID_PATTERN, description="Empreinte du run (16 hex)")]
DatasetId = Annotated[str, Path(pattern=ID_PATTERN, description="Empreinte du jeu de données (16 hex)")]
StudyId = Annotated[str, Path(pattern=ID_PATTERN, description="Empreinte de l'étude (16 hex)")]


class JobsBusyError(RuntimeError):
    pass


class StorageQuotaError(RuntimeError):
    pass


def max_rows() -> int:
    return int(os.environ.get("ATO_MAX_ROWS", "3000000"))


def _dir_size(path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def create_app(catalog: LabCatalog | None = None) -> FastAPI:
    policy_mode()  # fail fast on an invalid ATO_RISK_POLICY
    app = FastAPI(title="AI Trader Optimizer — Quant API", version=__version__,
                  description="Simulation uniquement. Aucune route d'ordre, aucun identifiant de courtier.")
    origins = [o.strip() for o in os.environ.get("ATO_CORS_ORIGINS", DEFAULT_ORIGINS).split(",") if o.strip()]
    if "*" in origins:
        raise RuntimeError("ATO_CORS_ORIGINS='*' interdit : listez explicitement les origines locales.")
    app.add_middleware(CORSMiddleware, allow_origins=origins,
                       allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d{1,5})?$",
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-ATO-Request"],
                       allow_credentials=False)
    app.add_middleware(LocalRequestGuard)  # added last = outermost: runs before any body parsing (I3/I4)
    jobs = threading.BoundedSemaphore(max(1, int(os.environ.get("ATO_MAX_CONCURRENT_JOBS", "2"))))

    @contextmanager
    def heavy_job():
        """Bound concurrent imports / simulations (I3): extra requests get 429 instead of queuing work."""
        if not jobs.acquire(blocking=False):
            raise JobsBusyError("Trop de traitements simultanés : réessayez dans quelques secondes.")
        try:
            quota = float(os.environ.get("ATO_MAX_STORAGE_MB", "5120")) * 1024 * 1024
            if _dir_size(cat().root) >= quota:
                raise StorageQuotaError("Quota de stockage du laboratoire atteint (ATO_MAX_STORAGE_MB).")
            yield
        finally:
            jobs.release()

    def cat() -> LabCatalog:
        return catalog if catalog is not None else LabCatalog()

    # ---------------------------------------------------------------- errors
    def err(status: int, message: str, detail=None) -> JSONResponse:
        return JSONResponse(status_code=status, content={"error": message, "detail": to_jsonable(detail)})

    @app.exception_handler(StrategyNotRunnableError)
    async def _not_runnable(_r: Request, exc: StrategyNotRunnableError):
        return err(422, str(exc))

    @app.exception_handler(ReproducibilityError)
    async def _repro(_r: Request, exc: ReproducibilityError):
        return err(409, str(exc))

    @app.exception_handler(RiskPolicyViolation)
    async def _policy(_r: Request, exc: RiskPolicyViolation):
        return err(403, str(exc))

    @app.exception_handler(JobsBusyError)
    async def _busy(_r: Request, exc: JobsBusyError):
        return err(429, str(exc))

    @app.exception_handler(StorageQuotaError)
    async def _quota(_r: Request, exc: StorageQuotaError):
        return err(507, str(exc))

    @app.exception_handler(ProvenanceConflictError)
    async def _provenance(_r: Request, exc: ProvenanceConflictError):
        return err(409, str(exc))

    @app.exception_handler(CorruptRunError)
    async def _corrupt(_r: Request, exc: CorruptRunError):
        return err(409, str(exc))

    @app.exception_handler(StudyIntegrityError)
    async def _corrupt_study(_r: Request, exc: StudyIntegrityError):
        return err(409, str(exc))

    @app.exception_handler(RegistryIntegrityError)
    async def _corrupt_registry(_r: Request, exc: RegistryIntegrityError):
        return err(409, str(exc))

    @app.exception_handler(RunNotFoundError)
    async def _run_missing(_r: Request, exc: RunNotFoundError):
        return err(404, f"Backtest introuvable : {exc.args[0]}")

    @app.exception_handler(RequestValidationError)
    async def _request_validation(_r: Request, exc: RequestValidationError):
        details = [{k: v for k, v in e.items() if k in ("loc", "msg", "type")} for e in exc.errors()]
        return err(422, "Requête invalide : vérifiez les paramètres.", details)

    @app.exception_handler(HTTPException)
    async def _http(_r: Request, exc: HTTPException):
        return err(exc.status_code, str(exc.detail))

    @app.exception_handler(ValidationError)
    async def _validation(_r: Request, exc: ValidationError):
        return err(422, "Paramètres invalides", exc.errors(include_url=False, include_context=False))

    @app.exception_handler(ValueError)
    async def _value(_r: Request, exc: ValueError):
        return err(422, str(exc))

    @app.exception_handler(Exception)
    async def _unexpected(_r: Request, exc: Exception):
        log.exception("Unexpected API error")
        return err(500, "Erreur interne du moteur (détails dans le journal du serveur).")

    # ---------------------------------------------------------------- health
    @app.get("/api/v1/health", response_model=Health)
    def health() -> Health:
        return Health(software_version=__version__, engine_version=ENGINE_VERSION, code_hash=code_fingerprint(),
                      live_trading_enabled=LIVE_TRADING_ENABLED, demo_trading_enabled=DEMO_TRADING_ENABLED)

    # ---------------------------------------------------------------- datasets
    @app.get("/api/v1/datasets")
    def list_datasets() -> list[dict]:
        return frame_records(cat().list_datasets())

    @app.get("/api/v1/datasets/{dataset_id}")
    def get_dataset(dataset_id: DatasetId) -> dict:
        meta = cat().dataset_meta(dataset_id)
        if meta is None:
            raise HTTPException(404, f"Jeu de données introuvable : {dataset_id}")
        return to_jsonable(meta.model_dump(mode="json"))

    @app.post("/api/v1/datasets/demo", status_code=201)
    def create_demo_dataset(req: DemoDatasetRequest) -> dict:
        with heavy_job():
            ds = synthetic_dataset(seed=req.seed, days=req.days)
            cat().save_dataset(ds)
        return {"dataset": ds.meta.model_dump(mode="json"), "quality": ds.meta.quality}

    @app.post("/api/v1/datasets/import", status_code=201)
    async def import_dataset(
        file: Annotated[UploadFile, File(description="CSV OHLC ou export MetaTrader 5")],
        name: Annotated[str, Form(min_length=1, max_length=120)],
        symbol: Annotated[str, Form(pattern=r"^\s*[A-Za-z0-9][A-Za-z0-9._\-]{1,19}\s*$")],
        source: Annotated[str, Form(min_length=1, max_length=200)],
        kind: Annotated[Literal["historical", "synthetic"], Form()],
        price_side: Annotated[Literal["bid", "mid"], Form()] = "bid",
        source_timezone: Annotated[str | None, Form(max_length=64)] = None,
        expected_timeframe: Annotated[Literal["M1", "M5", "M15", "M30", "H1", "H4", "D1"] | None, Form()] = None,
        notes: Annotated[str, Form(max_length=2000)] = "",
    ):
        filename = (file.filename or "").lower()
        if not filename.endswith((".csv", ".txt")):
            raise HTTPException(415, "Seuls les fichiers .csv ou .txt sont acceptés.")
        if kind == "historical" and "synth" in filename:
            raise HTTPException(422, "Fichier nommé comme des données synthétiques : déclarez-le « synthetic ».")
        limit, buf = max_upload_bytes(), io.BytesIO()
        while chunk := await file.read(1 << 20):  # second barrier (the guard already bounded the body)
            buf.write(chunk)
            if buf.tell() > limit:
                raise HTTPException(413, f"Fichier trop volumineux (> {limit // (1024 * 1024)} Mo).")
        raw = buf.getvalue()
        # bounded BEFORE pandas parses anything; CR-only, LF and CRLF files are all counted (audit N4)
        if max(raw.count(b"\n"), raw.count(b"\r")) > max_rows() + 1:
            raise HTTPException(413, f"Trop de lignes (> {max_rows()}) : découpez le fichier.")

        def process():
            with heavy_job():
                rep, ds = import_csv(raw, name=name, symbol=symbol, source_label=source, price_side=price_side,
                                     source_timezone=source_timezone or None, expected_timeframe=expected_timeframe,
                                     kind=DataKind(kind), notes=notes)
                if ds is not None and ds.meta.rows > max_rows():  # postcondition on what was really parsed (N4)
                    raise HTTPException(413, f"Trop de lignes (> {max_rows()}) : découpez le fichier.")
                if ds is not None:
                    cat().save_dataset(ds, raw)
                return rep, ds

        rep, ds = await run_in_threadpool(process)  # parsing / hashing off the event loop
        if ds is None:  # rejected as a whole: nothing stored, no partial dataset
            return err(422, "Fichier refusé par la validation : aucune donnée enregistrée.", rep.as_dict())
        stored = cat().dataset_meta(ds.meta.dataset_id)  # the PERSISTED provenance (first declaration, audit N8)
        declared = ds.meta
        return {"dataset": stored.model_dump(mode="json"), "quality": rep.as_dict(),
                "declaration": {"name": declared.name, "source": declared.source, "notes": declared.notes,
                                "kind": declared.kind.value, "raw_sha256": declared.raw_sha256,
                                "primary": declared.source == stored.source and declared.name == stored.name,
                                "note": "Déclaration ajoutée à l'historique de provenance ; la provenance principale "
                                        "reste la première déclaration enregistrée."}}

    # ---------------------------------------------------------------- strategies & settings
    @app.get("/api/v1/strategies")
    def list_strategies() -> dict:
        strats = load_catalog()
        items = []
        for spec in strats.specs.values():
            problems = spec.runnable_problems()
            if spec.implementation and spec.implementation not in IMPLEMENTATIONS:
                problems.append(f"implémentation inconnue : {spec.implementation}")
            items.append({"key": spec.key, "runnable": not problems, "problems": problems,
                          "spec": spec.model_dump(mode="json")})
        return {"strategies": items, "errors": strats.errors}

    @app.get("/api/v1/settings/defaults")
    def get_defaults() -> dict:
        return default_config(cat()).model_dump(mode="json")

    @app.get("/api/v1/settings/risk-policy")
    def get_risk_policy() -> dict:
        mode = policy_mode()
        return {"mode": mode, "enforced": mode == "supervised",
                "saved_profile": default_config(cat()).risk.model_dump(mode="json")}

    @app.get("/api/v1/reference/rejection-reasons")
    def rejection_reasons() -> dict:
        return {**REJECTION_LABELS_FR, **ENGINE_REASON_LABELS_FR}

    # ---------------------------------------------------------------- backtests
    @app.post("/api/v1/backtests", status_code=201)
    def create_backtest(req: BacktestRequest) -> dict:
        c = cat()
        strats = load_catalog()
        spec = strats.specs.get(req.strategy_key)
        if spec is None:
            raise HTTPException(404, f"Stratégie inconnue : {req.strategy_key}")
        if c.dataset_meta(req.dataset_id) is None:
            raise HTTPException(404, f"Jeu de données introuvable : {req.dataset_id}")
        config = req.config if req.config is not None else default_config(c)
        request_policy = resolve_risk_policy(c, config)  # attestation of THIS request (audit N5)
        with heavy_job():
            result = run_and_store(c, req.dataset_id, spec, config, label=req.label)
        stored = c.load_run(result.run_id)  # respond with what was PERSISTED, not an in-memory copy
        return {"run_id": result.run_id, "manifest": to_jsonable(stored.manifest), "metrics": to_jsonable(stored.metrics),
                "request_policy": {**request_policy,
                                   "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                   "note_manifest": "Le manifeste est celui de la PREMIÈRE publication de ce run ; "
                                                    "il n'est jamais réécrit. Cette attestation décrit la requête actuelle."}}

    @app.get("/api/v1/backtests")
    def list_backtests() -> list[dict]:
        return frame_records(cat().list_runs())

    @app.get("/api/v1/backtests/{run_id}")
    def get_backtest(run_id: RunId) -> dict:
        r = cat().load_run(run_id)
        return {"run_id": run_id, "manifest": to_jsonable(r.manifest), "metrics": to_jsonable(r.metrics)}

    @app.get("/api/v1/backtests/{run_id}/trades")
    def get_trades(run_id: RunId) -> list[dict]:
        return frame_records(cat().load_run(run_id).trades)

    @app.get("/api/v1/backtests/{run_id}/decisions")
    def get_decisions(run_id: RunId, outcome: Literal["ENTERED", "REJECTED"] | None = None,
                      limit: Annotated[int, Query(ge=1, le=50_000)] = 5_000) -> dict:
        d = cat().load_run(run_id).decisions
        if outcome and len(d):
            d = d[d["outcome"] == outcome]
        return {"total": int(len(d)), "items": frame_records(d.head(limit))}

    @app.get("/api/v1/backtests/{run_id}/equity")
    def get_equity(run_id: RunId, max_points: Annotated[int, Query(ge=10, le=20_000)] = 2_000) -> dict:
        run = cat().load_run(run_id)
        e = run.equity.copy()
        n = len(e)
        if n:  # computed by the engine's analytics on the FULL series, before any thinning
            e["drawdown_mtm_pct"] = drawdown_series_pct(e["mtm_equity"].to_numpy(float),
                                                        float(run.metrics["initial_equity"]))
        if n > max_points:  # thinning for display only; first, last and worst-drawdown points always kept
            step = -(-n // max_points)
            keep = set(range(0, n, step)) | {n - 1, int(e["drawdown_mtm_pct"].to_numpy().argmin())}
            e = e.iloc[sorted(keep)]
        return {"total_points": n, "points": frame_records(e)}

    @app.post("/api/v1/backtests/{run_id}/reproduce", response_model=ReproduceResult)
    def reproduce_backtest(run_id: RunId) -> ReproduceResult:
        cat().run_dir(run_id)
        with heavy_job():
            return ReproduceResult(**reproduce(cat(), run_id, load_catalog()))

    @app.get("/api/v1/backtests/{run_id}/export/{name}")
    def export(run_id: RunId, name: Literal["trades.csv", "decisions.csv", "equity.csv.gz", "metrics.json",
                                            "manifest.json"]):
        filename, media = EXPORTS[name]
        data = cat().read_verified_artifact(run_id, filename)  # bytes that passed verification
        return Response(data, media_type=media,
                        headers={"Content-Disposition": f'attachment; filename="{run_id}_{filename}"'})

    @app.get("/api/v1/backtests/{run_id}/robustness")
    def get_robustness(run_id: RunId) -> dict:
        """How much of a stored result could be luck: bootstrap intervals + Monte Carlo drawdowns (seeded)."""
        with heavy_job():  # bootstrap + permutations: bounded like any heavy computation (audit I04-8)
            run = cat().load_run(run_id)
            cfg = run.manifest["config"]
            return to_jsonable(run_robustness(run.trades, float(run.metrics["initial_equity"]),
                                              float(cfg["risk"]["max_drawdown_pct"]), run.manifest["result_hash"]))

    # ---------------------------------------------------------------- research (evidence, never orders)
    @app.post("/api/v1/research/edge-studies", status_code=201)
    def create_edge_study(req: EdgeStudyRequest) -> dict:
        c = cat()
        spec = load_catalog().specs.get(req.strategy_key)
        if spec is None:
            raise HTTPException(404, f"Stratégie inconnue : {req.strategy_key}")
        if c.dataset_meta(req.dataset_id) is None:
            raise HTTPException(404, f"Jeu de données introuvable : {req.dataset_id}")
        config = req.config if req.config is not None else default_config(c)
        resolve_risk_policy(c, config)  # supervised mode: same contract / limits checks as a backtest (I04-3)
        settings = StudySettings(horizon_bars=req.horizon_bars, folds=req.folds,
                                 initial_train_fraction=req.initial_train_fraction)
        with heavy_job():
            return to_jsonable(run_edge_study(c, req.dataset_id, spec, config, settings))

    @app.get("/api/v1/research/edge-studies")
    def get_edge_studies() -> list[dict]:
        return to_jsonable(list_studies(cat().root))

    @app.get("/api/v1/research/edge-studies/{study_id}")
    def get_edge_study(study_id: StudyId) -> dict:
        s = load_study(cat().root, study_id)
        if s is None:
            raise HTTPException(404, f"Étude introuvable : {study_id}")
        return to_jsonable(s)

    return app
