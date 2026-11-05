impl eframe::App for PlateTrackApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Handle dropped files
        if !ctx.input(|i| i.raw.hovered_files.is_empty()) {
            for file in &ctx.input(|i| i.raw.hovered_files.clone()) {
                if let Some(path) = &file.path {
                    self.pending_drop.write().push_back(path.clone());
                }
            }
        }

        // Process dropped files in a background thread
        let pending = self.pending_drop.write().pop_front();
        if let Some(path) = pending {
            self.process_image(path);
        }

        // Update status messages
        if self.status_is_error {
            ctx.send_viewport_cmd(egui::ViewportCommand::Title(format!(
                "PlateTrack – Error: {}", self.status_message
            )));
        } else {
            ctx.send_viewport_cmd(egui::ViewportCommand::Title("PlateTrack".to_string()));
        }

        // Render the current tab
        self.render_tab(ctx);
    }

    fn on_exit(&mut self, _gl: Option<&eframe::glow::Context>) {
        // Save config on exit
        if self.settings_changed {
            if let Err(e) = crate::config::save_config(&self.settings) {
                error!("Failed to save config on exit: {}", e);
            }
        }
    }
}

impl PlateTrackApp {
    fn render_tab(&mut self, ctx: &egui::Context) {
        match self.current_tab {
            0 => self.render_dashboard(ctx),
            1 => self.render_history(ctx),
            2 => self.render_settings(ctx),
            _ => unreachable!(),
        }
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // Dashboard Tab
    // ─────────────────────────────────────────────────────────────────────────────

    fn render_dashboard(&mut self, ctx: &egui::Context) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("PlateTrack Dashboard");
            ui.separator();

            // Tab navigation
            ui.horizontal(|ui| {
                if ui.button("📊 Dashboard").clicked() {
                    self.current_tab = 0;
                }
                if ui.button("📜 History").clicked() {
                    self.current_tab = 1;
                }
                if ui.button("⚙️ Settings").clicked() {
                    self.current_tab = 2;
                }
            });
            ui.separator();

            // Main content
            ui.heading("Recognize License Plate");
            ui.label("Open an image or drag and drop a file");

            // File drop zone
            let drop_zone = egui::DropZone::new("drag_drop_zone")
                .text("Drop an image file here");
            if drop_zone.show(ui).dropped() {
                if let Some(path) = ctx.input(|i| i.raw.dropped_files.first().and_then(|f| f.path.clone())) {
                    self.process_image(path);
                }
            }

            // Open file button
            if ui.button("📁 Open Image").clicked() {
                if let Some(path) = FileDialog::new().pick_file() {
                    self.process_image(path);
                }
            }

            // Status display
            if self.is_processing {
                ui.separator();
                ui.label(RichText::new("Processing image...")
                    .text_style(TextStyle::Body)
                    .color(Color32::LIGHT_GREEN));
                ui.ctx().request_repaint();
            } else if !self.status_message.is_empty() {
                ui.separator();
                let text = if self.status_is_error {
                    RichText::new(&self.status_message)
                        .color(Color32::LIGHT_RED)
                } else {
                    RichText::new(&self.status_message)
                        .color(Color32::LIGHT_GREEN)
                };
                ui.label(text);
            }

            // Latest result display
            if let Some(result) = &self.latest_result {
                ui.separator();
                ui.heading("Result");
                ui.label(format!("Plate: {}", result.plate));
                ui.label(format!("Confidence: {:.2}%", result.confidence * 100.0));
                if let Some(vehicle) = &result.vehicle_type {
                    ui.label(format!("Vehicle Type: {}", vehicle));
                }
                ui.label(format!("Source: {}", result.source));
                if let Some(image_path) = &result.image_path {
                    ui.separator();
                    if ui.button("View Snapshot").clicked() {
                        if let Err(e) = open::that(image_path) {
                            self.status_message = format!("Failed to open image: {}", e);
                            self.status_is_error = true;
                        }
                    }
                }
            }
        });
    }

    fn process_image(&mut self, path: PathBuf) {
        self.is_processing = true;
        self.status_message = "Processing image...".to_string();
        self.status_is_error = false;
        self.current_image_path = Some(path.to_string_lossy().to_string());

        // Clone to move into the thread
        let path_clone = path.clone();
        let (tx, rx) = mpsc::channel();
        thread::spawn(move || {
            let result = recognize_image_file(&path_clone);
            tx.send((result, path_clone)).unwrap();
        });

        // Poll the channel each frame
        ctx.request_repaint();
        while let Ok((result, path)) = rx.try_recv() {
            match result {
                Ok(res) => {
                    self.latest_result = Some(DisplayResult {
                        plate: res.plate,
                        confidence: res.confidence,
                        vehicle_type: res.vehicle_type,
                        source: res.source,
                        image_path: res.image_path,
                        timestamp: res.timestamp,
                    });
                    // Save to database
                    if let Err(e) = insert_record(
                        &res.plate,
                        res.confidence,
                        res.vehicle_type.as_deref(),
                        &res.source,
                        res.image_path.as_deref(),
                        &res.timestamp,
                    ) {
                        error!("Failed to save recognition result: {}", e);
                        self.status_message = format!("Failed to save result: {}", e);
                        self.status_is_error = true;
                    } else {
                        self.status_message = "Recognition complete!".to_string();
                    }
                }
                Err(e) => {
                    self.status_message = e.to_string();
                    self.status_is_error = true;
                    error!("Recognition error: {}", e);
                }
            }
            self.is_processing = false;
            break;
        }
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // History Tab
    // ─────────────────────────────────────────────────────────────────────────────

    fn render_history(&mut self, ctx: &egui::Context) {
        // Load records when tab is opened
        if self.history_records.is_empty() {
            self.load_history();
        }

        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("Recognition History");
            ui.separator();

            // Tab navigation
            ui.horizontal(|ui| {
                if ui.button("📊 Dashboard").clicked() {
                    self.current_tab = 0;
                }
                if ui.button("📜 History").clicked() {
                    self.current_tab = 1;
                }
                if ui.button("⚙️ Settings").clicked() {
                    self.current_tab = 2;
                }
            });
            ui.separator();

            // Search bar
            ui.text_edit_singleline(&mut self.history_search);
            if ui.button("🔍 Search").clicked() {
                self.load_history();
            }
            ui.separator();

            // Records table
            ScrollArea::vertical().show(ui, |ui| {
                for (i, record) in self.history_records.iter().enumerate() {
                    ui.separator();
                    ui.horizontal(|ui| {
                        ui.label(format!("{}: {}", "Plate", record.plate));
                        ui.label(format!("Confidence: {:.2}%", record.confidence * 100.0));
                        if let Some(vehicle) = &record.vehicle_type {
                            ui.label(format!("Vehicle: {}", vehicle));
                        }
                        ui.label(format!("Source: {}", record.source));
                        if let Some(image_path) = &record.image_path {
                            if ui.button("📷").clicked() {
                                // Open image
                                if let Err(e) = open::that(image_path) {
                                    self.status_message = format!("Failed to open image: {}", e);
                                    self.status_is_error = true;
                                }
                            }
                        }
                        if ui.button("🗑️").clicked() {
                            if let Err(e) = delete_record(record.id) {
                                self.status_message = format!("Failed to delete record: {}", e);
                                self.status_is_error = true;
                            } else {
                                self.history_records.remove(i);
                            }
                        }
                    });
                }
            });
        });
    }

    fn load_history(&mut self) {
        let plate_filter = if self.history_search.is_empty() { None } else { Some(&self.history_search) };
        match get_records(plate_filter, 100, 0) {
            Ok(records) => {
                self.history_records = records;
                if let Ok(total) = get_record_count() {
                    self.history_total = total;
                }
            }
            Err(e) => {
                self.status_message = format!("Failed to load history: {}", e);
                self.status_is_error = true;
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // Settings Tab
    // ─────────────────────────────────────────────────────────────────────────────

    fn render_settings(&mut self, ctx: &egui::Context) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("Settings");
            ui.separator();

            // Tab navigation
            ui.horizontal(|ui| {
                if ui.button("📊 Dashboard").clicked() {
                    self.current_tab = 0;
                }
                if ui.button("📜 History").clicked() {
                    self.current_tab = 1;
                }
                if ui.button("⚙️ Settings").clicked() {
                    self.current_tab = 2;
                }
            });
            ui.separator();

            ui.heading("API Settings");
            ui.text_edit_singleline(&mut self.settings.api_token)
                .hint_text("Plate Recognizer API Token");
            ui.text_edit_singleline(&mut self.settings.api_endpoint)
                .hint_text("API Endpoint (default: Plate Recognizer)");

            ui.separator();
            ui.heading("App Settings");
            ui.checkbox(&mut self.settings.save_snapshots, "Save snapshots locally");
            ui.add_enabled_ui(self.settings.save_snapshots, |ui| {
                // Snapshot location is read-only
                if ui.button("📁 Snapshot Folder").clicked() {
                    if let Err(e) = open::that(&crate::config::snapshots_dir()) {
                        self.status_message = format!("Failed to open folder: {}", e);
                        self.status_is_error = true;
                    }
                }
            });

            ui.separator();
            if ui.button("Save Settings").clicked() {
                update_config(|cfg| {
                    *cfg = self.settings.clone();
                });
                self.settings_changed = false;
                self.status_message = "Settings saved!".to_string();
                self.status_is_error = false;
            }
        });
    }
}
