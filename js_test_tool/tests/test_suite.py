import unittest
import mock
import os
import os.path
from StringIO import StringIO
import yaml
from textwrap import dedent
from lxml import etree

from js_test_tool.tests.helpers import TempWorkspaceTestCase

from js_test_tool.suite import SuiteDescription, SuiteDescriptionError, \
    SuiteRenderer, SuiteRendererError


class SuiteDescriptionTest(TempWorkspaceTestCase):

    # Temporary directory paths to be created within our root temp dir
    TEMP_DIRS = ['src/subdir', 'spec/subdir', 'lib/subdir',
                 'src/empty', 'spec/empty', 'lib/empty',
                 'other_src', 'other_spec', 'other_lib']

    # Test files to create.  Paths specified relative to the root temp dir.
    LIB_FILES = ['lib/1.js', 'lib/2.js', 'lib/subdir/3.js',
                 'other_lib/test.js']

    SRC_FILES = ['src/1.js', 'src/2.js', 'src/subdir/3.js',
                 'other_src/test.js']

    SPEC_FILES = ['spec/1.js', 'spec/2.js', 'spec/subdir/3.js',
                  'other_spec/test.js']

    IGNORE_FILES = ['src/ignore.txt', 'spec/ignore.txt', 'lib/ignore.txt']

    # Valid data used to create the YAML file describing the test suite
    YAML_DATA = {'name': 'test_suite',
                 'lib_dirs': ['lib', 'other_lib'],
                 'src_dirs': ['src', 'other_src'],
                 'spec_dirs': ['spec', 'other_spec'],
                 'test_runner': 'jasmine'}

    def setUp(self):
        """
        Generate fake JS files in a temporary directory.
        """

        # Call the superclass implementation to create the temp workspace
        super(SuiteDescriptionTest, self).setUp()

        # Create subdirectories for dependency, source, and spec files
        # Because we are using `makedirs()`, the intermediate directories
        # will also be created.
        for dir_path in self.TEMP_DIRS:
            os.makedirs(os.path.join(self.temp_dir, dir_path))

        # Create the test files
        all_files = (self.LIB_FILES + self.SRC_FILES
                     + self.SPEC_FILES + self.IGNORE_FILES)

        for file_path in all_files:
            full_path = os.path.join(self.temp_dir, file_path)
            with open(full_path, "w") as file_handle:
                file_handle.write('Test data')

    def test_valid_description(self):

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(self.YAML_DATA)

        # Create the suite description using the YAML file
        desc = SuiteDescription(yaml_file, self.temp_dir)

        # Check that the root directory is stored
        self.assertEqual(desc.root_dir(), self.temp_dir)

        # Check that we find the files we expect
        self.assertEqual(desc.lib_paths(), self.LIB_FILES)
        self.assertEqual(desc.src_paths(), self.SRC_FILES)
        self.assertEqual(desc.spec_paths(), self.SPEC_FILES)
        self.assertEqual(desc.test_runner(), self.YAML_DATA['test_runner'])

    def test_no_such_root_dir(self):

        # Try to create a description with a non-existent root directory
        yaml_file = self._yaml_buffer(self.YAML_DATA)
        no_such_dir = os.path.join(self.temp_dir, 'no_such_dir')

        with self.assertRaises(SuiteDescriptionError):
            SuiteDescription(yaml_file, no_such_dir)

    def test_root_dir_is_file(self):

        # Try to create a description with a file (not directory) root
        yaml_file = self._yaml_buffer(self.YAML_DATA)
        file_path = os.path.join(self.temp_dir, self.SRC_FILES[0])

        with self.assertRaises(SuiteDescriptionError):
            SuiteDescription(yaml_file, file_path)

    def test_non_list_data(self):

        # Replace all list values with single values
        yaml_data = self.YAML_DATA.copy()
        yaml_data['lib_dirs'] = 'lib'
        yaml_data['src_dirs'] = 'src'
        yaml_data['spec_dirs'] = 'spec'

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(yaml_data)

        # Create the suite description using the YAML file
        desc = SuiteDescription(yaml_file, self.temp_dir)

        # Check that we get the right paths
        # (exclude files from the directories we left out)
        self.assertEqual(desc.lib_paths(), self.LIB_FILES[0:3])
        self.assertEqual(desc.src_paths(), self.SRC_FILES[0:3])
        self.assertEqual(desc.spec_paths(), self.SPEC_FILES[0:3])

    def test_no_lib_specified(self):

        # 'lib_dirs' is an optional key
        yaml_data = self.YAML_DATA.copy()
        del yaml_data['lib_dirs']

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(yaml_data)

        # Create the suite description using the YAML file
        desc = SuiteDescription(yaml_file, self.temp_dir)

        # Check that we get an empty list of lib paths
        self.assertEqual(desc.lib_paths(), [])

    def test_missing_required_data(self):

        for key in ['src_dirs', 'spec_dirs', 'test_runner']:

            # Delete the required key from the description
            yaml_data = self.YAML_DATA.copy()
            del yaml_data[key]

            # Print a message to make failures more informative
            print "Missing key '{}' should raise an exception".format(key)

            # Check that we get an exception
            self._assert_invalid_desc(yaml_data)

    def test_empty_required_list(self):

        for key in ['src_dirs', 'spec_dirs']:

            # Replace the key with an empty list
            yaml_data = self.YAML_DATA.copy()
            yaml_data[key] = []

            # Print a message to make failures more informative
            print "Empty list for '{}' should raise an exception".format(key)

            # Check that we get an exception
            self._assert_invalid_desc(yaml_data)

    def test_invalid_test_runner(self):
        yaml_data = self.YAML_DATA.copy()
        yaml_data['test_runner'] = 'invalid_test_runner'

        # Check that we get an exception
        self._assert_invalid_desc(yaml_data)

    def _assert_invalid_desc(self, yaml_data):
        """
        Given `yaml_data` (dict), assert that it raises
        a `SuiteDescriptionError`.
        """

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(yaml_data)

        # Expect an exception when we try to parse the YAML file
        with self.assertRaises(SuiteDescriptionError):
            SuiteDescription(yaml_file, self.temp_dir)

    @staticmethod
    def _yaml_buffer(data_dict):
        """
        Create an in-memory buffer with YAML-encoded data
        provided by `data_dict` (a dictionary).

        Returns the buffer (a file-like object).
        """

        # Encode the `data_dict` as YAML and write it to the buffer
        yaml_str = yaml.dump(data_dict)

        # Create a file-like string buffer to hold the YAML data
        string_buffer = StringIO(yaml_str)

        return string_buffer


