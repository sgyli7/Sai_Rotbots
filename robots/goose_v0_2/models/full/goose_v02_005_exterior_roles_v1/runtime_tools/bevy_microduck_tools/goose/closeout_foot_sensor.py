"""Two-foot native contact view over four explicit closeout sole leaves.

The upstream sensor still creates one native sensor per named leaf. This view
sums the two same-foot global forces and combines found flags before tracking
air/contact time, so side-shell contacts cannot be mistaken for sole contacts.
"""
from dataclasses import dataclass

from mjlab.sensor import ContactSensorCfg
from mjlab.sensor.contact_sensor import ContactSensor


@dataclass
class CloseoutFootContactSensorCfg(ContactSensorCfg):
    groups: tuple[tuple[str, str], tuple[str, str]] = ((), ())

    def build(self):
        return CloseoutFootContactSensor(self)


class CloseoutFootContactSensor(ContactSensor):
    """Expose right/left force and contact state, not four separate feet."""

    def _group_indices(self):
        raw = ContactSensor.primary_names.fget(self)
        groups = self.cfg.groups
        if len(groups) != 2 or any(len(group) != 2 for group in groups):
            raise ValueError('Closeout foot sensor needs two explicit leaves per side')
        flattened = [name for group in groups for name in group]
        if len(set(flattened)) != 4 or len(raw) != 4:
            raise ValueError('Closeout foot sensor requires four distinct native primaries')
        indices = []
        for group in groups:
            pair = []
            for name in group:
                matches = [i for i, value in enumerate(raw)
                           if value == name or value.endswith('/' + name)]
                if len(matches) != 1:
                    raise ValueError('Closeout foot primary does not resolve exactly once: '+name)
                pair.append(matches[0])
            indices.append(pair)
        return indices

    @property
    def primary_names(self):
        raw = ContactSensor.primary_names.fget(self)
        if not raw:
            return []
        self._group_indices()
        return ['right_sole', 'left_sole']

    def _extract_sensor_data(self):
        data = super()._extract_sensor_data()
        indices = self._group_indices()
        if self.cfg.num_slots != 1 or self.cfg.reduce != 'netforce':
            raise ValueError('Grouped sole contact requires one native net-force slot')
        if data.found is None or data.force is None:
            raise ValueError('Grouped sole contact requires found and force')
        data.found = data.found[:, indices].sum(dim=2)
        data.force = data.force[:, indices, :].sum(dim=2)
        return data
