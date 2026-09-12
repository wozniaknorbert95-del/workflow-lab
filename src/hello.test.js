import { test } from "node:test";
import assert from "node:assert/strict";
import { greet } from "./hello.js";

test("greet default", () => {
  assert.equal(greet(), "hello workflow-lab");
});

test("greet trims whitespace", () => {
  assert.equal(greet("  lab  "), "hello lab");
});

test("greet rejects empty name", () => {
  assert.throws(() => greet("  "), TypeError);
});

test("greet rejects non-string name", () => {
  assert.throws(() => greet(123), TypeError);
});

test("greet Cloud", () => {
  assert.equal(greet("Cloud"), "hello Cloud");
});
