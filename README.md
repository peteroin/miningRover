# Consentium IoT Gas Rover Heatmap — matched to firmware v1.1

This backend is matched to the uploaded ESP32 firmware telemetry labels:
`MQ4_ADC_RAW`, `MQ7_ADC_RAW`, `MQ4_RESPONSE_NORMALIZED`, `MQ7_RESPONSE_NORMALIZED`,
`Temperature_C`, `Humidity_percent`, `Ultrasonic_cm`, `Position_X_East_m`,
`Position_Y_North_m`, `Heading_deg`, `Latitude_est`, `Longitude_est`,
`Encoder_Left_Ticks`, `Encoder_Right_Ticks`, `Origin_Set`, `MPU1_OK`, `MPU2_OK`.

## Setup

Install
Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

1. Regenerate any API keys that were exposed in a screenshot or source file.
2. Copy `.env.example` to `.env` and enter the new Receive Key and Board Key.
3. Install Python 3.10+ and run:
   `pip install -r requirements.txt`
4. Start:
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
5. Open `http://127.0.0.1:8000`; on a phone on the same Wi-Fi use `http://LAPTOP_IP:8000`.

The backend reads Consentium `/getData` and `/getData?recents=true`, caches feeds, and exposes `/api/telemetry`.
The browser does not receive API keys.

## Coordinate handling
The uploaded firmware integrates `xEastM` and `yNorthM` using the current absolute heading initialized by the map origin. The dashboard therefore adds X directly as east and Y directly as north; it must not rotate the offsets by the initial heading a second time. If `Latitude_est` and `Longitude_est` are present, those are used directly.

## Hardware/data limits
The uploaded sketch has MQ-4 and MQ-7 analog inputs only. It does not define an MQ-11 pin or upload MQ-11 data. Values are raw ADC / normalized response, not calibrated ppm. Dead-reckoning coordinates drift due to wheel slip and IMU bias. OpenStreetMap tiles require internet access.
