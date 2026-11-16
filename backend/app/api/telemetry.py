from fastapi import APIRouter, HTTPException, Request, Response
from backend.app.services.telemetry_relay import telemetry_relay
from fastapi.responses import JSONResponse


router = APIRouter(prefix="/otel", tags=["otel"])


@router.post("/traces")
async def ingest_traces(request: Request):
    """OTLP HTTP endpoint for trace ingestion.

    Receives OpenTelemetry trace data and attributes it to the
    originating actor. This stub implementation validates the
    presence of an ``actor_uid`` field in the payload and returns
    a simple acknowledgement. Real implementations would parse the
    OTLP binary/JSON, apply identity attribution, enforce cardinality
    limits, and forward to the metric store.
    """
    raw = await request.body()
    # Very lightweight parsing: try to extract JSON for attribute demo
    # In practice OTLP over HTTP is protobuf; this stub assumes JSON
    # for testability.
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    # Apply identity attribution
    attributed = telemetry_relay.attribute_actor(payload)

    # Optionally enforce cardinality / delta temporality if needed
    # telemetry_relay.enforce_cardinality(attributed)
    # telemetry_relay.enforce_delta_temporality(attributed)

    # Respond with the attributed payload (for debugging)
    return JSONResponse(content=attributed, status_code=200)


@router.post("/metrics")
async def ingest_metrics(request: Request):
    """OTLP HTTP endpoint for metric ingestion.

    Similar to traces, this stub accepts metric data and attributes
    it before acknowledging receipt.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    attributed = telemetry_relay.attribute_actor(payload)
    return JSONResponse(content=attributed, status_code=200)


@router.get("/health")
async def otel_health():
    """Simple health check for the telemetry relay."""
    return {"status": "ok", "service": "telemetry_relay"}
