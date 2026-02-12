# Playtopro Home Assistant Integration

A custom **Home Assistant integration** for **Playtopro / Lichen Play** devices.

This integration allows Home Assistant to automatically discover, configure, and control Playtopro devices on your local network using **mDNS (Zeroconf)**. It is distributed as a **custom repository via HACS**.

---

## ✨ Features

- ✅ **Automatic device discovery** using Zeroconf (mDNS)
- ✅ **Guided setup** via the Home Assistant config flow
- ✅ **Manual setup** option if discovery is unavailable
- ✅ **Options flow** to update connection details (host/port)

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

All changes are validated before being applied.

---

## 🧠 How It Works

- Devices are identified by their **serial number**
- Zeroconf discovery keeps the IP address up to date automatically
- Each physical device maps to a **single Home Assistant device**
- All entities are grouped under the correct device

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
