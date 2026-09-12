extends Node3D
# The policy supplies joint/speed targets. Godot/Jolt owns every body state.
var robot
var peer := StreamPeerTCP.new()
var buffer := ""
var port := 19341
var test_case := ""
var output := ""
var screenshot := ""
var captured := false
var cleared_at := -1.0
var duration := 12.0
var visuals := true
var riser := 0.0
var descending := false
var records: Array = []
var input_events: Array = []
var injected: Dictionary = {}
var command: Dictionary = {}
var finished := false
var camera: Camera3D
var hud: Label
var sensor_views: Array = []
var specification: Dictionary

func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--port="):port=int(arg.split("=")[1])
		elif arg.begins_with("--case="):test_case=arg.split("=")[1]
		elif arg.begins_with("--output="):output=arg.substr(9)
		elif arg.begins_with("--screenshot="):screenshot=arg.substr(13)
		elif arg.begins_with("--duration="):duration=float(arg.split("=")[1])
		elif arg.begins_with("--stairs="):riser=float(arg.split("=")[1])
		elif arg=="--descending":descending=true
		elif arg=="--no-visuals":visuals=false
	for pair in [["forward",KEY_W],["reverse",KEY_S],["left",KEY_A],["right",KEY_D],["crouch",KEY_SHIFT]]:
		InputMap.add_action(pair[0])
		var event := InputEventKey.new()
		event.physical_keycode=pair[1]
		InputMap.action_add_event(pair[0],event)
	specification=JSON.parse_string(FileAccess.get_file_as_string("res://sai_agent/robot.json"))
	robot=load("res://robot.gd").new()
	add_child(robot)
	build_ground()
	robot.setup(specification,visuals,4*riser if descending else 0.0)
	if visuals:build_view()
	peer.connect_to_host("127.0.0.1",port)
	var deadline := Time.get_ticks_msec()+10000
	while peer.get_status()!=StreamPeerTCP.STATUS_CONNECTED:
		peer.poll()
		if Time.get_ticks_msec()>deadline:
			push_error("Sai controller connection timeout")
			get_tree().quit(2)
			return
		OS.delay_usec(1000)
	peer.set_no_delay(true)
	print("SAI_GODOT_READY bodies=",robot.bodies.size()," joints=",robot.drives.size())

func box_surface(name_text: String,left: float,right: float,width: float,top: float,depth: float) -> void:
	var body := StaticBody3D.new()
	body.name=name_text
	body.collision_layer=2
	body.collision_mask=5
	body.position=Vector3((left+right)/2,top-depth/2,0)
	var pm := PhysicsMaterial.new()
	pm.friction=.8
	body.physics_material_override=pm
	add_child(body)
	var shape := BoxShape3D.new()
	shape.size=Vector3(right-left,depth,width)
	shape.margin=.0002
	var cs := CollisionShape3D.new()
	cs.shape=shape
	body.add_child(cs)
	if visuals:
		var mesh := BoxMesh.new()
		mesh.size=shape.size
		var mi := MeshInstance3D.new()
		mi.mesh=mesh
		mi.material_override=robot.material(Color(.57,.61,.64))
		body.add_child(mi)

func build_ground() -> void:
	box_surface("ground",-10,10,20,-.002 if riser>0 else 0.,.1)
	if riser<=0:return
	var boundaries := [-1.,.45,.63,.81,.99,3.]
	for i in range(5):
		box_surface("stair_"+str(i),boundaries[i],boundaries[i+1],1.,riser*(4-i if descending else i),1.)

func inject_test_keys(time_s: float) -> void:
	var desired: Dictionary = {}
	if time_s>=1:
		if test_case in ["W","WA","W_shift"]:desired[KEY_W]=true
		if test_case=="S":desired[KEY_S]=true
		if test_case in ["A","WA"]:desired[KEY_A]=true
		if test_case=="D":desired[KEY_D]=true
		if test_case in ["shift","W_shift"] and time_s>=3 and time_s<8:desired[KEY_SHIFT]=true
	for key in [KEY_W,KEY_S,KEY_A,KEY_D,KEY_SHIFT]:
		var pressed: bool=desired.has(key)
		if pressed!=injected.get(key,false):
			var event := InputEventKey.new()
			event.keycode=key
			event.physical_keycode=key
			event.pressed=pressed
			Input.parse_input_event(event)
			injected[key]=pressed
			input_events.append({"time":time_s,"key":key,"pressed":pressed})

func movement_command() -> Array:
	var speed := .14 if test_case in ["WA","W_shift"] else .16
	var yaw_speed := .3 if test_case=="WA" else .45
	if cleared_at>=0:return [0.,0.,0.]
	return [speed*Input.get_axis("reverse","forward"),yaw_speed*Input.get_axis("right","left"),1. if Input.is_action_pressed("crouch") else 0.]

func height_scan() -> Array:
	var base: RigidBody3D=robot.bodies.chassis
	var direction: Vector3=base.global_basis*Vector3.RIGHT
	var yaw := atan2(-direction.z,direction.x)
	var heights: Array = []
	for x in [-.36,-.18,0.,.18,.36,.54,.72,.9]:
		for y in [-.24,0.,.24]:
			var sx: float=base.position.x+cos(yaw)*x-sin(yaw)*y
			var sy: float=-base.position.z+sin(yaw)*x+cos(yaw)*y
			var query := PhysicsRayQueryParameters3D.create(Vector3(sx,base.position.y+1.,-sy),Vector3(sx,base.position.y-1.,-sy),2)
			var hit := get_world_3d().direct_space_state.intersect_ray(query)
			heights.append(float(hit.position.y) if not hit.is_empty() else -.002)
	return heights

