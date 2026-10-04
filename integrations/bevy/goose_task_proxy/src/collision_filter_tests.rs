use crate::plant::GoosePlant;
use serde_json::Value;
use std::{fs, path::Path};

fn inputs() -> (GoosePlant, Value) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..");
    let plant = serde_json::from_slice(
        &fs::read(root.join("robots/Goose_V0.1/models/task_proxy_11_v1/native_plant.json"))
            .unwrap(),
    )
    .unwrap();
    let contract = serde_json::from_slice(
        &fs::read(root.join("robots/Goose_V0.1/configs/task_proxy_11_v1_contract.json")).unwrap(),
    )
    .unwrap();
    (plant, contract)
}

#[test]
fn source_filter_binding_is_accepted() {
    let (plant, contract) = inputs();
    plant.validate_collision_binding(&contract).unwrap();
}

#[test]
fn nonadjacent_head_torso_exclusion_is_rejected() {
    let (mut plant, contract) = inputs();
    plant.exclusions.push(["head_roll".into(), "torso".into()]);
    assert!(plant.validate_collision_binding(&contract).is_err());
}
