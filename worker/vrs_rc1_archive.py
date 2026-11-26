"""Byte-preserving local archive inspection; no conversion, extraction or scientific weighting."""
import collections
import re
import stat
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from vrs_portable import need,digest

MAX_RAW=64*1024**2
MAX_ZIP=32*1024**2
ARCHIVE_SCHEMES=('EvaT','Eva-','v101','FSG-','Curr','v101-legacy','EVT-EVA')
HEADER=re.compile(rb'#=IVTFF ([A-Za-z0-9-]+) 2\.0 ([MD])\s*([0-9]+)\s*')
LOCUS=re.compile(rb'<(f(?:\d+[rv]\d*|Ros)\.\d+),([^<>]+)>\s*(.*)')
PAGE=re.compile(rb'<f(?:\d+[rv]\d*|Ros)>\s*.*')

def checked_zip(path):
    """Return opened bounded archive. Never extract, follow links or load macros."""
    z=zipfile.ZipFile(path)
    try:
        seen=set();total=0;files={}
        for i in z.infolist():
            name=i.filename;parts=name.rstrip('/').split('/')
            need(name and not name.startswith('/') and '\\' not in name and ':' not in name and all(p not in ('','.','..') for p in parts),'Unsafe ZIP path')
            need(name.casefold() not in seen and len(seen)<2048,'Duplicate ZIP path or quota');seen.add(name.casefold())
            need(not stat.S_ISLNK(i.external_attr>>16) and not i.flag_bits&1,'Linked or encrypted ZIP entry')
            total+=i.file_size;need(total<=MAX_ZIP and i.file_size<=MAX_ZIP,'Expanded archive quota')
            if not i.is_dir():files[name]=i
        need(files,'Empty archive')
        return z,files
    except BaseException:z.close();raise

def line_counts(raw,pattern,page_pattern=None):
    rows=collections.Counter();pages=0;comments=0;blank=0;bad=0;nonascii=0
    for line in raw.splitlines():
        if not line.strip():blank+=1;continue
        if line.startswith(b'#'):comments+=1;continue
        m=pattern.fullmatch(line)
        if m:
            rows[m.group(1)]+=1;nonascii+=any(b>=128 for b in line)
        elif page_pattern and page_pattern.fullmatch(line):pages+=1
        else:bad+=1
    need(not bad and rows,'Unsupported archive record syntax')
    return dict(records=sum(rows.values()),unique_loci=len(rows),duplicate_records=sum(n-1 for n in rows.values()),page_headers=pages,comment_lines=comments,blank_lines=blank,non_ascii_records=nonascii)

def inspect_transcription(path,scheme):
    path=Path(path);need(0<path.stat().st_size<=MAX_RAW,'Archive source quota')
    raw=path.read_bytes();need(len(raw)<=MAX_RAW,'Archive source quota')
    if scheme=='v101-legacy':
        result=line_counts(raw,re.compile(rb'<([^<>]+)>(.*)'))
        return dict(format='legacy-v101',scheme=scheme,encoding='raw bytes; no decoded glyph assertion',runtime_eligible=False,**result)
    if scheme=='EVT-EVA':return inspect_evt(path)
    first,_,rest=raw.partition(b'\n');head=HEADER.fullmatch(first.rstrip(b'\r'))
    need(head is not None and head.group(1).decode('ascii')==scheme,'Archive IVTFF header mismatch')
    result=line_counts(rest,LOCUS,PAGE)
    return dict(format='IVTFF 2.0',scheme=scheme,header=first.rstrip(b'\r').decode('ascii'),mode=head.group(2).decode('ascii'),runtime_eligible=False,**result)

def inspect_evt(path):
    z,files=checked_zip(path)
    with z:
        need(len(files)==1,'Expected one historical EVT member')
        name=next(iter(files));need(name.lower().endswith('.evt'),'Expected EVT member')
        raw=z.read(name)
    import hashlib
    rows=collections.Counter();loci=set();pages=set();pairs=set();headers=0;comments=0;nonascii=0
    for line in raw.splitlines():
        if not line.strip():continue
        if line.startswith(b'#'):comments+=1;continue
        m=re.fullmatch(rb'<([^;<>]+);([A-Za-z0-9]+)>\s*(.*)',line)
        if m:
            locus,code=m.group(1,2);need((locus,code) not in pairs,'Duplicate EVT locus/variant pair')
            pairs.add((locus,code));loci.add(locus);pages.add(locus.split(b'.')[0]);rows[code.decode('ascii')]+=1;nonascii+=any(b>=128 for b in line)
        elif re.fullmatch(rb'<[^;<>]+>\s*.*',line):headers+=1
        else:raise ValueError('Unsupported EVT record')
    need(rows,'No EVT records')
    return dict(format='EVT interlinear',scheme='EVT-EVA',member=name,member_sha256=hashlib.sha256(raw).hexdigest(),records=sum(rows.values()),unique_loci=len(loci),unique_locus_variant_pairs=len(pairs),page_identifiers=len(pages),header_records=headers,comment_lines=comments,variant_counts=dict(sorted(rows.items())),non_ascii_records=nonascii,runtime_eligible=False,independent_sources_established=False)

def xml(z,name):
    raw=z.read(name);need(b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper(),'XML declaration refused')
    return ET.fromstring(raw)

def inspect_document(path,role):
    z,files=checked_zip(path)
    with z:
        need('[Content_Types].xml' in files,'Not an OOXML container')
        need(not any('vbaproject' in p.lower() or 'embeddings/' in p.lower() for p in files),'Active/embedded content refused')
        if role=='metadata_workbook':
            root=xml(z,'xl/workbook.xml')
            ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
            sheets=[s.attrib['name'] for s in root.iter(ns+'sheet')]
            need(sheets and len(sheets)<=100,'Invalid workbook sheets')
            return dict(format='XLSX',sheets=sheets,runtime_eligible=False,semantic_mapping_verified=False)
        root=xml(z,'word/document.xml');ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        need(root.tag==ns+'document','Invalid DOCX document')
        return dict(format='DOCX',paragraphs=sum(1 for _ in root.iter(ns+'p')),runtime_eligible=False,notation_verified=False)
