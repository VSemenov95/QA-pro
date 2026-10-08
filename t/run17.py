# Артефакт: вкладка ТМС → «Скачать загрузчик (.zip)» → архив через downloads
import asyncio, os, base64, io, zipfile
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'shot17.py')).read().split('async def main')[0])
EXT_SRC=os.path.join(os.path.dirname(D),'uploader','qa-pro-sfera-uploader')
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':1000})
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock.js'))
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://app.test/'); await pg.wait_for_timeout(1300)
        await pg.click('#btn-settings'); await pg.click('#settab-tms'); await pg.wait_for_timeout(1500)
        print('Z1 banner:', (await pg.inner_text('#tms-body .banner')).replace('\n',' ')[:160])
        await pg.click('#tms-body [data-act=sfera-zip]'); await pg.wait_for_timeout(500)
        print('Z2 dl:', await pg.evaluate('window.__dl'))
        b64 = await pg.evaluate("window.__dlBlob.arrayBuffer().then(a => { let s=''; new Uint8Array(a).forEach(x => s += String.fromCharCode(x)); return btoa(s); })")
        zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(b64)))
        print('Z3 testzip:', zf.testzip(), '| names:', zf.namelist())
        print('Z3 identical:', all(zf.read('qa-pro-sfera-uploader/'+f) == open(os.path.join(EXT_SRC,f),'rb').read() for f in os.listdir(EXT_SRC)))
        print('ERRORS', errs); await b.close()
asyncio.run(main())
