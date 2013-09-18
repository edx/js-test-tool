define(["jasmine"], function(jasmine) {
  describe("the test runner can load failing tests", function() {
    it("should be a failing test", function() {
      expect(true).toBeFalsy();
    });
  });
});
