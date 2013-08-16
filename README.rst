js-test-tool
============

Run JavaScript test suites and collect coverage information.


Installation
------------

.. code:: bash

    cd js-test-tool
    python setup.py install


Getting Started
---------------

1. Create a file describing the test suite.

.. code:: bash

    js-test-tool init js_test.yml

This will create a YAML file (``js_test.yml``) that looks like:

.. code:: yaml

    ---
    # Name of the test suite, used to construct
    # the URL from which pages are served.
    #
    # For example, if the suite name is "test_suite",
    # then:
    #
    #   * /suite/test_suite
    #     serves the test suite runner page
    #   * /suite/test_suite/include/*
    #     serves dependencies (src, spec, lib, and fixtures)
    #
    # Test suite names must be URL-encodable and unique
    # among suite descriptions passed to js-test-tool
    test_suite_name: test_suite

    # Currently, the only supported test runner is Jasmine
    # See http://pivotal.github.io/jasmine/
    # for the Jasmine documentation.
    test_runner: jasmine

    # Path prepended to source files in the coverage report (optional)
    # For example, if the source path
    # is "src/source.js" (relative to this YAML file)
    # and the prepend path is "base/dir"
    # then the coverage report will show
    # "base/dir/src/source.js"
    prepend_path: base/path

    # Paths to library JavaScript files (optional)
    lib_paths:
        - path/to/lib

    # Paths to source JavaScript files
    src_paths:
        - path/to/src

    # Paths to spec (test) JavaScript files
    spec_paths:
        - path/to/spec

    # Paths to fixture files (optional)
    # The fixture path will be set automatically when using jasmine-jquery.
    # (https://github.com/velesin/jasmine-jquery)
    #
    # You can then access fixtures using paths relative to
    # the test suite description:
    #
    #   loadFixtures('path/to/fixture/fixture.html');
    #
    fixture_paths:
        - path/to/fixture

    # Regular expressions used to exclude *.js files from
    # appearing in the test runner page.
    # Files are included by default, which means that they
    # are loaded using a <script> tag in the test runner page.
    # When loading many files, this can be slow, so
    # exclude any files you don't need.
    exclude_from_page:
        - path/to/lib/exclude/*

    # Regular expression used to guarantee that a *.js file
    # is included in the test runner page.
    # If a file name matches both `exclude_from_page` and
    # `include_in_page`, the file WILL be included.
    # You can use this to exclude all files in a directory,
    # but make an exception for particular files.
    include_in_page:
        - path/to/lib/exclude/exception_*.js


* All paths are specified relative
  to the location of the YAML file.

* Directory paths are searched recursively.

* JavaScript files are loaded in the specified order.

* Paths cannot contain up-level references. For example, ``path/to/dir`` is okay,
  but ``../path/to/dir`` is not.
  If you need to access files in directories above the test suite directory,
  use symbolic links.

2. Run the test suite.

.. code:: bash

    js-test-tool run js_test.yml --use-firefox

This will output a report to the console showing which tests passed or failed.


Dev Mode
--------

``js-test-tool`` has a special mode for writing and debugging tests:

.. code:: bash

    js-test-tool dev js_test.yml

This will start ``js-test-tool`` in **dev mode**:

* Tests will run in your default browser.
* The tool will keep running until you terminate it with ``Ctrl-C``.
* Test results are displayed directly in the browser.


Timeouts
--------

If tests take too long to run, the test runner will time out.
The default timeout is 5 minutes, but you can override this:

.. code:: bash

    js-test-tool run js_test.yml --use-chrome --timeout-sec 10

The above command sets the timeout to 10 seconds.


Coverage
--------

To collect JavaScript coverage:

1. Download and unzip `JSCover`__

__ http://tntim96.github.io/JSCover/

2. Set the environment variable ``JSCOVER_JAR``:

.. code:: bash

    export JSCOVER_JAR=~/jscover/target/dist/JSCover-all.jar

3. Run ``js-test-tool`` with coverage:

.. code:: bash

    js-test-tool run js_test.yml --use-phantomjs --coverage-xml=js_coverage.xml --coverage-html=js_coverage.html

This will create coverage reports in two formats:

* Cobertura XML
* HTML


Multiple Browsers
------------------

Using command-line options, you can run the tests in
multiple browsers:

.. code:: bash

    js-test-tool run js_test.yml --use-chrome --use-phantomjs

will run the tests in both Chrome and PhantomJS if the
browsers are installed.

The tool currently supports these browsers:

* Chrome
* PhantomJS
* Firefox

Coverage information is combined across browsers: a line is
considered covered if it is executed under *any* browser.


Multiple Test Suites
--------------------

You can run test suites sequentially:

.. code:: bash

    js-test-tool run test_1.yml test_2.yml --use-firefox

If collecting coverage, then the coverage report
will contain information for all files included
in each test suite.


License
-------

The code in this repository is licensed under version 3 of the AGPL unless
otherwise noted.

Please see ``LICENSE.txt`` for details.


How to Contribute
-----------------

Contributions are very welcome. The easiest way is to fork this repo, and then
make a pull request from your fork. The first time you make a pull request, you
may be asked to sign a Contributor Agreement.


Reporting Security Issues
-------------------------

Please do not report security issues in public. Please email security@edx.org


Mailing List and IRC Channel
----------------------------

You can discuss this code on the `edx-code Google Group`__ or in the
``edx-code`` IRC channel on Freenode.

__ https://groups.google.com/forum/#!forum/edx-code
