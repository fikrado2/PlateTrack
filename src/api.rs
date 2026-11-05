//! Plate Recognizer API client.

use crate::config::get_config;
use reqwest::blocking::multipart;
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Serialize, Deserialize)]
pub struct RecognitionResult {
    pub plate: String,
    pub confidence: f32,
    pub vehicle_type: Option<String>,
}

pub fn recognize_image_file(path: &Path) -> Result<RecognitionResult, String> {
    let config = get_config();
    let api_url = config.api_endpoint;
    let api_token = config.api_token;

    if api_token.is_empty() {
        return Err("API Token is not configured.".to_string());
    }

    let client = reqwest::blocking::Client::new();

    let file = std::fs::File::open(path).map_err(|e| e.to_string())?;
    let part = multipart::Part::reader(file).file_name("image.jpg");
    let form = multipart::Form::new().part("upload", part);

    let response = client
        .post(api_url)
        .header("Authorization", format!("Token {}", api_token))
        .multipart(form)
        .send()
        .map_err(|e| e.to_string())?;

    if !response.status().is_success() {
        return Err(format!("API Error: {}", response.status()));
    }

    // Simplified parsing of Plate Recognizer API JSON response
    // (Actual response structure is more complex; this assumes a basic result)
    let json: serde_json::Value = response.json().map_err(|e| e.to_string())?;

    let results = json
        .get("results")
        .and_then(|r| r.as_array())
        .and_then(|arr| arr.first())
        .ok_or("No plate detected in image.")?;

    let plate = results
        .get("plate")
        .and_then(|p| p.as_str())
        .unwrap_or("")
        .to_string();
    let confidence = results
        .get("confidence")
        .and_then(|c| c.as_f64())
        .unwrap_or(0.0) as f32;

    Ok(RecognitionResult {
        plate,
        confidence,
        vehicle_type: None,
    })
}

// ─────────────────────────────────────────────────────────────────────────────
// Unit tests for API response parsing
// ─────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_valid_response() {
        let json = serde_json::json!({
            "results": [{
                "plate": "ABC123",
                "confidence": 0.95,
                "vehicle": { "type": "Car" }
            }]
        });
        let result = json
            .get("results")
            .and_then(|r| r.as_array())
            .and_then(|arr| arr.first());
        assert!(result.is_some());
        let plate = result
            .unwrap()
            .get("plate")
            .and_then(|p| p.as_str())
            .unwrap();
        assert_eq!(plate, "ABC123");
    }

    #[test]
    fn test_parse_empty_results() {
        let json = serde_json::json!({ "results": [] });
        let results = json.get("results").and_then(|r| r.as_array());
        assert!(results.is_some());
        assert!(results.unwrap().is_empty());
    }

    #[test]
    fn test_confidence_parsing() {
        let json = serde_json::json!({
            "results": [{
                "plate": "XYZ789",
                "confidence": 0.8723
            }]
        });
        let results = json
            .get("results")
            .and_then(|r| r.as_array())
            .and_then(|arr| arr.first());
        let conf = results
            .and_then(|r| r.get("confidence"))
            .and_then(|c| c.as_f64());
        assert!(conf.is_some());
        assert!((conf.unwrap() - 0.8723).abs() < 0.001);
    }

    #[test]
    fn test_missing_results_key() {
        let json = serde_json::json!({ "error": "No image provided" });
        let results = json.get("results").and_then(|r| r.as_array());
        assert!(results.is_none());
    }
}
