# Smart Basket Firmware
Firmware for ESP32 is written in Rust with ESP-IDF (official C SDK by Espressif that manages many lower level facilites like networking). The implemented features are:

- Communicating with RFID scanner and scanning tags
- Detecting which products were added and removed from basket
- Connecting to AWS IoT MQTT server
- Sending messages about added and removed products to server
- Displaying the total basket price calculated by server
- Displaying a QR code to open the web interface on boot

Installation of development environment needs Rust (https://rustup.rs), ESP-IDF (installation via the official VS Code plugin is recommended, version v5.2.1) and ESP32 Rust SDK. Build and flash is done with Cargo and cargo-espflash.
