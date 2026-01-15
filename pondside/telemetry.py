"""Telemetry - OTel setup for Pondside.

Usage:
    from pondside.telemetry import init, get_tracer
    import logging

    init("my-service")
    logger = logging.getLogger(__name__)
    tracer = get_tracer()

    logger.info("This goes to Parallax")

    with tracer.start_as_current_span("doing-a-thing"):
        logger.info("This nests under the span")
"""

import logging
import os

from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk.trace import TracerProvider, SpanLimits
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

_initialized = False


def init(service_name: str) -> None:
    """Initialize OTel. Call once at startup.

    Sets up:
    - TracerProvider with OTLP exporter → Parallax (traces)
    - LoggerProvider with OTLP exporter → Parallax (logs)
    - Python logging handler so logger.info() flows to OTel

    Reads OTEL_EXPORTER_OTLP_ENDPOINT from environment.
    If not set, telemetry is disabled (no-op).
    """
    global _initialized
    if _initialized:
        return

    # No endpoint = no telemetry. Intentional.
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        _initialized = True  # Don't try again
        return

    # Resource identifies this service in traces and logs
    resource = Resource.create({SERVICE_NAME: service_name})

    # === TRACES ===
    trace_exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")

    # Remove all limits - LLM spans have massive message histories
    span_limits = SpanLimits(
        max_attributes=100000,
        max_attribute_length=100000,
        max_events=10000,
        max_links=1000,
        max_event_attributes=10000,
        max_link_attributes=1000,
    )

    tracer_provider = TracerProvider(resource=resource, span_limits=span_limits)
    tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(tracer_provider)

    # === LOGS ===
    log_exporter = OTLPLogExporter(endpoint=f"{endpoint}/v1/logs")

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)

    # Attach OTel handler to Python's root logger
    # This makes logger.info() etc flow to OTel
    handler = LoggingHandler(level=logging.DEBUG, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)

    _initialized = True


def get_tracer(name: str = "pondside") -> trace.Tracer:
    """Get a tracer for creating spans.

    Usage:
        tracer = get_tracer()
        with tracer.start_as_current_span("my-operation"):
            # stuff happens here
            pass
    """
    return trace.get_tracer(name)
