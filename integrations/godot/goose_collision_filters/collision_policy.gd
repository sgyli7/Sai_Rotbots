extends RefCounted
## Applies the bound task-proxy policy to one robot instance, after joint creation.
## All nine effective source exceptions are explicit here, including MuJoCo's
## four implicit parent exclusions. No layer, name-global or cross-instance mask.

static func pair_key(a: String, b: String) -> String:
	return a + "|" + b if a < b else b + "|" + a

static func validate(policy: Dictionary, plant: Dictionary) -> String:
	if policy.get("schema") != "goose_collision_filter_policy_v1" or plant.get("schema") != "goose_task_proxy_plant_v1":
		return "Unsupported collision policy/plant schema"
	if policy.get("candidate_id") != plant.get("candidate_id") or policy.get("candidate_id") != "goose_task_proxy_11_v1":
		return "Candidate identity mismatch"
	if policy.get("model_sha256") != plant.get("model_sha256") or policy.get("contract_sha256") != plant.get("derived_contract_sha256"):
		return "Source identity mismatch"
	if policy.get("self_collision_default") != "enabled" or policy.get("exception_scope") != "one_robot_instance":
		return "Self contact and instance scope must be preserved"
	for key in ["ground_collision", "object_collision"]:
		if policy.get(key) != "enabled_for_every_role": return "External contact must be preserved"
	if policy.get("other_robot_collision") != "enabled_including_same_named_roles":
		return "Cross-instance contact must be preserved"
	var parents: Dictionary = {}
	var roles: Dictionary = {}
	var owners: Dictionary = {}
	for body in plant.get("bodies", []):
		if parents.has(body.name): return "Duplicate source body"
		parents[body.name] = body.parent
	for collider in plant.get("colliders", []):
		if roles.has(collider.name) or owners.has(collider.body): return "Duplicate role/owner"
		if not parents.has(collider.body): return "Unknown source body"
		roles[collider.name] = collider.body
		owners[collider.body] = collider.name
	if roles.size() != 11 or parents.size() != 21: return "Wrong task-proxy shape/body counts"
	var exclusions: Dictionary = {}
	for pair in plant.get("exclusions", []):
		if pair.size() != 2: return "Invalid source exclusion"
		exclusions[pair_key(pair[0], pair[1])] = true
	var seen: Dictionary = {}
	for row in policy.get("pairs", []):
		var first: String = row.get("first", "")
		var second: String = row.get("second", "")
		if first == second or not roles.has(first) or not roles.has(second): return "Unknown collision role"
		var key := pair_key(first, second)
		if seen.has(key): return "Duplicate collision pair"
		seen[key] = true
		var a: String = roles[first]
		var b: String = roles[second]
		var expected: bool = not (parents[a] == b or parents[b] == a or exclusions.has(pair_key(a, b)))
		if typeof(row.get("collision_enabled")) != TYPE_BOOL or row.collision_enabled != expected:
			return "Pair differs from effective source filtering: " + key
		if not expected:
			var chain: Array = row.get("connected_body_chain", [])
			if chain.size() < 2: return "Missing mechanical connection witness"
			if not ((chain[0] == a and chain[-1] == b) or (chain[0] == b and chain[-1] == a)):
				return "Wrong connection endpoints"
			for i in range(chain.size()-1):
				if not parents.has(chain[i]) or parents[chain[i]] != chain[i+1]: return "Invalid connection chain"
			for i in range(1, chain.size()-1):
				if owners.has(chain[i]): return "Exclusion crosses another exterior role"
	if seen.size() != roles.size()*(roles.size()-1)/2: return "Incomplete collision pair table"
	return ""

static func configure_joint(joint: RID) -> void:
	# Joint defaults must not introduce additional unlisted exclusions.
	PhysicsServer3D.joint_disable_collisions_between_bodies(joint, false)

static func apply(policy: Dictionary, plant: Dictionary, role_bodies: Dictionary) -> String:
	var error := validate(policy, plant)
	if not error.is_empty(): return error
	if role_bodies.size() != plant.colliders.size(): return "Incomplete instance role handles"
	var handles: Dictionary = {}
	for collider in plant.colliders:
		var body = role_bodies.get(collider.name)
		if not body is PhysicsBody3D or not is_instance_valid(body): return "Invalid instance body"
		if handles.has(body.get_rid()): return "Two roles alias one instance body"
		handles[body.get_rid()] = true
	# Validation above finishes before any mutation. Clear stale intra-instance
	# exceptions for retained pairs, then apply only the bound exceptions.
	for row in policy.pairs:
		var a: PhysicsBody3D = role_bodies[row.first]
		var b: PhysicsBody3D = role_bodies[row.second]
		if row.collision_enabled:
			a.remove_collision_exception_with(b)
			b.remove_collision_exception_with(a)
		else:
			a.add_collision_exception_with(b)
			b.add_collision_exception_with(a)
	return verify(policy, role_bodies)

static func verify(policy: Dictionary, role_bodies: Dictionary) -> String:
	for row in policy.pairs:
		var a: PhysicsBody3D = role_bodies[row.first]
		var b: PhysicsBody3D = role_bodies[row.second]
		var ab := a.get_collision_exceptions().has(b)
		var ba := b.get_collision_exceptions().has(a)
		if ab != (not row.collision_enabled) or ba != (not row.collision_enabled):
			return "Exception readback differs: " + pair_key(row.first, row.second)
		# External exclusions are not owned by this helper; reject them rather
		# than silently accepting a global/self-only collision setup.
		for excluded in a.get_collision_exceptions():
			if not role_bodies.values().has(excluded): return "Exception escapes this robot instance"
	return ""
