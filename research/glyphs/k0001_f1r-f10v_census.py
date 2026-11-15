"""Exploratory MS408 f1r-f10v index. EVA ASCII is NOT physical glyph evidence.
Usage: python k0001_census.py /path/to/voynich.pdf /path/to/ZL3b-n.txt
Requires existing PyMuPDF (fitz). Emits derived counts, never source text.
"""
import collections, hashlib, json, pathlib, re, sys
import fitz
PDF_HASH = 'd095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c'
EVA_HASH = 'bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'

def hash_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):
            h.update(chunk)
    return h.hexdigest()

def tally(s):
    flags=collections.Counter()
    for pattern,key in [(r'<![^>]*>','comments'), (r'<[^>]*>','angles'),
                        (r'\[[^\]]*\]','alternative_brackets'),
                        (r'\{[^}]*\}','uncertain_braces'),
                        (r'@\d+;','rare_sign_codes')]:
        flags[key]=len(re.findall(pattern,s))
        s=re.sub(pattern,'',s)
    flags['question_marks']=s.count('?')
    return collections.Counter(c for c in s if 'a'<=c<='z'),flags

def main():
    pdf_path,eva_path=map(pathlib.Path,sys.argv[1:3])
    assert hash_file(pdf_path)==PDF_HASH and hash_file(eva_path)==EVA_HASH
    doc=fitz.open(pdf_path)
    assert len(doc)==214
    folios=[f'f{i}{side}' for i in range(1,11) for side in 'rv']
    patt=re.compile(r'^<(f\d+[rv])\.(\d+),([^>]+)>\s+(.*)$')
    lines=collections.defaultdict(list)
    for s in eva_path.read_text(encoding='utf8').splitlines():
        m=patt.match(s)
        if m and m[1] in folios:
            lines[m[1]].append((int(m[2]),m[3],m[4]))
    total_lines=total_ascii=0
    for i,folio in enumerate(folios):
        page=i+4
        if not re.search(rf'(?m)^\s*{folio[1:]}\s*$',doc[page-1].get_text()):
            raise ValueError('PDF label mismatch '+folio)
        chars,flags=collections.Counter(),collections.Counter()
        seen=set()
        for number,kind,raw in lines[folio]:
            if number in seen: raise ValueError('Duplicate line '+folio)
            seen.add(number)
            c,f=tally(raw);chars.update(c);flags.update(f)
        total_lines+=len(lines[folio]);total_ascii+=sum(chars.values())
        print(json.dumps({'folio':folio,'pdf_page':page,'editorial_lines':len(lines[folio]),
          'unqualified_ascii_units':sum(chars.values()),'ascii_labels':''.join(sorted(chars)),
          'markup':dict(sorted(flags.items())),'image_alignment':'NOT_RUN',
          'physical_glyph_count':None}))
    if (total_lines,total_ascii)!=(268,8605):
        raise ValueError('Regression failure: '+str((total_lines,total_ascii)))

if __name__=='__main__': main()
