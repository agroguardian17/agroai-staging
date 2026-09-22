#!/usr/bin/env python3
"""Live smoke check for the WhatsApp advisory template (credential-gated).

Sends ONE real ``agroguardian_advisory_v1`` template message to a phone number,
through the exact production path (``MetaCloudWhatsappSender.send_template``) the
delivery subscriber uses -- but bypassing the DB and the subscriber, so it
isolates one question: does the approved template + token + number deliver a
WhatsApp message end-to-end?

It sends a real message, so it takes an explicit ``--to`` (no default recipient)
and needs live Meta Cloud API credentials. In WABA dev/test mode the recipient
must be on the app's test-number allowlist (Meta dashboard); once the app is
live any opted-in number works. A template message may be sent proactively
(outside the 24h window) -- that is the point of an approved template.

Usage (inside the app container, where the credentials live):

    docker compose exec app python scripts/dev/whatsapp_smoke.py --to 9198XXXXXXXX

Env (required -- the same vars the app reads):
    META_WHATSAPP_TOKEN             Meta Cloud API access token
    META_WHATSAPP_PHONE_NUMBER_ID   the sender phone-number id
Env (optional, defaulted):
    META_WHATSAPP_GRAPH_VERSION         (default v20.0)
    META_WHATSAPP_ADVISORY_TEMPLATE_NAME (default agroguardian_advisory_v1)

Options:
    --to     recipient number, international format, no '+' (e.g. 9198XXXXXXXX)
    --text   the Marathi body parameter that fills the template's {{1}}
    --template / --lang   override the template name / language (default mr)

Exit codes: 0 accepted by Meta, 1 rejected/error, 2 skipped (creds absent).
"""

from __future__ import annotations

import argparse
import asyncio
import os

_SAMPLE_MR = (
    "AgroGuardian चाचणी सूचना: आपल्या आल्याच्या प्लॉटसाठी आजची चाचणी सूचना आहे. "
    "जमिनीतील ओलावा योग्य आहे, आज पाणी देण्याची गरज नाही. उद्या सकाळी पुन्हा तपासा. "
    "ही फक्त यंत्रणा-चाचणी आहे, कृपया दुर्लक्ष करा."
)


def main() -> int:
    token = os.environ.get("META_WHATSAPP_TOKEN")
    phone_number_id = os.environ.get("META_WHATSAPP_PHONE_NUMBER_ID")
    if not token or not phone_number_id:
        print("SKIP: set META_WHATSAPP_TOKEN and META_WHATSAPP_PHONE_NUMBER_ID to run.")
        return 2

    parser = argparse.ArgumentParser(description="WhatsApp advisory-template live smoke check.")
    parser.add_argument("--to", required=True, help="recipient number, e.g. 9198XXXXXXXX (no '+')")
    parser.add_argument("--text", default=_SAMPLE_MR, help="Marathi body parameter ({{1}})")
    parser.add_argument(
        "--template",
        default=os.environ.get("META_WHATSAPP_ADVISORY_TEMPLATE_NAME", "agroguardian_advisory_v1"),
    )
    parser.add_argument("--lang", default="mr", help="template language code (default mr)")
    args = parser.parse_args()

    # Imported here so --help / the SKIP path do not require the app deps.
    from app.infra.whatsapp.meta_cloud_sender import MetaCloudSettings, MetaCloudWhatsappSender

    sender = MetaCloudWhatsappSender(
        MetaCloudSettings(
            graph_version=os.environ.get("META_WHATSAPP_GRAPH_VERSION", "v20.0"),
            phone_number_id=phone_number_id,
            access_token=token,
        )
    )

    async def run() -> int:
        print(f"Sending template '{args.template}' (lang {args.lang}) to {args.to} ...")
        try:
            result = await sender.send_template(
                phone=args.to,
                template_name=args.template,
                language_code=args.lang,
                body_params=[args.text],
            )
        except Exception as exc:  # a smoke script reports any failure verbatim
            print(f"FAIL: {type(exc).__name__}: {exc}")
            return 1
        if result.accepted:
            print(f"OK: accepted by Meta. provider_message_id={result.provider_message_id}")
            print("Check the recipient handset for the message.")
            return 0
        print(f"REJECTED: error_code={result.error_code} detail={result.error_detail}")
        return 1

    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
