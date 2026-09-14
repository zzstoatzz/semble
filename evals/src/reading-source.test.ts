import assert from "node:assert/strict";
import test from "node:test";
import { publicReadingAddress, readRecommendationSource } from "./reading-source.js";

test("source reader rejects private and local destinations", async () => {
  for (const address of ["127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.1", "169.254.169.254", "::1", "::ffff:127.0.0.1", "fc00::1"]) assert.equal(publicReadingAddress(address), false);
  assert.equal(publicReadingAddress("1.1.1.1"), true);
  await assert.rejects(readRecommendationSource("file:///etc/passwd"), /HTTPS/);
  await assert.rejects(readRecommendationSource("https://user:password@example.org/"), /HTTPS/);
});
