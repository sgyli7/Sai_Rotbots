# Own cross-flow plate stack: oil and water remain separate actual cavities.
oilfluid=[];oilroutes=[];oilnodes={};oiledges=[]
def oilwet(id,body,m,**kw):oilfluid.append({'id':id,'body':body,'mesh':m,**kw})
c=np.array([-.20,0,1.77]);oilms=[];waterms=[]
for i in range(16):
 z=c[2]-.0475+i*.006
 if i%2==0:oilms.append(box([c[0],c[1],z],[.178,.174,.0035]))
 else:waterms.append(box([c[0],c[1],z],[.148,.218,.0035]))
# Oil collectors are beyond water X ends; water collectors beyond oil Y ends.
for sg in [-1,1]:
 oilms.append(cylinder(c+[sg*.086,0,-.0495],c+[sg*.086,0,.0495],.006))
 waterms.append(cylinder(c+[0,sg*.105,-.0495],c+[0,sg*.105,.0495],.006))
# Ports on each collector connect actual native fluid through the full shell.
osp=node('e2_oil_HX_in',c+[-.086,0,.075],'torso');orp=node('e2_oil_HX_out',c+[.086,0,-.075],'torso')
wsp=node('e2_oil_HX_water_supply',c+[0,-.105,.075],'torso');wrp=node('e2_oil_HX_water_return',c+[0,.105,-.075],'torso')
oilms += [cylinder(c+[-.086,0,.040],nodes[osp]['center_world_m'],.005),cylinder(c+[.086,0,-.040],nodes[orp]['center_world_m'],.005)]
waterms += [cylinder(c+[0,-.105,.040],nodes[wsp]['center_world_m'],.005),cylinder(c+[0,.105,-.040],nodes[wrp]['center_world_m'],.005)]
oh=union(oilms);wh=union(waterms);hxmix=float(trimesh.boolean.intersection([oh,wh],engine='manifold').volume)
assert hxmix<1e-10
hxmat=diff(box(c,[.204,.244,.126]),[oh,wh]);emit('e2_dual_fluid_HX_material','torso','oil_water_HX_native_material',hxmat,own='Own crossflow alternating16plate channels8oil/8water; finite separating metal >=2.5mm between opposing channel planes; real ports/collectors. No manufacturer UA, pressure-fatigue/braze qualification or mixing-fault guarantee',heat_capacity_is_unknown=True,oil_water_native_intersection_m3=hxmix)
for id,sg,xy in [(osp,1,[-.086,0]),(orp,-1,[.086,0]),(wsp,1,[0,-.105]),(wrp,-1,[0,.105])]:
 emit(id+'_actual_hollow_port','torso','HX_fitting_native_material',tube(c+[xy[0],xy[1],sg*.063],nodes[id]['center_world_m'],.009,.005),density=2700,own='Finite positive outer port shell encloses the actual oil/water bore outside HX block; seal/thread/port strength unknown')
wet('e2_dual_HX_water_cavity','torso',wh);oilwet('e2_dual_HX_oil_cavity','torso',oh)
targets.append({'id':'e2_true_oil_water_HX','body':'torso','supply':wsp,'return':wrp,'flow':6.0,'source_scope':'Own separate oil/water channels, real positive installation space; pressure/UA/fouling unknown','internal_fluid_CAD_known':False})
