"""SO101 source-axis FK for the audited scripted contact task; millimetres."""
import json
import numpy as np
from scipy.spatial.transform import Rotation
from .paths import resource_root
GROUPS=["base","pan_carrier","upper","lower","wrist","gripper","moving_jaw"]

def metre(h):
    h=h.copy();h[:3,3]*=.001;return h

class Arm:
    def __init__(self):
        self.axes=json.loads((resource_root()/"models/tasks/so101-axes.json").read_text())
        self.root = np.eye(4)
        # Clock the original base 90 degrees from layout_r0. The front pose
        # then uses pan delta +90, leaving travel to the rear at about -90.
        # This changes local base installation, not its front-centre location.
        self.root[:3,:3] = np.eye(3)
        self.root[:3,3] = [83,0,256.6057044657792]
        # Analytic distal planar face 61 of Wrist_Roll_Follower_SO101_v10, as
        # imported in derived/so101_links/gripper.step (child 0).
        self.fixed_contact = np.array([6.981563026764376,-220.18122292575873,143.28642212881962])
        self.contact_normal = np.array([-.01745207628636318,-.008801353052346078,.9998089623611818])
        forward = -np.array(self.axes[4]["direction"])
        forward -= self.contact_normal * np.dot(forward,self.contact_normal)
        self.tool_forward = forward / np.linalg.norm(forward)

    def pose(self, delta_degrees, chassis_drop_mm=0):
        root = self.root.copy()
        root[2,3] -= chassis_drop_mm
        chain = np.eye(4)
        frames = {"base": root}
        for name,axis,angle in zip(GROUPS[1:], self.axes, delta_degrees):
            r = Rotation.from_rotvec(np.asarray(axis["direction"])*np.deg2rad(angle)).as_matrix()
            p = np.asarray(axis["point_mm"])
            t = np.eye(4); t[:3,:3]=r; t[:3,3]=p-r@p
            chain = chain @ t
            frames[name] = root @ chain
        return frames

    def tool(self, delta_degrees, chassis_drop_mm=0, object_width_mm=30):
        h = self.pose(delta_degrees,chassis_drop_mm)["gripper"]
        source_point = self.fixed_contact + self.contact_normal*object_width_mm*.5
        return (h[:3,:3]@source_point+h[:3,3], h[:3,:3]@self.tool_forward,
                h[:3,:3]@self.contact_normal)
