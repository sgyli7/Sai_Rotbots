@wp.func
def _area4(
  # In:
  vert: wp.array[wp.vec3],
  vertadr: int,
  polyvert: wp.array[int],
  face_vertadr: int,
  a: int,
  b: int,
  c: int,
  d: int,
) -> float:
  """Returns the area of a quadrilateral on a mesh polygon."""
  va = vert[vertadr + polyvert[face_vertadr + a]]
  vb = vert[vertadr + polyvert[face_vertadr + b]]
  vc = vert[vertadr + polyvert[face_vertadr + c]]
  vd = vert[vertadr + polyvert[face_vertadr + d]]
  return 0.5 * wp.length(wp.cross(va - vc, vb - vd))


@wp.func
def _hull4(
  # In:
  vert: wp.array[wp.vec3],
  vertadr: int,
  polyvert: wp.array[int],
  face_vertadr: int,
  nhull: int,
  a: int,
) -> Tuple[int, wp.vec4i]:
  """Prunes a convex polygon to at most four vertices, keeping anchor `a` (MuJoCo's hull4f)."""
  b = (a + 1) % nhull
  c = (a + 2) % nhull
  d = (a + 3) % nhull
  res = wp.vec4i(a, b, c, d)
  if nhull <= 4:
    return nhull, res

  m = _area4(vert, vertadr, polyvert, face_vertadr, a, b, c, d)
  while True:
    d_next = (d + 1) % nhull
    m_next = _area4(vert, vertadr, polyvert, face_vertadr, a, b, c, d_next)
    if m_next <= m:
      break
    d = d_next
    m = m_next
    res = wp.vec4i(a, b, c, d)
    while True:
      c_next = (c + 1) % nhull
      m_next = _area4(vert, vertadr, polyvert, face_vertadr, a, b, c_next, d)
      if m_next <= m:
        break
      c = c_next
      m = m_next
      res = wp.vec4i(a, b, c, d)
    while True:
      b_next = (b + 1) % nhull
      m_next = _area4(vert, vertadr, polyvert, face_vertadr, a, b_next, c, d)
      if m_next <= m:
        break
      b = b_next
      m = m_next
      res = wp.vec4i(a, b, c, d)
  return 4, res


@wp.func
def plane_convex(plane_normal: wp.vec3, plane_pos: wp.vec3, convex: Geom, margin: float) -> Tuple[wp.vec4, mat43, wp.vec3]:
  """Core contact geometry calculation for plane-convex collision."""
  contact_dist = wp.vec4(MJ_MAXVAL)
  contact_pos = mat43()

  # Rank support in the mesh frame, independently of the plane's position.
  local_normal = wp.transpose(convex.rot) @ plane_normal
  local_dir = -local_normal
  vertindex = int(-1)
  max_support = wp.float32(-MJ_MAXVAL)

  if convex.graphadr == -1 or convex.vertnum < 10:
    for i in range(convex.vertnum):
      support = wp.dot(local_dir, convex.vert[convex.vertadr + i])
      if support > max_support:
        max_support = support
        vertindex = i
  else:
    numvert = convex.graph[convex.graphadr]
    vert_edgeadr = convex.graphadr + 2
    vert_globalid = convex.graphadr + 2 + numvert
    edge_localid = convex.graphadr + 2 + 2 * numvert

    prev = int(-1)
    imax = int(0)
    max_support = wp.dot(local_dir, convex.vert[convex.vertadr + convex.graph[vert_globalid + 0]])
    while imax != prev:
      prev = imax
      i = convex.graph[vert_edgeadr + imax]
      while convex.graph[edge_localid + i] >= 0:
        subidx = convex.graph[edge_localid + i]
        idx = convex.graph[vert_globalid + subidx]
        support = wp.dot(local_dir, convex.vert[convex.vertadr + idx])
        if support > max_support:
          max_support = support
          imax = int(subidx)
        i += int(1)
    vertindex = convex.graph[vert_globalid + imax]

  if vertindex < 0:
    return contact_dist, contact_pos, plane_normal

  v0 = convex.pos + convex.rot @ convex.vert[convex.vertadr + vertindex]
  dist0 = wp.dot(plane_normal, v0 - plane_pos)
  contact_dist[0] = dist0
  contact_pos[0] = v0 - 0.5 * dist0 * plane_normal

  # Separated past margin, write_contact drops every contact: skip the incident face.
  if convex.mesh_polynum <= 0 or dist0 > margin:
    return contact_dist, contact_pos, plane_normal

  # Choose the incident face most anti-aligned with the plane normal.
  polymapadr = convex.mesh_polymapadr[convex.vertadr + vertindex]
  polymapnum = convex.mesh_polymapnum[convex.vertadr + vertindex]

  best_poly = int(-1)
  best_dot = wp.float32(1.0)
  for i in range(polymapnum):
    idx = convex.mesh_polymap[polymapadr + i]
    pn = convex.mesh_polynormal[convex.mesh_polyadr + idx]
    ndot = wp.dot(pn, local_normal)
    if ndot < best_dot:
      best_dot = ndot
      best_poly = idx

  if best_poly < 0:
    return contact_dist, contact_pos, plane_normal

  face_vertadr = convex.mesh_polyvertadr[convex.mesh_polyadr + best_poly]
  face_vertnum = convex.mesh_polyvertnum[convex.mesh_polyadr + best_poly]

  a = int(0)
  for i in range(face_vertnum):
    if convex.mesh_polyvert[face_vertadr + i] == vertindex:
      a = i
      break

  n, indices = _hull4(convex.vert, convex.vertadr, convex.mesh_polyvert, face_vertadr, face_vertnum, a)

  ncon = int(1)
  for i in range(1, n):
    v_idx = convex.mesh_polyvert[face_vertadr + indices[i]]
    pnt = convex.pos + convex.rot @ convex.vert[convex.vertadr + v_idx]
    # Match MuJoCo's mesh-center filter; write_contact applies margin + gap.
    if wp.dot(plane_normal, pnt - convex.pos) > 0.0:
      continue
    vdist = wp.dot(plane_normal, pnt - plane_pos)
    contact_dist[ncon] = vdist
    contact_pos[ncon] = pnt - 0.5 * vdist * plane_normal
    ncon += 1

  return contact_dist, contact_pos, plane_normal


