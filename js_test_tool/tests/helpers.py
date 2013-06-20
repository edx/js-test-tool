"""
Test helpers.
"""

import unittest
import tempfile
import shutil
import os


class TempWorkspaceTestCase(unittest.TestCase):
    """
    Test case that creates a temporary directory that it uses
    as the working directory for the duration of the test.
    """

    def setUp(self):
        """
        Create the temporary directory and set it as the current
        working directory.
        """

        # Create a temporary directory 
        self.temp_dir = tempfile.mkdtemp()

        # Set the working directory to the temp dir, so we can
        # use relative paths within the directory.
        self._old_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """
        Delete the temporary directory and restore the working directory.
        """
        shutil.rmtree(self.temp_dir)
        os.chdir(self._old_cwd)
