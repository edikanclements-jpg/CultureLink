"""Compatibility guard: seller notifications are on-screen simulations only.

These former entry points deliberately do nothing, even if an older computer
still has outgoing-email settings. No network client or background sender is
imported or started.
"""


def mail_config():
    return None


def mail_enabled():
    return False


def start_delivery():
    return None


def deliver_one(*args, **kwargs):
    return False


def retry_failed(*args, **kwargs):
    return None
