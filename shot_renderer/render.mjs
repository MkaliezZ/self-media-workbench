// Local, headless renderer. All inputs are frozen by the Python API.
import {bundle} from '@remotion/bundler';
import {selectComposition, renderMedia} from '@remotion/renderer';
import {readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
const [jobDir,browserExecutable,chromeMode='headless-shell'] = process.argv.slice(2);
if(!jobDir) throw Error('Expected frozen job directory');
const inputProps=JSON.parse(await readFile(path.join(jobDir,'props.json'),'utf8'));
const serveUrl=await bundle({entryPoint:path.resolve(jobDir,'src/index.tsx'),
  publicDir:path.join(jobDir,'public'),outDir:path.join(jobDir,'bundle'),
  webpackOverride:config=>({...config,resolve:{...config.resolve,modules:[path.resolve('node_modules'),'node_modules']}})});
const chromiumOptions={gl:'angle'};
const composition=await selectComposition({serveUrl,id:'WorkbenchShot',inputProps,browserExecutable,chromiumOptions,chromeMode});
await renderMedia({serveUrl,composition,inputProps,codec:'h264',pixelFormat:'yuv420p',
  outputLocation:path.join(jobDir,'shot.mp4'),browserExecutable,chromiumOptions,chromeMode,
  concurrency:1,timeoutInMilliseconds:120000});
await writeFile(path.join(jobDir,'render-info.json'),JSON.stringify({
  composition:{width:composition.width,height:composition.height,fps:composition.fps,durationInFrames:composition.durationInFrames},
  codec:'h264',pixelFormat:'yuv420p',audio:'none; mix voice/music in native timeline',
  remotion:'4.0.484',node:process.version},null,2));
