"""Mandatory farmer-facing advisory disclaimer (LEGAL_COMPLIANCE_CERTIFICATE §7.2).

Per the advisory-liability framework, IT Act 2000 §79 intermediary safe-harbour
does NOT apply to VIRAAI (it generates active advisory content), so every
advisory delivered on every channel (WhatsApp, farmer app, print) must carry the
disclaimer below, verbatim. The text is reproduced exactly from the certificate;
it is applied downstream unchanged (no rewording).

Note: the certificate is, per its own Appendix A, a fully-researched compliance
template pending admitted-advocate sign-off. Should legal revise the wording,
this constant is the single point of change.
"""

from __future__ import annotations

# Verbatim §7.2 — Marathi (the farmer-facing record).
DISCLAIMER_MR = (
    "हा सल्ला उपलब्ध डेटा आणि विज्ञान-आधारित नियमांवर आधारित आहे. "
    "शेतकऱ्याने स्थानिक परिस्थिती, स्वतःच्या अनुभवाने आणि आवश्यक असल्यास "
    "मान्यताप्राप्त कृषी सल्लागाराच्या मार्गदर्शनाने अंतिम निर्णय घ्यावा. "
    "VIRAAI हा सल्ला विशिष्ट उत्पन्नाची किंवा परिणामाची हमी देत नाही. "
    "रासायनिक निविष्ठांचा वापर करण्यापूर्वी CIB&RC-प्रमाणित लेबल-सूचना "
    "काळजीपूर्वक वाचाव्यात व PPE वापरावेत."
)

# Verbatim §7.2 — English (for the KB author / audit, never the primary record).
DISCLAIMER_EN = (
    "This advisory is based on available data and science-based rules. "
    "The farmer shall make the final decision considering local conditions, "
    "personal experience, and if needed, with the guidance of a qualified "
    "agronomist. VIRAAI does not guarantee any specific yield or outcome. "
    "Before use of chemical inputs, farmer shall carefully read CIB&RC-certified "
    "product labels and use appropriate PPE."
)

_SEP = "\n\n—\n"


def append_disclaimer(message_mr: str) -> str:
    """Append the Marathi disclaimer to an advisory, exactly once.

    Idempotent: a message that already carries the disclaimer is returned
    unchanged, so re-composition or re-delivery never double-appends it.
    """
    if DISCLAIMER_MR in message_mr:
        return message_mr
    body = message_mr.rstrip()
    return f"{body}{_SEP}{DISCLAIMER_MR}" if body else DISCLAIMER_MR


__all__ = ["DISCLAIMER_EN", "DISCLAIMER_MR", "append_disclaimer"]
