Feature: Collect JavaScript coverage metrics
    In order to improve software quality
    As a JavaScript developer
    I want to run JavaScript unit tests and view code coverage metrics.

    Scenario: XML coverage
        Given Coverage dependencies are configured
        When I run js-test-tool with XML coverage
        Then An XML coverage report is generated

    Scenario: HTML coverage
        Given Coverage dependencies are configured
        When I run js-test-tool with HTML coverage
        Then An HTML coverage report is generated

    Scenario: Missing dependencies
        Given Coverage dependencies are missing
        When I run js-test-tool with XML and HTML coverage
        Then No coverage reports are generated
