"""DPDP consent notice (LEGAL_COMPLIANCE_CERTIFICATE §3.1, D12-DPDP-001).

The verbatim Marathi notice shown to a farmer before registration, plus a
version tag and a content hash so a captured consent can evidence exactly which
notice text the farmer saw (DPDP §12). The text is reproduced exactly from the
certificate and applied downstream unchanged.

Note: the certificate is a compliance template pending admitted-advocate
sign-off; if legal revises the wording, bump ``CONSENT_NOTICE_VERSION`` so
existing captured consents remain attributable to the version they saw.
"""

from __future__ import annotations

import hashlib

CONSENT_NOTICE_VERSION = "dpdp-consent/v1"

# Verbatim §3.1 — Marathi (the notice the farmer is shown and consents to).
CONSENT_NOTICE_MR = (
    "शेतकऱ्याची नोंदणी करण्यापूर्वी, त्यांच्याकडून मराठीत सोप्या भाषेत स्पष्ट, "
    "माहितीपूर्ण आणि निःसंदिग्ध पूर्व-संमती (Prior Explicit Consent) घेण्यात यावी. "
    "संमती-निवेदनात खालील बाबी नमूद असणे बंधनकारक आहे: "
    "(१) संकलित होणाऱ्या वैयक्तिक डेटाचे स्वरूप, (२) डेटा-प्रक्रियेचा उद्देश, "
    "(३) जतन कालावधी (हंगाम समाप्तीनंतर ३ वर्षे), "
    "(४) डेटा-अधिपतीचे अधिकार — प्रवेश (Access), दुरुस्ती (Correction), "
    "डिलीट करण्याचा (Erasure) व तक्रार निवारण (Grievance) यंत्रणा. "
    "संमती कधीही मागे घेण्याचा अधिकार व त्याचे परिणाम स्पष्टपणे कळवावेत. "
    "संमती वयोमापित (Age-verified) असणे बंधनकारक — १८ वर्षांखालील शेतकऱ्यांसाठी "
    "पालकांची पडताळणीयोग्य संमती (Verifiable Parental Consent) आवश्यक."
)

# Verbatim §3.1 — English (record/audit only, never the primary consent record).
CONSENT_NOTICE_EN = (
    "Prior to farmer registration, obtain explicit, informed, unconditional and "
    "unambiguous consent in plain Marathi in accordance with DPDP Act 2023 §§ 5-6. "
    "The consent notice shall specify: (i) categories of personal data collected, "
    "(ii) purpose of processing, (iii) retention period (season-end + 3 years), "
    "(iv) data-principal rights including access, correction, erasure, grievance "
    "mechanism, and (v) right to withdraw consent at any time with disclosure of "
    "consequences. Age verification mandatory — verifiable parental consent "
    "required for data principals under 18 years per DPDP Act § 9."
)


def consent_notice_hash() -> str:
    """SHA-256 of the Marathi notice — proof of the exact text consented to."""
    return hashlib.sha256(CONSENT_NOTICE_MR.encode("utf-8")).hexdigest()


__all__ = [
    "CONSENT_NOTICE_EN",
    "CONSENT_NOTICE_MR",
    "CONSENT_NOTICE_VERSION",
    "consent_notice_hash",
]
