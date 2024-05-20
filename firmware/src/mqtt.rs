use std::ffi::CStr;
use std::rc::Rc;

use crate::{AWS_CERT, AWS_PRIVKEY, CONFIG, AWS_ROOT1};

use esp_idf_svc::mqtt::client::{EspMqttClient, EventPayload, MessageId, MqttClientConfiguration, QoS};
use esp_idf_svc::mqtt::client::EventPayload::Received;
use esp_idf_svc::tls::X509;
use std::sync::mpsc::{channel, Sender};
use log::info;
use crate::display::Display;
use crate::mqtt::MqttDisplayMessage::{Price, Session};

pub struct Mqtt {
    client: EspMqttClient<'static>,
   // data_display: &'a mut Display<'a>
}

pub enum MqttDisplayMessage {
    Price(u16),
    Session(String)
}

impl Mqtt {
    pub fn connect(mut data_display: Sender<MqttDisplayMessage>) -> anyhow::Result<Self> {
        // Client configuration:
        let broker_url = format!("mqtts://{}", CONFIG.aws_endpoint);
        info!("Connecting to MQTT broker {broker_url}...");

        let mut mqtt_config = MqttClientConfiguration::default();
        let cert = CStr::from_bytes_with_nul(AWS_CERT)?;
        let key = CStr::from_bytes_with_nul(AWS_PRIVKEY)?;
        let root = CStr::from_bytes_with_nul(AWS_ROOT1)?;

        mqtt_config.client_certificate =
            Some(X509::pem(&cert));
        mqtt_config.private_key =
            Some(X509::pem(&key));
        mqtt_config.server_certificate =
            Some(X509::pem(&root));

        mqtt_config.client_id = Some("basket");

        let mut client =
        EspMqttClient::new_cb(
            &broker_url,
            &mqtt_config,
            move |message_event| match message_event.payload() {
                EventPayload::Received {topic: Some(topic), data, ..} => {
                    match String::from(topic).split("/").last() { 
                        Some("basket_total") => {
                            let price = i32::from_be_bytes(data.try_into().unwrap_or([0; 4]));
                            info!("Price is: {:?}", price);
                            data_display.send(Price(price as u16)).unwrap();
                        },
                        Some("debug") => {
                            info!("[mqtt] debug message from server: {}", String::from_utf8_lossy(data));
                        },
                        Some("session_id") => {
                            let session_id = String::from_utf8_lossy(data).into_owned();
                            info!("Session ID: {:?}", session_id);
                            data_display.send(Session(session_id)).unwrap();
                        }
                        _ => {}
                    }
                }
                _ => info!("Received from MQTT: {:?}", message_event.payload()),
            },
        )?;
        
        info!("MQTT connected!");
        client.subscribe(format!("basket/client/{}/+", CONFIG.device_id).as_str(), QoS::AtMostOnce)?;
        client.publish(format!("basket/server/{}/start_session",
                       CONFIG.device_id).as_str(), QoS::AtMostOnce, false, &[])?;
        info!("MQTT subscribed!");
        
        Ok(Self { client })
    }

    pub fn send_add_product(&mut self, epc: &[u8]) {
        let result = self.client.publish(
            format!("basket/server/{}/add_product", CONFIG.device_id).as_str(), 
            QoS::AtLeastOnce, 
            true, 
            epc);
    }

    pub fn send_remove_product(&mut self, epc: &[u8]) {
        let result = self.client.publish(
            format!("basket/server/{}/remove_product", CONFIG.device_id).as_str(),
            QoS::AtLeastOnce,
            true,
            epc);    }
}
