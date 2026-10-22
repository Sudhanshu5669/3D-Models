#!/usr/bin/env python3
"""Generate texture-free, flat-shaded PlayStation studies. Python standard library only."""
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATERIALS = {
    'ink': ('#494d50', 0.8, 0.0),
    'gunmetal': ('#626e7c', 0.32, 0.6),
    'stand_blue': ('#164792', 0.4, 0.12),
    'ps1_gray': ('#abaeac', 0.78, 0.0),
    'ps1_light': ('#c5c5c1', 0.72, 0.0),
    'ps1_dark': ('#6e747e', 0.85, 0.0),
    'black': ('#20242b', 0.65, 0.0),
    'soft_black': ('#2b3038', 0.85, 0.0),
    'gloss_black': ('#141a23', 0.22, 0.12),
    'groove': ('#080d14', 0.95, 0.0),
    'silver': ('#a7b4c5', 0.3, 0.65),
    'white': ('#e7e9ee', 0.54, 0.0),
    'white_edge': ('#bcc8d9', 0.7, 0.0),
    'blue': ('#1264df', 0.4, 0.1),
    'led_blue': ('#36a9ff', 0.3, 0.0),
    'green': ('#68b482', 0.5, 0.0),
    'red': ('#d64e52', 0.5, 0.0),
    'yellow': ('#e7b65e', 0.5, 0.0),
}


