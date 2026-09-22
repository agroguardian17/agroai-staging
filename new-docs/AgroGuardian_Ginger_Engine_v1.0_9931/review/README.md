# Ginger KB — agronomist review workflow

Only **44 of 483** rules carry `status: AGRONOMIST_REVIEWED`. This folder turns
the remaining **439** into a worksheet the agronomist panel can work through,
and a script that folds their sign-offs back into the KB JSON.

## The loop

1. **Generate the packet** (from the authoring package root):
   ```
   python build/kb_review_packet.py --dir knowledge_base --out-dir review
   ```
   Produces:
   - `review_tracker.csv` — one row per un-reviewed rule + four blank sign-off
     columns. This is the working file; open it in a spreadsheet.
   - `review_packet.md` — the same rules with full English + Marathi text, for
     reading the content.

2. **Review.** For each rule the panel signs off, fill the four columns in
   `review_tracker.csv`:
   - `review_outcome` — `accepted`, `revise`, or `rejected`
   - `reviewer` — who reviewed (e.g. `panel_kannad`, `dr_patil`)
   - `review_date` — `YYYY-MM-DD`
   - `review_comment_mr` — a Marathi note (optional)

   Leave the four columns blank for rules not yet reviewed; only filled rows are
   applied.

3. **Apply the sign-offs** back into the JSON (dry run first):
   ```
   python build/kb_apply_reviews.py --dir knowledge_base --csv review/review_tracker.csv
   python build/kb_apply_reviews.py --dir knowledge_base --csv review/review_tracker.csv --apply
   ```
   - `accepted` → the rule's `status` becomes `AGRONOMIST_REVIEWED` and a
     `review` block `{tier, reviewer, date, outcome, comment_mr}` is written
     (mirrors the existing convention, e.g. `D05-CH-001`).
   - `revise` / `rejected` → the `review` block is recorded for the trail;
     `status` is left unchanged so the rule stays out of the reviewed set (act on
     the comment, then re-review).

4. **Regenerate** (optional but tidy): `python build/json_to_sql.py --dir
   knowledge_base --out "$(pwd)/generated/agroguardian_ginger_kb.sql"`, copy to
   `agro_backend/ginger/generated/`, and open a PR.

## Why this is low-risk

`status` and `review` are **authoring metadata only** — `json_to_sql.py` does
not emit them to SQL, and the drift / golden-test gates do not read them. So a
sign-off is a pure JSON change with **no SQL, migration, or gate impact**. Step
4 is only for keeping the generated artifact in sync; the review itself changes
nothing the engine runs.

## Priority tiers (how the packet is ordered)

| Tier | Meaning | Count |
|---|---|---:|
| **P1** | Executable (has a trigger) **and** severity blocking/red — fires now, high severity, on un-validated logic. Review first. | 35 |
| **P2** | Executable, severity yellow/info — fires now, lower severity. | 167 |
| **P3** | Non-executable — advisory / policy / computational, surfaced by context, not fired. | 237 |

The P1 set is the sharpest risk: those rules already fire in production on logic
no agronomist has signed off. D14 (0/47 reviewed), D07 (1/39) and D08 (2/38) are
the least-reviewed executable domains.

> The counts in this README and in each Domain file's `summary` block are
> descriptive snapshots; regenerate the packet for the live numbers.
