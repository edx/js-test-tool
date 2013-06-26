"""
Serve test runner pages and included JavaScript files on a local port.
"""

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import threading
import re
import pkg_resources
import os.path
from abc import ABCMeta, abstractmethod


class SuitePageServer(HTTPServer):
    """
    Serve test suite pages and included JavaScript files.
    """

    def __init__(self, suite_desc_list, suite_renderer):
        """
        Initialize the server to serve test runner pages
        and dependencies described by `suite_desc_list`
        (list of `SuiteDescription` instances).

        Use `suite_renderer` (a `SuiteRenderer` instance) to
        render the test suite pages.
        """

        # Store dependencies
        self.desc_list = suite_desc_list
        self.renderer = suite_renderer

        # Using port 0 assigns us an unused port
        address = ('127.0.0.1', 0)
        HTTPServer.__init__(self, address, SuitePageRequestHandler)

    def start(self):
        """
        Start serving pages on an open local port.
        """
        server_thread = threading.Thread(target=self.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def stop(self):
        """
        Stop the server and free the port.
        """
        self.shutdown()
        self.socket.close()

    def suite_url_list(self):
        """
        Return a list of URLs (unicode strings), where each URL
        is a test suite page containing the JS code to run
        the JavaScript tests.
        """
        return [self.root_url() + u'suite/{}'.format(suite_num)
                for suite_num in range(len(self.desc_list))]

    def root_url(self):
        """
        Return the root URL (including host and port) for the server
        as a unicode string.
        """
        host, port = self.server_address
        return u"http://{}:{}/".format(host, port)


class BasePageHandler(object):
    """
    Abstract base class for page handler.  Checks whether
    it can handle a given URL path.  If it can, it then generates
    the page contents.
    """

    __metaclass__ = ABCMeta
    
    # Subclasses override this to provide a regex that matches
    # URL paths.  Should be a `re` module compiled regex.
    PATH_REGEX = None

    def page_contents(self, path):
        """
        Check whether the handler can load the page at `path` (URL path).
        If so, return the contents of the page as a unicode string.
        Otherwise, return None.
        """

        # Check whether this handler matches the URL path
        result = self.PATH_REGEX.match(path)


        # If this is not a match, return None
        if result is None:
            return None

        # If we do match, attempt to load the page.
        else:
            return self.load_page(*result.groups())

    @abstractmethod
    def load_page(self, *args):
        """
        Subclasses override this to load the page.
        `args` is a list of arguments parsed using the regular expression.

        If the page cannot be loaded (e.g. accessing a file that
        does not exist), then return None.
        """
        pass


class SuitePageHandler(BasePageHandler):
    """
    Handle requests for paths of the form `/suite/SUITE_NUM`, where
    `SUITE_NUM` is the index of the test suite description.
    Serves the suite runner page.
    """

    PATH_REGEX = re.compile('^/suite/([0-9]+)/?$')

    def __init__(self, renderer, desc_list):
        """
        Initialize the `SuitePageHandler` to use `renderer`
        (a `SuiteRenderer` instance) and `desc_list` (a list
        of `SuiteDescription` instances).
        """
        super(SuitePageHandler, self).__init__()
        self._renderer = renderer
        self._desc_list = desc_list

    def load_page(self, *args):
        """
        Render the suite runner page.
        """

        # The only arg should be the suite number
        try:
            suite_num = int(args[0])

        except (ValueError, IndexError):
            return None

        # Try to find the suite description
        try:
            suite_desc = self._desc_list[suite_num]

        # If the index is out of range, we can't serve this suite page
        except IndexError:
            return None

        # Otherwise, render the page
        else:
            return self._renderer.render_to_string(suite_num, suite_desc)


class RunnerPageHandler(BasePageHandler):

    PATH_REGEX = re.compile('^/runner/(.+)$')

    def load_page(self, *args):
        """
        Load the runner file from this package's resources.
        """

        # Only arg should be the relative path
        rel_path = os.path.join('runner', args[0])

        # Attempt to load the package resource
        try:
            content = pkg_resources.resource_string('js_test_tool', rel_path)

        # If we could not load it, return None
        except BaseException:
            return None

        # If we successfully loaded it, return a unicode str
        else:
            return content.decode()


class DependencyPageHandler(BasePageHandler):
    """
    Load dependencies required by the test suite description.
    """

    PATH_REGEX = re.compile('^/suite/([0-9]+)/include/(.+)$')

    def __init__(self, desc_list):
        """
        Initialize the dependency page handler to serve dependencies
        specified by `desc_list` (a list of `SuiteDescription` instances).
        """
        super(DependencyPageHandler, self).__init__()
        self._desc_list = desc_list

    def load_page(self, *args):
        """
        Load the test suite dependency file, using a path relative
        to the description file.
        """

        # Interpret the arguments (from the regex)
        suite_num, rel_path = args

        # Try to parse the suite number
        try:
            suite_num = int(suite_num)

        except ValueError:
            return None

        # Retrieve the full path to the dependency, if it exists
        # and is specified in the test suite description
        full_path = self._dependency_path(suite_num, rel_path)

        if full_path is not None:

            # Load the file
            try:
                with open(full_path) as file_handle:
                    contents = file_handle.read()

            # If we cannot load the file (probably because it doesn't exist)
            # then return None
            except IOError:
                return None

            # Successfully loaded the file; return the contents as a unicode str
            else:
                return contents.decode()

        # If this is not one of our listed dependencies, return None
        else:
            return None

    def _dependency_path(self, suite_num, path):
        """
        Return the full filesystem path to the dependency, if it 
        is specified in the test suite description with index `suite_num`.  
        Otherwise, return None.
        """

        # Try to find the suite description with `suite_num`
        try:
            suite_desc = self._desc_list[suite_num]

        except IndexError:
            return None


        # Get all dependency paths
        all_paths = (suite_desc.lib_paths() +
                     suite_desc.src_paths() +
                     suite_desc.spec_paths())

        # If the path is in our listed dependencies, we can serve it
        if path in all_paths:

            # Resolve the full filesystem path
            return os.path.join(suite_desc.root_dir(), path)

        else:

            # If we did not find the path, we cannot serve it
            return None


class SuitePageRequestHandler(BaseHTTPRequestHandler):
    """
    Handle HTTP requests to the `SuitePageServer`.
    """

    protocol = "HTTP/1.0"

    def __init__(self, request, client_address, server):

        # Initialize the page handlers
        self._handlers = [SuitePageHandler(server.renderer, server.desc_list),
                          RunnerPageHandler(),
                          DependencyPageHandler(server.desc_list)]

        # Call the superclass implementation
        # This will immediately call do_GET() if the request is a GET
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_GET(self):
        """
        Serve suite runner pages and JavaScript dependencies.
        """

        for handler in self._handlers:

            # Try to retrieve the page
            content = handler.page_contents(self.path)

            # If we got a page, send the contents
            if content is not None:
                self._send_response(200, content)
                return

        # If we could not retrieve the contents (e.g. because
        # the file does not exist), send a file not found response
        self._send_response(404, None)

    def _send_response(self, status_code, content):
        """
        Send a response to an HTTP request as UTF-8 encoded HTML.
        `content` can be empty, None, or a UTF-8 string.
        """

        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()

        if content:
            self.wfile.write(content)
