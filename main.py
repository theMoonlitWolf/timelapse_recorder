#!/usr/bin/env python3

# See live log: journalctl -u timelapse -f
# To enable service on boot: sudo systemctl enable timelapse
# To disable service on boot: sudo systemctl disable timelapse
# To run manually: sudo timelapse
# To check service status: sudo systemctl status timelapse



import os
import datetime
import logging
import threading
import time
import signal
import shutil
import subprocess
import sys
import glob

import RPi.GPIO as GPIO
from picamera2 import Picamera2
from datetime import timedelta

# GPIO setup
LED_RED = 4
LED_GREEN = 27
LED_BLUE = 22
BUTTON_SPEED = 5
BUTTON_START_STOP = 6

FPS = 24
# Speed presets: (name, interval seconds)
speed_presets = [
    ("10x", 10/FPS),
    ("30x", 30/FPS),
    ("50x", 50/FPS),
    ("100x", 100/FPS),
    ("200x", 200/FPS),
    ("500x", 500/FPS),]
speed_index = 0

recording = False
done = False

capture_images_thread = None

picam2 = Picamera2()

next_capture = time.time()
start_time = time.time()

MOUNT_POINT = "/home/pi/usb" # Pi user needs to have permission
IMG_FOLDER = f"{MOUNT_POINT}/timelapse_images"
LOCAL_LOG_PATH = "/tmp/timelapse.log"
RENDER_FOLDER = f"{MOUNT_POINT}/render"

RENDER_WAIT_SECONDS = 5  # Seconds to wait before rendering

render_skip_requested = False  # Global flag for skipping render

# ----

