# Raspberry Pi Timelapse Recorder

A robust timelapse recorder for Raspberry Pi with hardware button controls, LED feedback, USB storage, and flexible video rendering options.

---

## Features

- **Timelapse recording** with customizable speed presets
- **Hardware controls:** Start/stop and speed buttons
- **LED status indicators** for all major states and errors
- **Automatic USB mounting** for storage and video output
- **Render images to video** directly on the Pi or later on your computer
- **Safe shutdown** after completion
- **Systemd integration** for autostart and logging

---

## Hardware Requirements

- Raspberry Pi 3 (headless setup recommended for low power; may work with other models)
- Raspberry Pi Camera Module
- 3x LEDs (Red, Green, Blue)
- 2x Push buttons (Speed, Start/Stop)
- USB drive (size depends on recording duration and resolution)
- Resistors and jumper wires

---

## Setup Guide (Raspberry Pi 3, Headless)

This guide is optimized to save power and run the Pi headless (without monitor/keyboard/mouse).

### 1. **Install OS and Enable SSH**

- **Install Raspberry Pi OS Lite** (no desktop) on the SD card.
- **Enable SSH** for remote access:
  - Place an empty file named `ssh` (no extension) in the `/boot` partition of the SD card before first boot.

### 2. **Configure for Low Power**

Edit `/boot/config.txt` and add the following lines to disable HDMI, onboard LEDs, and other unused hardware:

```
# Disable HDMI to save power
hdmi_blanking=2

# Disable ACT LED
dtparam=act_led_trigger=none
dtparam=act_led_activelow=on

# Disable onboard audio (if not needed)
dtparam=audio=off

# Disable Wi-Fi and Bluetooth if not needed
dtoverlay=disable-wifi
dtoverlay=disable-bt

# Limit CPU frequency for lower power usage
arm_freq=600
```

> **Note:** Only disable Wi-Fi/Bluetooth if you are using Ethernet or do not need wireless access.

---

### 3. **Connect to the Pi**

- Use an Ethernet cable or connect to the Pi's Wi-Fi network (only if needed; don't disable Wi-Fi in `/boot/config.txt` if you need it).
- Find the Pi's IP address using your router's admin page, or by running `hostname -I` on the Pi (requires monitor/keyboard), or try `raspberrypi.local`.
- **SSH into the Pi:**  
  ```sh
  ssh pi@<your_pi_ip>
  ```
- **Default credentials:**  
  Username: `pi`  
  Password: `raspberry`

---

### 4. **Disable Unused Services**

```sh
sudo systemctl disable --now hciuart.service
sudo systemctl disable --now bluetooth.service
sudo systemctl disable --now avahi-daemon.service
sudo systemctl disable --now triggerhappy.service
```

---

### 5. **Clone the Repository**

```sh
sudo apt update
sudo apt install git
cd /home/pi
git clone <repository_url> timelapse_recorder
```
Replace `<repository_url>` with the actual URL of this repository.

---

### 6. **Install Dependencies**

```sh
sudo apt update
sudo apt install python3 python3-pip ffmpeg libcamera-apps
pip3 install RPi.GPIO
```

---

### 7. **Wire Up the LEDs and Buttons**

See the GPIO table below for pin assignments.

---

### 8. **Set Up the Systemd Service**

- Copy `timelapse.service` to `/etc/systemd/system/`:
  ```sh
  sudo cp /home/pi/timelapse_recorder/timelapse.service /etc/systemd/system/
  ```
- Enable the service to start on boot:
  ```sh
  sudo systemctl enable timelapse.service
  ```
- Start the service manually (or reboot):
  ```sh
  sudo systemctl start timelapse.service
  ```

---

## Accessing the Pi for Setup and Troubleshooting

- **SSH:** Use `ssh pi@<your_pi_ip>` from another computer on your network.
- **File Transfer:** Use `scp` or an SFTP client (like WinSCP or FileZilla) to upload/download files.
- **Logs:** View live logs remotely with:
  ```sh
  journalctl -u timelapse -f
  ```
- **USB Drive:** All timelapse images and videos are saved to the USB drive, which can be removed and read on any computer.

---

## GPIO Pinout

