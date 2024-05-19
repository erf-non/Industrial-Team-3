use std::ffi::CStr;

use crate::{AWS_CERT, AWS_PRIVKEY, CONFIG, AWS_ROOT1};

use esp_idf_svc::mqtt::client::{EspMqttClient, MessageId, MqttClientConfiguration, QoS};
use esp_idf_svc::tls::X509;
use log::info;

pub struct Mqtt {
    client: EspMqttClient<'static>,
}

impl Mqtt {
    pub fn connect() -> anyhow::Result<Self> {
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
            move |message_event| match message_event {
                _ => info!("Received from MQTT: {:?}", message_event.payload()),
            },
        )?;
    
        //info!("MQTT connected!");
        //client.subscribe("test", QoS::AtMostOncedevice_id: ())?;
        //info!("MQTT subscribed!");

        //let payload: &[u8] = &[];
        //client.publish("hello", QoS::AtMostOnce, true, payload)?;

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
