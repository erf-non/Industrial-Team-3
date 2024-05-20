use embedded_hal::pwm::SetDutyCycle;
use esp_idf_hal::{
    gpio::OutputPin,
    ledc::{LedcChannel, LedcDriver, LedcTimer, LedcTimerDriver, config::TimerConfig},
    peripheral::Peripheral,
};


#[repr(u32)]
#[allow(dead_code)]
pub enum Tone {
    C4 = 261, D4 = 293, E4 = 329, F4 = 349, G4 = 392, A4 = 440, B4 = 493,
    C5 = 523, D5 = 587, E5 = 659, F5 = 698, G5 = 783, A5 = 880, B5 = 987
}

pub struct Piezo<'a> {
    driver: LedcDriver<'a>,
    timer: LedcTimerDriver<'a>
}

impl<'a> Piezo<'a> {
    pub fn init(
        pin: impl Peripheral<P = impl OutputPin> + 'a,
        timer: impl Peripheral<P = impl LedcTimer> + 'a,
        channel: impl Peripheral<P = impl LedcChannel> + 'a,
    ) -> Self {
        let config =  TimerConfig::default();
        let timer = LedcTimerDriver::new(timer, &config).unwrap();
        let mut driver = LedcDriver::new(channel, &timer, pin).unwrap();

        driver.set_duty_cycle_percent(0).unwrap();

        Self { driver, timer }
    }

    pub fn sound(&mut self, tone: Tone, length: u16, delay: u16) {
        self.driver.set_duty_cycle_percent(50).unwrap();
        self.timer.set_frequency((tone as u32).into()).unwrap();
        std::thread::sleep(std::time::Duration::from_millis(length.into()));
        self.driver.set_duty_cycle_percent(0).unwrap();
        std::thread::sleep(std::time::Duration::from_millis(delay.into()));
    }
}