| Function       | GPIO Pin |
|----------------|----------|
| LED Red        | 4        |
| LED Green      | 27       |
| LED Blue       | 22       |
| Speed Button   | 5        |
| Start/Stop Btn | 6        |

---

## Software Requirements

- Raspberry Pi OS Lite (or compatible Linux)
- Python 3
- [RPi.GPIO](https://pypi.org/project/RPi.GPIO/) (usually preinstalled)
- [libcamera-still](https://www.raspberrypi.com/documentation/computers/camera_software.html) (for image capture)
- [ffmpeg](https://ffmpeg.org/) (for video rendering)

---

## Usage

- **Insert a USB drive** before or just after powering on.
- **LEDs** will indicate status (see below).
- **Press the Speed button** to cycle through speed presets (LED blinks to indicate selection).
- **Press the Start/Stop button** to begin or end recording.
- After recording, the video is rendered and saved to the USB drive.
- The Pi will power down automatically when finished.

---

## LED Status Table

| Status         | Meaning                                 | Color         |
|----------------|-----------------------------------------|---------------|
| off            | Idle/shutdown                           | off           |
| waiting        | Waiting for USB or before render        | yellow        |
| speed          | Speed selection feedback                | yellow        |
| ready          | Ready to record                         | green         |
| recording      | Recording timelapse                     | red           |
| video          | Rendering video                         | blue          |
| error          | Error occurred                          | magenta       |
| shutdown       | Shutting down                           | cyan          |
| selftest_*     | Startup self-test (white/red/green/blue)| various       |


### Default Speed Presets

| Speed Preset   | Description                          | LED Blinks |
|----------------|--------------------------------------|------------|
| 30x            | 1 frame every 1.25 seconds           | 1          |
| 50x            | 1 frame every 2.08 seconds           | 2          |
| 100x           | 1 frame every 4.17 seconds           | 3          |
| 200x           | 1 frame every 8.33 seconds           | 4          |
| 500x           | 1 frame every 20.83 seconds          | 5          |

---

## Viewing Logs

The log file will be saved at `/tmp/timelapse.log` and copied to the USB drive after the script finishes.

To view live logs from the service:
```sh
journalctl -u timelapse -f
```
This shows all output and errors from the script in real time.

---

## Rendering the Timelapse Video Later

### Skip Rendering on the Pi

- The Pi waits a few seconds before rendering.
- **To skip rendering and save images for later:**  
  During the waiting period (yellow LED), **press the SPEED button**.
- The Pi will move the images to the `render` folder and power down.
- Remove the USB drive and connect it to your computer.

### Render Later on the Pi

1. **Insert the USB drive** with the `render` folder back into the Pi.
2. **Power on the Pi** (or reboot).
3. The script will detect the `render` folder and automatically start the rendering process after a short wait.
4. **Do not press the SPEED button** during the wait if you want rendering to proceed.
5. When rendering is complete, the video will be saved to your USB drive and the Pi will power down.
   The `render` folder will be deleted.

- This feature can be used in case of render failure (rename `timelapse_images` to `render` on the USB drive), or if the battery is nearly empty after recording.

### Render on Your Computer

#### Install FFmpeg on Windows

1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html) (choose a Windows build, e.g., from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)).
2. Extract the zip (e.g., to `C:\ffmpeg`).
3. (Optional) Add `C:\ffmpeg\bin` to your system PATH for easy access.

#### Render the Video from Images

1. Open **Command Prompt** (`cmd`).
2. Navigate to the folder with your images (e.g., `render`):
   ```sh
   cd E:\render
   ```
3. Run FFmpeg:
   ```sh
   ffmpeg -framerate 24 -i img%05d.jpg -c:v libx264 -pix_fmt yuv420p timelapse.mp4
   ```
   - You can add `-vf "scale=1280:960,setsar=1:1"` to specify scale and aspect ratio. Images are shot at 1440x1080 (4:3).

---

## Troubleshooting

- **Service won’t start:** Check wiring, dependencies, and run `sudo systemctl status timelapse`.
- **No video output:** Ensure images are captured and USB has enough space.
- **LED stuck on error:** Check logs with `journalctl -u timelapse -f`.
- **Network/SSH issues:** Re-enable Wi-Fi/Ethernet as needed for remote access.

---

## License

MIT License

---

## Credits

Project by Viktor Potužník.