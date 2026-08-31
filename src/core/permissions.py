"""
Permission failures

Raised by the core when a caller may not do something. Transports decide
how to say it — HTTP answers 403.
"""


class NotYours(PermissionError):
    """The caller does not own what they are trying to act through."""
