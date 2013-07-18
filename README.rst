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

    js-test-tool init

This will create a YAML file that looks like:

.. code:: yaml

    ---
    # Currently, the only supported test runner is Jasmine
    # See http://pivotal.github.io/jasmine/
    # for the Jasmine documentation.
    test_runner: jasmine

    # Paths to source JavaScript files
    src_paths:
        - path/to/src

    # Paths to library JavaScript files (optional)
    lib_paths:
        - path/to/lib

    # Paths to spec (test) JavaScript files
    spec_paths:
        - path/to/spec

    # Paths to fixture files (optional)
    # You can access these within JavaScript code
    # at the URL: document.location.href + "/include/"
    # plus the path to the file (relative to this YAML file)
    fixture_paths:
        - path/to/fixture

* All paths are specified relative 
  to the location of the YAML file.

* Directory paths are searched recursively.

* JavaScript files are loaded in the specified order.

2. Run the test suite.

.. code:: bash

    js-test-tool run js_test.yml --use-firefox

This will output a report to the console showing which tests passed or failed.

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
