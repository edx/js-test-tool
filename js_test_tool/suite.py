"""
Load test suite descriptions and generate test runner files.
"""
import yaml
import os
import os.path
from textwrap import dedent
import re
from jinja2 import Environment, PackageLoader
import urllib

import logging
LOGGER = logging.getLogger(__name__)

# Set up the template environment
TEMPLATE_LOADER = PackageLoader(__package__)
TEMPLATE_ENV = Environment(
    loader=TEMPLATE_LOADER, trim_blocks=True
)


class SuiteDescriptionError(Exception):
    """
    Raised when the suite description is invalid.
    For example, if the suite description file is missing
    required data.
    """
    pass


class SuiteDescription(object):
    """
    Description of a JavaScript test suite loaded from a file.
    """

    REQUIRED_KEYS = [
        'test_suite_name',
        'src_paths',
        'spec_paths',
        'test_runner'
    ]

    # Supported test runners
    TEST_RUNNERS = ['jasmine']

    def __init__(self, file_handle, root_dir):
        """
        Load the test suite description from a file.

        `file_handle` is a file-like object containing the test suite
        description (YAML format).

        `root_dir` is the directory relative to which paths are specified
        in the test suite description.  This directory must exist.

        Raises a `SuiteDescriptionError` if the YAML file could
        not be loaded or contains invalid data.
        """

        # Load the YAML file describing the test suite
        try:
            self._desc_dict = yaml.load(file_handle.read())

        except (IOError, ValueError):
            raise SuiteDescriptionError("Could not load suite description file")

        # Store the root directory
        self._root_dir = root_dir

        # Validate that we have all the required data
        # Raises a `SuiteDescriptionError` if the required data is not found
        self._validate_description(self._desc_dict)

        # Validate the root directory
        self._validate_root_dir(self._root_dir)

        # Validate that the suite name is acceptable
        self._validate_suite_name(self.suite_name())

        # Compile exclude/include regular expressions
        rules = self._desc_dict.get('include_in_page', [])
        self._include_regex_list = [re.compile(r) for r in rules]

        rules = self._desc_dict.get('exclude_from_page', [])
        self._exclude_regex_list = [re.compile(r) for r in rules]

        # Try to find all paths once, with warnings enabled
        # This way, we print warnings for missing files to the
        # console only one time.
        self.lib_paths(enable_warnings=True)
        self.spec_paths(enable_warnings=True)
        self.src_paths(enable_warnings=True)
        self.fixture_paths(enable_warnings=True)

    def suite_name(self):
        """
        Return the unique identifier for the test suite.
        """
        return self._desc_dict.get('test_suite_name')

    def root_dir(self):
        """
        Return the root directory to which all paths in the suite
        description are relative.
        """
        return self._root_dir

    def prepend_path(self):
        """
        Return a user-defined path prepended to source file
        paths in reports.  May be an empty string.
        """
        return self._desc_dict.get('prepend_path', '')

    def lib_paths(self, only_in_page=False, enable_warnings=False):
        """
        Return a list of paths to the dependency files needed by
        the test suite.

        If `only_in_page` is True, returns only the paths
        that should be included in <script> tags on the
        test runner page.

        If `enable_warnings` is true, then log a warning whenever
        we can't find a file we expect.

        If no dependencies were specified, returns an empty list.

        Preserves the order of lib directories.

        Raises a `SuiteDescriptionError` if a file or directory could not be found.
        """
        if 'lib_paths' in self._desc_dict:
            return self._js_paths(self._desc_dict['lib_paths'],
                                  only_in_page,
                                  enable_warnings)
        else:
            return []

    def src_paths(self, only_in_page=False, enable_warnings=False):
        """
        Return a list of paths to JavaScript source
        files used by the test suite.

        If `only_in_page` is True, returns only the paths
        that should be included in <script> tags on the
        test runner page.

        If `enable_warnings` is true, then log a warning whenever
        we can't find a file we expect.

        Preserves the order of source directories.

        Raises a `SuiteDescriptionError` if a file or directory could not be found.
        """
        return self._js_paths(self._desc_dict['src_paths'],
                              only_in_page,
                              enable_warnings)

    def spec_paths(self, only_in_page=False, enable_warnings=False):
        """
        Return a list of paths to JavaScript spec files used by the test suite.

        If `only_in_page` is True, returns only the paths
        that should be included in <script> tags on the
        test runner page.

        If `enable_warnings` is true, then log a warning whenever
        we can't find a file we expect.

        Preserves the order of spec directories.

        Raises a `SuiteDescriptionError` if a file or directory could not be found.
        """
        return self._js_paths(self._desc_dict['spec_paths'],
                              only_in_page,
                              enable_warnings)

    def fixture_paths(self, enable_warnings=False):
        """
        Return a list of paths to fixture files used by the test suite.
        These can be non-JavaScript files.

        If `enable_warnings` is true, then log a warning whenever
        we can't find a file we expect.

        Raises a `SuiteDescriptionError` if a file or directory could not be found.
        """
        if 'fixture_paths' in self._desc_dict:
            return self._file_paths(self._desc_dict['fixture_paths'],
                                    enable_warnings)
        else:
            return []

    def test_runner(self):
        """
        Return the name of the test runner to use (e.g. "Jasmine")
        """

        # We validated data in the constructor,
        # so the key is guaranteed to exist
        return self._desc_dict['test_runner']

    def _include_in_page(self, script_path):
        """
        Return True if and only if the script should be
        included in the test runner page using <script> tags.

        A script is included by default, UNLESS it matches
        the regex rule `exclude_from_page` in the YAML description.
        and it does NOT match the `include_in_page` rule.
        """

        # Check if the script matches a rule to always be included
        for include_regex in self._include_regex_list:
            if include_regex.match(script_path) is not None:
                return True

        # Check if the script matches an exclude rule
        for exclude_regex in self._exclude_regex_list:
            if exclude_regex.match(script_path) is not None:
                return False

        # Default is to include it
        return True

    def _js_paths(self, path_list, only_in_page, enable_warnings):
        """
        Find *.js files in `path_list`.  See `_file_paths` for
        more information.

        If `only_in_page` is True, filters the results for
        only JS files to be included in the test runner page
        <script> tags.

        If `enable_warnings` is true, then log a warning whenever
        we can't find a file we expect.
        """
        paths = self._file_paths(path_list,
                                 enable_warnings,
                                 include_func=self._is_js_file) 
        if only_in_page:
            return filter(self._include_in_page, paths)
        else:
            return paths

    def _file_paths(self, path_list,
                    enable_warnings,
                    include_func=lambda file_path: True):
        """
        Recursively search the directories in `path_list` for
        files that satisfy `include_func`.

        `path_list` is a list of file and directory paths.
        `include_func` is a function that acccepts a `file_path` argument
        and returns a bool indicating whether to include the file.

        If `enable_warnings` is true, then log a warning whenever
        we can't find a file we expect.

        Returns the list of  paths to each file it finds.
        These are relative paths to the root directory passed
        to the constructor.

        Within each directory in `dir_path_list`, paths are sorted
        alphabetically.  However, order of the root directories
        is preserved.

        The paths in the resulting list are guaranteed to be unique.

        Raises a `SuiteDescriptionError` if the directory could not be found.
        """

        # Create a list of paths to return
        # We use a list instead of a set, even though we
        # want paths to be unique, because we want
        # to preserve the dependency order the user
        # specified.
        result_paths = []

        for path in path_list:

            # We use the full path here so that we actually find
            # the files we're looking for
            full_path = os.path.join(self._root_dir, path)

            # If the path is a file and satisfies the include function
            # then add it to the list.
            if os.path.isfile(full_path):
                if include_func(full_path):
                    result_paths.append(full_path)

                # This is a user-specified file, so we let the
                # user know that we are skipping the dependency.
                elif enable_warnings:
                    msg = "Skipping '{}' because it does not have a '.js' extension".format(path)
                    LOGGER.warning(msg)

            # If the path is a directory, recursively search for JS files
            elif os.path.isdir(full_path):

                # Store all paths within this root directory, so
                # we can sort them while preserving the order of
                # the root directories.
                inner_paths = []

                for root_dir, _, filenames in os.walk(full_path):

                    # Look for files that satisfy the include func
                    for name in filenames:
                        if include_func(name):
                            inner_paths.append(os.path.join(root_dir, name))

                # Sort the paths in this directory in alphabetical order
                # then add them to the final list.
                result_paths.extend(sorted(inner_paths, key=str.lower))

            # If it's neither a file nor a directory,
            # this is a user input error, so log it.
            elif enable_warnings:
                msg = "Could not find file or directory at '{}'".format(path)
                LOGGER.warning(msg)

        # Now that we've found the files we're looking for, we
        # want to return relative paths to our root
        # (for use in URLs)
        rel_paths = [os.path.relpath(path, self._root_dir)
                     for path in result_paths]

        # Remove duplicates, preserving the order
        return self._remove_duplicates(rel_paths)

    @staticmethod
    def _is_js_file(file_path):
        """
        Returns True only if the file at `file_path` has a .js extension.
        """
        _, ext = os.path.splitext(file_path)
        return ext == '.js'

    @staticmethod
    def _remove_duplicates(path_list):
        """
        Return a list of paths with duplicates removed,
        preserving the order in `path_list`.
        """
        already_found = []
        result = []

        for path in path_list:

            if not path in already_found:
                result.append(path)
                already_found.append(path)

        return result

    @classmethod
    def _validate_description(cls, desc_dict):
        """
        Validate that `desc_dict` (a `dict`)contains all the required data,
        raising a `SuiteDescriptionError` if any key is missing.
        """

        # Check that we have a dict
        # The YAML syntax makes it easy to specify
        # a list of dicts rather than a dict, which we expect.
        if not isinstance(desc_dict, dict):
            msg = dedent("""
                    Suite description must be a dictionary.
                    Check that your keys look like this:

                    spec_paths:
                        - spec

                    and not like this:

                    - spec_paths:
                        - spec

                    (note the initial - sign).""")
            raise SuiteDescriptionError(msg)

        # Expect that all required keys are present and non-empty
        for key in cls.REQUIRED_KEYS:

            # Checks for non-existent key, empty lists, and empty strings
            if not desc_dict.get(key, None):
                msg = "Missing required key '{}'".format(key)
                raise SuiteDescriptionError(msg)

        # Convert keys that can have multiple values to lists
        for key in ['lib_paths', 'src_paths',
                    'spec_paths', 'fixture_paths',
                    'include_in_page', 'exclude_from_page']:
            if key in desc_dict and not isinstance(desc_dict[key], list):
                desc_dict[key] = [desc_dict[key]]

        # Check that we are using a valid test runner
        test_runner = desc_dict['test_runner']
        if not test_runner in cls.TEST_RUNNERS:
            msg = "'{}' is not a supported test runner.".format(test_runner)
            raise SuiteDescriptionError(msg)

        # Check that we are not using double-dot relative paths
        for key in ['lib_paths', 'src_paths', 'spec_paths', 'fixture_paths']:
            if key in desc_dict and cls.path_list_has_double_dot(desc_dict[key]):
                msg = ("Paths cannot use up-level references (e.g. ../path/to/dir).  " +
                      "Try using a symbolic link instead.")
                raise SuiteDescriptionError(msg)

        # Check that the prepend_path key is a string
        prepend_path = desc_dict.get('prepend_path', '')
        if not (isinstance(prepend_path, str) or
                isinstance(prepend_path, unicode)):
            msg = "Prepend path must be a string."
            raise SuiteDescriptionError(msg)

    @staticmethod
    def _validate_suite_name(name):
        """
        Suite name must be URL-encodable and not contain
        any GET param characters.
        """
        # If the encoding is different then the name,
        # then the name is not encoded.
        if urllib.quote(name) != name:
            msg = "'{}' must be URL-encoded.".format(name)
            raise SuiteDescriptionError(msg)

        # Also can't allow anything that will throw off
        # our path parsing (slashes)
        if '/' in name:
            msg = "'{}' cannot contain slashes".format(name)
            raise SuiteDescriptionError(msg)

    @staticmethod
    def _validate_root_dir(root_dir):
        """
        Validate that the root directory exists and is a directory,
        raising a `SuiteDescriptionError` if this is not the case.
        """
        if not os.path.isdir(root_dir):
            msg = "'{}' is not a valid directory".format(root_dir)
            raise SuiteDescriptionError(msg)

    @staticmethod
    def path_list_has_double_dot(path_list):
        """
        Return True if any path in `path_list` uses
        an up-level reference (double dot).
        """
        for path in path_list:
            if '..' in path.split('/'):
                return True
        return False


