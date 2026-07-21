import assert from "node:assert";
import { timeAgo, absoluteTime } from "./time.ts";

const now = Date.now();
assert.equal(timeAgo(new Date(now + 5000).toISOString()), "just now");
assert.equal(timeAgo(new Date(now - 30 * 60_000).toISOString()), "30m ago");
assert.equal(timeAgo(new Date(now - 3 * 3_600_000).toISOString()), "3h ago");
assert.equal(timeAgo(new Date(now - 2 * 86_400_000).toISOString()), "2d ago");
assert.ok(absoluteTime("2026-06-20T09:00:00.000Z").length > 0);
console.log("time.ts OK");
