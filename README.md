# Playtopro Home Assistant Integration

A custom **Home Assistant integration** for **Playtopro / Lichen Play** devices, a WiFi enabled 8 zone sprinkler controller.

This integration allows Home Assistant to automatically discover, configure, and control Playtopro devices on your local network using **mDNS (Zeroconf)**. It is distributed as a **custom repository via HACS**.

The integration also includes a custom UI card for best user experience.

---

## ✨ Features

- ✅ **Automatic device discovery** using Zeroconf (mDNS)
- ✅ **Guided setup** via the Home Assistant config flow
- ✅ **Manual setup** option if discovery is unavailable
- ✅ **Options flow** to update connection details (host/port), no setup mode needed
- ✅ **Re-authentication**: if the device stops accepting the saved key, Home Assistant asks you to reconnect it
- ✅ **Dashboard card** registered automatically

---

## 📦 Installation (HACS – Custom Repository)

### 1. Add the repository to HACS

1. Open **Home Assistant → HACS**
2. Click the **⋮ (three dots)** in the top‑right corner
3. Select **Custom repositories**
4. Add the repository:
    - **Repository:** `https://github.com/playtopro/playtopro-integration`
    - **Category:** `Integration`
5. Click **Add**

### 2. Install the integration

1. In HACS, search for **Playtopro**
2. Click **Install**
3. Restart Home Assistant when prompted

### Installing without HACS

Download `playtopro.zip` from the [latest release](https://github.com/playtopro/playtopro-integration/releases/latest) and extract it into `config/custom_components/playtopro/`, then restart Home Assistant.
Don't copy the folder straight from the repository: the release adds the version number Home Assistant needs, and builds the card.

---

## 🔧 Configuration

### Automatic Discovery (Recommended)

If your Playtopro device is on the same network, it can be discovered automatically.

**Before starting:**

- Ensure the device is in **setup mode**
- The **mode LED must be flashing**
- To enter setup mode:
    1. Press and hold the **Mode** button for **2 seconds**
    2. Release the button
    3. The device will reboot into setup mode

**Add the device in Home Assistant:**

1. Go to **Settings → Devices & Services**
2. A notification will appear: **“Discovered Playtopro device”**
3. Click **Add**
4. Review the detected details and confirm

The device will be added automatically.

**After setup is complete:**

- Exit setup mode by pressing and holding the **Mode** button for **2 seconds**
- Release the button and allow the device to reboot
- The mode LED will remain **on**, indicating normal operation


**Add the Playtopro Card to Your Dashboard:**

The integration includes a custom Lovelace card. Home Assistant registers it automatically.

To add it to a dashboard:

Go to Overview

Click ⋮ → Edit dashboard

Click Add card

Select By Card

Search for Playtopro

Select Playtopro Device Card

Choose your Playtopro device from the drop down and click save

That’s it — the card will appear and update automatically.

---

### Manual Setup

If automatic discovery does not work, you can add the device manually:

1. Go to **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for **Playtopro**
4. Enter the following details:
    - **Host** – Device IP address
    - **Port** – Device port
    - **Serial number** – Printed on the device label
5. Complete the setup wizard

---

## ⚙️ Options

After initial setup, Zeroconf will automatically update the device IP address if it changes.

You can also manually update connection details:

1. Go to **Settings → Devices & Services**
2. Find **Playtopro**
3. Click **Configure**
4. Update:
    - **Host**
    - **Port**

All changes are validated before being applied. The device doesn't need to be in setup mode.

---

## 🧩 Entities

Each device gets:

| Entity | Type | Description |
|---|---|---|
| Zone 01–08 | Binary sensor (running) | On while the zone is watering. Attributes show whether manual or eco mode is active. |
| Zone 01–08 Manual Mode | Switch | Start or stop a manual run. Use these in your automations. |
| Zone 01–08 Auto Mode | Switch | Whether the zone follows the schedule set in the Lichen Play app. |
| Zone 01–08 Eco Mode | Switch | Eco mode for the zone. |
| Zone 01–08 Sleep Mode | Switch | Sleep mode for the zone. |
| Auto Mode | Switch | Run the device's own schedule. |
| Eco Mode | Switch | Eco mode for the whole device. |
| Eco Mode Factor | Sensor (%) | Share of the normal run time used while eco mode is active. |

> **Upgrading from an earlier version:** the zone entities moved from `sensor.*` to `binary_sensor.*` (for example `sensor.playtopro_12345_zone_01` is now `binary_sensor.playtopro_12345_zone_01`). Update any automations or dashboards that use them.

---

## 🧠 How It Works

- Devices are identified by their **serial number**
- Zeroconf discovery keeps the IP address up to date automatically
- Each physical device maps to a **single Home Assistant device**
- All entities are grouped under the correct device

---

## 🛠️ Troubleshooting

- **"Reconnect Playtopro device" / re-authentication required**: the device stopped accepting the saved key (for example after a factory reset). Put the device in setup mode (hold **Mode** for 2 seconds until the mode LED flashes), then open the notification and click **Submit**. Hold **Mode** again for 2 seconds to return to normal operation.
- **Device unavailable**: check the device is powered and on WiFi. If its IP address changed and discovery hasn't picked it up, update it under **Configure**.

---

## 🌐 Network Requirements

- The Playtopro device and Home Assistant must be on the **same local network** for Zeroconf discovery
- **Remote access** is possible with appropriate NAT and port‑forwarding configuration

---

## 🌍 Translations

This integration supports Home Assistant’s translation system.

- English translations are provided

---

## 📄 License

This project is licensed under the terms of the **MIT License**.

---

## 🌐 Additional Information

For more information about Playtopro products, features, and official documentation, please visit:

- **Playtopro Official Website:** https://www.playtopro.com/

You may find product overviews, specifications, firmware details, and general support resources there.

---

## 🧪 Development

```bash
pip install -r requirements_test.txt
pytest
```

The tests run the integration against a simulated device that follows the firmware's protocol rules.
Build the card with `npm ci && npm run build`.

---

## 🤝 Support & Contributions

- Issues and feature requests are welcome via **GitHub Issues**
- Pull requests are welcome

Repository:
https://github.com/playtopro/playtopro-integration

---

## ✅ Status

✅ Actively developed
✅ Compatible with modern Home Assistant releases
✅ HACS‑friendly and suited for custom repository usage
