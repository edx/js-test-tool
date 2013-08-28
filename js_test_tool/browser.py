"""
Load suite runner pages in a browser and parse the results.
"""

from splinter.exceptions import DriverNotFoundError
from splinter.browser import Browser as SplinterBrowser
import json
from urllib import unquote
from js_test_tool.util import retry
import httplib

import logging
LOGGER = logging.getLogger(__name__)


class BrowserError(Exception):
    """
    Error occurred while loading a page in the browser.
    """
    pass


class JavaScriptError(Exception):
    """
    JavaScript error occurred in the test runner page.
    """
    pass


class Browser(object):
    """
    Browser capable of executing JavaScript.
    """

    # Expect the results page to have a <div> with this ID
    # containing the JSON-encoded test results
    RESULTS_DIV_ID = 'js_test_tool_results'

    # Expect that the results <div> will have this
    # class when all the results are posted.
    DONE_DIV_CLASS = "done"

    # Expect the results page to have a <div>
    # with this ID to report JavaScript exceptions
    ERROR_DIV_ID = 'js_test_tool_error'

    # Wait time for the DOM to load, in seconds
    # It could take a long time for all the tests to complete,
    # so we set this number relatively high.
    DEFAULT_TIMEOUT = 300 

    # Maximum number of times to retry if the browser crashed
    MAX_RESTARTS = 3

    # Max time to wait between restarts in seconds
    RESTART_WAIT_SEC = 1

    def __init__(self, browser_name, timeout_sec=None):
        """
        Initialize the browser to use `browser_name` (e.g. chrome).
        Valid browser names are those defined by the Splinter API:
        http://splinter.cobrateam.info/docs/

        `timeout_sec` is the amount of time to wait for the DOM
        to load.  It could take a long time, so default to a high
        value.
        """
        if timeout_sec is None:
            timeout_sec = self.DEFAULT_TIMEOUT

        self._name = browser_name
        self._timeout_sec = timeout_sec
        self._splinter_browser = None

        # Start the browser (raises an exception if the browser name is invalid)
        self._start_browser()

    def get_page_results(self, url):
        """
        Load the test suite page at `url`, parsing and returning the
        results on the page.

        Returns a list of dictionaries of the form:

            {'test_group': TEST_GROUP_NAME,
             'test_name': TEST_NAME,
             'status': pass | fail | error | skip,
             'detail': DETAILS}
        """
        return retry(
            lambda: self._get_page_results(url),
            self.MAX_RESTARTS,
            self.RESTART_WAIT_SEC,
            recover_func=self._start_browser,
            fail_fast_errors=[JavaScriptError],
            name="Get test results from browser {0}".format(self._name)
        )

    def name(self):
        """
        Return the name of the browser (e.g. 'chrome')
        """
        return self._name

    def quit(self):
        """
        Quit the browser.  This should be called to clean up
        the browser's resources.
        """
        try:
            self._safe_browser_call(
                self._splinter_browser.quit,
                name="quit"
            )

        # We assume that if we can't contact the browser,
        # it isn't running (usually because it's crashed).
        except BrowserError:
            LOGGER.debug("Could not quit browser.")

    def _start_browser(self):
        """
        Start the browser.  Raises a `BrowserError` if the browser
        could not be started, usually because it isn't installed correctly
        or is not supported.
        """
        # If there is already a browser, try to quit it
        # The quit method catches exceptions that can occur
        # if the browser crashed, so this is safe.
        if self._splinter_browser is not None:
            self.quit()

        try:
            self._splinter_browser = SplinterBrowser(self._name)

        except DriverNotFoundError:
            if self._name == 'chrome':
                msg = ' '.join([
                    'Could not create a browser instance.',
                    'Make sure you have both ChromeDriver and Chrome installed.',
                    'See http://splinter.cobrateam.info/docs/drivers/chrome.html'
                ])
            else:
                msg = 'Could not create a {} browser instance.  Is this browser installed?'.format(self._name)
            raise BrowserError(msg)

    def _safe_browser_call(self, call_func, name=""):
        """
        Execute `call_func` (function with no args)
        but catch disconnect exceptions and reraise them as
        `BrowserError`s.

        `name` is a name used to identify the operation
        when reporting errors.

        If successful, return the result of the method call.
        """
        try:
            return call_func()

        except (httplib.BadStatusLine, IOError):
            msg = "Could not connect to browser: {0}".format(name)
            raise BrowserError(msg)

    def _get_page_results(self, url):
        """
        Version of `get_page_results` with no retry logic.
        Raises a `BrowserError` is any browser operation fails.
        """
        # Load the URL in the browser
        try:
            self._splinter_browser.visit(url)

        except:
            # Phantom JS will refuse to load the page if any of the
            # included files are invalid JavaScript.  It gives a really
            # cryptic error message (TimeoutException)
            # We give a more helpful one.
            if self.name() == 'phantomjs':
                msg = ("PhantomJS could not load the suite page and " +
                       "dependencies.  This can occur when dependency " +
                       "pages are invalid JavaScript.")
                raise BrowserError(msg)

            else:
                raise BrowserError("Could not load page at '{}'".format(url))

        # Wait for the DOM to load and for all tests to complete
        css_sel = "#{}.{}".format(self.RESULTS_DIV_ID, self.DONE_DIV_CLASS)

        is_done = self._safe_browser_call(
            lambda: self._splinter_browser.is_element_present_by_css(
                css_sel, wait_time=self._timeout_sec
            ),
            name="check if tests finished"
        )

        if not is_done:
            self._raise_js_errors()
            raise BrowserError("Timed out waiting for test results.")

        else:
            # Raise an exception if JavaScript errors reported
            # (the test runner writes these to the DOM)
            self._raise_js_errors()
            return self._get_results_from_dom()

    def _raise_js_errors(self):
        """
        Retrieve any JavaScript errors written by the test
        runner to the DOM in the currently loaded browser
        page.

        If any errors are found, raise them as a
        `JavaScriptException`.
        """
        # Retrieve the <div> containing the reported JS errors
        elements = self._safe_browser_call(
            lambda: self._splinter_browser.find_by_id(self.ERROR_DIV_ID),
            name="check for JavaScript errors"
        )

        # Raise an error if the test runner reported any
        if not elements.is_empty():
            contents = elements.first.html
            if contents:
                raise JavaScriptError(contents)

        # If no errors found, then do nothing

    def _get_results_from_dom(self):
        """
        Retrieve the results from the DOM of the currently
        loaded browser page.
        """
        # Retrieve the <div> containing the JSON-encoded results
        elements = self._safe_browser_call(
            lambda: self._splinter_browser.find_by_id(self.RESULTS_DIV_ID),
            name="Get test results"
        )

        # Raise an error if we can't find the div we expect
        if elements.is_empty():
            msg = "Could not find test results on page"
            raise BrowserError(msg)

        else:
            # Try to JSON-decode the contents of the <div>
            contents = elements.first.html

            if contents == '':
                msg = "No test results reported"
                raise BrowserError(msg)

            try:
                return self._parse_runner_output(contents)

            # Raise an error if invalid JSON
            except ValueError:
                msg = "Could not decode JSON test results"
                raise BrowserError(msg)

    def _parse_runner_output(self, output):
        """
        Parse the output of the test runner in the rendered page.

        Expect `output` to be a JSON-encoded string representing
        a list of dictionaries with keys
        'testGroup', 'testName', 'testStatus', and 'testDetail'

        Returns a list of dictonaries with keys `test_group`, `test_name`,
        `status` and `detail`.

        If the test runner output does not have the expected keys,
        raises a `BrowserError`.
        """

        # We use strict=False to allow for control characters
        # such as newlines.
        results_list = json.loads(output, strict=False)

        final_list = []
        for result_dict in results_list:

            # Munge the keys to make them more Pythonic
            modified_dict = {'test_group': result_dict.get('testGroup'),
                             'test_name': result_dict.get('testName'),
                             'status': result_dict.get('testStatus'),
                             'detail': result_dict.get('testDetail')}

            # Verify and unescape the values
            for key, value in modified_dict.items():

                # Verify that we got all the keys we expected
                if value is None:
                    msg = "Test result is missing required key '{}'".format(key)
                    raise BrowserError(msg)

                else:
                    unescaped = unquote(value)
                    modified_dict[key] = unescaped

            # Add the modified dict to the list
            final_list.append(modified_dict)

        return final_list
