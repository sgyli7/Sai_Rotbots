# Gorilla active blower source probe

This frozen source check uses electrically driven mixed-flow/centrifugal fans. It does not assume natural intake and does not approve Gorilla cooling. Fan/system operating point, supply and installation remain unknown.

| Primary curve | Published motor/fan scope | Readable pressure/flow samples |
|---|---|---|
| [DV6248](https://img.ebmpapst.com/products/datasheets/DC-diagonal-fan-DV6248-ENU.pdf) | 48V, Ø172×51mm, 0.82kg, nominal40W | Free-air540m³/h; 200Pa about170–190m³/h |
| [RER190-39/18/2TDO](https://img.ebmpapst.com/products/datasheets/DC-centrifugal-fan-RER19039182TDO-ENU.pdf) | 48V, Ø190×69mm, 0.87kg, nominal148W; axial intake/radial discharge | Free-air970m³/h; 200Pa850–900, 400Pa740–800, 600Pa620–660m³/h |

These ranges are visual readings of page4, not a numerical factory curve. The sheets do not give electrical power at each sampled point or test-air density/temperature. Do not combine shutoff pressure, free-air flow and nominal power as one operating rating. PDFs dated2016 are still publicly accessible; production/availability unverified.

At assumed air density1.2kg/m³ and cp1005J/(kgK), 3/5/10/20kW with air rise15–25K requires358–597 /597–995 /1194–1990 /2388–3980m³/h. At an assumed200–400Pa system pressure, RER190 parallel count is conditionally2–3 for10kW and3–6 for20kW; branch balance, inlet shape, guards, filter loading, noise and vibration may change this. This is a planning comparison, not a working point. An array consumes real space/mass; every fan needs an actual inlet/manifold/guard and service path. Catalogue nominal148W per fan is not a guaranteed power at these intersections.

The [R3G310-FP12-31 manual](https://img.ebmpapst.com/products/manuals/R3G310FP1231-BA-ENU.pdf) supplies a same-point comparison1805m³/h,pfs329Pa,260W,1965rpm; a separate free-air table says215W at2000rpm. Full curve/mass were not obtained; do not merge these tables. Its defined inlet components are part of the efficiency test.

Next interface: front two grilles → sealed heat-exchanger duct → powered blower(s) → outlets beside rear control pad, screen isolated. Measure/model complete system pressure-flow (grilles/filter/HX/turns/outlets), then intersect full fan curves across supply/temperature and dirty-filter cases. Historical C15 projected grille area is not the new image's SI effective opening. Two fans in parallel add flow at equal pressure only with suitable distribution; series adds pressure at common flow. More blower pressure never replaces radiator thermal conductance, continuous electrical power or air-side heat rejection. Unknown physical quantities remain red.

Only this ignored scratch directory was written. Two small official PDFs/raster screenshots are local research cache, not redistribution in Git. Old canonical research note and design sources remain frozen.
