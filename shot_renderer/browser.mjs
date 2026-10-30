import {ensureBrowser} from '@remotion/renderer';
import {mkdir, writeFile} from 'node:fs/promises';
const chromeMode = process.env.SELF_MEDIA_SHOT_BROWSER ? 'chrome-for-testing' : 'headless-shell';
const browser = await ensureBrowser({browserExecutable: process.env.SELF_MEDIA_SHOT_BROWSER || null,chromeMode});
await mkdir('.runtime', {recursive:true});
await writeFile('.runtime/browser.json', JSON.stringify({...browser,chrome_mode:chromeMode}, null, 2));
console.log(JSON.stringify(browser));
