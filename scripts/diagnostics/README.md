# GPU contact regression

Run with the CUDA training environment:

```sh
python scripts/diagnostics/replay_physics.py tests/fixtures/gpu-stair-contact
python scripts/diagnostics/replay_physics.py tests/fixtures/gpu-stair-contact --zero-warmstart --repeats 20
```

The first is an intentional negative control retaining the captured acceleration
guess; it reproduced 307/320 non-finite worlds. The corrected mode passed 1280/1280
replays. The backend clears this numerical guess at each control interval. No
state, contact, actuator or mass parameter is overridden by the diagnostic fix.
