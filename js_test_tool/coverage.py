"""
Report coverage information for JavaScript.
"""

import subprocess
import requests
import logging
import random
import os.path
import threading
from js_test_tool.util import retry

LOGGER = logging.getLogger(__name__)


class SrcInstrumenterError(Exception):
    """
    An error occurred while trying to create an instrumented
    version of a JS source file.
    """
    pass


class SrcInstrumenter(object):
    """
    Instrument JavaScript sources to collect coverage information.
    """

    # Number of times to try starting the service to avoid
    # port conflicts.
    MAX_START_ATTEMPTS = 10

    # Number of times to try connecting to a service
    # that has not yet become available.
    MAX_CONNECT_ATTEMPTS = 10

    # Wait time between attempts
    WAIT_BETWEEN_ATTEMPTS = 0.4

    # Keep track of used ports across classes
    used_ports = []

    def __init__(self, root_dir, tool_path=None,
                 subprocess_module=subprocess, requests_module=requests):
        """
        Initialize the instrumenter to use the tool (JSCover) at
        `tool_path`.

        `root_url` is the URL from which to interpret relative paths.

        Makes the call to the tool using `subprocess_module`, which defaults
        to Python's `subprocess` module.  This can be overridden for testing.

        Uses `requests_module` to perform HTTP calls.  By default, this uses
        the Python `requests` library, but it can be overridden for testing.
        """
        self._root_dir = root_dir
        self._tool_path = tool_path
        self._subprocess = subprocess_module
        self._requests = requests_module

        # Create a variables to store JSCover information
        self._port_num = None
        self._jscover = None

    def start(self):
        """
        Start the service.  The caller is responsible for calling `stop()`.

        It chooses a random local port to start the service on,
        and will retry several times if it gets an address already in use
        error.  If it cannot find an open local port after a certain
        number of trieds, it raises a `SrcInstrumenterError`.
        """

        if self._jscover is None:

            try:
                self._port_num, self._jscover = retry(
                    self._start_jscover,
                    self.MAX_START_ATTEMPTS,
                    self.WAIT_BETWEEN_ATTEMPTS,
                    fail_fast_errors=[OSError],
                    name="Start JSCover"
                )
            except OSError:
                msg = "Could not find JSCover JAR file at '{}'".format(self._tool_path)
                raise SrcInstrumenterError(msg)

            except SrcInstrumenterError:
                msg = "Could not start JSCover, most likely due to port conflicts."
                raise SrcInstrumenterError(msg)

    def stop(self):
        """
        Stop the service.
        """

        # Terminate the JSCover service
        if self._jscover is not None:
            try:
                self._jscover.terminate()

            except OSError:
                LOGGER.debug("Could not terminate JSCover instance.")

            finally:
                self._jscover = None

        else:
            msg = "stop() called with no instance of JSCover running."
            LOGGER.warning(msg)

    def instrumented_src(self, rel_path):
        """
        Return an instrumented version of the JavaScript source
        file at `rel_path`, interpreted relative to the
        root URL (configured in the constructor).

        Raises a `SrcInstrumenterError` is the service hasn't been
        started or the source could not be retrieved.
        """

        # If have not started the service yet, do so now.
        if self._jscover is None:
            raise SrcInstrumenterError("You need to start the JSCover server first.")

        # Get the instrumented version of the source from JSCover
        try:
            return retry(
                lambda: self._get_src_from_jscover(rel_path),
                self.MAX_CONNECT_ATTEMPTS,
                self.WAIT_BETWEEN_ATTEMPTS,
                recover_func=self.start,
                num_attempts_before_recover=2,
                name="Get source from JSCover"
            )

        except requests.exceptions.ConnectionError:
            raise SrcInstrumenterError("Could not connect to JSCover server.")

    @classmethod
    def _random_unused_port(cls):
        """
        Return a random port number not used by any other
        `SrcInstrumenter` instance.  We won't know if this
        port is truly open until we try to start the JSCover server.
        """
        port_num = None
        while port_num is None or port_num in cls.used_ports:
            port_num = random.randint(10000, 40000)

        # Remember that we tried this port
        # There's a race condition here -- another instance might
        # try to start JSCover on `port_num` in between when we
        # start our process and when we add the port to `used_ports`.
        # This is harmless, though, since the other process will
        # get an "address is in use" error and will retry.
        cls.used_ports.append(port_num)

        return port_num

    def _start_jscover(self):
        """
        Start an instance of JSCover running in the root directory.
        The instance will serve instrumented versions of the Javascript
        in its directory.

        Returns a tuple `(port_num, jscover_process)`
        where `port_num` is the local port that JSCover is listening on
        and `jscover_process` is a `subprocess.Popen` object representing
        the `JSCover` server process.
        """

        # Choose a random port.  If we get a conflict, we'll raise
        # an exception and retry.
        port_num = self._random_unused_port()

        # Start JSCover
        call = ['java', '-jar', self._tool_path, '-ws',
                '--port={}'.format(port_num),
                '--document-root={}'.format(self._root_dir)]

        process = self._subprocess.Popen(call, stdout=None,
                                         stderr=self._subprocess.PIPE)

        # If JSCover has a port conflict, it will exit immediately
        # Check that this hasn't happened
        if process.poll() is not None:

            # Get the stderr
            _, stderr = process.communicate()

            # Raise an exception.  If this is being run in a `_retry` call,
            # then it will wait and retry on a different port.
            msg = "Could not start JSCover: '{}'".format(stderr)
            raise SrcInstrumenterError(msg)

        # Return the process information
        return (port_num, process)

    def _get_src_from_jscover(self, rel_path):
        """
        Retrieve the instrumented JS source file at `rel_path`
        from the JSCover server.

        The result is a `unicode` string.
        """

        # Send an HTTP request for the path
        url = 'http://127.0.0.1:{}/{}'.format(self._port_num, rel_path)
        response = self._requests.get(url)

        # Check the status
        if response.status_code != 200:
            msg = "Could not retrieve url '{}': status code {}".format(url, response.status_code)
            raise SrcInstrumenterError(msg)

        # Return a unicode representation of the response
        if isinstance(response.text, unicode):
            return response.text
        else:
            return response.text.decode('utf-8')


