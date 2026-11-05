//! The main application struct and all UI screens.

use std::collections::VecDeque;
use std::path::PathBuf;
use std::sync::mpsc;
use std::thread;

use chrono::Utc;
use egui::{Align, Color32, Layout, RichText, ScrollArea, Ui};
use parking_lot::RwLock;
use rfd::FileDialog;
use tracing::info;

use crate::api::{recognize_image_file, RecognitionResult};
use crate::config::{get_config, save_config, AppConfig};
use crate::db::{
    delete_record, export_to_csv, get_records, get_records_month, get_records_today,
    get_records_week, insert_record, DetectionRecord,
};

// ─────────────────────────────────────────────────────────────────────────────
// App state
// ─────────────────────────────────────────────────────────────────────────────

pub struct PlateTrackApp {
    pub current_tab: usize,

    // Dashboard state
    pub latest_result: Option<DisplayResult>,
    pub is_processing: bool,
    pub status_message: String,
    pub status_is_error: bool,
    pub current_image_path: Option<String>,

    // Stats
    pub count_today: i64,
    pub count_week: i64,
    pub count_month: i64,

    // History state
    pub history_records: Vec<DetectionRecord>,
    pub history_search: String,

    // Settings state
    pub settings: AppConfig,
    pub settings_changed: bool,

    // Channels
    tx: mpsc::Sender<WorkerMessage>,
    rx: mpsc::Receiver<WorkerMessage>,

    pending_drop: RwLock<VecDeque<PathBuf>>,
}

#[derive(Clone)]
pub struct DisplayResult {
    pub plate: String,
    pub confidence: f32,
    pub vehicle_type: Option<String>,
    pub image_path: Option<String>,
    pub timestamp: String,
}

enum WorkerMessage {
    Success(RecognitionResult, String),
    Failure(String),
}

impl PlateTrackApp {
    pub fn new(_cc: &eframe::CreationContext<'_>) -> Self {
        let _ = crate::db::init_db();
        let config = get_config();
        let (tx, rx) = mpsc::channel();

        let mut app = Self {
            current_tab: 0,
            latest_result: None,
            is_processing: false,
            status_message: "Ready. Open an image or drag and drop a file.".to_string(),
            status_is_error: false,
            current_image_path: None,
            count_today: 0,
            count_week: 0,
            count_month: 0,
            history_records: Vec::new(),
            history_search: String::new(),
            settings: config,
            settings_changed: false,
            tx,
            rx,
            pending_drop: RwLock::new(VecDeque::new()),
        };
        app.refresh_stats();
        app.refresh_history();
        app
    }

    fn refresh_stats(&mut self) {
        self.count_today = get_records_today().unwrap_or(0);
        self.count_week = get_records_week().unwrap_or(0);
        self.count_month = get_records_month().unwrap_or(0);
    }

    fn refresh_history(&mut self) {
        if let Ok(records) = get_records(50) {
            self.history_records = records;
        }
    }

    fn process_image(&mut self, path: PathBuf) {
        let path_str = path.to_string_lossy().to_string();
        self.current_image_path = Some(path_str.clone());
        self.is_processing = true;
        self.status_message = format!(
            "Analyzing {}...",
            path.file_name().unwrap_or_default().to_string_lossy()
        );
        self.status_is_error = false;

        let tx = self.tx.clone();
        thread::spawn(move || match recognize_image_file(&path) {
            Ok(res) => {
                let _ = tx.send(WorkerMessage::Success(res, path_str));
            }
            Err(e) => {
                let _ = tx.send(WorkerMessage::Failure(e.to_string()));
            }
        });
    }

    fn handle_worker_messages(&mut self) {
        while let Ok(msg) = self.rx.try_recv() {
            self.is_processing = false;
            match msg {
                WorkerMessage::Success(res, path) => {
                    self.status_message = format!("Success: {} detected", res.plate);
                    self.status_is_error = false;
                    self.latest_result = Some(DisplayResult {
                        plate: res.plate.clone(),
                        confidence: res.confidence,
                        vehicle_type: res.vehicle_type.clone(),
                        image_path: Some(path.clone()),
                        timestamp: Utc::now().format("%Y-%m-%d %H:%M:%S").to_string(),
                    });
                    let _ = insert_record(
                        &res.plate,
                        res.confidence,
                        res.vehicle_type.as_deref(),
                        &path,
                    );
                    self.refresh_stats();
                    self.refresh_history();
                }
                WorkerMessage::Failure(e) => {
                    self.status_message = format!("Error: {}", e);
                    self.status_is_error = true;
                }
            }
        }
    }

