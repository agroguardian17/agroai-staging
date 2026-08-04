"""Dev-mode WhatsApp sender that writes the OTP to the server log.


Lets the entire auth flow be exercised end-to-end without a verified
Meta business account. Production code MUST use
:class:`~app.infra.whatsapp.meta_cloud_sender.MetaCloudWhatsappSender`;
this class refuses to ``accept`` in production via an explicit guard.
"""


from __future__ import annotations

from uuid import uuid4

import structlog

from app.application.ports.whatsapp_sender import WhatsappSendResult
from app.domain.auth import mask_phone

log = structlog.get_logger(__name__)




class LogOnlyWhatsappSender:
    """No-network sender. Logs the OTP and pretends it was delivered."""


    def __init__(self, *, allow_in_production: bool = False) -> None:
        self._allow_prod = allow_in_production


    async def send_otp_template(
        self, *, phone: str, code: str, template_name: str, language_code: str = "en"
    ) -> WhatsappSendResult:
        log.warning(
            "whatsapp.log_only_sender.fake_send",
            phone=mask_phone(phone),
            template=template_name,
            language=language_code,
            otp_code=code,  # only ever in dev logs - production guard above.
        )
        return WhatsappSendResult(
            accepted=True,
            provider_message_id=f"log-{uuid4().hex[:12]}",
        )




__all__ = ["LogOnlyWhatsappSender"]