class CoverageData(object):
    """
    Load coverage data from JSON.
    """
    def __init__(self):
        """
        Initialize the coverage data instance.
        """

        # Create a dict mapping source file names to coverage
        # information.  Coverage information is stored
        # as a dict mapping line numbers to True/False values
        # indicating whether the line is covered.
        self._src_dict = dict()

        # Create a dict mapping absolute source paths
        # to the path relative to the test suite root directory
        self._rel_path_dict = dict()

        # Create a set to store the suite names we encounter
        self._suite_name_set = set()

    def add_suite_name(self, suite_name):
        """
        Record that we received information from the suite
        with name `suite_name`.

        This is used to check whether we have gotten
        coverage data for every test suite.
        """
        self._suite_name_set.add(suite_name)

    def add_expected_src(self, root_dir, rel_path):
        """
        Add an expected source to the coverage data.
        If no information is received for the source,
        it will be reported as 0% covered.

        `root_dir` is an absolute path to a directory
        from which to interpret `rel_path`.
        """
        full_path = os.path.join(root_dir, rel_path)
        if not full_path in self._src_dict:
            self._src_dict[full_path] = None
            self._rel_path_dict[full_path] = rel_path

    # Ensure that `load_from_dict()` is isolated
    LOAD_LOCK = threading.Lock()

    def load_from_dict(self, root_dir, prepend_path, cover_dict):
        """
        Load coverage data from `cover_dict`, which is in
        the format used by JSCover:

            {SRC_PATH:
                {"lineData": [LINE_DATA, ...],
                 "functionData": [NOT_USED, ...],
                 "branchData": [NOT_USED, ...]}, ...}

        Where `SRC_PATH` is a source path defined relative to the
        `root_dir`.

        `SRC_PATH` is always interpreted as a *relative* path.  If it
        has a leading forward slash, the slash will be removed.

        `LINE_DATA` is a list of values indicating the coverage info
        for the line at that index in the list:

            * null: No coverage information (e.g. a comment)
            * integer: Number of times the line was executed.

        You can call `load_from_dict()` multiple times.  A line is
        considered "covered" if ANY of the JSON descriptions
        indicates that it is covered.

        `root_dir` is the root directory relative to which
        source paths in `cover_dict` are interpreted.

        `prepend_path` is the user-specified path to prepend
        to source files in the report.  This is useful for
        controlling how filenames are reported in a project
        with several test suites.

        This call is thread safe.
        """

        # Check that we got a dict (not a list)
        if not isinstance(cover_dict, dict):
            raise ValueError("Cover data must be a dictionary")

        # For each source file
        for rel_src, cover_dict in cover_dict.iteritems():

            # Always interpret the `rel_src` as relative;
            # if it has a leading slash, remove it
            if rel_src.startswith('/'):
                rel_src = rel_src[1:]

            # Get the full path to the source file from the root dir
            full_path = os.path.join(root_dir, rel_src)

            # Store the relative path
            self._rel_path_dict[full_path] = os.path.join(prepend_path, rel_src)

            # Retrieve the line data (list in which None indicates
            # that the line is not executable and an integer indicates
            # the number of times the line was executed).
            # If the key is not provided, assume no coverage information.
            line_list = cover_dict.get('lineData', None)

            # Only load this source if we have line data;
            # otherwise, ignore it
            if line_list is not None:

                # Line numbers are the indices into the line list
                # Transform this into a dictionary with keys
                # that are line numbers and values that are True/False
                # indicating whether the line is covered.
                # Ignore `None` values, since these are not executed.
                cover_dict = {num: line_list[num] > 0
                              for num in range(len(line_list))
                              if line_list[num] is not None}

                # Ensure that checking/updating the coverage info
                # is isolated
                with self.LOAD_LOCK:

                    # Combine the cover dict with any other dicts that we have
                    # for this source.
                    existing_dict = self._src_dict.get(full_path)

                    if existing_dict is not None:

                        for line_num, is_covered in cover_dict.iteritems():

                            # If the line is covered anywhere, call it covered
                            # Otherwise, call it uncovered
                            already_covered = existing_dict.get(line_num, False)
                            existing_dict[line_num] = is_covered or already_covered

                    # If we haven't encountered this source before, then
                    # store the coverage information we just acquired.
                    else:
                        self._src_dict[full_path] = cover_dict

    def src_list(self):
        """
        Return the list of source files for which we have coverage
        information OR were specified explicitly in the constructor.

        Each source in the list is an absolute path.
        """
        return sorted(self._src_dict.keys())

    def line_dict_for_src(self, full_src_path):
        """
        Returns a dictionary describing the line coverage
        for the JS src file located at `full_src_path`.

        The dictionary uses line numbers as keys
        and True/False as values, where True indicates
        that the line is covered.

        If the source file has no coverage information,
        return a dict with all keys set to False, indicating
        that the file is completely uncovered.

        If the source file is not in our source list,
        return None.
        """

        if full_src_path in self._src_dict:

            # Retrieve the coverage data
            coverage_data = self._src_dict[full_src_path]

            # If the coverage data is None, that means we didn't
            # get coverage information for a source we expected.
            # Report the source as completely uncovered.
            if coverage_data is None:

                # self.num_file_lines() is guaranteed to return an integer
                # If the file isn't found, it returns 0, so coverage_data
                # will be an empty dict.
                coverage_data = {line_num: False for line_num
                                 in range(self.num_file_lines(full_src_path))}

            return coverage_data

        # Source not found
        else:
            return None


    def rel_src_path(self, full_src_path):
        """
        Convert a full source path back to its path relative
        to the test suite root.

        This is useful for displaying a shorter identifier
        for the source file.
        """
        return self._rel_path_dict.get(full_src_path)

    def total_coverage(self):
        """
        Return a decimal in the range [0.0, 1.0] indicating
        the total coverage across source files.

        If no coverage information available, returns None.
        """
        lines_covered = 0
        lines_measured = 0

        for src_path in self.src_list():

            # `line_dict` has keys that are line numbers
            # and values that are True/False indicating
            # whether that line is covered.
            line_dict = self.line_dict_for_src(src_path)
            lines_covered += sum([1 if is_covered else 0
                                  for is_covered in line_dict.values()])
            lines_measured += len(line_dict.items())

        if lines_measured > 0:
            return float(lines_covered) / lines_measured

        else:
            return None

    def coverage_for_src(self, full_src_path):
        """
        Return a decimal in the range [0.0, 1.0] indicating
        the line coverage for the source file at `full_src_path`.

        Returns `None` if no coverage information available
        for `full_src_path`.
        """
        line_dict = self.line_dict_for_src(full_src_path)

        if line_dict is None:
            return None

        else:
            lines_covered = sum([1 if is_covered else 0
                                 for is_covered in line_dict.values()])

            return float(lines_covered) / len(line_dict)

    def suite_name_list(self):
        """
        Return the list of all test suite names for
        which we have coverage information.
        """
        return sorted([name for name in self._suite_name_set])

    @staticmethod
    def num_file_lines(file_path):
        """
        Returns the number of lines in the file
        at `file_path`.  If the file does not exist,
        returns 0.
        """
        try:
            with open(file_path) as file_handle:
                lines = file_handle.readlines()
                return len(lines)

        # If the file could not be accessed, treat
        # it as a file with 0 lines.
        except IOError:
            return 0
