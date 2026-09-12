"""Wheel-leg stair curriculum with per-world kinematic terrain segments."""
import math
from pathlib import Path
import torch
import warp as wp
from .env import LocomotionEnv
from .terrain import Staircase, scene_xml


class StairEnv(LocomotionEnv):
    def __init__(self, model_path, worlds=256, seed=47, max_riser=.02, output_dir=None,
                 lift_height=.055,heading_control=False,ascent_only=False,min_riser=.006,speed=None,leg_scale=.18,
                 descent_only=False,crouch_command=0.,yaw_correction_limit=.4,lane_control=False,
                 tread=.18,initial_yaw_range=0.,start_x_range=0.):
        self.course=Staircase(riser=max_riser,tread=tread)
        self.initial_yaw_range=initial_yaw_range
        self.start_x_range=start_x_range
        self.max_riser=max_riser
        self.lift_height=lift_height
        self.heading_control=heading_control
        self.ascent_only=ascent_only
        self.descent_only=descent_only
        self.crouch_command=crouch_command
        self.yaw_correction_limit=yaw_correction_limit
        self.lane_control=lane_control
        if ascent_only and descent_only:raise ValueError('Choose one stair direction')
        if not 0<=crouch_command<=1:raise ValueError('Invalid crouch command')
        if not 0<yaw_correction_limit<=1.2:raise ValueError('Invalid heading correction bound')
        self.min_riser=min_riser
        self.speed=speed
        self.leg_scale=leg_scale
        self.terrain_ready=False
        output=Path(output_dir)/'stairs.xml'
        output.write_text(scene_xml(Path(model_path).read_text(),self.course))
        super().__init__(output,worlds,seed,random_commands=True)
        self.risers=torch.zeros(worlds,device=self.device)
        self.descending=torch.zeros(worlds,dtype=torch.bool,device=self.device)
        self.mocap=wp.to_torch(self.backend.data.mocap_pos)
        self.phase_offsets=torch.tensor([0.,.5,.75,.25],device=self.device)
        self.feet_xy=torch.tensor([[.115,.146],[.115,-.146],[-.115,.146],[-.115,-.146]],device=self.device)
        self.max_episode_length=1000
        self.gait_period=3.2
        self.terrain_ready=True
        self.reset(torch.ones(worlds,dtype=torch.bool,device=self.device))

    def reset(self,mask):
        super().reset(mask)
        if not self.terrain_ready:return
        # One fifth of resets remain flat, so the policy must also stop lifting
        # and return to rolling when it reaches level ground.
        samples=torch.rand(self.num_envs,device=self.device)
        h=torch.where(samples<.2,0.,self.min_riser+(self.max_riser-self.min_riser)*torch.rand_like(samples))
        self.risers[mask]=h[mask]
        self.descending[mask]=((torch.rand_like(samples)>.5) | self.descent_only)[mask] & (not self.ascent_only)
        for j in range(5):
            top=torch.where(self.descending,4-j,j)*self.risers
            self.mocap[mask,j,2]=top[mask]-.5
        self.backend.q[mask,2]+=torch.where(self.descending,self.risers*4,0.)[mask]
        # Change only the episode's initial placement, before physics resumes.
        # The actor must handle a different contact/gait alignment on each reset.
        if self.initial_yaw_range:
            yaw=(2*torch.rand_like(samples)-1)*self.initial_yaw_range
            self.backend.q[mask,3]=torch.cos(yaw[mask]/2)
            self.backend.q[mask,4:6]=0
            self.backend.q[mask,6]=torch.sin(yaw[mask]/2)
        if self.start_x_range:
            self.backend.q[mask,0]+=(2*torch.rand_like(samples[mask])-1)*self.start_x_range

    def sample_commands(self,mask):
        n=self.num_envs
        commands=torch.zeros((n,3),device=self.device)
        commands[:,0]=.08+.06*torch.rand(n,device=self.device) if self.speed is None else self.speed
        commands[:,2]=self.crouch_command
        self.command[mask]=commands[mask]

    def query(self,local_xy):
        q=self.backend.q
        w,x,y,z=q[:,3:7].unbind(-1)
        yaw=torch.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
        cos,sin=torch.cos(yaw)[:,None],torch.sin(yaw)[:,None]
        px=q[:,:1]+cos*local_xy[:,0]-sin*local_xy[:,1]
        py=q[:,1:2]+sin*local_xy[:,0]+cos*local_xy[:,1]
        level=torch.clamp(torch.floor((px-self.course.start)/self.course.tread)+1,0,4)
        level=torch.where(self.descending[:,None],4-level,level)
        return torch.where(py.abs()<=self.course.width/2,level*self.risers[:,None],0.)

    def terrain_heights(self):
        if not self.terrain_ready:return super().terrain_heights()
        return self.query(self.scan_xy)

    def ground_reference(self):
        if not self.terrain_ready:return super().ground_reference()
        return self.query(self.feet_xy).mean(-1)

    def task_failures(self):
        # Leaving the staircase is a failed navigation episode, not a way to
        # keep earning forward-velocity reward on the easier floor beside it.
        return (self.backend.q[:,1].abs()>.28) | (self.backend.q[:,0]<-.15)

    def task_metrics(self):
        q=self.backend.q
        return {'course_progress_x':q[:,0].mean(),
                'course_clear_fraction':(q[:,0]>1.3).float().mean(),
                'lane_exit_fraction':(q[:,1].abs()>.28).float().mean()}

    def task_reward(self,height_error):
        q,v=self.backend.q,self.backend.v
        w,x,y,z=q[:,3:7].unbind(-1)
        forward_x=1-2*(y*y+z*z)
        rough=self.terrain_heights().amax(-1)-self.terrain_heights().amin(-1)>.004
        # Reward progress along the staircase, rather than body-forward motion
        # in any heading. Permit body height to bridge discrete tread edges.
        return (4*v[:,0]+1.5*(forward_x-1)-8*q[:,1].square()
                +rough*1.5*height_error.square()/.0004)

    def targets(self,action):
        target=super().targets(action)
        # The reference only acts where the local scan sees a height change.
        # It is expressed as bounded joint targets, never a forced base/foot pose.
        scan=self.terrain_heights()
        active=((scan.max(-1).values-scan.min(-1).values)>.004) & (self.command[:,0]>.015)
        phase=(self.episode_length_buf[:,None]*self.dt/self.gait_period-self.phase_offsets)%1
        lift=torch.where(phase<.25,self.lift_height*torch.sin(math.pi*phase/.25)**2,0.)*active[:,None]
        dx=torch.where(phase<.25,-.025*torch.cos(math.pi*phase/.25),.05*(.5-(phase-.25)/.75))*active[:,None]
        down=.172812737-.035*self.crouch[:,None]-lift
        beta=-self.fronts*torch.acos(torch.clamp((down**2+dx**2-.09**2-.11**2)/(2*.09*.11),-1.,1.))
        theta=torch.atan2(dx,down)-torch.atan2(.11*torch.sin(beta),.09+.11*torch.cos(beta))
        theta0=self.fronts*math.atan2(.05,.074833147)
        beta0=-self.fronts*(math.atan2(.05,.09797959)+math.atan2(.05,.074833147))
        target[:,0::4]=torch.clamp(self.leg_scale*action[:,0::4],-.45,.45)
        target[:,1::4]=self.sides*(theta0-theta)+self.leg_scale*action[:,1::4]
        target[:,2::4]=self.sides*(beta0-beta)+self.leg_scale*action[:,2::4]
        target[:,1::4].clamp_(-.7,.7)
        target[:,2::4].clamp_(-1.2,1.2)
        if self.heading_control:
            w,x,y,z=self.backend.q[:,3:7].unbind(-1)
            yaw=torch.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
            desired=torch.clamp(torch.atan2(-self.backend.q[:,1],torch.full_like(yaw,.5)),-.4,.4) if self.lane_control else torch.zeros_like(yaw)
            error=torch.atan2(torch.sin(desired-yaw),torch.cos(desired-yaw))
            correction=torch.clamp(1.5*error-.25*self.backend.v[:,5],-self.yaw_correction_limit,self.yaw_correction_limit)
            target[:,3::4]-=correction[:,None]*.146/.048
        return target
