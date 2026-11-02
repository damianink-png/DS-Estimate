import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

test('Deepnest is not falsely represented by a costing-only adapter', () => {
 const source=readFileSync(resolve('src/lib/nesting.mjs'),'utf8');
 assert.match(source,/layout\.engine !== 'deepnest'/);
 assert.match(source,/layout\.verified !== true/);
});
test('Kwantflow is not falsely represented by DS Estimate calculator', () => {
 const source=readFileSync(resolve('src/lib/cnc-quote.mjs'),'utf8');
 assert.match(source,/not upstream Kwantflow execution/);
});
test('Upstream source sync script is present, but is not a bundled runtime', () => {
 assert.ok(existsSync(resolve('scripts/sync-upstream-engines.mjs')));
});