class SuiteRendererTest(unittest.TestCase):

    JASMINE_TEST_RUNNER_SCRIPT = dedent("""
        (function() {
            var jasmineEnv = jasmine.getEnv();
            jasmineEnv.updateInterval = 1000;

            var jsonReporter = new jasmine.JsonReporter("js_test_tool_results", "0");

            jasmineEnv.addReporter(jsonReporter);

            var currentWindowOnload = window.onload;

            window.onload = function() {
                if (currentWindowOnload) {
                    currentWindowOnload();
                }

                execJasmine();
            };

            function execJasmine() {
                jasmineEnv.execute();
            }

        })();
    """).strip()

    def setUp(self):

        # Create the renderer we will use
        self.renderer = SuiteRenderer()

    def test_unicode(self):

        # Create a mock test suite description
        desc = self._mock_desc(['lib1.js', 'lib2.js'],
                               ['src1.js', 'src2.js'],
                               ['spec1.js', 'spec2.js'],
                               'jasmine')

        # Render the description as HTML
        html = self.renderer.render_to_string(0, desc)

        # Expect that we get a `unicode` string
        self.assertTrue(isinstance(html, unicode))

    def test_jasmine_runner(self):

        jasmine_libs = ['jasmine/jasmine.js',
                        'jasmine/jasmine-json.js']
        lib_paths = ['lib1.js', 'lib2.js']
        src_paths = ['src1.js', 'src2.js']
        spec_paths = ['spec1.js', 'spec2.js']

        # Create a mock test suite description
        desc = self._mock_desc(lib_paths, src_paths, spec_paths, 'jasmine')

        # Check that we get the right script includes
        suite_includes = lib_paths + src_paths + spec_paths
        self._assert_js_includes(jasmine_libs, suite_includes, desc)

    def test_no_lib_files(self):

        jasmine_libs = ['jasmine/jasmine.js',
                        'jasmine/jasmine-json.js']
        src_paths = ['src.js']
        spec_paths = ['spec.js']

        # Create a mock test suite description
        desc = self._mock_desc([], src_paths, spec_paths, 'jasmine')

        # Check that we get the right script includes
        suite_includes = src_paths + spec_paths
        self._assert_js_includes(jasmine_libs, suite_includes, desc)

    def test_render_jasmine_runner(self):

        # Create a mock test suite description with no includes
        desc = self._mock_desc([], [], [], 'jasmine')

        # Render the description to HTML
        html = self.renderer.render_to_string(0, desc)

        # Parse the HTML
        tree = etree.HTML(html)

        # Expect that a <div> exists with the correct ID for the results
        div_id = SuiteRenderer.RESULTS_DIV_ID
        elems = tree.xpath('/html/body/div[@id="{}"]'.format(div_id))
        self.assertEqual(len(elems), 1)

        # Retrieve the script elements
        script_elems = tree.xpath('/html/head/script')

        # Expect at least one element
        self.assertTrue(len(script_elems) > 0)

        # Retrieve the last script element, which should be the inline
        # test runner code
        runner_script = script_elems[-1].text
        runner_script = runner_script.strip()

        # Check that it is the Jasmine test runner script
        self.assertEqual(runner_script, self.JASMINE_TEST_RUNNER_SCRIPT)

    def test_undefined_template(self):

        # Create a mock test suite description with an invalid test runner
        desc = self._mock_desc([], [], [], 'invalid_test_runner')

        # Should get an exception that the template could not be found
        with self.assertRaises(SuiteRendererError):
            self.renderer.render_to_string(0, desc)

    def test_template_render_error(self):

        # Create a mock test suite description with no includes
        desc = self._mock_desc([], [], [], 'jasmine')

        # Patch Jinja2's `render()` function
        with mock.patch.object(SuiteRenderer, 'render_template') as render_func:

            # Have the render function raise an exception
            render_func.side_effect = ValueError()

            # Expect that we get a `SuiteRendererError`
            with self.assertRaises(SuiteRendererError):
                self.renderer.render_to_string(0, desc)

    def _assert_js_includes(self, runner_includes, suite_includes, suite_desc):
        """
        Render `suite_desc` (a `SuiteDescription` instance or mock) to
        `html`, then asserts that the `html` contains `<script>` tags with
        `runner_includes` (files included by default, with a `/runner/` prefix)
        and `suite_includes` (files included by the test suite,
        with a `/suite/include` prefix)
        """
        # Render the description as HTML
        html = self.renderer.render_to_string(0, suite_desc)

        # Parse the HTML
        tree = etree.HTML(html)

        # Retrieve all <script> inclusions
        script_elems = tree.xpath('/html/head/script')

        # Prepend the runner and suite includes
        runner_includes = [os.path.join('/runner', path)
                           for path in runner_includes]
        suite_includes = [os.path.join('/suite', '0', 'include', path)
                          for path in suite_includes]

        # Check that they match the sources we provided, in order
        all_paths = [element.get('src') for element in script_elems
                     if element.get('src') is not None]

        self.assertEqual(all_paths, runner_includes + suite_includes)

    @staticmethod
    def _mock_desc(lib_paths, src_paths, spec_paths, test_runner):
        """
        Create a mock SuiteDescription configured to return
        `lib_paths` (paths to JS dependency files)
        `src_paths` (paths to JS source files)
        `spec_paths` (paths to JS spec files)
        `test_runner` (name of the test runner, e.g. Jasmine)

        Returns the configured mock
        """
        desc = mock.MagicMock(SuiteDescription)

        desc.lib_paths.return_value = lib_paths
        desc.src_paths.return_value = src_paths
        desc.spec_paths.return_value = spec_paths
        desc.test_runner.return_value = test_runner

        return desc