GPIO.setmode(GPIO.BCM)
GPIO.setup([LED_RED, LED_GREEN, LED_BLUE], GPIO.OUT)
GPIO.setup(BUTTON_SPEED, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_START_STOP, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# LED status definitions
LED_STATUS = {
    "off":       (0, 0, 0),
    "waiting":   (1, 1, 0),  # yellow
    "speed":     (1, 1, 0),   # yellow
    "ready":     (0, 1, 0),  # green
    "recording": (1, 0, 0),  # red
    "recording2":(1, 1, 0),  #yellow
    "video":     (0, 0, 1),  # blue
    "error":     (1, 0, 1),  # magenta
    "shutdown":  (0, 1, 1),  # cyan
    "selftest_white": (1, 1, 1),  # white
    "selftest_red":   (1, 0, 0),  # red
    "selftest_green": (0, 1, 0),  # green
    "selftest_blue":  (0, 0, 1),  # blue
}

def set_led_status(status):
    """Set LED color by status name."""
    r, g, b = LED_STATUS.get(status, (0, 0, 0))
    GPIO.output(LED_RED, GPIO.HIGH if r else GPIO.LOW)
    GPIO.output(LED_GREEN, GPIO.HIGH if g else GPIO.LOW)
    GPIO.output(LED_BLUE, GPIO.HIGH if b else GPIO.LOW)

def blink_led_status(status, times=3, interval=0.3):
    """Blink LED for a given status."""
    for _ in range(times):
        set_led_status(status)
        time.sleep(interval)
        set_led_status("off")
        time.sleep(interval)

def led_self_test():
    for status in ["selftest_white", "selftest_red", "selftest_green", "selftest_blue"]:
        set_led_status(status)
        time.sleep(0.25)
    set_led_status("off")
    time.sleep(0.1)

def setup_logging(timestamp):
    log_file = LOCAL_LOG_PATH

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode='w'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return log_file

def run_and_log(cmd):
    logging.info(f"\n> Running: {' '.join(cmd)}\n")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in process.stdout:
        logging.info(line.rstrip())
    process.stdout.close()
    returncode = process.wait()
    if returncode != 0:
        logging.error(f"!! Command failed with return code {returncode}\n")
        blink_led_status("error", times=5, interval=0.2)
        set_led_status("error")
    return returncode

def mount_usb(device):
    if not device:
        logging.error("No USB device found.")
        return False
    if not os.path.exists(MOUNT_POINT):
        os.makedirs(MOUNT_POINT, exist_ok=True)
    ret = run_and_log(["sudo", "mount", "-o", "uid=pi,gid=pi", device, MOUNT_POINT])
    return ret == 0

def unmount_usb():
    run_and_log(["sudo", "umount", MOUNT_POINT])

def find_usb_device():
    devices = glob.glob("/dev/sd[a-z][1-9]*")
    if not devices:
        devices = glob.glob("/dev/sd[a-z]")
    devices = sorted(set(devices))
    if len(devices) > 1:
        logging.debug(f"Multiple USB devices found: {devices}, using the first one.")
        return devices[0]
    elif devices:
        logging.debug(f"Found one USB device: {devices[0]}")
        return devices[0]
    else:
        return None

def wait_for_usb():
    device = find_usb_device()
    logging.info("Waiting for USB drive...")
    while True:
        device = find_usb_device()
        if device and os.path.exists(device):
            logging.info("USB device detected!")
            if mount_usb(device):
                logging.info(f"Mounted USB {device} at {MOUNT_POINT}")
                return True
            else:
                logging.error("Failed to mount USB. Retrying...")
                blink_led_status("error", times=3, interval=0.2)
                set_led_status("waiting")
        time.sleep(2)

def delete_old_images():
    if os.path.exists(IMG_FOLDER):
        msg = []
        msg.append("Deleting old recording images")
        for f in os.listdir(IMG_FOLDER):
            if f.endswith(".jpg"):
                os.remove(os.path.join(IMG_FOLDER, f))
                msg.append(".")
        msg.append("Done!")
        logging.info("".join(msg))
    else:
        os.makedirs(IMG_FOLDER, exist_ok=True)
        logging.info("Creating image folder")

def capture_images(interval):
    global recording, picam2
    picam2.configure(picam2.create_still_configuration())
    picam2.start()
    count = 0
    next_capture = time.time()
    while recording:
        next_capture += interval
        set_led_status("recording" if count%2 else "recording2")

        
        filename = f"{IMG_FOLDER}/img{count:05d}.jpg"
        # cmd = ["libcamera-still", "-o", filename, "--timeout", "100", "--nopreview", 
        #        "--width", "1440", "--height", "1080", "--quality", "90"]
        # run_and_log(cmd)
        picam2.capture_file(filename)
        logging.debug(f"Captured {filename}")

        count += 1

        if next_capture < time.time():
            logging.warning("Warning: capture is lagging behind.")
            next_capture = time.time()
        else:
            while next_capture > time.time():
                if not recording:
                    break
                time.sleep(0.05)

def create_video():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{MOUNT_POINT}/timelapse_{timestamp}.mp4"
    cmd = [
        "ffmpeg", "-framerate", F"{FPS}",
        "-i", f"{IMG_FOLDER}/img%05d.jpg",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        output_file
    ]
    logging.info("Creating video...")
    set_led_status("video")
    run_and_log(cmd)
    logging.info(f"Video saved to {output_file}")

def power_down():
    logging.info("Powering down...")
    set_led_status("off")
    subprocess.run(["sudo", "poweroff"])

def shutdown():
    set_led_status("shutdown")
    usb_log_path = os.path.join(MOUNT_POINT, f"timelapse.log")
    shutil.copy(LOCAL_LOG_PATH, usb_log_path)
    logging.info(f"Copied log to {usb_log_path}")
    logging.info("Unmounting USB and powering down in 1 second...")
    time.sleep(1)
    unmount_usb()
    power_down()


def button_speed_pressed(channel):
    set_led_status("off")
    global speed_index
    speed_index = (speed_index + 1) % len(speed_presets)
    name, _ = speed_presets[speed_index]
    logging.info(f"Speed set to {name}")
    blink_led_status("speed", times=speed_index+1)
    set_led_status("ready")

def wait_before_render():
    global render_skip_requested
    render_skip_requested = False

    def on_speed_press(channel):
        global render_skip_requested
        render_skip_requested = True

    GPIO.add_event_detect(BUTTON_SPEED, GPIO.FALLING, callback=on_speed_press, bouncetime=300)
    set_led_status("waiting")
    logging.info(f"Waiting {RENDER_WAIT_SECONDS} seconds before rendering. Press SPEED to skip and save images for later rendering.")
    for i in range(RENDER_WAIT_SECONDS):
        if render_skip_requested:
            break
        time.sleep(1)
    GPIO.remove_event_detect(BUTTON_SPEED)
    return render_skip_requested

def button_start_stop_pressed(channel):
    global recording, start_time, capture_images_thread, done
    if done:
        logging.info("Recording already done, please wait for USB to be unmounted.")
        return
    if not recording:
        set_led_status("recording")
        recording = True
        start_time = time.time()
        logging.info("Starting recording")
        GPIO.remove_event_detect(BUTTON_SPEED)
        capture_images_thread = threading.Thread(target=capture_images, args=(speed_presets[speed_index][1],))
        capture_images_thread.start()
    else:
        set_led_status("video")
        logging.info("Stopping recording")
        recording = False
        done = True
        if capture_images_thread is not None:
            capture_images_thread.join()
        time.sleep(1)
        recording_duration = time.time() - start_time
        num_images = len([f for f in os.listdir(IMG_FOLDER) if f.endswith(".jpg")])
        video_duration = num_images / FPS if num_images else 0
        effective_interval = recording_duration / num_images if num_images else 0
        effective_speed = effective_interval * FPS if num_images else 0
        
        logging.info("")
        logging.info("--- Recording Summary ---")
        logging.info(f"🕒  Real recording time: {str(timedelta(seconds=int(recording_duration)))}")
        logging.info(f"🎞️  Video duration:      {str(timedelta(seconds=int(video_duration)))} ({num_images} frames @ {FPS} fps)")
        logging.info(f"⚡  Playback speed:      {effective_speed:.1f}× (1s video = {str(timedelta(seconds=int(effective_speed)))}s real time)")
        logging.info(f"🧮  Effective interval:  {effective_interval:.2f}s between frames")
        logging.info("--------------------------")
        logging.info("")

        if wait_before_render():
            if os.path.isdir(RENDER_FOLDER):
                shutil.rmtree(RENDER_FOLDER)
            if os.path.isdir(IMG_FOLDER):
                shutil.copytree(IMG_FOLDER, RENDER_FOLDER)
                logging.info("Skiping render")
                shutdown()
                return
        
        set_led_status("video")
        create_video()
        shutdown()

def handle_exit(signum, frame):
    logging.warning(f"Received exit signal ({signum}), cleaning up...")
    try:
        set_led_status("off")
        GPIO.cleanup()
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")
    sys.exit(0)

def create_video_from_folder(img_folder, output_folder):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_folder, f"timelapse_{timestamp}.mp4")
    cmd = [
        "ffmpeg", "-framerate", f"{FPS}",
        "-i", os.path.join(img_folder, "img%05d.jpg"),
        "-vf", "scale=1280:960,setsar=1:1",  # adjust as needed
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        output_file
    ]
    logging.info(f"Rendering video from {img_folder} to {output_file}...")
    set_led_status("video")
    run_and_log(cmd)
    logging.info(f"Video saved to {output_file}")

