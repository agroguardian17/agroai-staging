"""Pipeline Self-Test — one-click "is the ingest pipeline healthy right now?".

Runs canned raw payloads through the *real* calibration + validation chain (the
same code the live broker uses) and shows whether each golden case lands on its
expected outcome. No database or device needed — this validates the code, so a
green run means calibration + the plausibility checks are behaving.
"""

from __future__ import annotations

import streamlit as st

st.title("🧪 Pipeline Self-Test")
st.caption(
    "Replays golden raw payloads through the real calibrate + validate chain. "
    "Green = the pipeline logic is healthy."
)

if st.button("▶️ Run self-test", type="primary"):
    try:
        from app.infra.pipeline_selftest import run_self_test
    except Exception as exc:  # app package / deps not importable in this container
        st.error(
            "Couldn't load the self-test in this container. Run it in the app "
            f"container instead:\n\n`docker compose exec app python -m app.infra.pipeline_selftest`\n\n`{exc}`"
        )
        st.stop()

    report = run_self_test()
    passed = sum(c.passed for c in report.cases)
    if report.passed:
        st.success(f"ALL PASS — {passed}/{len(report.cases)} golden cases green.")
    else:
        st.error(f"FAILURES — {passed}/{len(report.cases)} passed. The pipeline logic regressed.")

    for r in report.cases:
        icon = "✅" if r.passed else "❌"
        with st.expander(
            f"{icon} {r.name} — overall `{r.overall}` (expected `{r.expected}`)",
            expanded=not r.passed,
        ):
            st.write("**Calibrated values**")
            st.json(r.calibrated)
            if r.findings:
                st.write("**Validation findings**")
                st.json(r.findings)
            else:
                st.caption("No validation findings.")
else:
    st.info("Press **Run self-test** to replay the golden cases.")
