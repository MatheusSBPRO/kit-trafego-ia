// Renderiza a cena quadro a quadro (30 fps, 1080x1920) e grava video_mudo.mp4 nesta pasta.
// Precisa de um servidor local servindo esta pasta na porta 8765 (o fazer_video.sh sobe sozinho).
//
//   node render.js <duração_s>              vídeo inteiro
//   node render.js <duração_s> 2,10.5,20    só prévias prev_<t>.jpg nesses segundos (rápido)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const ANGLE = process.platform === 'darwin' ? 'metal' : 'default';
(async () => {
  const browser = await chromium.launch({ args: [`--use-angle=${ANGLE}`, '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.log('ERRO NA PÁGINA:', e.message));
  page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE:', m.text()); });
  await page.goto('http://127.0.0.1:8765/cena.html');
  await page.waitForFunction(() => window.ready === true, null, { timeout: 60000 });
  require('fs').writeFileSync('sfx.json', JSON.stringify(await page.evaluate(() => window.SFX)));
  const fps = 30, dur = +process.argv[2] || 11, only = process.argv[3];
  if (only) {
    for (const t of only.split(',')) {
      await page.evaluate(t => window.renderAt(t), +t);
      await page.screenshot({ path: `prev_${t}.jpg`, type: 'jpeg', quality: 85 });
    }
    await browser.close(); return;
  }
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', 'video_mudo.mp4'], { stdio: ['pipe', 'inherit', 'inherit'] });
  const N = Math.round(dur * fps), t0 = Date.now();
  for (let i = 0; i < N; i++) {
    await page.evaluate(t => window.renderAt(t), i / fps);
    const b = await page.screenshot({ type: 'jpeg', quality: 94 });
    if (!ff.stdin.write(b)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 90 === 0) console.log('quadro', i, '/', N, ((Date.now() - t0) / 1000).toFixed(1) + 's');
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  console.log('ok', ((Date.now() - t0) / 1000).toFixed(1) + 's');
})();