def main():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = setup_logging(timestamp)
    global speed_index

    led_self_test()  # Startup self-test

    set_led_status("waiting")  # waiting for USB

    # Handle SIGTERM/SIGINT for systemd and manual stops
    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    try:
        wait_for_usb()
        if os.path.isdir(RENDER_FOLDER):
            # Wait before rendering, allow user to skip and save images for later rendering
            set_led_status("video")
            create_video_from_folder(RENDER_FOLDER, MOUNT_POINT)
            # Delete the render folder after rendering
            try:
                shutil.rmtree(RENDER_FOLDER)
                logging.info(f"Deleted render folder: {RENDER_FOLDER}")
            except Exception as e:
                logging.error(f"Failed to delete render folder: {e}")
            set_led_status("shutdown")
            logging.info("Render-only mode complete.")
            shutdown()
            return
        set_led_status("ready")  # ready to record
        delete_old_images()

        GPIO.add_event_detect(BUTTON_SPEED, GPIO.FALLING, callback=button_speed_pressed, bouncetime=300)
        GPIO.add_event_detect(BUTTON_START_STOP, GPIO.FALLING, callback=button_start_stop_pressed, bouncetime=300)

        logging.info("Press speed button to set speed, start/stop button to record, Ctrl+C to exit.")

        name, _ = speed_presets[speed_index]
        logging.info(f"Speed set to {name}")
        blink_led_status("speed", times=speed_index+1)
        set_led_status("ready")

        while True:
            time.sleep(1)
    except Exception as e:
        logging.exception("Fatal error occurred:")
        blink_led_status("error", times=10, interval=0.2)
        set_led_status("error")
    finally:
        try:
            set_led_status("off")
            GPIO.cleanup()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    main()