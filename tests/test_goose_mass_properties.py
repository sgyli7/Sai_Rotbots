import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from sai_agent.goose.mass_properties import aggregate_rigid_components


@pytest.mark.parametrize('rotation_vector',[[0,0,0],[.4,-.3,.7]])
def test_two_spaced_spherical_masses_obey_parallel_axis_theorem(rotation_vector):
    rotation=Rotation.from_rotvec(rotation_vector).as_matrix();origin=np.array([9,-4,11])
    items=[dict(mass_kg=1,center_m=(origin+rotation@np.array([x,0,0])).tolist(),inertia_at_com_kg_m2=(np.eye(3)*.1).tolist()) for x in [-1,1]]
    result=aggregate_rigid_components(items,origin)
    assert result['mass_kg']==2
    np.testing.assert_allclose(result['com_local_m'],[0,0,0],atol=1e-12)
    np.testing.assert_allclose(result['inertia_at_com_body_kg_m2'],rotation@np.diag([.2,2.2,2.2])@rotation.T,atol=1e-12)


def test_impossible_principal_moments_are_rejected():
    item=dict(mass_kg=1,center_m=[0,0,0],inertia_at_com_kg_m2=np.diag([1,1,4]).tolist())
    with pytest.raises(ValueError,match='physical'):aggregate_rigid_components([item],[0,0,0])
