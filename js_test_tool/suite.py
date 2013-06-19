"""
Load test suite descriptions and generate test runner files.
"""
import yaml
import os
import os.path
import pkg_resources

# The template directory should be part of this package
TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates'),
)

# Use Django templates in stand-alone mode
# See https://docs.djangoproject.com/en/dev/ref/templates/api/#configuring-the-template-system-in-standalone-mode
from django.conf import settings 
settings.configure(TEMPLATE_DIRS=TEMPLATE_DIRS)

from django.template.loader import render_to_string


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

    REQUIRED_KEYS = ['src_dirs', 'spec_dirs', 'test_runner', 'browsers']

    # Supported browsers and test runners
    BROWSERS = ['chrome', 'firefox', 'phantomjs']
    TEST_RUNNERS = ['jasmine']

    def __init__(self, file_handle):
        """
        Load the test suite description from a file.

        `file_handle` is a file-like object containing the test suite
        description (YAML format).

        Raises a `SuiteDescriptionError` if the YAML file could
        not be loaded or contains invalid data.
        """

        # Load the YAML file describing the test suite
        try:
            self._desc_dict = yaml.load(file_handle.read())

        except IOError, ValueError:
            raise SuiteDescriptionError("Could not load suite description file")

        # Validate that we have all the required data
        # Raises a `SuiteDescriptionError` if the required data is not found
        self._validate_description(self._desc_dict)

    def lib_paths(self):
        """
        Return a list of paths to the dependency files needed by
        the test suite.

        If no dependencies were specified, returns an empty list.

        Preserves the order of lib directories.

        Raises a `SuiteDescriptionError` if the directory could not be found.
        """
        if 'lib_dirs' in self._desc_dict:
            return self._js_paths(self._desc_dict['lib_dirs'])
        else:
            return []

    def src_paths(self):
        """
        Return a list of paths to JavaScript source
        files used by the test suite.

        Preserves the order of source directories.

        Raises a `SuiteDescriptionError` if the directory could not be found.
        """
        return self._js_paths(self._desc_dict['src_dirs'])

    def spec_paths(self):
        """
        Return a list of paths to JavaScript spec files used by the test suite.

        Preserves the order of spec directories.

        Raises a `SuiteDescriptionError` if the directory could not be found.
        """
        return self._js_paths(self._desc_dict['spec_dirs'])

    def test_runner(self):
        """
        Return the name of the test runner to use (e.g. "Jasmine")
        """

        # We validated data in the constructor, 
        # so the key is guaranteed to exist
        return self._desc_dict['test_runner']

    def browsers(self):
        """
        Return a list of browsers under which to run the tests.
        """

        # We validated data in the constructor, 
        # so the key is guaranteed to exist
        return self._desc_dict['browsers']

    @staticmethod
    def _js_paths(dir_path_list):
        """
        Recursively search the directories at `dir_path_list` (list of paths)
        for *.js files.  

        Returns the list of paths to each JS file it finds, prepending
        the path to the search directory.

        Within each directory in `dir_path_list`, paths are sorted
        alphabetically.  However, order of the root directories
        is preserved.

        Raises a `SuiteDescriptionError` if the directory could not be found.
        """
        js_paths = []

        # Recursively search each directory
        for dir_path in dir_path_list:
            
            # Store all paths within this root directory, so
            # we can sort them while preserving the order of
            # the root directories.
            inner_js_paths = []

            for root_dir, subdirs, filenames in os.walk(dir_path):

                # Look for JavaScript files (*.js)
                for name in filenames:
                    (_, ext) = os.path.splitext(name)

                    if ext == '.js':
                        inner_js_paths.append(os.path.join(root_dir, name))

            # Sort the paths in this directory in alphabetical order
            # then add them to the final list.
            js_paths.extend(sorted(inner_js_paths, key=str.lower))

        return js_paths


    @classmethod
    def _validate_description(cls, desc_dict):
        """
        Validate that `desc_dict` (a `dict`)contains all the required data,
        raising a `SuiteDescriptionError` if any key is missing.
        """

        # Expect that all required keys are present and non-empty
        for key in cls.REQUIRED_KEYS:

            # Checks for non-existent key, empty lists, and empty strings
            if not desc_dict.get(key, None):
                msg = "Missing required key '{}'".format(key)
                raise SuiteDescriptionError(msg)

        # Convert keys that can have multiple values to lists
        for key in ['lib_dirs', 'src_dirs', 'spec_dirs', 'browsers']:
            if not isinstance(desc_dict[key], list):
                desc_dict[key] = [desc_dict[key]]

        # Check that we are using a valid browser
        for browser in desc_dict['browsers']:
            if not browser in cls.BROWSERS:
                msg = "'{}' is not a supported browser.".format(browser)
                raise SuiteDescriptionError(msg)

        # Check that we are using a valid test runner
        if not desc_dict['test_runner'] in cls.TEST_RUNNERS:
            msg = "'{}' is not a supported test runner.".format(browser)
            raise SuiteDescriptionError(msg)


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
    TEMPLATE_DICT = { 'jasmine': 'jasmine_test_runner.html' }

    def render_to_string(self, suite_desc):
        """
        Given a `test_suite_desc` (`TestSuiteDescription` instance),
        render a test runner page.  When loaded, this page will
        execute the JavaScript tests in the suite.

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
        template_context = {'lib_path_list': suite_desc.lib_paths(),
                            'src_path_list': suite_desc.src_paths(),
                            'spec_path_list': suite_desc.spec_paths()}

        # Render the template using Django template renderer
        try:
            html = render_to_string(template_name, template_context)
        except Exception as ex:
            msg = "Error occurred while rendering test runner page: {}".format(ex)
            raise SuiteRendererError(msg)

        return html