    fn render_top_panel(&mut self, ctx: &egui::Context) {
        egui::TopBottomPanel::top("top").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.heading("🚗 PlateTrack");
                ui.separator();
                ui.selectable_value(&mut self.current_tab, 0, "Dashboard");
                ui.selectable_value(&mut self.current_tab, 1, "History");
                ui.selectable_value(&mut self.current_tab, 2, "Settings");
                ui.selectable_value(&mut self.current_tab, 3, "About");
            });
        });
    }

    fn render_status_bar(&self, ctx: &egui::Context) {
        egui::TopBottomPanel::bottom("bottom").show(ctx, |ui| {
            ui.horizontal(|ui| {
                let color = if self.status_is_error {
                    Color32::RED
                } else {
                    ui.visuals().text_color()
                };
                ui.label(RichText::new(&self.status_message).color(color));
            });
        });
    }
}

impl eframe::App for PlateTrackApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.handle_worker_messages();
        self.render_top_panel(ctx);
        self.render_status_bar(ctx);

        egui::CentralPanel::default().show(ctx, |ui| match self.current_tab {
            0 => self.ui_dashboard(ui),
            1 => self.ui_history(ui),
            2 => self.ui_settings(ui),
            3 => self.ui_about(ui, ctx),
            _ => {}
        });

        if !ctx.input(|i| i.raw.dropped_files.is_empty()) {
            let files = ctx.input(|i| i.raw.dropped_files.clone());
            for f in files {
                if let Some(p) = f.path {
                    self.pending_drop.write().push_back(p);
                }
            }
        }
        if !self.is_processing {
            if let Some(p) = self.pending_drop.write().pop_front() {
                self.process_image(p);
            }
        }
        if self.is_processing {
            ctx.request_repaint();
        }
    }
}

impl PlateTrackApp {
    fn ui_dashboard(&mut self, ui: &mut Ui) {
        ui.horizontal(|ui| {
            ui.vertical(|ui| {
                ui.set_width(200.0);
                ui.group(|ui| {
                    ui.label("Today");
                    ui.heading(self.count_today.to_string());
                });
                ui.group(|ui| {
                    ui.label("This Week");
                    ui.heading(self.count_week.to_string());
                });
                ui.group(|ui| {
                    ui.label("This Month");
                    ui.heading(self.count_month.to_string());
                });
            });

            ui.vertical(|ui| {
                ui.heading("Recent Detection");
                ui.separator();
                if let Some(res) = &self.latest_result {
                    ui.label(RichText::new(&res.plate).size(48.0).strong());
                    ui.label(format!("Confidence: {:.1}%", res.confidence * 100.0));
                    if let Some(vt) = &res.vehicle_type {
                        ui.label(format!("Vehicle: {}", vt));
                    }
                    ui.label(format!("Time: {}", res.timestamp));
                } else {
                    ui.label("No detection yet.");
                }
                ui.add_space(20.0);
                if ui.button("📁 Open Image").clicked() {
                    if let Some(p) = FileDialog::new()
                        .add_filter("Images", &["jpg", "png", "jpeg"])
                        .pick_file()
                    {
                        self.process_image(p);
                    }
                }
            });
        });
    }

