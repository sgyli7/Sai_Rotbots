extends RigidBody3D
## Artificial filter fixture: records actual native contacts, not query overlap.
var peak_contacts: Dictionary = {}
var peak_impulse := 0.0

func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
	for i in range(state.get_contact_count()):
		var peer := state.get_contact_collider(i)
		peak_contacts[peer] = int(peak_contacts.get(peer, 0)) + 1
		peak_impulse = maxf(peak_impulse, state.get_contact_impulse(i).length())
