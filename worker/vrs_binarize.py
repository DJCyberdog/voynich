"""Experimental RC2-02b/c: aligned binary hypotheses, not ink ground truth."""
import numpy as np
from PIL import Image, ImageFilter

POLICY = 'rc2-native-mask-hypotheses-v1'


def array(image):
    a = np.asarray(image)
    if a.dtype != np.uint8 or a.ndim != 2 or not a.size:
        raise ValueError('expected nonempty uint8 grayscale')
    return a


def stats(a, window):
    if type(window) is not int or window < 3 or window % 2 != 1:
        raise ValueError('window must be odd and >=3')
    p = window // 2
    x = np.pad(array(a).astype(np.float64), p, mode='edge')
    def mean(y):
        s = np.pad(y.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        return (s[window:, window:] - s[:-window, window:] - s[window:, :-window] + s[:-window, :-window]) / window**2
    m = mean(x)
    return m, np.sqrt(np.maximum(0, mean(x*x)-m*m))


def otsu(a):
    a = array(a)
    h = np.bincount(a.ravel(), minlength=256).astype(float)
    w = h.cumsum(); s = (h*np.arange(256)).cumsum()
    valid = (w > 0) & (w < w[-1])
    if not valid.any():
        return np.zeros(a.shape, bool)
    score = np.full(256, -1.)
    score[valid] = (s[-1]*w[valid]-s[valid]*w[-1])**2/(w[valid]*(w[-1]-w[valid]))
    return a <= int(score.argmax())


def adaptive(a, window, k, method):
    a = array(a)
    if not np.isfinite(k):
        raise ValueError('invalid k')
    m, sd = stats(a, window)
    if method == 'niblack':
        t = m + k*sd
    elif method == 'sauvola':
        t = m*(1+k*(sd/128-1))
    elif method == 'wolf':
        r = sd.max()
        if r <= 1e-9:
            return np.zeros(a.shape, bool)
        t = m+k*(sd/r-1)*(m-float(a.min()))
    else:
        raise ValueError('unknown method')
    return a < t


def normalize(a, radius=16):
    a = array(a)
    bg = np.asarray(Image.fromarray(a).filter(ImageFilter.GaussianBlur(radius)), dtype=float)
    return np.clip(np.rint(255*a.astype(float)/np.maximum(bg, 1)), 0, 255).astype(np.uint8)


def retinex(a, radius=16):
    a = array(a)
    bg = np.asarray(Image.fromarray(a).filter(ImageFilter.GaussianBlur(radius)), dtype=float)
    return np.clip(np.rint(200+100*(np.log1p(a.astype(float))-np.log1p(bg))), 0, 255).astype(np.uint8)


def blackhat(a, size=15):
    im = Image.fromarray(array(a))
    closed = np.asarray(im.filter(ImageFilter.MaxFilter(size)).filter(ImageFilter.MinFilter(size)), dtype=np.int16)
    return np.clip(255-(closed-np.asarray(im, dtype=np.int16)), 0, 255).astype(np.uint8)


def clahe(a, tile=32, clip=2.):
    """Tile histogram clipping with bilinear LUT interpolation, not OpenCV parity."""
    a = array(a)
    if type(tile) is not int or tile < 2 or not np.isfinite(clip) or clip < 1:
        raise ValueError('invalid CLAHE parameters')
    h, w = a.shape
    ys = list(range(0, h, tile)); xs = list(range(0, w, tile))
    cy = np.array([(y+min(y+tile,h)-1)/2 for y in ys]); cx = np.array([(x+min(x+tile,w)-1)/2 for x in xs])
    lut = np.empty((len(ys),len(xs),256), float)
    for i,y in enumerate(ys):
        for j,x in enumerate(xs):
            v = a[y:y+tile,x:x+tile]
            hist = np.bincount(v.ravel(), minlength=256)
            limit = max(1, int(clip*v.size/256))
            excess = int(np.maximum(hist-limit,0).sum())
            hist = np.minimum(hist,limit)+excess//256
            remainder = excess%256
            if remainder:
                hist[np.arange(remainder)*256//remainder] += 1
            lut[i,j] = 255*hist.cumsum()/v.size
    def indices(c,n):
        f = np.interp(np.arange(n),c,np.arange(len(c)))
        lo = f.astype(int)
        return lo, np.minimum(lo+1,len(c)-1), f-lo
    y0,y1,fy=indices(cy,h); x0,x1,fx=indices(cx,w)
    top = lut[y0[:,None],x0,a]*(1-fx)+lut[y0[:,None],x1,a]*fx
    bot = lut[y1[:,None],x0,a]*(1-fx)+lut[y1[:,None],x1,a]*fx
    return np.rint(top*(1-fy[:,None])+bot*fy[:,None]).astype(np.uint8)


def hypotheses(rgb):
    if not isinstance(rgb, Image.Image) or rgb.mode != 'RGB':
        raise ValueError('expected native RGB')
    g = np.asarray(rgb.convert('L')); n = normalize(g)
    out = {'fixed160':g<160,'otsu':otsu(g)}
    for w in (15,31,51):
        for k in (.15,.25,.35):
            for m in ('sauvola','wolf'):
                out[f'{m}_{w}_{k}'] = adaptive(g,w,k,m)
        out[f'niblack_{w}'] = adaptive(g,w,-.2,'niblack')
    for name,a in [('norm',n),('red_norm',normalize(np.asarray(rgb.getchannel('R')))),('green_norm',normalize(np.asarray(rgb.getchannel('G')))),('blue_norm',normalize(np.asarray(rgb.getchannel('B')))),('clahe',clahe(g)),('retinex',retinex(g)),('blackhat',blackhat(g))]:
        for m in ('sauvola','wolf'):
            out[f'{name}_{m}'] = adaptive(a,31,.25,m)
    return out


def agreement(masks):
    """Votes are method agreement, NOT calibrated probability; no erasure."""
    a = [np.asarray(m) for m in masks]
    if not a or len(a)>65535 or any(m.dtype!=bool or m.ndim!=2 or not m.size or m.shape!=a[0].shape for m in a):
        raise ValueError('expected aligned nonempty boolean masks')
    votes = np.sum(a,axis=0,dtype=np.uint16)
    n = len(a)
    return {'votes':votes,'n':n,'union':votes>0,'intersection':votes==n,'majority':votes>n/2,'uncertain':(votes>0)&(votes<n)}


ENSEMBLE = ('sauvola_31_0.25','wolf_31_0.25','norm_sauvola','norm_wolf','red_norm_sauvola','blue_norm_sauvola')
