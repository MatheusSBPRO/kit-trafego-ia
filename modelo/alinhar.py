import json, re, difflib, unicodedata
rot = open('roteiro.txt', encoding='utf-8').read().split()
wh = json.load(open('whisper.json'))
norm = lambda s: re.sub(r'[^\w]', '', unicodedata.normalize('NFC', s.lower()))
a = [norm(t) for t in rot]; b = [norm(w[0]) for w in wh]
st = [None]*len(rot); en = [None]*len(rot)
sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        for k in range(i2-i1): st[i1+k], en[i1+k] = wh[j1+k][1], wh[j1+k][2]
    elif j2 > j1:  # replace: espalha o trecho do whisper pelas palavras do roteiro
        s0, e0, n = wh[j1][1], wh[j2-1][2], i2-i1
        for k in range(n): st[i1+k] = round(s0+(e0-s0)*k/n, 2); en[i1+k] = round(s0+(e0-s0)*(k+1)/n, 2)
for i in range(len(rot)):
    if st[i] is None: st[i] = en[i-1]; en[i] = en[i-1]
words = [[re.sub(r'[.,]', '', t)[:1].upper()+re.sub(r'[.,]', '', t)[1:], st[i]] for i, t in enumerate(rot)]
def mk(key, occ=1):
    c = 0
    for i, t in enumerate(rot):
        if norm(t) == norm(key):
            c += 1
            if c == occ: return st[i]
    raise SystemExit('marca não achada: '+key)
keys = {'km1':('três',1),'sabe':('sabe',1),'essa':('Essa',1),'impulsiona':('impulsiona',1),'brasil':('Brasil',1),'pisar':('pisar',1),
 'no':('No',1),'circulo':('círculo',1),'tipo':('Tipo',1),'so':('só',1),'dentro':('dentro',1),'botao':('botão',1),'perfil':('perfil',1),
 'whats':('WhatsApp',1),'mensagem':('mensagem',1),'entao':('Então',1),'ve':('vê',1),'clica':('clica',1),'conversando':('conversando',1),
 'conta':('conta',1),'custou':('custou',1),'vinte':('vinte',1),'manda':('Manda',2),'bairro':('bairro',1)}
MK = {k: mk(*v) for k, v in keys.items()}; MK['fim'] = en[-1]
open('tempos.js', 'w').write('window.WORDS=' + json.dumps(words, ensure_ascii=False) + ';\nwindow.MK=' + json.dumps(MK) + ';\n')
print(MK)