def rgb(hex_color):
    return [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def linear_rgb(hex_color):
    return [c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb(hex_color)]


def normal(a, b, c):
    u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
    n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    length = math.sqrt(sum(x*x for x in n))
    if length < 1e-10:
        raise ValueError('Degenerate triangle')
    return [x/length for x in n]


class Model:
    def __init__(self, name, title):
        self.name, self.title, self.parts = name, title, []

    def mesh(self, name, verts, faces, material):
        triangles = []
        for face in faces:
            for j in range(1, len(face)-1):
                triangles.append([face[0], face[j], face[j+1]])
        for tri in triangles:
            normal(*(verts[i] for i in tri))
        self.parts.append(dict(name=name, vertices=verts, triangles=triangles, material=material))

    def box(self, name, center, size, material, shear=0):
        x, y, z = center
        w, h, d = [v/2 for v in size]
        verts = [[x+dx+shear*dy/h, y+dy, z+dz] for dx,dy,dz in
                 [(-w,-h,-d),(w,-h,-d),(w,h,-d),(-w,h,-d),
                  (-w,-h,d),(w,-h,d),(w,h,d),(-w,h,d)]]
        self.mesh(name, verts, [[0,3,2,1],[4,5,6,7],[0,4,7,3],
                               [1,2,6,5],[0,1,5,4],[3,7,6,2]], material)

    def cylinder(self, name, center, radius, height, material, sides=16, axis='y'):
        verts = []
        for y in (-height/2, height/2):
            for i in range(sides):
                a = 2*math.pi*i/sides
                p = [radius*math.cos(a), y, radius*math.sin(a)]
                if axis == 'z':
                    p = [p[0], -p[2], p[1]]
                verts.append([center[k]+p[k] for k in range(3)])
        faces = [list(range(sides)), list(range(2*sides-1, sides-1, -1))]
        for i in range(sides):
            j = (i+1) % sides
            faces.append([i, i+sides, j+sides, j])
        self.mesh(name, verts, faces, material)

    def profile(self, name, profile, depth, z, material):
        """Extrude a counter-clockwise XY outline along Z."""
        n = len(profile)
        verts = [[x,y,z+dz] for dz in (-depth/2, depth/2) for x,y in profile]
        faces = [list(range(n-1,-1,-1)), list(range(n,2*n))]
        faces += [[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
        self.mesh(name, verts, faces, material)


# A small stroke alphabet keeps the silkscreen markings as editable geometry.
FONT = {
 'A':[[(0,0),(.5,1),(1,0)],[(.23,.4),(.77,.4)]],
 'B':[[(0,0),(0,1),(.65,1),(1,.8),(.65,.52),(0,.52)],[(.65,.52),(1,.25),(.65,0),(0,0)]],
 'C':[[(1,.9),(.75,1),(.2,1),(0,.8),(0,.2),(.2,0),(.75,0),(1,.1)]],
 'D':[[(0,0),(0,1),(.6,1),(1,.75),(1,.25),(.6,0),(0,0)]],
 'E':[[(1,1),(0,1),(0,0),(1,0)],[(0,.52),(.8,.52)]],
 'I':[[(.5,0),(.5,1)]],
 'L':[[(0,1),(0,0),(1,0)]],
 'M':[[(0,0),(0,1),(.5,.45),(1,1),(1,0)]],
 'N':[[(0,0),(0,1),(1,0),(1,1)]],
 'O':[[(.2,0),(0,.2),(0,.8),(.2,1),(.8,1),(1,.8),(1,.2),(.8,0),(.2,0)]],
 'P':[[(0,0),(0,1),(.75,1),(1,.8),(1,.6),(.75,.5),(0,.5)]],
 'R':[[(0,0),(0,1),(.75,1),(1,.8),(1,.6),(.75,.5),(0,.5)],[(.55,.5),(1,0)]],
 'S':[[(1,.9),(.8,1),(.2,1),(0,.8),(.15,.6),(.85,.4),(1,.2),(.8,0),(.2,0),(0,.1)]],
 'T':[[(0,1),(1,1)],[(.5,1),(.5,0)]],
 'U':[[(0,1),(0,.2),(.2,0),(.8,0),(1,.2),(1,1)]],
 'W':[[(0,1),(.2,0),(.5,.5),(.8,0),(1,1)]],
 'Y':[[(0,1),(.5,.5),(1,1)],[(.5,.5),(.5,0)]],
 '0':[[(.2,0),(0,.2),(0,.8),(.2,1),(.8,1),(1,.8),(1,.2),(.8,0),(.2,0)]],
 '1':[[(.2,.75),(.5,1),(.5,0)]],
 '2':[[(0,.8),(.2,1),(.8,1),(1,.8),(1,.65),(0,0),(1,0)]],
 '3':[[(0,1),(1,1),(.5,.52),(1,.33),(1,.15),(.8,0),(0,0)]],
 '4':[[(.75,0),(.75,1),(0,.3),(1,.3)]],
 '5':[[(1,1),(0,1),(0,.55),(.8,.55),(1,.35),(1,.2),(.8,0),(0,0)]],
}


def bevel(m,name,center,size,mat,r=.012,shear_z=0):
    """Closed 4-ring chamfered box, with clipped plan corners."""
    x,y,z=center;w,h,d=[v/2 for v in size]
    r=min(r,w*.45,h*.65,d*.45)
    verts=[]
    for yy,ww,dd in [(-h,w-r,d-r),(-h+r,w,d),(h-r,w,d),(h,w-r,d-r)]:
        c=min(r,ww*.3,dd*.3)
        ring=[(-ww,-dd+c),(-ww+c,-dd),(ww-c,-dd),(ww,-dd+c),
              (ww,dd-c),(ww-c,dd),(-ww+c,dd),(-ww,dd-c)]
        verts += [[x+xx,y+yy,z+zz+shear_z*yy/h] for xx,zz in ring]
    faces=[list(range(8)),list(range(31,23,-1))]
    for k in range(3):
        for i in range(8):
            j=(i+1)%8
            faces.append([k*8+i,(k+1)*8+i,(k+1)*8+j,k*8+j])
    m.mesh(name,verts,faces,mat)


def disc(m,name,center,radius,height,mat,sides=32,bevel_size=.004):
    x,y,z=center;r=min(bevel_size,height*.3)
    verts=[]
    for yy,rr in [(-height/2,radius-r),(-height/2+r,radius),(height/2-r,radius),(height/2,radius-r)]:
        verts += [[x+rr*math.cos(2*math.pi*i/sides),y+yy,z+rr*math.sin(2*math.pi*i/sides)] for i in range(sides)]
    faces=[list(range(sides)),list(range(4*sides-1,3*sides-1,-1))]
    for k in range(3):
        faces += [[k*sides+i,(k+1)*sides+i,(k+1)*sides+(i+1)%sides,k*sides+(i+1)%sides] for i in range(sides)]
    m.mesh(name,verts,faces,mat)


def strokes(m,name,paths,origin,u,v,width,mat):
    verts=[];faces=[]
    for path in paths:
        for a,b in zip(path,path[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
            if length<1e-10: continue
            nx,ny=-dy/length*width/2,dx/length*width/2
            n=len(verts)
            for xx,yy in [(a[0]-nx,a[1]-ny),(b[0]-nx,b[1]-ny),(b[0]+nx,b[1]+ny),(a[0]+nx,a[1]+ny)]:
                verts.append([origin[k]+xx*u[k]+yy*v[k] for k in range(3)])
            faces.append([n,n+1,n+2,n+3])
    m.mesh(name,verts,faces,mat)


def text(m,word,origin,u,v,height,mat='silver',width=None):
    glyph=height*.65;advance=glyph*1.45
    paths=[]
    for i,char in enumerate(word.upper()):
        for path in FONT.get(char,[]):
            paths.append([(i*advance+x*glyph,y*height) for x,y in path])
    if paths: strokes(m,word+' lettering',paths,origin,u,v,width or height*.095,mat)


TOP_U,TOP_V=(-1,0,0),(0,0,1)
FRONT_U,FRONT_V=(-1,0,0),(0,1,0)


def ps_badge(m,origin,u,v,size,colored=True):
    # A compact geometric interpretation of the classic upright P / lying S emblem.
    paths=[[(.32,0),(.32,1),(.62,.92),(.76,.77),(.76,.51),(.65,.43)]]
    strokes(m,'P emblem',paths,origin,[x*size for x in u],[x*size for x in v],.16,'red' if colored else 'silver')
    for path,mat in [([(.22,.21),(.05,.14),(.02,.04),(.2,-.05),(.48,-.08)],'yellow'),
                     ([(.42,-.13),(.71,-.06),(.92,.05),(.84,.13),(.57,.18)],'blue'),
                     ([(.55,-.01),(.78,.06)],'green')]:
        strokes(m,'S emblem '+mat,[path],origin,[x*size for x in u],[x*size for x in v],.10,mat if colored else 'silver')


def usb(m,x,y,z,name='USB',width=.054):
    bevel(m,name+' metal liner',(x,y,z),(width,.023,.009),'silver',.002)
    m.box(name+' shadow',(x,y,z-.0055),(width-.008,.014,.003),'groove')
    m.box(name+' tongue',(x,y-.002,z-.0075),(width-.017,.004,.003),'soft_black')


def ps1():
    m=Model('ps1','PlayStation / 1994')
    bevel(m,'lower molded shell',(0,.085,0),(1.02,.13,.735),'ps1_gray',.025)
    bevel(m,'shell parting line',(0,.145,0),(1.016,.006,.731),'ps1_dark',.002)
    bevel(m,'upper molded shell',(0,.176,0),(1.025,.061,.74),'ps1_light',.018)
    disc(m,'lid circular recess',(0,.208,.026),.293,.006,'ps1_dark',48,.001)
    disc(m,'beveled CD lid',(0,.216,.026),.285,.013,'ps1_light',48,.003)
    bevel(m,'lid hinge',(0,.208,.326),(.225,.024,.062),'ps1_light',.008)
    for x,label,r,z in [(.404,'POWER',.047,-.206),(.404,'RESET',.027,-.087),(-.404,'OPEN',.047,-.206)]:
        disc(m,label+' button socket',(x,.207,z),r+.003,.005,'ps1_dark',24,.001)
        disc(m,label+' button',(x,.214,z),r,.013,'ps1_gray',24,.003)
        text(m,label,(x+.035,.210,z-.068),TOP_U,TOP_V,.010,'ink')
    m.box('green power light',(.404,.208,-.293),(.013,.003,.007),'green')
    for side in (-1,1):
        for i in range(12):
            m.box('deck cooling slit',(side*.414,.207,.01+i*.024),(.112,.002,.007),'ps1_dark')
            m.box('side ventilation',(side*.513,.102,-.13+i*.035),(.003,.026,.009),'ps1_dark')
    for i,x in enumerate((.255,-.255)):
        bevel(m,'port surround '+str(i),(x,.088,-.371),(.415,.115,.017),'ps1_gray',.008)
        bevel(m,'memory slot '+str(i),(x,.124,-.382),(.274,.027,.008),'ps1_dark',.003)
        m.box('memory flap '+str(i),(x,.126,-.387),(.250,.016,.003),'ps1_light')
        bevel(m,'controller bezel '+str(i),(x,.064,-.382),(.203,.066,.014),'ps1_dark',.009)
        bevel(m,'controller cavity '+str(i),(x,.064,-.391),(.165,.043,.007),'groove',.004)
        for j in range(5):
            m.box('controller contact',(x-.055+j*.0275,.064,-.396),(.007,.009,.002),'silver')
        text(m,str(i+1),(x+.008,.151,-.374),FRONT_U,FRONT_V,.016,'ink')
    ps_badge(m,(.039,.224,.015),TOP_U,TOP_V,.075)
    text(m,'PlayStation',(.109,.225,-.028),TOP_U,TOP_V,.019,'ink',.0013)
    text(m,'SONY',(.046,.224,.213),TOP_U,TOP_V,.021,'ink',.0018)
    for x in (-.37,.37):
        for z in (-.23,.23): bevel(m,'rubber foot',(x,.012,z),(.09,.024,.07),'groove',.006)
    return m


def ps2():
    m=Model('ps2','PlayStation 2 / 2000')
    bevel(m,'blue vertical stand',(0,.028,0),(.40,.056,.83),'stand_blue',.018)
    bevel(m,'stand upper inset',(0,.055,0),(.31,.028,.75),'black',.009)
    bevel(m,'ribbed chassis',(0,.671,0),(.235,1.21,.735),'black',.009)
    bevel(m,'broad offset shell',(.07,.673,.014),(.125,1.196,.77),'soft_black',.008)
    for i in range(7):
        x=-.117+i*.026
        m.box('continuous front fin',(x,.669,-.381),(.014,1.19,.024),'soft_black')
        m.box('rear exhaust fin',(x,.669,.377),(.014,1.19,.022),'soft_black')
        m.box('top cooling fin',(x,1.273,-.002),(.014,.023,.75),'soft_black')
    bevel(m,'front fascia',(.071,.67,-.399),(.123,1.19,.026),'black',.004)
    bevel(m,'optical tray seam',(.069,.94,-.415),(.092,.49,.009),'groove',.003)
    bevel(m,'optical tray face',(.069,.94,-.421),(.080,.476,.007),'soft_black',.002)
    for i,y in enumerate((1.218,1.157)):
        bevel(m,'front button '+str(i),(.068,y,-.419),(.049,.032,.010),'soft_black',.004)
        m.box('button light',(.068,y+.009,-.425),(.012,.004,.002),'green' if i==0 else 'led_blue')
    for i,y in enumerate((.48,.32)):
        bevel(m,'memory bay '+str(i),(.067,y+.055,-.418),(.090,.023,.009),'groove',.002)
        bevel(m,'controller port '+str(i),(.067,y,-.421),(.084,.059,.012),'ps1_dark',.006)
        bevel(m,'controller opening '+str(i),(.067,y,-.428),(.064,.038,.005),'groove',.003)
        for j in range(3): m.box('port pin',(.047+j*.02,y,-.432),(.004,.006,.002),'silver')
    for y in (.14,.19): usb(m,.067,y,-.418,width=.044)
    ps_badge(m,(.086,.675,-.426),FRONT_U,FRONT_V,.035)
    # Large, thin PS2 line mark on the broad panel facing the default camera.
    side_u,side_v=(0,0,-1),(0,1,0)
    paths=[[(0,0),(0,1),(.7,1),(.7,.5),(0,.5)],
           [(1.0,0),(1.7,0),(1.7,.5),(1,.5),(1,1),(1.7,1)],
           [(2,1),(2.7,1),(2.7,.5),(2,.5),(2,0),(2.7,0)]]
    strokes(m,'PS2 blue monoline',paths,(.133,.84,.18),[a*.112 for a in side_u],[a*.112 for a in side_v],.025,'blue')
    text(m,'PlayStation 2',(.133,.806,.19),side_u,side_v,.014,'ps1_dark',.001)
    text(m,'SONY',(.133,1.177,.27),side_u,side_v,.021,'silver',.0015)
    return m


def ps3():
    m=Model('ps3','PlayStation 3 / 2006')
    bevel(m,'inset bottom chassis',(0,.061,.0),(1.05,.10,.79),'black',.028)
    bevel(m,'lower front rail',(0,.102,-.392),(1.074,.055,.06),'soft_black',.012)
    # A vault over the depth axis, with chamfered ends; no box-shaped extrusion.
    sections=[(-.444,.512,.218),(-.429,.543,.247),(-.355,.562,.307),(-.22,.57,.355),
              (-.06,.57,.378),(.10,.564,.375),(.25,.548,.343),(.366,.515,.281),(.403,.48,.237)]
    verts=[]
    for z,w,top in sections:
        low=.112;c=.022
        profile=[(-w+c,low),(w-c,low),(w,low+c),(w,top-.032),(w-.035,top),
                 (-w+.035,top),(-w,top-.032),(-w,low+c)]
        verts += [[x,y,z] for x,y in profile]
    faces=[list(range(7,-1,-1)),list(range(64,72))]
    for k in range(len(sections)-1):
        for j in range(8):faces.append([k*8+j,k*8+(j+1)%8,(k+1)*8+(j+1)%8,(k+1)*8+j])
    m.mesh('swept glossy vault',verts,faces,'gloss_black')
    bevel(m,'chrome front ribbon',(0,.132,-.449),(1.025,.018,.015),'silver',.004)
    bevel(m,'front optical slot',(-.17,.192,-.446),(.515,.011,.007),'groove',.002)
    m.box('disc slot bevel',(-.17,.184,-.451),(.50,.003,.003),'gunmetal')
    for i,x in enumerate((.36,.26,.16,.06)):usb(m,x,.084,-.425,'USB '+str(i),.047)
    for side in (-1,1):
        for i in range(11):
            m.box('side exhaust',(side*.544,.135,-.28+i*.055),(.004,.026,.017),'groove')
    ps_badge(m,(.442,.169,-.448),FRONT_U,FRONT_V,.031)
    text(m,'SONY',(.49,.210,-.447),FRONT_U,FRONT_V,.016,'silver',.0012)
    for x in (-.37,-.44):
        m.box('touch control',(x,.154,-.452),(.026,.003,.002),'silver')
    m.box('power status',(-.47,.144,-.456),(.009,.003,.002),'green')
    # Surface-conforming lettering across the crown.
    text(m,'PLAYSTATION 3',(.29,.380,-.067),TOP_U,TOP_V,.038,'silver',.0018)
    return m


def ps4():
    m=Model('ps4','PlayStation 4 / 2013')
    for x in (-.37,.37):
        for z in (-.34,.34):bevel(m,'rubber foot',(x,.012,z),(.065,.024,.055),'groove',.004)
    bevel(m,'lower tapered tier',(0,.066,0),(1.04,.091,1.08),'soft_black',.009,shear_z=.025)
    bevel(m,'recessed waist',(0,.12,.005),(1.005,.018,1.022),'groove',.003,shear_z=.004)
    bevel(m,'upper satin panel',(-.176,.177,.016),(.687,.096,1.08),'black',.007,shear_z=.026)
    bevel(m,'upper polished panel',(.351,.177,.016),(.342,.096,1.08),'gloss_black',.007,shear_z=.026)
    m.box('blue light channel',(.173,.226,.041),(.005,.002,1.052),'led_blue')
    m.box('front light continuation',(.173,.185,-.549),(.005,.068,.003),'led_blue')
    bevel(m,'optical slot',(.317,.174,-.551),(.29,.010,.005),'groove',.002)
    for i,x in enumerate((-.13,-.36)):usb(m,x,.120,-.519,'USB '+str(i),.056)
    text(m,'SONY',(.477,.192,-.553),FRONT_U,FRONT_V,.014,'silver',.001)
    text(m,'PS4',(-.29,.228,-.29),TOP_U,TOP_V,.028,'silver',.0017)
    ps_badge(m,(-.325,.228,.258),TOP_U,TOP_V,.045,False)
    for side in (-1,1):
        for i in range(14):
            m.box('side intake',(side*.521,.149,-.43+i*.065),(.003,.017,.029),'groove')
    for i in range(12):m.box('rear exhaust',(-.44+i*.08,.166,.577),(.044,.035,.004),'groove')
    return m


def ps5():
    m=Model('ps5','PlayStation 5 / 2020')
    disc(m,'stand',(0,.023,.01),.265,.046,'black',40,.007)
    # Core follows the white shells, narrowing at the waist.
    rows=[(.055,.109,-.335,.315),(.17,.104,-.346,.322),(.36,.095,-.348,.32),
          (.57,.088,-.337,.315),(.80,.091,-.318,.313),(1.02,.108,-.302,.319),
          (1.22,.126,-.31,.33),(1.37,.146,-.338,.335)]
    verts=[]
    for y,w,front,back in rows:
        rear_y=y-(max(0,y-1.20)/.17)*.074
        verts += [[-w,y,front],[-w,rear_y,back],[w,rear_y,back],[w,y,front]]
    faces=[[0,3,2,1]]
    for k in range(len(rows)-1):
        faces += [[k*4+j,k*4+(j+1)%4,(k+1)*4+(j+1)%4,(k+1)*4+j] for j in range(4)]
    faces.append(list(range(28,32)))
    m.mesh('tapered black core',verts,faces,'gloss_black')
    # Front-to-back curvature, an integrated drive swelling, and a swept top edge.
    ny,nz=12,8
    for side in (-1,1):
        verts=[]
        for inner in (False,True):
            for iy in range(ny+1):
                t=iy/ny
                for iz in range(nz+1):
                    q=iz/nz
                    y=.060+t*(1.475-.12*q-.060)
                    z=(-.385-.055*t**4)+q*(.754+.025*t)
                    base=.145-.037*math.sin(math.pi*t)+.055*t**4
                    # Convex side surface and a smooth drive bulge low on the right.
                    bow=.033*math.sin(math.pi*q)
                    plateau=min(1,t/.07)*max(0,min(1,(.65-t)/.22))
                    plateau=plateau*plateau*(3-2*plateau)
                    drive=(max(0,.240-base-.017)*plateau*(1-.80*q)**2) if side==1 else 0
                    x=side*(base+bow+drive*(.15 if inner else 1)+(.0 if inner else .017))
                    verts.append([x,y,z])
        n=(ny+1)*(nz+1);faces=[]
        for iy in range(ny):
            for iz in range(nz):
                a=iy*(nz+1)+iz;b=a+1;c=a+nz+2;d=a+nz+1
                # Outer orientation is +X, inner -X; flip for the left shell.
                outer=[a,d,c,b];inside=[a+n,b+n,c+n,d+n]
                if side<0:outer.reverse();inside.reverse()
                faces += [outer,inside]
        boundary=list(range(nz+1))+[i*(nz+1)+nz for i in range(1,ny+1)]+[ny*(nz+1)+i for i in range(nz-1,-1,-1)]+[i*(nz+1) for i in range(ny-1,0,-1)]
        for a,b in zip(boundary,boundary[1:]+boundary[:1]):
            face=[a,b,b+n,a+n]
            if side<0:face.reverse()
            faces.append(face)
        m.mesh(('left' if side<0 else 'disc-side')+' sculpted shell',verts,faces,'white')
    # Continuous blue intake strips, integrated into the gap rather than floating bars.
    for side in (-1,1):
        path=[]
        for y,w,front,back in rows[3:]:path.append((side*(w+.004),y,front-.002))
        verts=[]
        for x,y,z in path:verts += [[x-.003,y,z],[x+.003,y,z]]
        faces=[[2*i,2*i+2,2*i+3,2*i+1] for i in range(len(path)-1)]
        m.mesh('continuous blue intake',verts,faces,'led_blue')
        for i in range(13):
            m.box('top intake fin',(side*.135,1.37-i*.0048,-.265+i*.043),(.016,.012,.014),'soft_black')
    # The disc slot sits on the widened white panel's front edge.
    bevel(m,'disc slot',(.189,.398,-.389),(.010,.438,.005),'groove',.002)
    m.box('slot lip',(.200,.398,-.391),(.003,.427,.002),'white_edge')
    usb(m,0,.625,-.339,'USB A',.040)
    bevel(m,'USB C liner',(0,.744,-.325),(.025,.012,.006),'gunmetal',.002)
    bevel(m,'USB C opening',(0,.744,-.329),(.019,.006,.002),'groove',.0007)
    for y in (.15,.215):bevel(m,'front control',(0,y,-.351),(.007,.026,.005),'gunmetal',.001)
    return m


def export_obj(model, folder):
    lines = [f'# {model.title}: low-poly study. Y up, front -Z. Stylized scene units.', f'mtllib {model.name}.mtl']
    offset = 1
    for part in model.parts:
        lines += ['o '+part['name'].replace(' ','_'), 'usemtl '+part['material']]
        lines += ['v '+' '.join(f'{v:.6f}' for v in vertex) for vertex in part['vertices']]
        lines += ['s off']
        lines += ['f '+' '.join(str(i+offset) for i in triangle) for triangle in part['triangles']]
        offset += len(part['vertices'])
    (folder/f'{model.name}.obj').write_text('\n'.join(lines)+'\n')
    mats=[]
    for key,(color,rough,metal) in MATERIALS.items():
        mats += [f'newmtl {key}', 'Kd '+' '.join(f'{c:.5f}' for c in rgb(color)),
                 f'Ns {(1-rough)*200:.2f}', 'Ks 0.15 0.15 0.15', 'd 1.0', '']
    (folder/f'{model.name}.mtl').write_text('\n'.join(mats))


def export_glb(model, folder):
    blob=bytearray()
    doc={'asset':{'version':'2.0','generator':'Low-poly console generator'},'scene':0,
         'scenes':[{'name':model.title,'nodes':[]}], 'nodes':[], 'meshes':[],
         'materials':[], 'buffers':[], 'bufferViews':[], 'accessors':[]}
    material_indices={}
    for key,(color,rough,metal) in MATERIALS.items():
        material_indices[key]=len(doc['materials'])
        mat={'name':key,'pbrMetallicRoughness':{'baseColorFactor':linear_rgb(color)+[1],
             'metallicFactor':metal,'roughnessFactor':rough}}
        if key=='led_blue':
            mat['emissiveFactor']=[.02,.3,.85]
        doc['materials'].append(mat)
    def accessor(values):
        start=len(blob)
        for v in values:
            blob.extend(struct.pack('<3f',*v))
        view=len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(blob)-start,'target':34962})
        index=len(doc['accessors'])
        doc['accessors'].append({'bufferView':view,'componentType':5126,'count':len(values),'type':'VEC3',
                                'min':[min(v[i] for v in values) for i in range(3)],
                                'max':[max(v[i] for v in values) for i in range(3)]})
        return index
    for part in model.parts:
        pos,norm=[],[]
        for tri in part['triangles']:
            points=[part['vertices'][i] for i in tri]
            n=normal(*points)
            pos.extend(points)
            norm.extend([n]*3)
        p,n=accessor(pos),accessor(norm)
        index=len(doc['meshes'])
        doc['meshes'].append({'name':part['name'],'primitives':[{'attributes':{'POSITION':p,'NORMAL':n},
                                'material':material_indices[part['material']],'mode':4}]})
        doc['nodes'].append({'name':part['name'],'mesh':index})
        doc['scenes'][0]['nodes'].append(index)
    doc['buffers']=[{'byteLength':len(blob)}]
    raw=json.dumps(doc,separators=(',',':')).encode()
    raw+=b' '*((-len(raw))%4)
    blob+=b'\x00'*((-len(blob))%4)
    total=12+8+len(raw)+8+len(blob)
    data=struct.pack('<III',0x46546c67,2,total)+struct.pack('<II',len(raw),0x4e4f534a)+raw
    data+=struct.pack('<II',len(blob),0x004e4942)+blob
    (folder/f'{model.name}.glb').write_bytes(data)


def main():
    models=[ps1(),ps2(),ps3(),ps4(),ps5()]
    manifest=[]
    for model in models:
        folder=ROOT/'models'/model.name
        folder.mkdir(parents=True,exist_ok=True)
        export_obj(model,folder)
        export_glb(model,folder)
        vertices=[v for p in model.parts for v in p['vertices']]
        bounds=[[min(v[i] for v in vertices) for i in range(3)],
                [max(v[i] for v in vertices) for i in range(3)]]
        info={'id':model.name,'title':model.title,'triangles':sum(len(p['triangles']) for p in model.parts),
              'parts':len(model.parts),'bounds':bounds}
        manifest.append(info)
        print(f"{model.name}: {info['triangles']} triangles, {info['parts']} parts")
    (ROOT/'models'/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    preview={'materials':{k:v[0] for k,v in MATERIALS.items()},'surfaces':{k:[v[1],v[2]] for k,v in MATERIALS.items()},
             'models':[dict(name=m.name,title=m.title,parts=m.parts,**{k:v for k,v in info.items() if k not in ('id','title','parts')})
                       for m,info in zip(models,manifest)]}
    (ROOT/'preview'/'models.js').write_text('window.CONSOLES = '+json.dumps(preview,separators=(',',':'))+';\n')


if __name__=='__main__':
    main()
