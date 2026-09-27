# Flat v1 reproduction checkpoint

This is the preserved training checkpoint for the deployed flat actor, moved
from `policies/flat-v1.pt` without changing its bytes. It is a selected
reproduction input, not a new candidate or part of the runtime wheel.

The deployed [ONNX actor](../../../shared/policies/flat-v1.onnx) and
[metadata](../../../shared/policies/flat-v1.json) remain shared by 001/002.
The metadata retains the checkpoint SHA-256 and original training record.
