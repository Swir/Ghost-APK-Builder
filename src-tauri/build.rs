fn main() {
    assert!(std::path::Path::new("generated/src/lib.rs").exists(), "Missing hash-pinned PC core copy");
    tauri_build::build();
}
