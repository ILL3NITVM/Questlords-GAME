"""Conservative pixel operations; no landmarks, geometry editing or generation."""
from __future__ import annotations

import io
import math
import warnings

import imagehash
import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFilter, ImageOps

PRESETS = {
    'x': (1600, 900), 'instagram-square': (1080, 1080),
    'instagram-portrait': (1080, 1350), 'story': (1080, 1920),
    'profile': (400, 400), 'banner': (1500, 500), 'reference-sheet': (2048, 2048),
}
POLISH_DEFAULTS = dict(denoise=0.0, sharpen=0.20, exposure=0.0,
                       wb=[1.0, 1.0, 1.0], contrast=0.0,
                       shadows=0.0, highlights=0.0, max_side=0, format='png', quality=95)


def decode(data):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as raw:
                if getattr(raw, 'n_frames', 1) != 1:
                    raise ValueError('Animated/multipage images require explicit frame selection')
                raw.load()
                return ImageOps.exif_transpose(raw).copy()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError('Image exceeds the safe decode limit: {}'.format(exc))


def inspect_bytes(data):
    image = decode(data)
    result = metrics(image)
    result.update(width=image.width, height=image.height, mode=image.mode,
                  phash=str(imagehash.phash(image)), dhash=str(imagehash.dhash(image)))
    center = ImageOps.fit(image, (256, 256))
    result['center_hash'] = str(imagehash.phash(center))
    return result


def metrics(image):
    small = image.convert('RGB')
    small.thumbnail((512,512), Image.Resampling.LANCZOS)
    if min(small.size)<4:
        small=small.resize((max(4,small.width),max(4,small.height)))
    a = np.asarray(small, dtype=np.float32)/255.0
    lum = a @ np.array([0.2126,0.7152,0.0722], dtype=np.float32)
    if min(lum.shape) >= 3:
        lap = -4*lum[1:-1,1:-1]+lum[:-2,1:-1]+lum[2:,1:-1]+lum[1:-1,:-2]+lum[1:-1,2:]
        sharpness = float(lap.var()*255**2)
        edge = np.abs(np.diff(lum, axis=1, prepend=lum[:,:1])) + np.abs(np.diff(lum, axis=0, prepend=lum[:1,:]))
    else:
        sharpness, edge = 0.0, np.zeros_like(lum)
    grid = [float(cell.mean()) for rows in np.array_split(edge,4,axis=0)
            for cell in np.array_split(rows,4,axis=1)]
    norm = math.sqrt(sum(x*x for x in grid))
    grid = [v/max(norm,1e-8) for v in grid]
    return {'sharpness':sharpness,'mean_luminance':float(lum.mean()),
            'shadow_clip':float((lum<0.015).mean()),'highlight_clip':float((lum>0.985).mean()),
            'mean_rgb':a.mean(axis=(0,1)).tolist(),'composition_grid':grid,
            'metrics_basis':'512px thumbnail; texture/exposure evidence, not beauty or identity'}


def valid_box(box):
    if not isinstance(box,(list,tuple)) or len(box)!=4:
        raise ValueError('ROI must be [left,top,right,bottom], normalized 0..1')
    if not all(isinstance(x,(float,int)) and math.isfinite(x) and 0<=x<=1 for x in box):
        raise ValueError('ROI coordinates must be finite and inside 0..1')
    if box[0]>=box[2] or box[1]>=box[3]:
        raise ValueError('ROI must have positive area')
    return list(box)


def hair_evidence(image, roi):
    valid_box(roi)
    box = (math.floor(roi[0]*image.width),math.floor(roi[1]*image.height),
           math.ceil(roi[2]*image.width),math.ceil(roi[3]*image.height))
    crop = image.crop(box).convert('HSV')
    hsv = np.asarray(crop, dtype=np.float32)
    hue = hsv[:,:,0]*360/255
    green = (hue>=45)&(hue<=105)&(hsv[:,:,1]>65)&(hsv[:,:,2]>45)
    return {'green_fraction':float(green.mean()),
            'median_green_hue':float(np.median(hue[green])) if green.any() else None,
            'basis':'color evidence inside manually annotated hair ROI; not hair detection'}


