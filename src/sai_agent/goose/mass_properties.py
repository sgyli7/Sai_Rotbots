"""Aggregate SI rigid components with their own COM-centred inertia tensors."""
import numpy as np


def aggregate_rigid_components(items, origin_m):
    origin=np.asarray(origin_m,dtype=float)
    if origin.shape!=(3,) or not np.isfinite(origin).all() or not items:
        raise ValueError('finite XYZ origin and nonempty components required')
    masses=[];centres=[];tensors=[]
    for item in items:
        mass=float(item['mass_kg']);centre=np.asarray(item['center_m'],dtype=float)
        tensor=np.asarray(item['inertia_at_com_kg_m2'],dtype=float)
        if mass<=0 or not np.isfinite(mass) or centre.shape!=(3,) or not np.isfinite(centre).all() or tensor.shape!=(3,3) or not np.isfinite(tensor).all():
            raise ValueError('invalid SI component')
        if not np.allclose(tensor,tensor.T,atol=1e-12) or np.linalg.eigvalsh(tensor).min()< -1e-12:
            raise ValueError('symmetric nonnegative component inertia required')
        masses.append(mass);centres.append(centre);tensors.append(tensor)
    mass=sum(masses);centre=sum(m*c for m,c in zip(masses,centres))/mass
    tensor=np.zeros((3,3))
    for m,c,I in zip(masses,centres,tensors):
        d=c-centre;tensor+=I+m*((d@d)*np.eye(3)-np.outer(d,d))
    values=np.linalg.eigvalsh(tensor)
    if values.min()<=0 or values[-1]>values[:2].sum()+1e-10:
        raise ValueError('positive physical aggregate inertia required')
    return dict(mass_kg=mass,com_local_m=(centre-origin).tolist(),inertia_at_com_body_kg_m2=tensor.tolist())
