#!/usr/bin/env python3
"""Render the actual exported source meshes using NumPy/Pillow and a depth buffer.
No generative imagery: every visible feature comes from the model geometry.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from generate_models import ps1,ps2,ps3,ps4,ps5,MATERIALS,normal,ROOT,rgb


def unit(a):
    a=np.asarray(a,dtype=float)
    return a/np.linalg.norm(a)


def font(size):
    for path in ['/System/Library/Fonts/Helvetica.ttc','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        try:return ImageFont.truetype(path,size)
        except OSError:pass
    return ImageFont.load_default()


def render(model,width=1000,height=800):
    ss=2;w,h=width*ss,height*ss
    tall=model.name in ('ps2','ps5')
    eye=unit([1.65,1.05 if tall else 2.0,-3.5]);right=unit(np.cross([0,1,0],eye));up=np.cross(eye,right)
    points=np.asarray([v for p in model.parts for v in p['vertices']])
    uv=np.stack((points@right,-points@up),axis=1)
    bounds=np.array([uv.min(axis=0),uv.max(axis=0)])
    zoom=min(w*.78/(bounds[1,0]-bounds[0,0]),h*.76/(bounds[1,1]-bounds[0,1]))
    center=(bounds[0]+bounds[1])/2
    def project(p):
        p=np.asarray(p)
        return np.stack(((p@right-center[0])*zoom+w*.5,(-p@up-center[1])*zoom+h*.47),axis=-1)
    # Neutral studio background with a subtle vertical gradient.
    background=np.zeros((h,w,3),dtype=np.float32)
    for y in range(h): background[y,:,:]=np.array([239,242,244])-(y/h)*np.array([8,9,9])
    base=Image.fromarray(background.astype('uint8'))
    light=unit([-.7,2,-1.6]);fill=unit([2,1,.6])
    shadow=Image.new('L',(w,h));sd=ImageDraw.Draw(shadow)
    triangles=[]
    for part in model.parts:
        for ids in part['triangles']:
            p=np.asarray([part['vertices'][i] for i in ids])
            floor=p.copy();floor[:,0]-=floor[:,1]*light[0]/light[1];floor[:,2]-=floor[:,1]*light[2]/light[1];floor[:,1]=0
            sd.polygon([tuple(v) for v in project(floor)],fill=65)
            n=np.asarray(normal(*p))
            if np.dot(n,eye)>0:triangles.append((p,n,part['material']))
    shadow=shadow.filter(ImageFilter.GaussianBlur(13*ss))
    base.paste(Image.new('RGB',(w,h),'#8b99ab'),(0,0),shadow)
    # Tight contact shadow underneath the feet complements the projected silhouette.
    contact=Image.new('L',(w,h));cd=ImageDraw.Draw(contact)
    ground=project([[0,0,0]])[0]
    rx=(bounds[1,0]-bounds[0,0])*zoom*.35;ry=zoom*.035
    cd.ellipse((ground[0]-rx,ground[1]-ry,ground[0]+rx,ground[1]+ry),fill=90)
    contact=contact.filter(ImageFilter.GaussianBlur(8*ss))
    base.paste(Image.new('RGB',(w,h),'#8490a0'),(0,0),contact)
    pixels=np.array(base)
    depth=np.full((h,w),-np.inf,dtype=np.float32)
    # A broad key and rim create material-dependent studio highlights.
    half1=unit(light+eye);half2=unit(unit([1.8,2,.6])+eye)
    for p,n,material in triangles:
        screen=project(p);z=p@eye
        xmin=max(0,int(np.floor(screen[:,0].min())));xmax=min(w,int(np.ceil(screen[:,0].max()))+1)
        ymin=max(0,int(np.floor(screen[:,1].min())));ymax=min(h,int(np.ceil(screen[:,1].max()))+1)
        if xmin>=xmax or ymin>=ymax:continue
        a,b,c=screen
        denom=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(denom)<1e-7:continue
        yy,xx=np.mgrid[ymin:ymax,xmin:xmax];xx=xx+.5;yy=yy+.5
        u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/denom
        v=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/denom
        t=1-u-v;zz=u*z[0]+v*z[1]+t*z[2]
        patch=depth[ymin:ymax,xmin:xmax]
        mask=(u>=-1e-7)&(v>=-1e-7)&(t>=-1e-7)&(zz>patch)
        color,rough,metal=MATERIALS[material]
        srgb=np.array(rgb(color));linear=np.where(srgb<=.04045,srgb/12.92,((srgb+.055)/1.055)**2.4)
        diffuse=.56+.58*max(0,np.dot(n,light))+.24*max(0,np.dot(n,fill))
        power=12+(1-rough)*70
        spec=(max(0,np.dot(n,half1))**power*.36+max(0,np.dot(n,half2))**(power*.45)*.16)*(1-rough*.8)
        shaded=linear*diffuse+spec*(np.array([.83,.91,1.0]) if metal<.4 else srgb)
        if material=='led_blue':shaded=linear*1.4
        final=np.where(shaded<=.0031308,shaded*12.92,1.055*np.maximum(shaded,0)**(1/2.4)-.055)
        color=np.uint8(np.clip(final*255,0,255))
        pixels[ymin:ymax,xmin:xmax][mask]=color
        patch[mask]=zz[mask]
    return Image.fromarray(pixels).resize((width,height),Image.Resampling.LANCZOS)


def main():
    models=[ps1(),ps2(),ps3(),ps4(),ps5()]
    board=Image.new('RGB',(1800,1280),'#f0f2f4')
    d=ImageDraw.Draw(board)
    d.text((60,34),'PLAYSTATION   /   LOW-POLY HARDWARE STUDIES',font=font(13),fill='#687785')
    d.text((60,65),'Five generations, carefully shaped.',font=font(37),fill='#273440')
    positions=[(30,145),(620,145),(1210,145),(320,705),(910,705)]
    for m,(x,y) in zip(models,positions):
        hero=render(m)
        hero.save(ROOT/'preview'/f'{m.name}.png')
        board.paste(hero.resize((560,448),Image.Resampling.LANCZOS),(x,y))
        d.line((x+24,y+450,x+536,y+450),fill='#ccd3da',width=1)
        d.text((x+24,y+470),m.name.upper(),font=font(26),fill='#263440')
        count=sum(len(p['triangles']) for p in m.parts)
        d.text((x+24,y+507),f'{m.title.split(" / ")[1]}   /   {count:,} triangles',font=font(14),fill='#657482')
        print(f'Rendered {m.name}: {count} triangles',flush=True)
    board.save(ROOT/'preview/collection.png')


if __name__=='__main__':main()
