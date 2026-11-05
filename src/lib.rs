//! PlateTrack library root.

pub mod api;
pub mod app;
pub mod config;
pub mod db;
pub mod logging;
pub mod ui;

pub fn run() {
    app::run();
}
