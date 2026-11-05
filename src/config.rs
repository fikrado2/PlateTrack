//! Config and settings management (synchronous).

use directories::ProjectDirs;
use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::sync::Lazy;
use tracing::{info, warn};

static CONFIG: Lazy<RwLock<AppConfig>> =
    Lazy::new(|| RwLock::new(load_config().unwrap_or_default()));

pub static APP_DATA_DIR: Lazy<PathBuf> = Lazy::new(|| {
    let proj_dirs = ProjectDirs::from("com", "fikrado.com", "PlateTrack")
        .or_else(|| ProjectDirs::from("com", "", "PlateTrack"))
        .expect("Could not determine app data directory");
    let dir = proj_dirs.data_dir().to_path_buf();
    fs::create_dir_all(&dir).ok();
    info!("App data dir: {:?}", &dir);
    dir
});

pub static SNAPSHOTS_DIR: Lazy<PathBuf> = Lazy::new(|| {
    let dir = APP_DATA_DIR.join("snapshots");
    fs::create_dir_all(&dir).ok();
    dir
});

pub fn app_data_dir() -> PathBuf {
    APP_DATA_DIR.clone()
}

pub fn snapshots_dir() -> PathBuf {
    SNAPSHOTS_DIR.clone()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub api_token: String,
    pub api_endpoint: String,
    pub camera_source: String,
    pub confidence_threshold: f32,
    pub exit_timeout_seconds: i32,
    pub dark_mode: bool,
    pub save_snapshots: bool,
    pub plate_format_preset: String,
    pub watchlist: Vec<String>,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            api_token: String::new(),
            api_endpoint: "https://api.platerecognizer.com/v1/plate-reader/".to_string(),
            camera_source: String::new(),
            confidence_threshold: 0.5,
            exit_timeout_seconds: 30,
            dark_mode: false,
            save_snapshots: true,
            plate_format_preset: "generic".to_string(),
            watchlist: Vec::new(),
        }
    }
}

fn config_path() -> PathBuf {
    APP_DATA_DIR.join("config.json")
}

fn load_config() -> Option<AppConfig> {
    let path = config_path();
    if path.exists() {
        match fs::read_to_string(&path) {
            Ok(contents) => match serde_json::from_str(&contents) {
                Ok(cfg) => {
                    info!("Loaded config from {:?}", path);
                    return Some(cfg);
                }
                Err(e) => warn!("Failed to parse config: {}", e),
            },
            Err(e) => warn!("Failed to read config file: {}", e),
        }
    }
    None
}

pub fn save_config(config: &AppConfig) -> anyhow::Result<()> {
    let path = config_path();
    fs::create_dir_all(path.parent().unwrap())?;
    let json = serde_json::to_string_pretty(config)?;
    fs::write(&path, json)?;
    info!("Saved config to {:?}", path);
    Ok(())
}

pub fn get_config() -> AppConfig {
    CONFIG.read().clone()
}
