"""Independent analytic witnesses for D's restricted asymmetric contact LP."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'gorilla_d_statics', ROOT / 'scripts/evaluation/evaluate_gorilla_distributed_layout.py')
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)
VERTICES = np.array([[-1., -1., 0.], [-1., 1., 0.], [1., -1., 0.], [1., 1., 0.]])


@pytest.mark.parametrize('gravity_force,peak,feasible', [(-50., .5, True), (-80., 2., False)])
def test_asymmetric_capacity_matches_forced_contact_sum(gravity_force, peak, feasible):
    # Equilibrium fixes the positive-X reaction sum at 60 N. Thus the mapped
    # actuator force is exactly +10 N or -20 N, regardless of solver allocation.
    loads = [{'position_world_m': [.2, -.3, 1.], 'force_world_N': [0., 0., -100.]}]
    models = [{'id': 'analytic', 'force_gravity_N': gravity_force,
               'force_contact_coefficients': [0., 0., 1., 1.],
               'positive_force_hypothesis_N': 20., 'negative_force_hypothesis_N': 10.}]
    result = D.asymmetric_contact_lp(VERTICES, loads, models)
    assert result['minimum_peak_force_hypothesis_use'] == pytest.approx(peak)
    assert result['conditional_normal_force_and_mapped_capacity_feasible'] is feasible
    certificate = result['numerical_dual_certificate']
    assert certificate['valid_with_declared_float_tolerances']
    assert certificate['lower_bound_on_peak_use'] == pytest.approx(peak)
    assert result['physics_accepted'] is False


def test_shared_allocation_is_not_independent_free_corner_extrema():
    # At the center, f0=f3 and f1=f2, hence f0+f1=50. Joint capacities 20/30
    # yield the analytic minimax t=50/(20+30)=1, despite 50 N free maxima.
    loads = [{'position_world_m': [0., 0., 1.], 'force_world_N': [0., 0., -100.]}]
    models = [
        {'id': 'push', 'force_gravity_N': 0., 'force_contact_coefficients': [1., 0., 0., 0.],
         'positive_force_hypothesis_N': 20., 'negative_force_hypothesis_N': 10.},
        {'id': 'pull', 'force_gravity_N': 0., 'force_contact_coefficients': [0., -1., 0., 0.],
         'positive_force_hypothesis_N': 10., 'negative_force_hypothesis_N': 30.},
    ]
    result = D.asymmetric_contact_lp(VERTICES, loads, models)
    assert result['minimum_peak_force_hypothesis_use'] == pytest.approx(1.)
    assert result['normal_reactions_N'] == pytest.approx([20., 30., 30., 20.])
    assert result['conditional_normal_force_and_mapped_capacity_feasible'] is True


@pytest.mark.parametrize('horizontal_force,contact_height', [(10., 0.), (0., .1)])
def test_unsupported_force_or_contact_plane_cannot_claim_feasibility(horizontal_force, contact_height):
    vertices = VERTICES.copy()
    vertices[:, 2] = contact_height
    loads = [{'position_world_m': [0., 0., 1.],
              'force_world_N': [horizontal_force, 0., -100.]}]
    models = [{'id': 'probe', 'force_gravity_N': 0.,
               'force_contact_coefficients': [0., 0., 0., 0.],
               'positive_force_hypothesis_N': 20., 'negative_force_hypothesis_N': 10.}]
    with pytest.raises(ValueError, match='scope exceeded'):
        D.asymmetric_contact_lp(vertices, loads, models)
