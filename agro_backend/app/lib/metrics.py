"""Prometheus metrics registry. Single source of truth for counters/histograms.


Phase 0 ships only the bare-minimum metric set; subsequent phases extend it
without touching the registry plumbing. Metrics are namespaced ``agro_*`` so
they're easy to find in Grafana.
"""


from __future__ import annotations


from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram


# Use a dedicated registry rather than the global one so we can reset it in
# unit tests without touching prometheus-client internals.
REGISTRY = CollectorRegistry(auto_describe=True)




# ----- HTTP --------------------------------------------------------------
http_requests_total = Counter(
    "agro_http_requests_total",
    "HTTP requests received, labeled by method, route template and status.",
    ["method", "route", "status"],
    registry=REGISTRY,
)


http_request_duration_seconds = Histogram(
    "agro_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)




# ----- Ingest (Phase 2 will fill these in) -------------------------------
ingest_received_total = Counter(
    "agro_ingest_received_total",
    "MQTT messages received by topic.",
    ["topic"],
    registry=REGISTRY,
)


ingest_dropped_total = Counter(
    "agro_ingest_dropped_total",
    "MQTT messages dropped by reason (parse_error|duplicate|unknown_tenant|validation).",
    ["reason"],
    registry=REGISTRY,
)




# ----- LLM (Phase 5 will fill these in) ----------------------------------
llm_calls_total = Counter(
    "agro_llm_calls_total",
    "LLM calls by model name and outcome.",
    ["model", "outcome"],
    registry=REGISTRY,
)


llm_tokens_total = Counter(
    "agro_llm_tokens_total",
    "LLM tokens consumed by model and direction (in|out).",
    ["model", "direction"],
    registry=REGISTRY,
)


llm_cost_inr_total = Counter(
    "agro_llm_cost_inr_total",
    "Cumulative LLM cost in INR by model.",
    ["model"],
    registry=REGISTRY,
)




# ----- Auth / OTP (Phase 3 will fill these in) ---------------------------
auth_otp_total = Counter(
    "agro_auth_otp_total",
    "OTP lifecycle events (requested|verified_success|verified_fail|locked).",
    ["event", "transport"],
    registry=REGISTRY,
)




# ----- Notifications (Phase 7 will fill these in) ------------------------
dispatch_total = Counter(
    "agro_dispatch_total",
    "Notification dispatches by channel and outcome.",
    ["channel", "outcome"],
    registry=REGISTRY,
)




# ----- Background queue depth -------------------------------------------
ingest_queue_depth = Gauge(
    "agro_ingest_queue_depth",
    "Current depth of the in-process MQTT ingest queue.",
    registry=REGISTRY,
)




# ----- Rule engine (Phase 4) ---------------------------------------------
rule_evaluations_total = Counter(
    "agro_rule_evaluations_total",
    "Reading -> rule evaluations performed (one per process_reading call).",
    registry=REGISTRY,
)


rule_hits_total = Counter(
    "agro_rule_hits_total",
    "Rule predicate matches across an evaluation pass (pre-cooldown).",
    registry=REGISTRY,
)


alerts_created_total = Counter(
    "agro_alerts_created_total",
    "AlertCandidates persisted (post-cooldown).",
    registry=REGISTRY,
)


alerts_cooldown_suppressed_total = Counter(
    "agro_alerts_cooldown_suppressed_total",
    "Rule hits dropped because the same alert_type fired recently.",
    registry=REGISTRY,
)




__all__ = [
    "REGISTRY",
    "alerts_cooldown_suppressed_total",
    "alerts_created_total",
    "auth_otp_total",
    "dispatch_total",
    "http_request_duration_seconds",
    "http_requests_total",
    "ingest_dropped_total",
    "ingest_queue_depth",
    "ingest_received_total",
    "llm_calls_total",
    "llm_cost_inr_total",
    "llm_tokens_total",
    "rule_evaluations_total",
    "rule_hits_total",
]
