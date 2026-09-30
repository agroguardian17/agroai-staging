#!/usr/bin/env python3
"""Wave 8 — KB 7 Final Decisions (items 1 + 4).

D04-MC-005 basal ZnSO4 (marathwada_central pre-planting default) and D06-BW-004
bacterial-wilt history-capture prompt. Exprs byte-match the KB JSON (drift gate).
"""

T, F, U = 'TRUE', 'FALSE', 'UNKNOWN'

TRIGGERS_W8 = {

'D04-MC-005': {
  'expr': "plot_status == 'pre_planting' AND agro_climatic_zone == 'marathwada_central' AND basal_znso4_applied_kg_acre IS NULL",
  'tests': [({'plot_status': 'pre_planting', 'agro_climatic_zone': 'marathwada_central'}, T, 'Kannad pre-plant — Zn default'),
            ({'plot_status': 'pre_planting', 'agro_climatic_zone': 'marathwada_central', 'basal_znso4_applied_kg_acre': 10}, F, 'Zn applied — silent'),
            ({'plot_status': 'growing', 'agro_climatic_zone': 'marathwada_central'}, F, 'already planted — too late'),
            ({'plot_status': 'pre_planting', 'agro_climatic_zone': 'marathwada_western'}, F, 'other zone — not applicable')]},

'D06-BW-004': {
  'expr': "plot_status == 'pre_planting' AND field_history_wilt IS NULL",
  'tests': [({'plot_status': 'pre_planting'}, T, 'history unknown — prompt'),
            ({'plot_status': 'pre_planting', 'field_history_wilt': True}, F, 'wilt recorded — BW-001 handles'),
            ({'plot_status': 'pre_planting', 'field_history_wilt': False}, F, 'no wilt — resolved')]},

}
