from js_test_tool.tests.helpers import TempWorkspaceTestCase
from js_test_tool.suite import SuiteDescription
from js_test_tool.tool import create_default_suite
import os.path


class InitCommandTest(TempWorkspaceTestCase):

    def test_create_default_suite(self):

        # Create the default suite
        create_default_suite('js_test_suite.yml')

        # Expect that the file was created in the current working dir
        expected_file = os.path.join(self.temp_dir, 'js_test_suite.yml')
        self.assertTrue(os.path.isfile(expected_file))

        # Expect that the file is a parseable suite description
        # This will throw an exception if not parseable
        with open(expected_file) as suite_file:
            SuiteDescription(suite_file, self.temp_dir)

    def test_create_default_suite_twice(self):

        # Create a file at the expected location
        test_data = 'original suite data'
        expected_file = os.path.join(self.temp_dir, 'js_test_suite.yml')
        with open(expected_file, 'w') as suite_file:
            suite_file.write(test_data)

        # Try to create it again
        create_default_suite('js_test_suite.yml')

        # There should be a warning logged, but the
        # original data still exists
        with open(expected_file) as suite_file:
            contents = suite_file.read()

        self.assertEqual(contents, test_data)
