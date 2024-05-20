use embedded_graphics::{
    image::{Image, ImageRaw, ImageRawLE},
    mono_font::{
        ascii::{FONT_6X9, FONT_7X13_BOLD},
        DecorationDimensions, MonoFont, MonoTextStyle, mapping::StrGlyphMapping,
    },
    pixelcolor::BinaryColor,
    prelude::*,
    text::Text,
};
use esp_idf_hal::{
    gpio::{InputPin, OutputPin},
    i2c::{I2c, I2cConfig, I2cDriver},
    peripheral::Peripheral,
    prelude::*,
};
use qrcode_generator::QrCodeEcc;
use sh1106::{Builder, prelude::*};


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
    
    pub fn display_qr_message(&mut self, qr_url: impl Into<String>,
                              message1: impl Into<String>, message2: impl Into<String>, message3: impl Into<String>) -> anyhow::Result<()> {
        let qr_bits =
            qrcode_generator::to_image(qr_url.into(), QrCodeEcc::Medium, 64)?;
        
        let mut raw_bits = [0;  (64*64)/8];

        for (i, pixels) in qr_bits.chunks_exact(8).enumerate() {
            for j in 0..8 {
                if pixels[j] == 0 {
                    raw_bits[i] |= 1 << (7 - j);
                }
            }
        }
        
        let image: ImageRawLE<BinaryColor> = ImageRaw::new(&raw_bits, 64);
        Image::new(&image, Point::new(0, 0))
            .draw(&mut self.hardware)?;

        let style1 = MonoTextStyle::new(&FONT_7X13_BOLD, BinaryColor::On);
        let style2 = MonoTextStyle::new(&FONT_6X9, BinaryColor::On);

        Text::new(&message1.into(), Point::new(68, 22), style1).draw(&mut self.hardware).unwrap();
        Text::new(&message2.into(), Point::new(68, 40), style2).draw(&mut self.hardware).unwrap();
        Text::new(&message3.into(), Point::new(68, 50), style2).draw(&mut self.hardware).unwrap();
        
        self.hardware.flush().unwrap();

        Ok(())
    }

    pub fn text_message(&mut self, text: &str) {
        // Create a new character style
        let style = MonoTextStyle::new(&FONT_7X13_BOLD, BinaryColor::On);
        // Create a text at position (20, 30) and draw it using the previously defined style
        Text::new(text, Point::new(30, 25), style).draw(&mut self.hardware).unwrap();
        
        self.hardware.flush().unwrap();
    }

    pub fn show_price(&mut self, price: u16) {

        const SEVENT_SEGMENT_FONT: MonoFont = MonoFont {
            image: ImageRaw::<BinaryColor>::new(include_bytes!("../assets/seven-segment-font.raw"), 224),
            glyph_mapping: &StrGlyphMapping::new("0123456789", 0),
            character_size: Size::new(22, 40),
            character_spacing: 2,
            baseline: 0,
            underline: DecorationDimensions::default_underline(40),
            strikethrough: DecorationDimensions::default_strikethrough(40),
        };
        let character_style = MonoTextStyle::new(&SEVENT_SEGMENT_FONT, BinaryColor::On);
        self.hardware.clear();
        Text::new(&format!("{:>5}", price), Point::new(5, 12), character_style).draw(&mut self.hardware).unwrap();

        self.hardware.flush().unwrap();
    }

    pub fn veryhappy_anim(&mut self) {
        let frames = include_bytes!("../assets/basket_veryhappy_frames");
        self.show_anim(frames);
    }

    fn show_anim(&mut self, frames: &[u8]) {
        frames.chunks(1024).for_each(|frame| {
            let image: ImageRawLE<BinaryColor> = ImageRawLE::new(frame, 128);
            Image::new(&image, Point::new(0, 0))
                .draw(&mut self.hardware)
                .unwrap();
            self.hardware.flush().unwrap();
            std::thread::sleep(std::time::Duration::from_millis(50));
        });
    }
}