def normalized_color(image):
    profile = image.info.get('icc_profile')
    if profile:
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(profile))
            dst = ImageCms.createProfile('sRGB')
            image = ImageCms.profileToProfile(image,src,dst,outputMode='RGB')
        except Exception as exc:
            raise ValueError('Cannot safely convert embedded ICC profile: {}'.format(exc))
    else:
        image = image.convert('RGB')
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    return image, srgb


def safe_metadata(image, size):
    # Preserve useful authorship/capture fields, never stale dimensions, thumbnails or GPS.
    keep = {271,272,305,306,315,33432}
    capture = {33434,33437,34855,36867,36868,37386,42036}
    exif = Image.Exif()
    source = image.getexif()
    for key in keep:
        if key in source:
            exif[key] = source[key]
    nested=source.get_ifd(34665) if 34665 in source else {}
    details={key:nested.get(key,source.get(key)) for key in capture if key in nested or key in source}
    if exif or details:
        exif[274]=1
        exif[256],exif[257]=size
        details[40962],details[40963]=size
        exif[34665]=details
    return exif.tobytes() if exif else b''


def validate_polish(options):
    o = dict(POLISH_DEFAULTS, **options)
    bounds = {'denoise':(0,0.3),'sharpen':(0,0.6),'exposure':(-1,1),
              'contrast':(0,0.15),'shadows':(0,0.25),'highlights':(0,0.25)}
    for key,(low,high) in bounds.items():
        if not math.isfinite(o[key]) or not low<=o[key]<=high:
            raise ValueError('{} must be within {}..{}'.format(key,low,high))
    if len(o['wb'])!=3 or not all(math.isfinite(v) and 0.9<=v<=1.1 for v in o['wb']):
        raise ValueError('White balance requires three RGB gains within 0.9..1.1')
    if not isinstance(o['max_side'],int) or not 0<=o['max_side']<=16384:
        raise ValueError('max-side must be an integer 0..16384; 0 means no resize')
    if o['format'] not in ('png','jpeg') or not 90<=o['quality']<=100:
        raise ValueError('Use PNG or JPEG quality 90..100')
    return o


def polish_image(image, options):
    o = validate_polish(options)
    if image.mode not in ('RGB','RGBA','L','LA','P'):
        raise ValueError('Polish supports 8-bit display images, not RAW/HDR/high-bit masters')
    original = image.copy()
    alpha = image.convert('RGBA').getchannel('A') if image.mode in ('RGBA','LA','P') else None
    image, profile = normalized_color(image.convert('RGB') if alpha else image)
    if o['denoise']:
        image = Image.blend(image,image.filter(ImageFilter.MedianFilter(3)),o['denoise'])
    if o['exposure'] or o['wb']!=[1.0,1.0,1.0] or o['shadows'] or o['highlights']:
        a = np.asarray(image,dtype=np.float32)/255
        linear = np.where(a<=0.04045,a/12.92,((a+0.055)/1.055)**2.4)
        linear *= (2**o['exposure'])*np.array(o['wb'],dtype=np.float32)
        a = np.where(linear<=0.0031308,linear*12.92,1.055*np.maximum(linear,0)**(1/2.4)-0.055)
        lum = a @ np.array([0.2126,0.7152,0.0722],dtype=np.float32)
        delta = o['shadows']*(1-lum)**2*lum - o['highlights']*lum**2*(1-lum)
        a += delta[:,:,None]
        image = Image.fromarray(np.clip(np.rint(a*255),0,255).astype('uint8'),'RGB')
    if o['contrast']:
        blur = np.asarray(image.filter(ImageFilter.GaussianBlur(10)),dtype=np.float32)
        a = np.asarray(image,dtype=np.float32)
        image = Image.fromarray(np.clip(np.rint(a+(a-blur)*o['contrast']),0,255).astype('uint8'),'RGB')
    if o['sharpen']:
        image = image.filter(ImageFilter.UnsharpMask(radius=0.7,percent=round(o['sharpen']*100),threshold=3))
    if o['max_side']:
        image.thumbnail((o['max_side'],o['max_side']),Image.Resampling.LANCZOS)
    if alpha is not None:
        alpha = alpha.resize(image.size,Image.Resampling.LANCZOS)
        image.putalpha(alpha)
    metadata = {'icc_profile':profile,'exif':safe_metadata(original,image.size),'quality':o['quality']}
    return image, metadata


