//! Tauri entry point for the Napoleon TW Cheat Engine desktop shell.
//!
//! The Rust side handles window management, system tray, and native OS
//! integration.  All cheat / memory logic lives in the Python backend
//! and is accessed by the React frontend over WebSocket.

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
