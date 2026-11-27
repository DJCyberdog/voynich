"""RC2-01: source-pinned Yale PDF wrapper isolation; not script recognition."""
import hashlib
import math

YALE_SHA256='d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c'
YALE_PAGES=214
DPI=200
POLICY='yale-pdf-image-envelope-v1'


def require(ok,message):
    if not ok:raise ValueError(message)


def close_box(a,b):
    return len(a)==len(b) and all(abs(x-y)<=.001 for x,y in zip(a,b))


def pixel_box(box,width,height):
    # Cover every pixel intersecting the original source image rectangle.
    s=DPI/72
    return [max(0,math.floor(box[0]*s)),max(0,math.floor(box[1]*s)),
            min(width,math.ceil(box[2]*s)),min(height,math.ceil(box[3]*s))]


def isolate_page(page,source_sha256):
    """Return full-page-coordinate raster and local audit metadata.

    Caller must have verified the source file's SHA256 before opening it.
    A known wrapper structural mismatch fails closed; no unverified cropping.
    """
    import fitz
    require(source_sha256==YALE_SHA256 and len(page.parent)==YALE_PAGES,
            'Unapproved Yale surface source')
    rect=page.rect
    require(page.rotation==0 and rect.x0==rect.y0==0,'Unsupported Yale page coordinates')
    number=page.number+1
    text=page.get_text().splitlines()
    require(text[:2]==['Yale University Library','Beinecke Rare Book and Manuscript Library']
            and text[-1]==f'Page {number} of {YALE_PAGES}','Yale wrapper text mismatch')
    log=page.get_bboxlog()
    images=[b for b in page.get_text('dict')['blocks'] if b['type']==1]
    excluded=[dict(kind=k,box_pt=list(b),reason='MODERN_PDF_WRAPPER') for k,b in log if k!='fill-image']
    record=dict(policy=POLICY,page=number,source_sha256=source_sha256,dpi=DPI,
                page_rect_pt=list(rect),excluded_objects=excluded,physical_mapping='UNVERIFIED',
                script_status='UNRESOLVED_WITHIN_IMAGE')
    with fitz.open() as isolated:
        q=isolated.new_page(width=rect.width,height=rect.height)
        if number==1:
            require(not images and log and all(k in ('fill-text','ignore-text') for k,_ in log),
                    'Unexpected content on catalog page')
            pix=q.get_pixmap(dpi=DPI,colorspace=fitz.csRGB,alpha=False)
            record.update(status='METADATA_ONLY',image_box_pt=None,pixel_box=None,
                          source_image_sha256=None,source_image_size=None,script_status='NOT_APPLICABLE',
                          excluded_area_px=pix.width*pix.height)
            return pix,record
        require(len(images)==1 and sum(k=='fill-image' for k,_ in log)==1,'Ambiguous Yale image layout')
        image=images[0];box=fitz.Rect(image['bbox']);t=image['transform']
        require(rect.contains(box) and not box.is_empty and t[0]>0 and t[3]>0
                and abs(t[1])+abs(t[2])<.001 and image.get('mask') is None,
                'Unsupported Yale image geometry')
        require(all(k in ('fill-image','fill-text','ignore-text','stroke-path') for k,_ in log),
                'Unclassified Yale page object')
        require(close_box(next(b for k,b in log if k=='fill-image'),box),'Image log geometry mismatch')
        # Never discard an overlapping text object without explicit review.
        require(all(not box.intersects(fitz.Rect(b)) for k,b in log if k in ('fill-text','ignore-text')),
                'Text overlaps manuscript image; independent review required')
        drawings=page.get_drawings()
        require(len(drawings)==2 and sum(k=='stroke-path' for k,_ in log)==2
                and all(d['type']=='s' and len(d['items'])==1 and d['items'][0][0]=='re'
                        and close_box(d['items'][0][1],box) for d in drawings),
                'Unclassified vector content; independent review required')
        # Reconstruct the image object only, in a disposable in-memory PDF.
        # Verify exact extracted image bytes, placement and original dimensions.
        q.insert_image(box,stream=image['image'],keep_proportion=False)
        copied=[b for b in q.get_text('dict')['blocks'] if b['type']==1]
        require(len(copied)==1 and copied[0]['image']==image['image']
                and close_box(copied[0]['bbox'],box) and close_box(copied[0]['transform'],t)
                and (copied[0]['width'],copied[0]['height'])==(image['width'],image['height']),
                'Image-only rendering changed source image or geometry')
        require(len(q.get_bboxlog())==1 and q.get_bboxlog()[0][0]=='fill-image',
                'Wrapper object survived isolation')
        pix=q.get_pixmap(dpi=DPI,colorspace=fitz.csRGB,alpha=False)
        bounds=pixel_box(box,pix.width,pix.height)
        require(bounds==pixel_box(copied[0]['bbox'],pix.width,pix.height),'Raster envelope mismatch')
        record.update(status='IMAGE_ENVELOPE',image_box_pt=list(box),pixel_box=bounds,
                      source_image_sha256=hashlib.sha256(image['image']).hexdigest(),
                      source_image_size=[image['width'],image['height']],
                      excluded_area_px=pix.width*pix.height-(bounds[2]-bounds[0])*(bounds[3]-bounds[1]))
        return pix,record


def inventory(pdf,expected_sha256):
    """All 214 pages, no inferred folio mapping and no persisted manuscript pixels."""
    import fitz
    from pathlib import Path
    with Path(pdf).open('rb') as f:
        require(hashlib.file_digest(f,'sha256').hexdigest()==expected_sha256==YALE_SHA256,
                'Yale PDF SHA256 mismatch')
    rows=[]
    with fitz.open(pdf) as doc:
        require(len(doc)==YALE_PAGES,'Yale PDF page count mismatch')
        for page in doc:
            pix,row=isolate_page(page,expected_sha256)
            row['page_dimensions']=[pix.width,pix.height]
            rows.append(row)
    return dict(schema=1,policy=POLICY,source_sha256=expected_sha256,renderer=fitz.VersionBind,
                page_count=len(rows),pages=rows,scientific_status='UNADJUDICATED')
