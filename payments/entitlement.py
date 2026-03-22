# payments/entitlement.py
import os


def is_export_entitled() -> bool:
    """
    Returns True if the current user has paid for the Export Pack.

    Dev override: set ATLAS_DEV_EXPORT=1 in your environment to bypass.
    Replace the body of this function with a real Stripe/DB check in production.
    """
    if os.environ.get("ATLAS_DEV_EXPORT") == "1":
        return True
    # v1: stub — replace with Stripe entitlement check
    return False
