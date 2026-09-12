"""Versioned control contract shared by training and deployment.

All public state uses MuJoCo right-handed X-forward, Y-left, Z-up SI units.
The policy is a bounded residual on an explicit wheel-speed/body-height reference.
"""
import math
import numpy as np

CONTROL_DT = .02
STAND_HEIGHT = .2192
CROUCH_DROP = .035
OBS_SIZE = 82
ACTION_SIZE = 16
SIDES = np.array([1., -1., 1., -1.])
FRONTS = np.array([1., 1., -1., -1.])
LEG_INDICES = np.array([i for i in range(16) if i % 4 != 3])
WHEEL_INDICES = np.array([3, 7, 11, 15])
SCAN_XY = np.array([(x, y) for x in [-.36, -.18, 0., .18, .36, .54, .72, .9]
                    for y in [-.24, 0., .24]])


class HeadingHold:
    """Bounded outer steering loop for deployment across contact solvers.

    Integrates requested yaw rate; observes actual attitude/gyro. It changes
    only wheel-speed targets, never pose or joint state. Reset while parked.
    """
    def __init__(self,max_correction=.4):
        if not 0<max_correction<=1.2:raise ValueError('Heading correction limit must be in (0, 1.2] rad/s')
        self.max_correction=max_correction
        self.desired=None

    def apply(self,target,command,yaw,yaw_rate,dt=CONTROL_DT):
        if self.desired is None or np.linalg.norm(command[:2])<1e-5:
            self.desired=yaw
        if np.linalg.norm(command[:2])<1e-5:return target
        self.desired+=float(command[1])*dt
        error=math.atan2(math.sin(self.desired-yaw),math.cos(self.desired-yaw))
        correction=np.clip(1.5*error-.25*(yaw_rate-command[1]),-self.max_correction,self.max_correction)
        result=target.copy()
        result[3::4]-=correction*.146/.048
        return result


def filter_action_numpy(action,command):
    """Zero velocity command explicitly parks wheels and uses the height IK.

    This is ordinary torque-controlled braking, not a frozen body or pose reset.
    The policy's unused residual is also excluded from previous-action history.
    """
    return np.clip(np.asarray(action),-1.,1.) if np.linalg.norm(command[:2])>1e-5 else np.zeros(16)


def targets_numpy(action, command, crouch):
    action = filter_action_numpy(action,command)
    down = .172812737 - CROUCH_DROP * crouch
    beta = -FRONTS * np.arccos(np.clip((down**2 - .09**2 - .11**2) / (2*.09*.11), -1., 1.))
    theta = -np.arctan2(.11*np.sin(beta), .09+.11*np.cos(beta))
    theta0 = FRONTS * math.atan2(.05, .074833147)
    beta0 = -FRONTS * (math.atan2(.05, .09797959) + math.atan2(.05, .074833147))
    target = .18 * action.copy()
    target[1::4] += SIDES * (theta0 - theta)
    target[2::4] += SIDES * (beta0 - beta)
    target[3::4] = SIDES * ((command[0] - command[1] * SIDES * .146) / .048 + 6 * action[3::4])
    return target


def targets_stairs_numpy(action,command,crouch,phase_cycles,scan_heights,lift_height=.055,leg_scale=.18,stride=.05):
    action=filter_action_numpy(action,command)
    target=targets_numpy(action,command,crouch)
    target[0::4]=np.clip(leg_scale*action[0::4],-.45,.45)
    active=np.ptp(scan_heights)>.004 and command[0]>.015
    phase=(phase_cycles-np.array([0.,.5,.75,.25]))%1
    lift=np.where(phase<.25,lift_height*np.sin(math.pi*phase/.25)**2,0.)*active
    dx=np.where(phase<.25,-stride/2*np.cos(math.pi*phase/.25),stride*(.5-(phase-.25)/.75))*active
    down=.172812737-CROUCH_DROP*crouch-lift
    beta=-FRONTS*np.arccos(np.clip((down**2+dx**2-.09**2-.11**2)/(2*.09*.11),-1.,1.))
    theta=np.arctan2(dx,down)-np.arctan2(.11*np.sin(beta),.09+.11*np.cos(beta))
    theta0=FRONTS*math.atan2(.05,.074833147)
    beta0=-FRONTS*(math.atan2(.05,.09797959)+math.atan2(.05,.074833147))
    target[1::4]=np.clip(SIDES*(theta0-theta)+leg_scale*action[1::4],-.7,.7)
    target[2::4]=np.clip(SIDES*(beta0-beta)+leg_scale*action[2::4],-1.2,1.2)
    return target


def observation_numpy(q, v, command, crouch, previous, phase, terrain_heights):
    w, x, y, z = q[3:7]
    r = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                  [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                  [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    jointq, jointv = q[7:], v[6:]
    scan = np.clip((np.asarray(terrain_heights) - (q[2]-STAND_HEIGHT))*5, -2., 2.)
    return np.concatenate([r[2], r.T @ v[:3], v[3:6],
        [command[0], command[1], crouch], jointq[LEG_INDICES],
        jointv[LEG_INDICES]*.1, jointv[WHEEL_INDICES]*SIDES*.1, previous,
        [math.sin(phase), math.cos(phase)], scan]).astype(np.float32)


def torque_numpy(q, v, target):
    u = np.clip(80*(target-q[7:])-2*v[6:], -8., 8.)
    u[3::4] = np.clip(.4*(target[3::4]-v[9::4]), -1.3, 1.3)
    return u
