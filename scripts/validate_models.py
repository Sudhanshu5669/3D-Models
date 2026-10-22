#!/usr/bin/env python3
"""Validate generated GLB structure, geometric normals, OBJ parity and manifest."""
import json
import math
import struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def validate():
    manifest=json.loads((ROOT/'models/manifest.json').read_text())
    for entry in manifest:
        name=entry['id']
        base=ROOT/'models'/name
        data=(base/f'{name}.glb').read_bytes()
        magic,version,length=struct.unpack_from('<III',data)
        assert (magic,version,length)==(0x46546c67,2,len(data))
        size,kind=struct.unpack_from('<II',data,12)
        assert kind==0x4e4f534a and size%4==0
        doc=json.loads(data[20:20+size])
        offset=20+size
        binsize,kind=struct.unpack_from('<II',data,offset)
        assert kind==0x004e4942
        blob=data[offset+8:]
        assert len(blob)==binsize==doc['buffers'][0]['byteLength']
        def vectors(index):
            a=doc['accessors'][index]
            v=doc['bufferViews'][a['bufferView']]
            assert a['componentType']==5126 and a['type']=='VEC3'
            assert v['byteOffset']%4==0
            assert v['byteLength']==a['count']*12
            assert v['byteOffset']+v['byteLength']<=len(blob)
            result=list(struct.iter_unpack('<3f',blob[v['byteOffset']:v['byteOffset']+v['byteLength']]))
            assert all(math.isfinite(x) for row in result for x in row)
            for axis in range(3):
                assert abs(min(p[axis] for p in result)-a['min'][axis])<1e-5
                assert abs(max(p[axis] for p in result)-a['max'][axis])<1e-5
            return result
        triangle_count=0
        for mesh in doc['meshes']:
            for primitive in mesh['primitives']:
                p=vectors(primitive['attributes']['POSITION'])
                n=vectors(primitive['attributes']['NORMAL'])
                assert len(p)==len(n) and len(p)%3==0
                assert 0<=primitive['material']<len(doc['materials'])
                triangle_count+=len(p)//3
                for i in range(0,len(p),3):
                    a,b,c=p[i:i+3]
                    u=[b[k]-a[k] for k in range(3)]
                    v=[c[k]-a[k] for k in range(3)]
                    cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                    area=math.sqrt(sum(x*x for x in cross))
                    assert area>1e-10, 'Degenerate triangle'
                    assert abs(sum(x*x for x in n[i])-1)<1e-5
                    assert sum(cross[k]/area*n[i][k] for k in range(3))>.9999
                    assert n[i]==n[i+1]==n[i+2]
        assert triangle_count==entry['triangles']
        assert len(doc['meshes'])==len(doc['nodes'])==entry['parts']
        obj=(base/f'{name}.obj').read_text().splitlines()
        verts=[line for line in obj if line.startswith('v ')]
        faces=[line for line in obj if line.startswith('f ')]
        assert len(faces)==triangle_count
        assert all(1<=int(i)<=len(verts) for f in faces for i in f.split()[1:])
        assert (base/f'{name}.mtl').is_file()
        print(f'{name}: valid GLB structure, flat normals, {triangle_count} triangles; OBJ parity OK')
    print('All 5 models passed.')


if __name__=='__main__':
    validate()
