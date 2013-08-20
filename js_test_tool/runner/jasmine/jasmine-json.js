/* Jasmine JSON reporter
 * 
 * Encodes test results in JSON format and
 * includes them in a <div> tag on the page.
 */

/*
 * Public Jasmine interface methods.
 */
jasmine.JsonReporter = function(divId, suiteName) {
    // Create a JsonReporter
    // `divId` is the CSS ID selector in which to output JSON
    // test results.
    // `suiteName` is the unique suite name, used to report back
    // coverage information to the server (if JSCover is configured).
    this._divId = divId;
    this._suiteName = suiteName;

    // Create a list to hold test results
    this._testResultList = [];
};

jasmine.JsonReporter.prototype.reportSpecResults = function(spec) {
    // Record the test result for a test spec
    // `spec` is the Jasmine spec
    
    // Retrieve information from the spec
    var testGroup = spec.suite.getFullName();
    var testName = spec.description;
    var testStatus = this._getTestStatus(spec);
    var testDetail = this._getTestDetail(spec);

    // Create a Result object to hold the information
    var result = new jasmine.JsonReporter.Result(testGroup, testName,
                                                 testStatus, testDetail);

    // Add the test result to our list of results
    this._testResultList.push(result);
};

jasmine.JsonReporter.prototype.reportRunnerResults = function(runner) {
    // Output the results as a JSON-encoded string to the
    // contents of a <div> tag.
    // If the <div> with the configured ID could not be found,
    // throws an exception.
    var divElement = document.getElementById(this._divId);
    
    if (divElement) {
        // Trigger JSCover to POST coverage data to server
        // at /jscoverage-store/{suite_num}
        // where {suite_num} is the argument to jscoverage_report.
        if (window.jscoverage_report) {
            try {
                jscoverage_report(this._suiteName)
            }
            catch(err) {
                window.js_test_tool.reportError(err)
            }
        }

        // Write the results to the specified div
        divElement.innerHTML = this._jsonResults();

        // Change the class to "done" to indicate that
        // all results are written.
        divElement.className = "done";
    }

    // If we could not find the <div>, throw an error.
    else {
        var msg = "No element with CSS selector ID '" + this._divId + "' found";
        window.js_test_tool.reportError(new Error(msg));
    }
};

jasmine.JsonReporter.prototype.specFilter = function(spec) {
    // Do not filter specs -- instead, always show everything
    return true;
};


/*
 * Private helper methods.
 */
jasmine.JsonReporter.prototype._getTestStatus = function(spec) {
    // Given `spec` (a Jasmine spec), return a string
    // indicating the result of the test.
    //
    // Will return either:
    //
    // * "pass"
    // * "fail"
    // * "error"
    // * "skip"
    //
    var specResults = spec.results();

    if (specResults.passed) {
        return specResults.passed() ? "pass" : "fail";
    }

    else if (results.skipped) {
        return "skip";
    }

    // Error in this case means an error in the test runner,
    // since Jasmine treats tests with errors as failures.
    else {
        return "error";
    }
};

jasmine.JsonReporter.prototype._getTestDetail = function(spec) {
    // Given `spec` (a Jasmine spec), return a string
    // describing any test failures that occurred.
    var resultItems = spec.results().getItems();
    var detailList = [];

    // Each spec can have multiple results, one for each
    // assertion ("expectation" in Jasmine terms) that the
    // test performs.
    for (var i = 0; i < resultItems.length; i++) {

        var result = resultItems[i];

        // If this is a failed expectation, store the message
        if (result.type == "expect" && result.passed && !result.passed()) {
            detailList.push(result.message)
        }
    }

    // Concatenate the failure messages
    return detailList.join('\n');
};

jasmine.JsonReporter.prototype._jsonResults = function() {
    // Return a JSON-encoded string representing the list
    // of test results.
    // If no results collected yet, returns a JSON representation
    // of an empty list.
    return JSON.stringify(this._testResultList);
};

/* We do not use most of the reporter functions Jasmine defines. */
jasmine.JsonReporter.prototype.reportRunnerStarting = function() {};
jasmine.JsonReporter.prototype.reportSpectStarting = function() {};
jasmine.JsonReporter.prototype.reportSuiteResults = function(suite) {};


/*
 * Result
 */
jasmine.JsonReporter.Result = function(testGroup, testName, 
                                       testStatus, testDetail) {
    // Store a test result
    // `testGroup` is the name of the group of test cases
    // `testName` is the name of the specific test case
    // `testStatus` is either "pass", "fail", "error", or "skip"
    // `testDetail` is a string describing the test result
    this.testGroup = escape(testGroup);
    this.testName = escape(testName);
    this.testStatus = escape(testStatus);
    this.testDetail = escape(testDetail);
};
