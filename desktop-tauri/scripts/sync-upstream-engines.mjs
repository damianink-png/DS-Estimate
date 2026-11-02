/** Fetches pinned upstream source trees for local integration development.
 * No source is silently embedded into a public installer.
 * Run: node scripts/sync-upstream-engines.mjs
 */
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const engines = [
  { name:'kwantflow', repo:'muicci/kwantflow', license:'GPL-3.0', files:['LICENSE','package.json','src/lib/services/db.estimate.test.ts','src/lib/services/db.ts'] },
  { name:'deepnest', repo:'deepnest-next/deepnest', license:'MIT (check file-level GPL)', files:['LICENSE','package.json','main/deepnest.js','main/background.js','main/util/geometryutil.js'] },
];
const root = resolve('vendor-engines');
for (const engine of engines) {
  const metadata = await fetch(`https://api.github.com/repos/${engine.repo}/commits/HEAD`);
  if (!metadata.ok) throw new Error(`${engine.repo}: HTTP ${metadata.status}`);
  const sha = (await metadata.json()).sha;
  const target = resolve(root, engine.name);
  await mkdir(target, { recursive:true });
  for (const file of engine.files) {
    const url = `https://raw.githubusercontent.com/${engine.repo}/${sha}/${file}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
    const dest = resolve(target, file);
    await mkdir(resolve(dest, '..'), { recursive:true });
    await writeFile(dest, await response.text());
  }
  await writeFile(resolve(target,'UPSTREAM.json'),JSON.stringify({repository:engine.repo,revision:sha,license:engine.license,files:engine.files},null,2));
  console.log(`Fetched ${engine.repo}@${sha}`);
}