def encode(image, suffix, metadata):
    stream = io.BytesIO()
    kwargs = {k:metadata[k] for k in ('icc_profile','exif') if metadata.get(k)}
    if suffix.lower() in ('.jpg','.jpeg'):
        if image.mode!='RGB':
            rgba=image.convert('RGBA')
            bg=Image.new('RGBA',image.size,(248,248,248,255))
            image=Image.alpha_composite(bg,rgba).convert('RGB')
        image.save(stream,format='JPEG',quality=metadata.get('quality',95),subsampling=0,optimize=True,**kwargs)
    else:
        image.save(stream,format='PNG',**kwargs)
    data=stream.getvalue()
    checked=decode(data)
    if checked.size!=image.size:
        raise ValueError('Encoded image verification failed')
    return data


def tile(image,size,background=(244,245,246)):
    canvas=Image.new('RGB',size,background)
    fitted=ImageOps.contain(image.convert('RGB'),size,Image.Resampling.LANCZOS)
    canvas.paste(fitted,((size[0]-fitted.width)//2,(size[1]-fitted.height)//2))
    return canvas


def comparison(before,after):
    canvas=Image.new('RGB',(816,640),(244,245,246))
    canvas.paste(tile(before,(400,600)),(0,32))
    canvas.paste(tile(after,(400,600)),(416,32))
    draw=ImageDraw.Draw(canvas)
    draw.text((12,10),'BEFORE',fill=(35,35,35))
    draw.text((428,10),'AFTER',fill=(35,35,35))
    return canvas


def safe_export(image,preset,fit='contain',box=None):
    if preset not in PRESETS or fit not in ('contain','crop'):
        raise ValueError('Unknown export preset or fit mode')
    size=PRESETS[preset]
    image, profile=normalized_color(image)
    detail={'preset':preset,'size':size,'requested_fit':fit,'fit':'contain','crop_box':None,
            'subject_basis':'entire image protected' if box is None else 'manual subject ROI',
            'metadata':'EXIF/GPS removed; normalized sRGB ICC retained'}
    working=image
    if fit=='crop':
        if box is None:
            raise ValueError('Cropping requires a reviewed subject ROI; use --box or annotate subject_roi')
        valid_box(box)
        w,h=image.size
        ratio=size[0]/size[1]
        cw,ch=(w,w/ratio) if w/h<ratio else (h*ratio,h)
        left,top,right,bottom=[v*(w if i%2==0 else h) for i,v in enumerate(box)]
        margin=0.025*min(w,h)
        left,top=max(0,left-margin),max(0,top-margin)
        right,bottom=min(w,right+margin),min(h,bottom+margin)
        if right-left<=cw and bottom-top<=ch:
            xlo,xhi=max(0,right-cw),min(left,w-cw)
            ylo,yhi=max(0,bottom-ch),min(top,h-ch)
            x=min(max((left+right-cw)/2,xlo),xhi)
            y=min(max((top+bottom-ch)/2,ylo),yhi)
            crop=(max(0,math.floor(x)),max(0,math.floor(y)),min(w,math.ceil(x+cw)),min(h,math.ceil(y+ch)))
            working=image.crop(crop)
            detail.update(fit='crop',crop_box=crop)
        else:
            detail['reason']='Target ratio would clip protected subject; padded instead'
    # Profile padding protects circular display; banner keeps subject clear of vertical trim.
    inset=0.15 if preset=='profile' else 0.12 if preset=='banner' else 0.025
    inner=(round(size[0]*(1-2*inset)),round(size[1]*(1-2*inset)))
    fitted=ImageOps.contain(working,inner,Image.Resampling.LANCZOS)
    result=Image.new('RGB',size,(244,245,246))
    x,y=(size[0]-fitted.width)//2,(size[1]-fitted.height)//2
    result.paste(fitted,(x,y))
    detail['placement']=[x,y,x+fitted.width,y+fitted.height]
    detail['safe_padding']=inset
    detail['upscaled']=fitted.width>working.width or fitted.height>working.height
    return result, {'icc_profile':profile,'quality':95}, detail
