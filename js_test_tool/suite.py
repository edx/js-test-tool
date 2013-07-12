"""
Load test suite descriptions and generate test runner files.
"""
import yaml
import os
import os.path
from jinja2 import Environment, PackageLoader


# Set up the template environment
TEMPLATE_LOADER = PackageLoader(__package__)
TEMPLATE_ENV = Environment(loader=TEMPLATE_LOADER,
                           trim_blocks=True)


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

    REQUIRED_KEYS = ['src_dirs', 'spec_dirs', 'test_runner']

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

    def root_dir(self):
        """
        Return the root directory to which all paths in the suite
        description are relative.
        """
        return self._root_dir

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

    def _js_paths(self, dir_path_list):
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

            # We use the full path here so that we actually find
            # the files we're looking for
            full_dir_path = os.path.join(self._root_dir, dir_path)
            for root_dir, _, filenames in os.walk(full_dir_path):

                # Look for JavaScript files (*.js)
                for name in filenames:
                    (_, ext) = os.path.splitext(name)

                    if ext == '.js':
                        inner_js_paths.append(os.path.join(root_dir, name))

            # Sort the paths in this directory in alphabetical order
            # then add them to the final list.
            js_paths.extend(sorted(inner_js_paths, key=str.lower))

        # Now that we've found the files we're looking for, we
        # want to return relative paths to our root
        # (for use in URLs)
        rel_paths = [os.path.relpath(path, self._root_dir)
                     for path in js_paths]

        return rel_paths

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
        for key in ['lib_dirs', 'src_dirs', 'spec_dirs']:
            if key in desc_dict and not isinstance(desc_dict[key], list):
                desc_dict[key] = [desc_dict[key]]

        # Check that we are using a valid test runner
        test_runner = desc_dict['test_runner']
        if not test_runner in cls.TEST_RUNNERS:
            msg = "'{}' is not a supported test runner.".format(test_runner)
            raise SuiteDescriptionError(msg)

    @classmethod
    def _validate_root_dir(cls, root_dir):
        """
        Validate that the root directory exists and is a directory,
        raising a `SuiteDescriptionError` if this is not the case.
        """
        if not os.path.isdir(root_dir):
            msg = "'{}' is not a valid directory".format(root_dir)
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
    TEMPLATE_DICT = {'jasmine': 'jasmine_test_runner.html'}

    # The CSS ID of the <div> that will contain the output test results
    RESULTS_DIV_ID = 'js_test_tool_results'

    def render_to_string(self, suite_num, suite_desc):
        """
        Given a `test_suite_desc` (`TestSuiteDescription` instance),
        render a test runner page.  When loaded, this page will
        execute the JavaScript tests in the suite.

        `suite_num` is the index of the suite, used to generate
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
        template_context = {'suite_num': suite_num,
                            'lib_path_list': suite_desc.lib_paths(),
                            'src_path_list': suite_desc.src_paths(),
                            'spec_path_list': suite_desc.spec_paths(),
                            'div_id': self.RESULTS_DIV_ID}

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
