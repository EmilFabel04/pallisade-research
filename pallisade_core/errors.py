class HardError(Exception):
    """Errors that must not be retried by the worker.

    Raised for non-transient failures: invalid input, exhausted parsers,
    timeouts, or any condition where another attempt will produce the
    same outcome and waste resources.
    """
