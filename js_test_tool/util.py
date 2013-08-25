"""
Utility functions.
"""
import time
import logging

LOGGER = logging.getLogger(__name__)


def retry(try_func, max_attempts, wait_sec,
          recover_func=None,
          num_attempts_before_recover=1,
          fail_fast_errors=None,
          name=''):
    """
    Call `try_func` (lambda with no args) until it executes
    with no exception.  If the function does not succeed after
    `max_attempts` tries, re-raises the last exception.

    `wait_sec` is the number of seconds to wait between attempts.

    `recover_func` is an optional function called
    before retrying.  It should accept no arguments,
    and its return value is ignored.

    `num_attempts_before_recover` allows you to delay the recover
    attempt until the `try_func` fails a few times.

    `fail_fast_exceptions` is an optional list of exception types
    for which to fail immediately.

    `name` is a unique name to use in log messages.

    Returns the output of the successful call to `try_func`.
    """

    # Keep track of how many attempts we've made
    num_attempts = 0

    # Retry until we're successful or run out of attempts
    while True:

        try:
            return try_func()

        except BaseException as ex:

            LOGGER.debug("{0}: Retrying after catching exception: {1}".format(name, ex))

            # Check if this is a fail fast exception
            # If it is, re-raise the exception immediately
            if fail_fast_errors is not None:
                for exception_class in fail_fast_errors:
                    if isinstance(ex, exception_class):
                        raise ex

            # Check if we are out of attempts
            num_attempts += 1
            if num_attempts >= max_attempts:
                LOGGER.debug("{0}: Exceeded maximum number of attempts.".format(name))
                raise ex

            # Otherwise, wait a bit and retry
            time.sleep(wait_sec)

            # Perform the recover function if one is provided
            if (recover_func is not None and num_attempts >= num_attempts_before_recover):
                LOGGER.debug("{0}: Attempting recovery function.".format(name))
                recover_func()
