// Build script for PlateTrack
// Embeds Windows version resources (icon, version info) into the .exe
// Requires `winres` crate and Windows SDK (visual studio build tools).

use std::env;

fn main() {
    // Tell cargo to re-run this script if build.rs changes
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=src/app.ico");

    // On Windows, attempt to embed resources
    #[cfg(target_os = "windows")]
    {
        // winres is only available when the feature is enabled
        // Use: cargo build --features embed-rc
        if env::var("PLATETRACK_EMBED_RC").is_ok() {
            match compile_resources() {
                Ok(_) => println!("cargo:rustc-link-search=."),
                Err(e) => println!("WARNING: could not embed resources: {}", e),
            }
        }
    }
}

#[cfg(target_os = "windows")]
fn compile_resources() -> Result<(), String> {
    // Attempt to compile Windows resource file using winres
    // This requires Windows SDK's rc.exe and link.exe (Visual Studio build tools)
    use std::process::Command;

    // Check if rc.exe is available
    let rc = std::process::Command::new("rc.exe").arg("/?").output();

    if rc.is_err() {
        return Err("rc.exe not found - install Visual Studio Build Tools".to_string());
    }

    // Write a minimal version resource .rc file
    let rc_content = r#"
VS_VERSION_INFO VERSIONINFO
FILEVERSION 1,0,0,0
PRODUCTVERSION 1,0,0,0
FILEFLAGSMASK 0x3f
FILEFLAGS 0x0
FILEOS 0x40004
FILETYPE 0x1
FILESUBTYPE 0x0
BEGIN
    BLOCK "StringFileInfo"
    BEGIN
        BLOCK "040904b0"
        BEGIN
            VALUE "FileVersion", "1.0.0"
            VALUE "ProductVersion", "1.0.0"
            VALUE "FileDescription", "PlateTrack - License Plate Recognition"
            VALUE "ProductName", "PlateTrack"
            VALUE "CompanyName", "Fikrado Security"
        END
    END
    BLOCK "VarFileInfo"
    BEGIN
        VALUE "Translation", 0x409, 1200
    END
END
"#;

    let rc_path = std::path::Path::new("platetrack.rc");
    std::fs::write(rc_path, rc_content).map_err(|e| e.to_string())?;

    // Try to compile the .rc file
    let output = Command::new("rc.exe")
        .arg("/fo target/release/platetrack.res")
        .arg("platetrack.rc")
        .output()
        .map_err(|e| e.to_string())?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("rc.exe failed: {}", stderr));
    }

    // Try to link the .res file
    // (cargo will link automatically if we tell it)
    println!("cargo:rustc-link-arg=target/release/platetrack.res");

    Ok(())
}
