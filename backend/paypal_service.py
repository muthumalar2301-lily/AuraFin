# paypal_service.py

import os
from datetime import date

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api-m.sandbox.paypal.com"
REQUEST_TIMEOUT = 20


def get_access_token() -> str:
    """Obtain an OAuth access token from PayPal Sandbox."""

    client_id = os.getenv("PAYPAL_CLIENT_ID")
    client_secret = os.getenv("PAYPAL_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError(
            "PayPal credentials are missing. "
            "Configure PAYPAL_CLIENT_ID and PAYPAL_SECRET."
        )

    try:
        response = requests.post(
            f"{BASE_URL}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={
                "Accept": "application/json",
                "Accept-Language": "en_US",
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            "Unable to authenticate with PayPal Sandbox."
        ) from exc

    token = response.json().get("access_token")

    if not token:
        raise RuntimeError(
            "PayPal authentication succeeded without returning a token."
        )

    return token


def create_and_send_invoice(
    recipient_email: str,
    item_name: str,
    unit_amount: float,
    due_date: str,
) -> str:
    """
    Create and send a PayPal invoice.

    The function signature and return value remain compatible
    with the existing FastAPI endpoint.
    """

    token = get_access_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # 1. Generate an invoice number.
    try:
        number_response = requests.post(
            f"{BASE_URL}/v2/invoicing/generate-next-invoice-number",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        number_response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            "Failed to generate a PayPal invoice number."
        ) from exc

    invoice_number = number_response.json().get("invoice_number")

    if not invoice_number:
        raise RuntimeError(
            "PayPal did not return an invoice number."
        )

    # 2. Create the invoice.
    invoice_payload = {
        "detail": {
            "invoice_number": invoice_number,
            "invoice_date": date.today().isoformat(),
            "currency_code": "USD",
            "payment_term": {
                "term_type": "DUE_ON_DATE_SPECIFIED",
                "due_date": due_date,
            },
        },
        "primary_recipients": [
            {
                "billing_info": {
                    "email_address": recipient_email,
                }
            }
        ],
        "items": [
            {
                "name": item_name,
                "quantity": "1",
                "unit_amount": {
                    "currency_code": "USD",
                    "value": f"{unit_amount:.2f}",
                },
            }
        ],
    }

    try:
        create_response = requests.post(
            f"{BASE_URL}/v2/invoicing/invoices",
            json=invoice_payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        create_response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            "Failed to create the PayPal invoice."
        ) from exc

    invoice_id = create_response.json().get("id")

    if not invoice_id:
        raise RuntimeError(
            "PayPal created no identifiable invoice."
        )

    # 3. Send the invoice to the recipient.
    try:
        send_response = requests.post(
            f"{BASE_URL}/v2/invoicing/invoices/{invoice_id}/send",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        send_response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Invoice {invoice_id} was created, "
            "but sending it through PayPal failed. "
            "Check the invoice status in PayPal before retrying."
        ) from exc

    # Preserve the existing return contract.
    return invoice_id