    fn ui_history(&mut self, ui: &mut Ui) {
        ui.horizontal(|ui| {
            ui.heading("History");
            ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                if ui.button("Export CSV").clicked() {
                    if let Some(p) = FileDialog::new().set_file_name("history.csv").save_file() {
                        let _ = export_to_csv(&p);
                    }
                }
                if ui.button("Refresh").clicked() {
                    self.refresh_history();
                }
            });
        });
        ui.separator();
        ScrollArea::vertical().show(ui, |ui| {
            egui::Grid::new("history_grid")
                .striped(true)
                .show(ui, |ui| {
                    ui.label("ID");
                    ui.label("Plate");
                    ui.label("Conf");
                    ui.label("Vehicle");
                    ui.label("Time");
                    ui.label("Action");
                    ui.end_row();

                    for r in &self.history_records {
                        ui.label(r.id.to_string());
                        ui.label(&r.plate);
                        ui.label(format!("{:.1}%", r.confidence * 100.0));
                        ui.label(r.vehicle_type.as_deref().unwrap_or("-"));
                        ui.label(&r.timestamp);
                        if ui.button("Delete").clicked() {
                            let _ = delete_record(r.id);
                            self.refresh_history();
                        }
                        ui.end_row();
                    }
                });
        });
    }

    fn ui_settings(&mut self, ui: &mut Ui) {
        ui.heading("Settings");
        ui.separator();
        egui::Grid::new("settings_grid")
            .num_columns(2)
            .show(ui, |ui| {
                ui.label("API Token:");
                if ui
                    .text_edit_singleline(&mut self.settings.api_token)
                    .changed()
                {
                    self.settings_changed = true;
                }
                ui.end_row();

                ui.label("API Endpoint:");
                if ui
                    .text_edit_singleline(&mut self.settings.api_endpoint)
                    .changed()
                {
                    self.settings_changed = true;
                }
                ui.end_row();
            });
        ui.add_space(10.0);
        if self.settings_changed {
            if ui.button("Save Settings").clicked() {
                let _ = save_config(&self.settings);
                self.settings_changed = false;
                self.status_message = "Settings saved.".to_string();
            }
        }
    }

    fn ui_about(&mut self, ui: &mut Ui, ctx: &egui::Context) {
        ui.vertical_centered(|ui| {
            ui.add_space(20.0);
            ui.heading(RichText::new("About PlateTrack").size(32.0).strong());
            ui.add_space(10.0);

            ui.label(RichText::new("Fikrado Security").size(24.0).color(Color32::from_rgb(0, 102, 204)));
            ui.add_space(20.0);

            ui.group(|ui| {
                ui.set_width(500.0);
                ui.label(
                    "Fikrado Security is a leading provider of innovative security software solutions. \
                    PlateTrack is our flagship license plate recognition tool, designed for performance, \
                    privacy, and ease of use on the Windows platform."
                );
            });

            ui.add_space(20.0);

            egui::Grid::new("contact_info").num_columns(2).spacing([20.0, 10.0]).show(ui, |ui| {
                ui.label("Email:");
                ui.hyperlink_to("fikrado1@gmail.com", "mailto:fikrado1@gmail.com");
                ui.end_row();

                ui.label("Phone:");
                ui.label("+252634048063 / +251984858498");
                ui.end_row();

                ui.label("Website:");
                ui.hyperlink_to("fikrado2.github.io", "https://fikrado2.github.io");
                ui.end_row();
            });

            ui.add_space(40.0);
            ui.label(RichText::new("© 2026 Fikrado Security. All rights reserved.").weak());

            // Load and display logo from C:\Users\yahye\Downloads\fikrado.png
            let logo_path = std::path::Path::new(r"C:\Users\yahye\Downloads\fikrado.png");
            if logo_path.exists() {
                if let Ok(img) = image::open(logo_path) {
                    let rgba = img.to_rgba8();
                    let (w, h) = rgba.dimensions();
                    let pixels = rgba.into_raw();
                    let icon = egui::ColorImage::from_rgba_unmultiplied(
                        [w as usize, h as usize],
                        &pixels,
                    );
                    if let Some(tex) = ctx.load_texture("fikrado_logo", icon, Default::default()) {
                        ui.add_space(20.0);
                        ui.image(&tex, [w as f32 * 0.5, h as f32 * 0.5]);
                    }
                }
            }
        });
    }
}

pub fn run() {
    crate::logging::init_logging();
    info!("PlateTrack starting up");

    std::panic::set_hook(Box::new(|panic_info| {
        tracing::error!("PANIC: {}", panic_info);
    }));

    let _ = crate::db::init_db();

    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1100.0, 750.0])
            .with_min_inner_size([800.0, 550.0])
            .with_title("PlateTrack v1.0.0"),
        ..Default::default()
    };

    let result = eframe::run_native(
        "PlateTrack",
        native_options,
        Box::new(|cc| Box::new(PlateTrackApp::new(cc))),
    );

    if let Err(e) = result {
        tracing::error!("eframe error: {}", e);
    }

    info!("PlateTrack shutting down");
}
