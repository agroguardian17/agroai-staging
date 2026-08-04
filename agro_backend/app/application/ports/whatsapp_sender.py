"""Port: WhatsApp message sender.


Round 8 ships two adapters behind this port:


* :class:`~app.infra.whatsapp.log_only_sender.LogOnlyWhatsappSender` -
  default in dev/test; writes the OTP code to the server log and pretends
  to have delivered. Lets the auth flow be exercised end-to-end without
  a verified Meta business account.
* :class:`~app.infra.whatsapp.meta_cloud_sender.MetaCloudWhatsappSender` -
  real Meta Cloud API. Wired up in Round 8.5.


The send_otp use case calls only :meth:`send_otp_template`; future use
cases (advisories) will add their own methods to this port.
"""


from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class WhatsappSendResult:
    """Outcome of one WhatsApp send. Used by metrics and audit-log breadcrumbs."""


    accepted: bool
    provider_message_id: str | None
    error_code: str | None = None  # e.g. 'rate_limited', 'invalid_template'
    error_detail: str | None = None




@runtime_checkable
class WhatsappSender(Protocol):
    """One-way outbound WhatsApp delivery.


    The Meta Cloud API uses templates, not free-form messages, for
    initial conversations. The OTP template renders to something like
    "Your AgroGuardian code is {{1}}. It expires in 5 minutes."
    """


    async def send_otp_template(
        self, *, phone: str, code: str, template_name: str, language_code: str = "en"
    ) -> WhatsappSendResult:
        """Send the OTP via the named template.


        Implementations MUST NOT raise on provider errors; instead set
        ``accepted=False`` and populate ``error_code``. The use case
        decides whether to surface the failure to the client.
        """
        ...




__all__ = ["WhatsappSendResult", "WhatsappSender"]