class SuiteRendererError(Exception):
    """
    Raised when the test runner page could not be rendered
    for a given test suite description.
    """
    pass


class SuiteRenderer(object):
    """
    Render a test runner page for a test suite description.
    """

    # Dictionary mapping test runner names (e.g. 'jasmine') to
    # templates used to render the test runner page.
    TEMPLATE_DICT = {'jasmine': 'jasmine_test_runner.html'}

    # The CSS ID of the <div> that will contain the output test results
    RESULTS_DIV_ID = 'js_test_tool_results'

    # Expect the results page to have a <div>
    # with this ID to report JavaScript exceptions
    ERROR_DIV_ID = 'js_test_tool_error'

    def __init__(self, dev_mode=False):
        """
        If `dev_mode` is `True`, then display results in the browser
        in a human-readable form.
        """
        self._dev_mode = dev_mode

    def render_to_string(self, suite_name, suite_desc):
        """
        Given a `test_suite_desc` (`TestSuiteDescription` instance),
        render a test runner page.  When loaded, this page will
        execute the JavaScript tests in the suite.

        `suite_name` is the unique name of the suite, used to generate
        links to that suite's dependencies.

        Returns a unicode string.

        Raises an `SuiteRendererError` if the page could not be rendered.
        """

        # Get the test runner template
        test_runner = suite_desc.test_runner()
        template_name = self.TEMPLATE_DICT.get(test_runner)

        # If we have no template for this name, raise an exception
        if template_name is None:
            msg = "No template defined for test runner '{}'".format(test_runner)
            raise SuiteRendererError(msg)

        # Create the context for the template
        template_context = {'suite_name': suite_name,
                            'lib_path_list': suite_desc.lib_paths(only_in_page=True),
                            'src_path_list': suite_desc.src_paths(only_in_page=True),
                            'spec_path_list': suite_desc.spec_paths(only_in_page=True),
                            'results_div_id': self.RESULTS_DIV_ID,
                            'error_div_id': self.ERROR_DIV_ID,
                            'dev_mode': self._dev_mode}

        # Render the template
        try:
            html = self.render_template(template_name, template_context)
        except Exception as ex:
            msg = "Error occurred while rendering test runner page: {}".format(ex)
            raise SuiteRendererError(msg)

        return html

    @staticmethod
    def render_template(template_name, context):
        """
        Render `template` (a Jinja2 `Template`) using `context`
        (a `dict`) and return the resulting unicode string.
        """
        template = TEMPLATE_ENV.get_template(template_name)
        return template.render(context)
