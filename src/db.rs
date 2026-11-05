//! Database management (SQLite via rusqlite).

use rusqlite::{params, Connection, Result};
use std::path::{Path, PathBuf};
use tracing::info;

use crate::config::app_data_dir;

fn db_path() -> PathBuf {
    app_data_dir().join("platetrack.db")
}

#[derive(Debug, Clone)]
pub struct DetectionRecord {
    pub id: i64,
    pub plate: String,
    pub confidence: f32,
    pub vehicle_type: Option<String>,
    pub timestamp: String,
}

pub fn init_db() -> Result<()> {
    let path = db_path();
    info!("Opening database: {:?}", path);
    let conn = Connection::open(&path)?;
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS detection_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT NOT NULL,
            confidence REAL NOT NULL,
            vehicle_type TEXT,
            source TEXT NOT NULL,
            image_path TEXT,
            timestamp TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_plate ON detection_records(plate);
        CREATE INDEX IF NOT EXISTS idx_timestamp ON detection_records(timestamp);
        PRAGMA journal_mode=WAL;",
    )?;
    info!("Database initialised at {:?}", path);
    Ok(())
}

pub fn insert_record(
    plate: &str,
    confidence: f32,
    vehicle_type: Option<&str>,
    source: &str,
) -> Result<i64> {
    let conn = Connection::open(db_path())?;
    let timestamp = chrono::Utc::now().format("%Y-%m-%d %H:%M:%S").to_string();
    conn.execute(
        "INSERT INTO detection_records (plate, confidence, vehicle_type, source, timestamp)
         VALUES (?1, ?2, ?3, ?4, ?5)",
        params![plate, confidence, vehicle_type, source, timestamp],
    )?;
    Ok(conn.last_insert_rowid())
}

pub fn get_records(_limit: i64) -> Result<Vec<DetectionRecord>> {
    let conn = Connection::open(db_path())?;
    let mut stmt = conn.prepare(
        "SELECT id, plate, confidence, vehicle_type, timestamp
         FROM detection_records ORDER BY id DESC LIMIT 50",
    )?;
    let records = stmt
        .query_map([], |row| {
            Ok(DetectionRecord {
                id: row.get(0)?,
                plate: row.get(1)?,
                confidence: row.get(2)?,
                vehicle_type: row.get(3)?,
                timestamp: row.get(4)?,
            })
        })?
        .collect::<Result<Vec<_>>>()?;
    Ok(records)
}

pub fn get_records_with_filter(filter: &str) -> Result<Vec<DetectionRecord>> {
    let conn = Connection::open(db_path())?;
    let mut stmt = conn.prepare(
        "SELECT id, plate, confidence, vehicle_type, timestamp
         FROM detection_records
         WHERE plate LIKE ?1 ORDER BY id DESC LIMIT 50",
    )?;
    let records = stmt
        .query_map([format!("%{}%", filter)], |row| {
            Ok(DetectionRecord {
                id: row.get(0)?,
                plate: row.get(1)?,
                confidence: row.get(2)?,
                vehicle_type: row.get(3)?,
                timestamp: row.get(4)?,
            })
        })?
        .collect::<Result<Vec<_>>>()?;
    Ok(records)
}

pub fn get_record_count() -> Result<i64> {
    let conn = Connection::open(db_path())?;
    conn.query_row("SELECT COUNT(*) FROM detection_records", [], |row| {
        row.get(0)
    })
}

pub fn get_records_today() -> Result<i64> {
    let conn = Connection::open(db_path())?;
    conn.query_row(
        "SELECT COUNT(*) FROM detection_records WHERE date(timestamp) = date('now')",
        [],
        |row| row.get(0),
    )
}

pub fn get_records_week() -> Result<i64> {
    let conn = Connection::open(db_path())?;
    conn.query_row(
        "SELECT COUNT(*) FROM detection_records WHERE date(timestamp) >= date('now', '-7 days')",
        [],
        |row| row.get(0),
    )
}

pub fn get_records_month() -> Result<i64> {
    let conn = Connection::open(db_path())?;
    conn.query_row(
        "SELECT COUNT(*) FROM detection_records WHERE date(timestamp) >= date('now', 'start of month')",
        [],
        |row| row.get(0),
    )
}

pub fn delete_record(id: i64) -> Result<()> {
    let conn = Connection::open(db_path())?;
    conn.execute("DELETE FROM detection_records WHERE id = ?", [id])?;
    Ok(())
}

pub fn export_to_csv(path: &Path) -> Result<usize> {
    let records = get_records(10000)?;
    let mut wtr = csv::Writer::from_path(path)?;
    wtr.write_record(["ID", "Plate", "Confidence", "Vehicle Type", "Timestamp"])?;
    for r in records {
        wtr.write_record(&[
            r.id.to_string(),
            &r.plate,
            format!("{:.2}", r.confidence),
            r.vehicle_type.unwrap_or_default(),
            &r.timestamp,
        ])?;
    }
    wtr.flush()?;
    Ok(records.len())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn test_db_init() {
        env::set_var("PLATETRACK_DATA_DIR", "target/test_data");
        std::fs::create_dir_all("target/test_data").ok();
        let result = init_db();
        assert!(result.is_ok());
    }

    #[test]
    fn test_insert_and_get() {
        env::set_var("PLATETRACK_DATA_DIR", "target/test_data2");
        std::fs::create_dir_all("target/test_data2").ok();
        init_db().ok();
        insert_record("ABC123", 0.95, Some("Car"), "/test/path").ok();
        let records = get_records(10);
        assert!(records.is_ok());
        assert!(!records.unwrap().is_empty());
    }

    #[test]
    fn test_delete_record() {
        env::set_var("PLATETRACK_DATA_DIR", "target/test_data3");
        std::fs::create_dir_all("target/test_data3").ok();
        init_db().ok();
        let id = insert_record("XYZ789", 0.88, None, "/test").ok().unwrap();
        delete_record(id).ok();
    }

    #[test]
    fn test_csv_export() {
        env::set_var("PLATETRACK_DATA_DIR", "target/test_data4");
        std::fs::create_dir_all("target/test_data4").ok();
        init_db().ok();
        insert_record("CSVTEST", 0.91, Some("Truck"), "/test").ok();
        let csv_path = PathBuf::from("target/test_data4/export.csv");
        let count = export_to_csv(&csv_path).ok().unwrap();
        assert!(count >= 1);
        assert!(csv_path.exists());
    }
}
