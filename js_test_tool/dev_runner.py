"""
Run test suite in dev mode.

In dev mode:

    * Test results are displayed in the browser instead
    of the console.

    * The test suite run in the user's default browser.

    * The test runner page continues to be served
    until the user terminates the tool using Ctrl-C.
"""
import webbrowser
import time
import os
from js_test_tool.suite_server import SuitePageServer
from js_test_tool.suite import SuiteDescription, SuiteRenderer


class SuiteDevRunner(object):
    """
    Run the test suite in dev mode.
    """

    def __init__(self, page_server,
                 webbrowser_module=None,
                 stop_fast=False):
        """
        Configure the runner to serve the test suite pages
        using `page_server` (a `SuitePageServer` object)

        `webbrowser_module` is a module with an `open_new(url)`
        function (usually Python's `webbrowser`, but could
        be overridden during testing).

        If `stop_fast` is True, then terminate immediately
        instead of waiting for the user to terminate
        using Ctrl-C (used for testing).
        """
        self._server = page_server
        self._stop_fast = stop_fast

        if webbrowser_module is None:
            webbrowser_module = webbrowser

        self._webbrowser = webbrowser_module

    def run(self):
        """
        Load the test suite in the user's default browser,
        and continue serving the page until the user
        terminates the program.
        """

        # Start the test suite page server
        self._server.start()

        try:

            # Argument validation should guarantee that there is
            # exactly one value in the list, but check just in case.
            url_list = self._server.suite_url_list()

            if len(url_list) < 1:
                raise ValueError('Expected at least one URL')

            # Print the URL to the console
            print('Serving JavaScript test suite at: {}'.format(url_list[0]))
            print('Use Ctrl-C to quit.')

            # Open the page in the user's default browser
            self._webbrowser.open_new(url_list[0])

            # Wait for the user to terminate
            while True:

                # Terminate early if configured
                if self._stop_fast:
                    raise KeyboardInterrupt

                time.sleep(1)

        except KeyboardInterrupt:
            pass

        finally:
            # Guarantee that the server stops
            print('\nStopping JavaScript test suite server...')
            self._server.stop()


class SuiteDevRunnerFactory(object):
    """
    Configure a `SuiteDevRunner`.
    """

    def __init__(self,
                 desc_class=SuiteDescription,
                 renderer_class=SuiteRenderer,
                 server_class=SuitePageServer,
                 runner_class=SuiteDevRunner):
        """
        Configure the factory to use each kwarg class
        when building the suite runner.  These can
        be overriden for testing purposes.
        """
        self._desc_class = desc_class
        self._renderer_class = renderer_class
        self._server_class = server_class
        self._runner_class = runner_class

    def build_runner(self, test_suite_path):
        """
        Configure a `SuiteDevRunner` to serve the test
        suite described by the file at `test_suite_path`.

        Returns the configured `SuiteDevRunner` instance.
        """

        # Load the suite description
        with open(test_suite_path) as suite_file:
            root_dir = os.path.dirname(os.path.abspath(test_suite_path))
            desc = self._desc_class(suite_file, root_dir)

        # Create the suite page renderer
        # and configure it to render pages in dev mode
        renderer = self._renderer_class(dev_mode=True)

        # Create the suite page server
        server = self._server_class([desc], renderer,
                                    jscover_path=None)

        # Create the dev test runner
        return self._runner_class(server)
