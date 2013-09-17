define(["jasmine", "src/main"], function(jasmine, main) {
  describe("the main module", function() {
    it("should be a string", function() {
      expect(main).toEqual("main module");
    });
    it("jamine should be defined", function() {
      expect(jasmine).toBeDefined();
    });
  });
});
