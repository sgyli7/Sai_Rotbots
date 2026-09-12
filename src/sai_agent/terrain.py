"""Continuous staircase geometry and its exact simulation height field.

The height field is a privileged simulator sensor until a depth reconstruction
backend is supplied. It must not be marketed as an RGB/VLA capability.
"""
from dataclasses import dataclass, asdict
import xml.etree.ElementTree as ET
import numpy as np


@dataclass(frozen=True)
class Staircase:
    riser: float = .02
    tread: float = .18
    count: int = 4
    start: float = .45
    width: float = 1.
    descending: bool = False

    def level(self, x):
        level=np.clip(np.floor((np.asarray(x)-self.start)/self.tread)+1,0,self.count)
        return self.count-level if self.descending else level

    def height(self, x, y=0.):
        return np.where(np.abs(y)<=self.width/2, self.level(x)*self.riser, 0.)

    def as_dict(self):
        return asdict(self)


def scene_xml(source_xml, course: Staircase):
    root=ET.fromstring(source_xml)
    world=root.find('worldbody')
    ground=world.find("geom[@name='ground']")
    # Avoid coincident support surfaces. The five terrain segments provide the
    # driving surface; the plane is the floor outside the course.
    ground.set('pos','0 0 -.002')
    boundaries=[-1., *[course.start+i*course.tread for i in range(course.count)], 3.]
    for j,(left,right) in enumerate(zip(boundaries[:-1],boundaries[1:])):
        height=course.riser*(course.count-j if course.descending else j)
        body=ET.SubElement(world,'body',name=f'stair_segment_{j}',mocap='true',
                           pos=f'{(left+right)/2} 0 {height-.5}')
        ET.SubElement(body,'geom',name=f'stair_surface_{j}',type='box',
                      size=f'{(right-left)/2} {course.width/2} .5',
                      rgba='.42 .46 .48 1',contype='2',conaffinity='5')
    base=world.find("body[@name='chassis']")
    pos=np.fromstring(base.get('pos'),sep=' ')
    pos[2]+=course.height(pos[0],pos[1])
    base.set('pos',' '.join(map(str,pos)))
    return ET.tostring(root,encoding='unicode')
