
Playtopro Home Assistant Integration
A custom Home Assistant integration for Playtopro / Lichen play devices.
This integration allows Home Assistant to automatically discover, configure, and control Playtopro devices on your local network using mDNS (Zeroconf). It is distributed as a custom repository via HACS.


✨ Features

✅ Automatic device discovery using Zeroconf (mDNS)
✅ Guided setup via Home Assistant config flow
✅ Manual setup option if discovery is unavailable
✅ Options flow to update host/port after setup



📦 Installation (HACS – Custom Repository)
1. Add the repository to HACS

Open Home Assistant → HACS
Click the ⋮ (three dots) in the top‑right corner
Select Custom repositories
Add the repository:Repository: https://github.com/playtopro/playtopro-integration
Category: Integration
Click Add
2. Install the integration

In HACS, search for Playtopro
Click Install
Restart Home Assistant when prompted


🔧 Configuration
Automatic Discovery (Recommended)
If your Playtopro device is on the same network it can be automatically discovered.
Ensure that the device is in setup mode - the mode LED must be flashing.
To place the device in setup mode press and hold the mode button for 2 seconds and release.
The device will reboot into setup mode.

Go to Settings → Devices & Services
A notification will appear: “Discovered Playtopro device”
Click Add
Review the detected details and confirm
The device will be added automatically.

Once the device has been added, exit setup mode, press and hold the mode button for 2 seconds and release.
The device will reboot and the mode button will remain on.


Manual Setup
If discovery does not work, you can add the device manually:

Go to Settings → Devices & Services
Click Add Integration
Search for Playtopro
Enter:Host (IP address)
Port
Serial number (Printed on label)
Complete the setup wizard


⚙️ Options
After setup, zero config will update the IP address for you if required.

You can manually update connection details:

Go to Settings → Devices & Services
Find Playtopro
Click Configure
Update:Host
Port
Changes are validated before being applied.


🧠 How It Works

Devices are identified by their serial number
Zeroconf discovery updates the IP address automatically if it changes
Each physical device maps to a single Home Assistant device
Entities are grouped under the correct device


🌐 Network Requirements

Playtopro device and Home Assistant must be on the same local network for zero cofig.
Remote access is possible with the correct NAT and port forwards in place.


🌍 Translations
This integration supports Home Assistant’s translation system, english is provided.



📄 License
This project is licensed under the terms of the MIT License.


🌐 Additional Information
For more information about Playtopro products, features, and official documentation, please visit:

Playtopro Official Website: https://www.playtopro.com/
You may find product overviews, specifications, firmware details, and general support resources there.


🤝 Support & Contributions

Issues and feature requests are welcome via GitHub Issues
Pull requests are welcome
Repository: https://github.com/playtopro/playtopro-integration

