"""
Global setup/teardown for the Lettuce tests.
"""

from lettuce import before, after, world
from mock import patch
from StringIO import StringIO
import os
import os.path
import shutil
import tempfile
from splinter import Browser
from nose.tools import assert_equal, assert_false, assert_true
from js_test_tool import tool


EXPECTED_DIR_NAME = 'expected'
OUTPUT_DIR_NAME = 'actual'
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')

JSCOVER_ENV = 'JSCOVER_JAR'
JSCOVER_JAR = 'jscover/target/dist/JSCover-all.jar'

BROWSER_ARGS = ['--use-firefox', '--use-phantomjs']


@before.all
def setup_all():
    """
    Create a temporary directory in which to install the fixtures.
    """
    world.temp_dir = tempfile.mkdtemp()
    world.fixtures_dir = os.path.join(world.temp_dir, 'fixtures')
    world.browser = Browser('firefox')


@after.all
def teardown_all(total_result):
    """
    Delete the temporary directory we created.
    """
    shutil.rmtree(world.temp_dir)
    world.browser.quit()


@before.each_scenario
def setup_scenario(scenario):
    """
    Install the fixtures in a temporary directory and clear captured stdout.
    """

    # Copy the fixtures directory into the temporary directory
    shutil.copytree(FIXTURE_DIR, world.fixtures_dir)

    # Set the working directory to the fixtures directory
    world.old_cwd = os.getcwd()
    os.chdir(world.fixtures_dir)

    # Mock the system, so we can pass in arguments and capture stdout
    world.mock_sys = patch('js_test_tool.tool.sys').start()
    world.mock_sys.stdout = StringIO()

    # Mock the webbrowser (for use with dev mode)
    world.mock_webbrowser = patch('js_test_tool.dev_runner.webbrowser').start()


@after.each_scenario
def teardown_scenario(scenario):
    """
    Empty the temporary directory and restore the working directory.
    """

    # Remove the fixtures directory
    shutil.rmtree(world.fixtures_dir)

    # Restore the current working directory
    os.chdir(world.old_cwd)

    # Uninstall all mocks
    patch.stopall()


@world.absorb
def run_tool_with_args(arg_list):
    """
    Run JSCover with the arguments in `arg_list`.
    """

    # Install the arguments
    world.mock_sys.argv = ["js-test-tool"] + arg_list + BROWSER_ARGS

    # Run the tool
    tool.main()


@world.absorb
def compare_files_at_paths(actual_filename, expected_filename):
    """
    Assert that the contents of the fixture files
    at `actual_filename` and `expected_filename` are equal.
    """

    # Check that both files exist (to print a better error message)
    world.assert_file_exists(actual_filename)
    world.assert_file_exists(expected_filename)

    # Open both files and compare the contents
    with open(actual_filename) as actual_file:
        with open(expected_filename) as expected_file:
            assert_equal(actual_file.read().strip(),
                         expected_file.read().strip())


@world.absorb
def assert_file_exists(path):
    """
    Assert that a file exists at `path`.
    """
    msg = "File '{}' does not exist.".format(path)
    assert_true(os.path.isfile(path), msg=msg)


@world.absorb
def assert_no_file(path):
    """
    Assert that no file exists at `path`.
    """
    msg = "'{}' should NOT exist".format(path)
    assert_false(os.path.isfile(path), msg=msg)


@world.absorb
def assert_tool_stdout(expected_filename):
    """
    Assert that the output of the tool is equal
    to the content of the fixture file at `expected_filename`.
    """

    # Retrieve captured stdout from our mock system
    captured_stdout = world.mock_sys.stdout.getvalue()

    # Open the file containing the expected report
    # and check that it matches the stdout captured by the tool
    with open(expected_filename) as expected_file:
        assert_equal(captured_stdout, expected_file.read())


@world.absorb
def set_jscover(enabled):
    """
    Configure the environment variables to enable or disable
    the JSCover dependency.  `enabled` is a bool.
    """

    # Set the environment variable to point to the JSCover JAR file
    if enabled:
        os.environ[JSCOVER_ENV] = JSCOVER_JAR

    # If the environment contains the JSCover JAR path,
    # remove the environment variable.
    else:
        if JSCOVER_ENV in os.environ:
            del os.environ[JSCOVER_ENV]


@world.absorb
def assert_exit_code(expected_code):
    """
    Assert that `sys.exit()` was called with `expected_code`.
    """

    # Assume that if mock_sys.exit() is not called, the tool
    # exited with status 0
    if world.mock_sys.exit.call_count == 0:
        assert_equal(0, int(expected_code))

    else:
        args, kwargs = world.mock_sys.exit.call_args
        assert_equal(args[0], int(expected_code))


@world.absorb
def load_page(url):
    """
    Load the page at `url` using the Splinter browser.
    """
    world.browser.visit(url)
