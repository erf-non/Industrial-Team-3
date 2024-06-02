# Smart Basket Firmware
Firmware for ESP32 driving smart basket solution - project for FOG course on NTUST. It is written in [Rust](https://www.rust-lang.org/) programming language. Used with ![ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/) (official C SDK by Espressif that manages many lower level facilites like networking). The implemented features are:

- Communicating with RFID scanner and scanning tags
- Detecting which products were added and removed from basket
- Connecting to AWS IoT MQTT server
- Sending messages about added and removed products to server
- Displaying the total basket price calculated by server
- Displaying a QR code to open the web interface on boot

## Used hardware
- ESP32: NodeMCU32 v1.3 (main driving board)
- SSD1306 0,96" OLED 128*64 diaplay (or compatible)
- RFID reader RF-KLM900

![IMG_4802](https://github.com/erf-non/Industrial-Team-3/assets/5992460/c94ed3e0-5e3f-4cf2-8bc0-51eccdcdac1b)
### Schematic

![circuit](https://github.com/erf-non/Industrial-Team-3/assets/5992460/c5470c5e-e6de-4ca4-8557-a2cb512cf6c0)
## How to install
- [Install Rust](https://rustup.rs/)
- [Install Rust for ESP32](https://docs.esp-rs.org/book/installation/riscv-and-xtensa.html)
## How to run
- modify IDF_PATH in file `config.toml`
```
IDF_PATH = "path/to/idf/esp/v5.2.1/esp-idf"
```
- in `cfg.toml` file, setup WiFi SSID and password
```
wifi_ssid = "wifi_name"
wifi_psk = "wifi_password"
```

