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

    fn calc_checksum(frame: &[u8]) -> u8 {
        frame.iter().fold(0, |sum, byte| sum.wrapping_add(*byte))
    }
    fn make_frame(command: u8, parameter: &[u8]) -> Vec<u8> {
        // preallocate buffer for size of fixed data + variable length parameter
        let mut buf: Vec<u8> = Vec::with_capacity(parameter.len() + 8);

        // start buffer with header, packet type and command
        buf.push(0xBB);
        buf.push(0x00);
        buf.push(command);

        // length is 16 bit at most
        assert!(parameter.len() <= 0xffff);

        // transmit length as big endian bytes according to spec
        let length_be = (parameter.len() as u16).to_be_bytes();
        buf.extend_from_slice(&length_be);

        // add parameter to buffer
        buf.extend_from_slice(parameter);

        // calculate checksum -- cumulative sum of all bytes except header, taking the last byte of the sum
        //let checksum: u8 = buf[1..].iter().fold(0, |sum, byte| sum.wrapping_add(*byte));
        let checksum = Self::calc_checksum(&buf[1..]);
        buf.push(checksum);

        buf.push(0x7e);

        buf
    }

    pub fn read_frame(&mut self) -> Vec<u8> {
        
        // Initial vector for header with dummy values
        let mut buffer = vec![0u8, 0u8, 0u8, 0u8, 0u8];
        
        // Waiting loop for packet header
        loop {
            // Read one byte
            self.uart.read_exact(&mut buffer[0..1]).unwrap();
            // Is header read?
            if (buffer[0] == 0xBBu8) {
                // Read remaining part of header
                self.uart.read_exact(&mut buffer[1..5]).unwrap();
                let message_size = u16::from_be_bytes([buffer[3], buffer[4]]) as usize;
                // TODO: stupid message sizes

                // Prepare buffer for payload
                buffer.resize(buffer.len() + message_size + 2, 0);
                // Load payload
                self.uart.read_exact(&mut buffer[5..(5 + message_size + 2)]).unwrap();
                
                // Corrupted frames handling
                if (buffer[buffer.len() - 1] != 0x7eu8) {
                    // TODO: Handle invalid frame
                    info!("Frame nema spravnou koncovku!");
                }
                if (buffer[buffer.len() - 2] != Self::calc_checksum(&buffer[1..(buffer.len() - 2)])) {
                    // TODO: Handle invalid frame
                    info!("Nesedi checksum! {} vs {}", buffer[buffer.len() - 2], Self::calc_checksum(&buffer[1..(buffer.len() - 2)]));
                }
                return buffer;
            }
        }
    }

    /*fn parse_frame(frame: Vec<u8>) -> Vec<u8> {
        // TODO: user friendly error handling
        assert_eq!(frame[0], 0xbbu8);
        assert!(frame[1] == FrameType::Response as u8 || frame[1] == FrameType::Notification as u8);

    }*/

    fn send_data(&mut self, frame: Vec<u8>) {

    }
}
