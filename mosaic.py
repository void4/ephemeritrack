from time import sleep
import os
from datetime import datetime

import win32com.client
from astropy.io import fits

from pwi4_client import PWI4

print("Connecting to PWI4...")
pwi4 = PWI4()

s = pwi4.status()
print("Mount connected:", s.mount.is_connected)

if not s.mount.is_connected:
    print("Connecting to mount...")
    s = pwi4.mount_connect()
    print("Mount connected:", s.mount.is_connected)

print("  RA/Dec: %.4f, %.4f" % (s.mount.ra_j2000_hours, s.mount.dec_j2000_degs))

print("Connecting to camera...")
# if you don't know what your driver is called, use the ASCOM Chooser
camera = win32com.client.Dispatch("MaxIm.CCDCamera")
camera.LinkEnabled = True

if not camera.LinkEnabled:
    print("Failed to start camera")
    exit(1)

print("Turning cooler on...")
camera.CoolerOn = True
if camera.CoolerOn:
    print("Cooler turned on")
else:
    print("Cooler did NOT turn on, continuing regardless")

print("Camera ready, starting exposure...")

print("Slewing...")
pwi4.mount_tracking_on()

ra_start = 7.33
dec_start = -26.33

#42 28

ra_step = 20/60/15
dec_step = 20/60

panels_x = 5
panels_y = 7

for y in range(panels_y):
    for x in range(panels_x):
        pwi4.mount_goto_ra_dec_j2000(ra_start+ra_step*x, dec_start+dec_step*y)
        sleep(0.2)

        while True:
            s = pwi4.status()

            print("RA: %.5f hours;  Dec: %.4f degs, Axis0 dist: %.1f arcsec, Axis1 dist: %.1f arcsec" % (
                s.mount.ra_j2000_hours, 
                s.mount.dec_j2000_degs,
                s.mount.axis0.dist_to_target_arcsec,
                s.mount.axis1.dist_to_target_arcsec
            ))

            if not s.mount.is_slewing:
                break
            sleep(0.2)

        print("Slew complete. Tracking...")
        camera.BinX = camera.BinY = 2
        print("Exposing...")
        # exposure, shutter open, #filter
        for f in range(4):
            print("filter", f)
            camera.expose(180,1,f)
            time_start = datetime.now()
            while not camera.ImageReady:
                sleep(0.01)

            print("finished exposure")

            os.makedirs(os.path.join(os.getcwd(), os.path.join("images", "mosaic2")), exist_ok=True)
            datetimestr = str(time_start).split('.')[0].replace(':', '-')
            camera.SaveImage(os.path.join(os.getcwd(), "images", "mosaic2", f"{datetimestr}_{x}_{y}_{f}.fit"))
            print("image saved")

pwi4.mount_tracking_off()
pwi4.mount_stop()
