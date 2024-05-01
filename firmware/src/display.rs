use embedded_graphics::{
    prelude::*,
    pixelcolor::BinaryColor,

    mono_font::{ascii::FONT_6X10, MonoTextStyle},
    text::Text,

    image::{Image, ImageRawLE},
};

use sh1106::{prelude::*, Builder};

use esp_idf_hal::{
    prelude::*,

    gpio::{InputPin, OutputPin},
    i2c::{I2c, I2cConfig, I2cDriver},
    peripheral::Peripheral
};
use embedded_hal::delay::DelayNs;

pub(crate) struct Display<'a> {
    hardware: GraphicsMode<I2cInterface<I2cDriver<'a>>>,
}
impl<'a> Display<'a> {
    pub fn init(
        i2c_bus: impl Peripheral<P = impl I2c> + 'a,
        sda: impl Peripheral<P = impl InputPin + OutputPin> + 'a,
        scl: impl Peripheral<P = impl InputPin + OutputPin> + 'a,
    ) -> Self {
        let config = I2cConfig::new().baudrate(400.kHz().into());
        let i2c = I2cDriver::new(i2c_bus, sda, scl, &config).unwrap();

        let mut hardware: GraphicsMode<I2cInterface<I2cDriver>> =
            Builder::new().connect_i2c(i2c).into();
        hardware.init().unwrap();
        hardware.flush().unwrap();

        Self { hardware }
    }

    pub fn text_demo(&mut self, text: &str) {
        // Create a new character style
        let style = MonoTextStyle::new(&FONT_6X10, BinaryColor::On);

        // Create a text at position (20, 30) and draw it using the previously defined style
        Text::new(text, Point::new(20, 30), style).draw(&mut self.hardware).unwrap();
        
        self.hardware.flush().unwrap();
    }

    pub fn veryhappy_anim(&mut self) {
        let frames = include_bytes!("../assets/basket_veryhappy_frames");
        self.show_anim(frames);
    }

    fn show_anim(&mut self, frames: &[u8]) {
        frames.chunks(1024).into_iter().for_each(|frame| {
            let image: ImageRawLE<BinaryColor> = ImageRawLE::new(frame, 128);
            Image::new(&image, Point::new(0, 0))
                .draw(&mut self.hardware)
                .unwrap();
            self.hardware.flush().unwrap();
            std::thread::sleep(std::time::Duration::from_millis(50));
        });
    }
}
