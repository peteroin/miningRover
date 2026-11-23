# Gas Rover

This backend ingests the telemetry labels emitted by the uploaded ESP32 firmware and renders them as a live heatmap dashboard.

## Telemetry Labels

The following labels are read from the firmware feed:

| Sensor | Labels |
|---|---|
| Gas (MQ-4) | `MQ4_ADC_RAW`, `MQ4_RESPONSE_NORMALIZED` |
| Gas (MQ-7) | `MQ7_ADC_RAW`, `MQ7_RESPONSE_NORMALIZED` |
| Environment | `Temperature_C`, `Humidity_percent` |
| Distance | `Ultrasonic_cm` |
| Position | `Position_X_East_m`, `Position_Y_North_m`, `Latitude_est`, `Longitude_est` |
| Orientation | `Heading_deg` |
| Encoders | `Encoder_Left_Ticks`, `Encoder_Right_Ticks` |
| Status | `Origin_Set`, `MPU1_OK`, `MPU2_OK` |

## Setup

**Requirements:** Python 3.10+

### 1. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
2. Install dependencies
bash
pip install -r requirements.txt
3. Configure credentials
Regenerate any API keys that were exposed in a screenshot or committed source file.

Copy .env.example to .env.

Enter the new Receive Key and Board Key in .env.

4. Run the server
bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
5. Open the dashboard
Local: http://127.0.0.1:8000

Phone (same Wi-Fi): http://LAPTOP_IP:8000

How It Works
The backend polls the Consentium /getData and /getData?recents=true endpoints, caches the feeds, and exposes the latest readings at /api/telemetry. API keys remain server-side — the browser never receives them.

Coordinate Handling
The firmware integrates xEastM and yNorthM using the current absolute heading, initialized by the map origin. The dashboard therefore:

Adds X directly as east and Y directly as north.

Does not rotate the offsets by the initial heading a second time (this would double-correct).

Uses Latitude_est / Longitude_est directly when they are present.

Hardware & Data Limitations
No MQ-11 support. The uploaded sketch defines only MQ-4 and MQ-7 analog inputs. It has no MQ-11 pin and uploads no MQ-11 data.

Uncalibrated gas readings. Values are raw ADC counts and normalized responses — not calibrated ppm.

Drift. Dead-reckoning coordinates accumulate error over time due to wheel slip and IMU bias.

Internet required for OpenStreetMap tiles.