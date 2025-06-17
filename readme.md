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
- 3x LEDs (Red, Green, Blue) or one RGB LED with common cathode
- 2x Push buttons (Speed, Start/Stop)
- USB drive (size depends on recording duration and resolution)
- Resistors and jumper wires

---

## Setup Guide (Raspberry Pi 3, Headless)

This guide is optimized to save power and run the Pi headless (without monitor/keyboard/mouse).

### 1. **Install OS and Enable SSH**

- **Install Raspberry Pi OS Lite** (no desktop) on the SD card (using the Raspberry Pi Imager: https://www.raspberrypi.com/software/).
   - Select "Raspberry Pi OS Lite"
   - When prompted, edit settings:
      - Set hostname (default is `raspberrypi.local`).
      - Create a user called `pi` and set password (there is no longer a default user).
      - Enable SSH by checking the box under Services (or create an empty file named `ssh` in the boot partition after writing the image).
   - Select the SD card and write the image.

### 2. **Configure for Low Power**

Edit `config.txt` in the `boot` partition of the SD card and edit (or add if not present) the following lines to disable HDMI, onboard LEDs, and other unused hardware:
   You will need to remove the SD card and plug it back in.

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
```

> **Note:** Only disable Wi-Fi/Bluetooth if you are using Ethernet or do not need wireless access.

---

### 3. **Boot the Pi**
- Insert the SD card into the Raspberry Pi and power it on.
- Wait for a minute or two for the Pi to boot up and enable SSH.

---

### 4. **Connect to the Pi**

- Use an Ethernet cable or connect to the Pi's Wi-Fi network (only if needed; don't disable Wi-Fi in `config.txt` if you need it).
- Use the domain name you set up (`raspberrypi.local`) or find the Pi's IP address using your router's admin page.
- **SSH into the Pi:**  
  ```sh
  ssh pi@<your_pi_ip>
  ```
> **Note:** You may need to accept the SSH key fingerprint on first connection.
- **Login** with the credentials you set up earlier  

---

### 5. **Disable Unused Services**

```sh
sudo systemctl disable --now hciuart.service
sudo systemctl disable --now bluetooth.service
sudo systemctl disable --now avahi-daemon.service
sudo systemctl disable --now triggerhappy.service
```

---

### 6. **Clone the Repository**

```sh
sudo apt update
sudo apt install git
git clone <repository_url> /home/pi/timelapse_recorder
```
Replace `<repository_url>` with the actual URL of this repository,
probably `https://github.com/theMoonlitWolf/timelapse_recorder`.
> **Note:** If you are using a different location for the repository, adjust the path in `timelapse_recorder_.service` accordingly.
> **Note:** You may need to accept instalation of additional packages when installing git.

---

### 7. **Install Dependencies**

```sh
sudo apt update
sudo apt install -y python3 python3-pip ffmpeg python3-picamera2
pip3 install RPi.GPIO
```

---

### 8. **Wire Up the LEDs and Buttons**

See the GPIO table below for pin assignments.

---

### 9. **Set Up the Systemd Service**

- Copy `timelapse_recorder.service` to `/etc/systemd/system/`:
  ```sh
  sudo cp /home/pi/timelapse_recorder/timelapse_recorder.service /etc/systemd/system/
  ```
- Enable the service to start on boot:
  ```sh
  sudo systemctl enable timelapse_recorder.service
  ```
- Start the service manually (or reboot):
  ```sh
  sudo systemctl start timelapse_recorder.service
  ```

---

## Accessing the Pi for Setup and Troubleshooting

- **SSH:** Use `ssh pi@<your_pi_ip>` from another computer on your network.
- **File Transfer:** Use `scp` or an SFTP client (like WinSCP or FileZilla) to upload/download files.
- **Logs:** View live logs remotely with:
```sh
journalctl -u timelapse_recorder -f
```
- **USB Drive:** All timelapse images, videos and log files are saved to the USB drive, which can be removed and read on any computer.

---

## GPIO Pinout

| Function       | GPIO Pin |
|----------------|----------|
| LED Red        | 4        |
| LED Green      | 27       |
| LED Blue       | 22       |
| Speed Button   | 5        |
| Start/Stop Btn | 6        |
Buttons are connected between the GPIO pin and ground (GND).
LEDs are connected between the GPIO pin and a ground (GND) pin with a suitable resistor (typically 220-330 ohms).

---

## Software Requirements

- Raspberry Pi OS Lite (or compatible Linux)
- Python 3
- [RPi.GPIO](https://pypi.org/project/RPi.GPIO/) (usually preinstalled)
- [Picamera2](https://www.raspberrypi.com/documentation/computers/camera_software.html#picamera2) (for image capture)
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

| Status         | Meaning                                 | Color                                     |
|----------------|-----------------------------------------|-------------------------------------------|
| off            | Idle/shutdown                           | off                                       |
| waiting        | Waiting for USB or before render        | yellow                                    |
| speed          | Speed selection feedback                | yellow                                    |
| ready          | Ready to record                         | green                                     |
| recording      | Recording timelapse                     | alternating yellow and red on every frame |
| video          | Rendering video                         | blue                                      |
| error          | Error occurred                          | magenta                                   |
| shutdown       | Shutting down                           | cyan                                      |
| selftest_*     | Startup self-test (white/red/green/blue)| various                                   |


### Default Speed Presets

| Speed Preset | Description                  | LED Blinks |
|--------------|------------------------------|------------|
| 10x          | 1 frame every 0.42 seconds   | 1          |
| 30x          | 1 frame every 1.25 seconds   | 2          |
| 50x          | 1 frame every 2.08 seconds   | 3          |
| 100x         | 1 frame every 4.17 seconds   | 4          |
| 200x         | 1 frame every 8.33 seconds   | 5          |
| 500x         | 1 frame every 20.83 seconds  | 6          |

---

## Viewing Logs

The log file will be saved at `/tmp/timelapse.log` and copied to the USB drive after the script finishes.

To view live logs from the service:
```sh
journalctl -u timelapse_recorder -f
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
   > **Note:** The `render` folder will be deleted. 

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

## Updating the Timelapse Recorder

To update your timelapse recorder code to the latest version, follow these steps:

1. Navigate to the project directory:
```sh
cd /home/pi/timelapse_recorder
```

2. Check if you have local changes:
```sh
git status
```
   If you have changes, resolve merge conflicts.

3. Pull the latest changes from the repository:
```sh
git pull
```
   This will download and apply any updates from the remote repository.

4. (Optional) Update Python dependencies if needed:
```sh
sudo apt update
sudo apt install --only-upgrade python3 python3-pip ffmpeg libcamera-apps
pip3 install --upgrade RPi.GPIO
```

5. (Optional) Update the service file if needed (mentioned in changelog)
```sh
sudo cp /home/pi/timelapse_recorder/timelapse_recorder.service /etc/systemd/system/
```

6. Restart the systemd service to apply the update:
```sh
sudo systemctl restart timelapse_recorder.service
```

- All necessary commands in one:
```sh
cd /home/pi/timelapse_recorder
git pull
sudo systemctl restart timelapse_recorder.service
```

- If it fails or the process returns imediatelly after start, you may want to delete and clone it again:
```sh
sudo rm -r /home/pi/timelapse_recorder
git clone <repository_url> /home/pi/timelapse_recorder
sudo systemctl restart timelapse_recorder.service
```

---

## Troubleshooting

- **Service won’t start:** Check wiring, dependencies, and run `sudo systemctl status timelapse_recorder`.
- **No video output:** Ensure images are captured and USB has enough space.
- **LED stuck on error:** Check logs with `journalctl -u timelapse_recorder -f`.
- **Network/SSH issues:** Re-enable Wi-Fi/Ethernet as needed for remote access.

---

## Changelog

- **1.0.0**
   First working version, needs to be instlled new
- **1.0.1**
   Added forgotten delay to wait for render skipping
- **1.0.2**
   Consistent shutdown procedure

---

## License

MIT License

---

## Credits

Project by Viktor Potužník.