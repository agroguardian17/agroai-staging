-- ============================================================================
-- AGRO-GUARDIAN AI  |  Ginger Knowledge Base  |  ROW UPDATES v1.0
-- Generated: 2026-09-18
--
-- Scope    : Row-level content updates for D01-D13 rows whose content
--            changed as a side effect of adding new rules.
-- Coverage : one row — D07 domain total_rules count (35 → 38 after
--            VPD retrofit added 3 rules).
--
-- Safety   : Optional. The engine reads rule counts from kb_rules directly,
--            not from kb_domains.total_rules. This UPDATE is cosmetic only —
--            aligns the kb_domains report with reality. Runtime behavior is
--            unaffected whether this runs or not.
--
-- Apply after kb_ginger_d14_v1.0.sql via:
--   psql -d agroguardian -f kb_ginger_d14_updates_v1.0.sql
-- ============================================================================

BEGIN;

-- D07 total_rules — 35 → 38 (VPD retrofit added D07-VP-001..003)
UPDATE kb_domains
SET total_rules = 38
WHERE domain_id = 7 AND total_rules = 35;

-- Sanity assertion: exactly one row updated
DO $$
DECLARE
    n INT;
BEGIN
    SELECT total_rules INTO n FROM kb_domains WHERE domain_id = 7;
    IF n != 38 THEN
        RAISE EXCEPTION 'D07 total_rules is %, expected 38', n;
    END IF;
END $$;

COMMIT;

-- Post-apply verification:
--   SELECT domain_id, name_en, total_rules FROM kb_domains ORDER BY domain_id;
--   -- expect D07 = 38, D14 = 47
