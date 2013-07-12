"""
Load suite runner pages in a browser and parse the results.
"""

from splinter.browser import Browser as SplinterBrowser
import json


class BrowserError(Exception):
    """
    Error occurred while loading a page in the browser.
    """
    pass


class Browser(object):
    """
    Browser capable of executing JavaScript.
    """

    # Expect the results page to have a <div> with this ID
    # containing the JSON-encoded test results
    RESULTS_DIV_ID = 'js_test_tool_results'

    # Wait time for the DOM to load, in seconds
    TIMEOUT = 10

    def __init__(self, browser_name):
        """
        Initialize the browser to use `browser_name` (e.g. chrome).
        Valid browser names are those defined by the Splinter API:
        http://splinter.cobrateam.info/docs/
        """
        # Store the browser name
        self._name = browser_name

        # Create a browser session
        try:
            self._splinter_browser = SplinterBrowser(browser_name)
        except:
            raise BrowserError('Could not create a browser instance')

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

        # Check that we successfully loaded the page
        if not self._splinter_browser.status_code.is_success():
            raise BrowserError("Could not load page at '{}'".format(url))

        # Wait for the DOM to load
        self._splinter_browser.is_element_present_by_id(self.RESULTS_DIV_ID,
                                                        wait_time=self.TIMEOUT)

        # Retrieve the <div> containing the JSON-encoded results
        elements = self._splinter_browser.find_by_id(self.RESULTS_DIV_ID)

        # Raise an error if we can't find the div we expect
        if elements.is_empty():
            msg = "Could not find test results on page at '{}'".format(url)
            raise BrowserError(msg)

        else:
            # Try to JSON-decode the contents of the <div>
            contents = elements.first.html

            try:
                return self._parse_runner_output(contents)

            # Raise an error if invalid JSON
            except ValueError:
                msg = "Could not decode JSON test results: '{}'".format(contents)
                raise BrowserError(msg)

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
        self._splinter_browser.quit()

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

            # Verify that we got all the keys we expected
            for key, value in modified_dict.items():
                if value is None:
                    msg = "Test result is missing required key '{}'".format(key)
                    raise BrowserError(msg)

            # Add the modified dict to the list
            final_list.append(modified_dict)

        return final_list
