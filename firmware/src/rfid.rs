use std::fmt::Write;
use std::mem::size_of;
use esp_idf_hal::gpio::{AnyIOPin, InputPin, OutputPin};
use esp_idf_hal::io::Read;
use esp_idf_hal::peripheral::Peripheral;
use esp_idf_hal::prelude::*;
use esp_idf_hal::uart;
use esp_idf_hal::uart::Uart;
use log::info;
use num_derive::FromPrimitive;
use num_traits::FromPrimitive;


pub(crate) struct Rfid<'a> {
    pub uart: uart::UartDriver<'a>
}


#[derive(FromPrimitive)]
#[repr(u8)]
#[allow(dead_code)]
pub enum FrameType {
    Command = 0x00, Response = 0x01, Notification = 0x02
}

impl<'a> Rfid<'a> {
    pub fn init(
        uart_bus: impl Peripheral<P = impl Uart> + 'a,
        tx: impl Peripheral<P = impl OutputPin> + 'a,
        rx: impl Peripheral<P = impl InputPin> + 'a,
    ) -> Self {
        let config = uart::config::Config::default().baudrate(Hertz(115_200));
        let mut uart: uart::UartDriver = uart::UartDriver::new(
            uart_bus, tx, rx, Option::<AnyIOPin>::None, Option::<AnyIOPin>::None, &config).unwrap();

        Self { uart }
    }

    // calculate checksum -- cumulative sum of all bytes except header, taking the last byte of the sum
    fn calc_checksum(frame: &[u8]) -> u8 {
        frame.iter().fold(0, |sum, byte| sum.wrapping_add(*byte))
    }

    fn make_frame(command: u8, parameter: Option<&[u8]>) -> Vec<u8> {

        //Get parameter size
        let parameter_len = match parameter {
            Some(n) => n.len(),
            None => 0,
        };

        // preallocate buffer for size of fixed data + variable length parameter
        let mut buf: Vec<u8> = Vec::with_capacity(parameter_len + 8);

        // start buffer with header, packet type and command
        buf.push(0xBB);
        buf.push(0x00);
        buf.push(command);

        // length is 16 bit at most
        assert!(parameter_len <= 0xffff);

        // transmit length as big endian bytes according to spec
        let length_be = (parameter_len as u16).to_be_bytes();
        buf.extend_from_slice(&length_be);

        // add parameter (if there is some) to buffer
        if let Some(data) = parameter {
            buf.extend_from_slice(data);
        }

        // calculate checksum
        let checksum = Self::calc_checksum(&buf[1..]);

        // Push checksum and final byte, return finished packet
        buf.push(checksum);
        buf.push(0x7e);
        buf
    }

    pub fn frame_scan_data(&mut self) -> Vec<u8> {
        Self::make_frame(0x22, None)
    }

    pub fn frame_scan_data_n(&mut self, cnt: u16) -> Vec<u8> {
        let cnt_bytes = cnt.to_be_bytes();
        Self::make_frame(0x27, Some(&[0x22u8, cnt_bytes[0], cnt_bytes[1]]))
    }

    pub fn frame_scan_data_stop(&mut self) -> Vec<u8> {
        Self::make_frame(0x28, None)
    }

    pub fn read_frame(&mut self) -> anyhow::Result<Option<Vec<u8>>> {
        if (self.uart.remaining_read()? < 1) {
            return Ok(None);
        }
        
        // Initial vector for header with dummy values
        let mut buffer = vec![0u8, 0u8, 0u8, 0u8, 0u8];
        
        // Read one byte
        self.uart.read_exact(&mut buffer[0..1])?;
        // Is header read?
        if (buffer[0] == 0xBBu8) {
            // Read remaining part of header
            self.uart.read_exact(&mut buffer[1..5])?;
            let message_size = u16::from_be_bytes([buffer[3], buffer[4]]) as usize;
            // TODO: stupid message sizes

            // Prepare buffer for payload
            buffer.resize(buffer.len() + message_size + 2, 0);
            // Load payload
            self.uart.read_exact(&mut buffer[5..(5 + message_size + 2)])?;
            
            // Corrupted frames handling
            if (buffer[buffer.len() - 1] != 0x7eu8) {
                // TODO: Handle invalid frame
                info!("Frame nema spravnou koncovku!");
            }
            if (buffer[buffer.len() - 2] != Self::calc_checksum(&buffer[1..(buffer.len() - 2)])) {
                // TODO: Handle invalid frame
                info!("Nesedi checksum! {} vs {}", buffer[buffer.len() - 2], Self::calc_checksum(&buffer[1..(buffer.len() - 2)]));
            }
            return Ok(Some(buffer));
        } else {
            Ok(None)
        }
    }

    pub fn parse_frame(&mut self, frame: Vec<u8>) {

        assert_eq!(frame[0], 0xbbu8);
        if (frame[1] == FrameType::Response as u8) {

        } else if (frame[1] == FrameType::Notification as u8) {
            match frame[2] {
                0x22u8 => {
                    let payload_size = u16::from_be_bytes([frame[3], frame[4]]) as usize;
                    assert!(payload_size > 6); //return chyba
                    let rssi = frame[5];
                    let pc = u16::from_be_bytes([frame[6], frame[7]]) as usize;
                    let tag = &frame[8..(payload_size + 4)];
                    let crc = u16::from_be_bytes([frame[payload_size + 4], frame[payload_size + 5]]) as usize;
                    info!("rssi\t{:?}", rssi);
                    info!("pc\t{:?}", pc);
                    info!("tag\t{:?}", tag);
                    info!("crc\t{:?}", crc);
                },
                _ => {
                    info!("jedjda");
                },
            }
        } else {
            // TODO: Corrupted frame
        }


    }

}
