p1=open('app1.js',encoding='utf-8').read(); p2=open('app2.js',encoding='utf-8').read(); p3=open('app3.js',encoding='utf-8').read()
# Правила, шаблоны и база знаний хранятся в .md-файлах: здесь они подставляются в исходники вместо заглушек /*@md:…*/ и /*@tpl*/
import re as _re, json as _json0, os as _os
def _md(path):
    return open(path, encoding='utf-8').read().rstrip('\n')
def _tpl():
    out = {}
    for t in ['api', 'ui', 'e2e']:
        s = open(f'templates/{t}.md', encoding='utf-8').read()
        idp = _re.search(r'^idPrefix: (.*)$', s, _re.M).group(1)
        rules = s.split('## Правила\n\n', 1)[1].split('\n\n## Образец', 1)[0]
        ex = s.split('```json\n', 1)[1].rsplit('\n```', 1)[0]
        out[t] = {'idPrefix': idp, 'rules': rules, 'example': ex}
    return out
p1 = p1.replace('/*@tpl*/null', _json0.dumps(_tpl(), ensure_ascii=False, indent=2))
p2 = _re.sub(r"/\*@md:([^*]+)\*/''", lambda m: _json0.dumps(_md(m.group(1)), ensure_ascii=False), p2)
assert '/*@md:' not in p2 and '/*@tpl*/' not in p1
def _prompts():
    out = {}
    for f in sorted(_os.listdir('prompts')):
        if f.endswith('.md'):
            out[f[:-3]] = open(_os.path.join('prompts', f), encoding='utf-8').read()
    return out
p2 = p2.replace('/*@prompts*/null', _json0.dumps(_prompts(), ensure_ascii=False, indent=1))
assert '/*@prompts*/' not in p2
# источник контекста (папка, git, GitHub) — отдельный файл, вставляется в конец второй части
p2 = p2.replace('/*__CTX__*/', open('appctx.js', encoding='utf-8').read())
assert '/*__CTX__*/' not in p2
import os, json as _json
_up='uploader/qa-pro-sfera-uploader'
_files={f: open(os.path.join(_up,f),encoding='utf-8').read() for f in sorted(os.listdir(_up)) if os.path.isfile(os.path.join(_up,f))}
p3=p3.replace('/*__UPLOADER__*/null', _json.dumps(_files, ensure_ascii=False).replace('</', '<\\/'))
_br='bridge/qa-pro-bridge'
_bfiles={os.path.relpath(os.path.join(r,f),_br).replace(os.sep,'/'): open(os.path.join(r,f),encoding='utf-8').read() for r,_,fs in os.walk(_br) for f in sorted(fs)}
p3=p3.replace('/*__BRIDGE__*/null', _json.dumps(_bfiles, ensure_ascii=False).replace('</', '<\\/'))
js=p1.replace('/*__PART2__*/', p2.replace('/*__PART3__*/', p3))
open('app.js','w',encoding='utf-8').write(js)
page=open('agent-test-cases.html',encoding='utf-8').read().replace('/*__APP__*/', js)
open('tc-agent.html','w',encoding='utf-8').write(page)
reset=':root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#fafafa}img{max-width:100%}[hidden]{display:none!important}'
standalone='<!doctype html>\n<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>'+reset+'</style></head><body>\n'+page+'\n</body></html>\n'
open('qa-pro.html','w',encoding='utf-8').write(standalone)
print(len(page), len(standalone))