func exchange(state: Dictionary) -> Dictionary:
	peer.put_data((JSON.stringify(state)+"\n").to_utf8_buffer())
	var deadline := Time.get_ticks_msec()+5000
	while buffer.find("\n")<0:
		peer.poll()
		var count := peer.get_available_bytes()
		if count>0:
			var packet := peer.get_data(count)
			if packet[0]==OK:buffer+=packet[1].get_string_from_utf8()
		elif Time.get_ticks_msec()>deadline:
			push_error("Sai controller response timeout")
			get_tree().quit(2)
			return {}
		else:OS.delay_usec(50)
	var newline := buffer.find("\n")
	var line := buffer.substr(0,newline)
	buffer=buffer.substr(newline+1)
	return JSON.parse_string(line)

func _physics_process(_delta: float) -> void:
	if finished or robot==null or peer.get_status()!=StreamPeerTCP.STATUS_CONNECTED:return
	var state: Dictionary=robot.state()
	if robot.tick%40==0:
		if test_case!="":inject_test_keys(float(state.time))
		state["robot_id"]="Sai_Agent_001"
		state["command"]=movement_command()
		state["terrain_heights"]=height_scan()
		state["physics_owner"]="Godot/Jolt"
		command=exchange(state)
		if command.is_empty():return
		state["policy_action"]=command.policy_action
		state["policy_observation"]=command.policy_observation
		state["upright"]=robot.bodies.chassis.global_basis.y.y
		var wheel_positions: Array=[]
		var supported := 0
		for name in ["front_left_wheel","front_right_wheel","rear_left_wheel","rear_right_wheel"]:
			var wheel: RigidBody3D=robot.bodies[name]
			wheel_positions.append(robot.source(wheel.position))
			if not wheel.get_colliding_bodies().is_empty():supported+=1
		state["wheel_positions"]=wheel_positions
		state["wheels_supported"]=supported
		state["controller_stage"]=command.stage
		if riser>0 and test_case=="W" and cleared_at<0:
			var cleared := true
			for position in wheel_positions:
				if position[0]<=1.07:cleared=false
			if cleared:cleared_at=float(state.time)
		if test_case!="":records.append(state)
		if (test_case!="" and float(state.time)>=duration) or float(state.upright)<.6 or (cleared_at>=0 and float(state.time)-cleared_at>=3):
			finish_run()
			return
	robot.apply_command(state,command)

func finish_run() -> void:
	finished=true
	peer.put_data((JSON.stringify({"finish":true})+"\n").to_utf8_buffer())
	if output!="":
		var file := FileAccess.open(output,FileAccess.WRITE)
		file.store_string(JSON.stringify({"robot_id":"Sai_Agent_001","case":test_case,
			"physics":"Godot/Jolt","engine":Engine.get_version_info().string,
			"physics_hz":2000,"controller_hz":50,"body_count":robot.bodies.size(),
			"riser":riser,"descending":descending,"cleared_at":cleared_at,
			"hinges":23,"sliders":2,"input_events":input_events,"samples":records}))
		file.close()
	print("SAI_GODOT_FINISHED seconds=",robot.tick*.0005)
	get_tree().quit()

func build_view() -> void:
	var light := DirectionalLight3D.new()
	light.rotation_degrees=Vector3(-55,-35,0)
	light.shadow_enabled=true
	light.light_energy=.7
	add_child(light)
	var environment := WorldEnvironment.new()
	environment.environment=Environment.new()
	environment.environment.background_mode=Environment.BG_COLOR
	environment.environment.background_color=Color(.72,.77,.82)
	environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	environment.environment.ambient_light_color=Color.WHITE
	environment.environment.ambient_light_energy=.22
	add_child(environment)
	camera=Camera3D.new()
	camera.fov=45
	add_child(camera)
	camera.current=true
	var canvas := CanvasLayer.new()
	add_child(canvas)
	hud=Label.new()
	hud.position=Vector2(20,16)
	hud.add_theme_color_override("font_color",Color(.05,.07,.1))
	hud.add_theme_font_size_override("font_size",20)
	canvas.add_child(hud)
	for i in range(specification.cameras.size()):
		var spec: Dictionary=specification.cameras[i]
		var viewport := SubViewport.new()
		viewport.size=Vector2i(320,180)
		viewport.world_3d=get_world_3d()
		viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
		add_child(viewport)
		var sensor := Camera3D.new()
		sensor.fov=spec.pinhole_fovy_deg
		sensor.near=.005
		viewport.add_child(sensor)
		sensor.current=true
		var rect := TextureRect.new()
		rect.texture=viewport.get_texture()
		rect.position=Vector2(940,20+i*200)
		rect.size=Vector2(320,180)
		canvas.add_child(rect)
		sensor_views.append({"camera":sensor,"spec":spec})

func _process(_delta: float) -> void:
	if camera==null or robot==null:return
	var base: RigidBody3D=robot.bodies.chassis
	camera.position=base.position+Vector3(.62,.36,.60)
	camera.look_at(base.position+Vector3(0,.05,0))
	hud.text="Sai_Agent_001\nW/S drive · A/D turn · Shift crouch · Esc quit\n"+str(command.get("stage","connecting"))
	for view in sensor_views:
		var spec: Dictionary=view.spec
		var body: RigidBody3D=robot.bodies[spec.body]
		var position: Vector3=body.global_transform*(robot.gv(spec.optical_center_m)-robot.gv(specification.bodies[spec.body].origin_m))
		view.camera.global_position=position
		view.camera.look_at(position+body.global_basis*robot.gv(spec.forward),body.global_basis*robot.gv(spec.up))
	if Input.is_key_pressed(KEY_ESCAPE):finish_run()
	if screenshot!="" and not captured and robot.tick>1000:
		captured=true
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(screenshot)
