from pathlib import Path
import re,json,html
ROOT=Path(__file__).resolve().parent
def inline(s):
    tokens=[]
    def save(x):tokens.append(x);return '\x00'+str(len(tokens)-1)+'\x00'
    def link(m):
        label=re.sub(r'\\([\[\]\\])',r'\1',m[1])
        return save('<a href="'+html.escape(m[2],quote=True)+'"'+(' target="_blank" rel="noopener noreferrer"' if m[2].startswith('https:') else '')+'>'+html.escape(label)+'</a>')
    s=re.sub(r'\[((?:\\.|[^\]\\])+)\]\(([^)]+)\)',link,s)
    s=html.escape(s)
    s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'<em>\1</em>',s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\x00(\d+)\x00',lambda m:tokens[int(m[1])],s)
    return s
def render(text):
    out=[]; lines=text.splitlines();i=0;ul=False
    while i<len(lines):
        line=lines[i].strip();i+=1
        if not line:continue
        if re.fullmatch(r'<a id="[^"]+"></a>',line):out.append(line);continue
        if line in ('<details>','</details>'):out.append(line);continue
        summary=re.fullmatch(r'<summary>(.*?)</summary>',line)
        if summary:out.append('<summary>'+inline(summary[1])+'</summary>');continue
        if line.startswith('```'):
            code=[]
            while i<len(lines) and not lines[i].strip().startswith('```'):code.append(lines[i]);i+=1
            i+=1;out.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>');continue
        if line.startswith('|') and i<len(lines) and re.match(r'\|[ :|\-]+\|',lines[i].strip()):
            rows=[line];i+=1
            while i<len(lines) and lines[i].strip().startswith('|'):rows.append(lines[i].strip());i+=1
            out.append('<div class="tablewrap"><table>')
            for n,row in enumerate(rows):
                tag='th' if n==0 else 'td';out.append('<tr>'+''.join(f'<{tag}>{inline(c.strip())}</{tag}>' for c in row.strip('|').split('|'))+'</tr>')
            out.append('</table></div>');continue
        h=re.match(r'^(#{1,6})\s+(.+)',line)
        if h:out.append(f'<h{min(len(h[1])+1,6)}>{inline(h[2])}</h{min(len(h[1])+1,6)}>');continue
        if re.match(r'^[-*]\s',line):out.append('<p class="bullet">'+inline(line[2:].replace('[ ]','□').replace('[x]','☑'))+'</p>');continue
        if line.startswith('>'):out.append('<blockquote>'+inline(line[1:].strip())+'</blockquote>');continue
        if re.fullmatch('[-*]{3,}',line):out.append('<hr>');continue
        out.append('<p>'+inline(line)+'</p>')
    return '\n'.join(out)
def build():
    manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    data=[]
    for country in manifest['countries']:
        text=(ROOT/country['file']).read_text(encoding='utf-8')
        import hashlib
        country['sha256']=hashlib.sha256((ROOT/country['file']).read_bytes()).hexdigest()
        parts=text.split('<!-- SECTION -->')
        for n,part in enumerate(parts[1:]):
            h=re.search(r'^#\s+(.+)$',part,re.M)
            if not h:continue
            anchors=re.findall(r'<a id="([^"]+)"></a>',part)
            section_id=anchors[0] if anchors else country['code'].lower()+'-'+str(n)
            part=part.replace(f'<a id="{section_id}"></a>','',1)
            data.append({'id':section_id,'country':country['code'],'name':country['name'],'title':h[1],'html':render(part),'text':re.sub('<[^>]+>','',part),'file':country['file']})
    template=(ROOT/'reader-template.html').read_text(encoding='utf-8')
    template=template.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/'))
    template=template.replace('__ENTRIES__',str(sum(c['entries'] for c in manifest['countries'])))
    template=template.replace('__CHAPTERS__',str(sum(c['chapters'] for c in manifest['countries'])))
    (ROOT/'index.html').write_text(template,encoding='utf-8')
    (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Built',len(data),'sections; all four books embedded for offline reading.')
if __name__=='__main__':build()
