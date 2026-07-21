/**
 * This file verifies the pure parser functions in debate.ts.
 *
 * ⚠️  CURRENTLY UNRUNNABLE under `node --experimental-strip-types` because debate.ts
 * imports `./api` without a file extension, and Node's ESM loader requires the `.ts`
 * extension. TypeScript's bundler moduleResolution prevents adding the extension (would
 * cause tsconfig errors).
 *
 * Authoritative verification:
 * - Types: `npx tsc --noEmit` (this file is tsc-excluded; main codebase passes)
 * - Logic: code review of parseFields, extractTakeaway, ratingTone
 *
 * To make this check runnable in future:
 * 1. Add `allowImportingTsExtensions: true` to tsconfig.json (requires `noEmit: true`)
 * 2. Change debate.ts line 1 to `import { api } from "./api.ts";`
 */

import assert from "node:assert";
import { extractTakeaway, parseFields, ratingTone } from "./debate.ts";

const md = "**Rating**: Buy\n\n**Takeaway**: Confirmed constructive.\n\n**Conviction**: High";
assert.equal(extractTakeaway(md), "Confirmed constructive.");
assert.equal(extractTakeaway("no takeaway here"), null);

const f = parseFields(md);
assert.equal(f["Rating"], "Buy");
assert.equal(f["Takeaway"], "Confirmed constructive.");
assert.equal(f["Conviction"], "High");

assert.equal(ratingTone("Buy"), "ok");
assert.equal(ratingTone("Overweight"), "ok");
assert.equal(ratingTone("Hold"), "neutral");
assert.equal(ratingTone("Underweight"), "warn");
assert.equal(ratingTone("Sell"), "err");
console.log("debate.ts parsers OK");
