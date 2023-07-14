import os
from time import sleep, time

from astroquery.jplhorizons import Horizons
from astropy.time import Time, TimeDelta
from datetime import datetime, timedelta
from astropy.coordinates import SkyCoord, AltAz, EarthLocation
import astropy.units as u

location = EarthLocation(lat=-30.52630901637761*u.deg, lon=-70.85329602458852*u.deg, height=1710*u.m)

class Every:
    def __init__(self, interval):
        self.interval = interval
        self.lasttime = time()

    def __bool__(self):
        current = time()
        if current-self.lasttime>=self.interval:
            self.lasttime = current
            return True
        return False

every = Every(1)


def track(eph, prod=True):

	if prod:
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

		print("Slewing...")
		pwi4.mount_tracking_on()

	# so the previous line is not erased, print an empty one
	print("")
	while True:
		now = datetime.utcnow()# + timedelta(hours=4.4)#XXX#SUBTRACT
		start = list(eph)[0]#just for testing
		end = None
		for t,c in eph.items():
		    if t >= now:
		        end = t
		        break
		    start = t

		if end is None:
			raise Exception("ran out of ephemerides need new ones")
		if start == end:
			raise Exception("need earlier ephemerides")
			exit(1)
		timediff = (end-start).total_seconds()
		factor = (now-start).total_seconds()
		p = factor/timediff
		#print(factor, timediff, p)

		start_ra = eph[start].ra.to_value()
		end_ra = eph[end].ra.to_value()
		start_dec = eph[start].dec.to_value()
		end_dec = eph[end].dec.to_value()

		# °/s
		ra_rate = (end_ra - start_ra)/timediff
		dec_rate = (end_dec - start_dec)/timediff
		
		# ''/s
		rate = (ra_rate**2+dec_rate**2)**0.5 * 60 * 60

		#print(start_ra, end_ra, start_dec, end_dec)
		ra = start_ra * (1-p) + end_ra * (p)
		dec = start_dec * (1-p) + end_dec * (p)

		coord = SkyCoord(ra/15, dec, unit=(u.hourangle, u.deg))

		obstime = Time.now()
		altaz = coord.transform_to(AltAz(obstime=obstime, location=location))

		if every:
			print ("\033[A                             \033[A")

			print(f"{now}\tRA: {coord.ra:.4f}\tDEC: {coord.dec:.4f}\tALT: {altaz.alt:.4f}\tAZ: {altaz.az:.4f}\tRATE: {rate:.4f}''/s")

		if prod:
		    pwi4.mount_goto_ra_dec_j2000(ra/15, dec)

		    s = pwi4.status()

		    print("RA: %.5f hours;  Dec: %.4f degs, Axis0 dist: %.1f arcsec, Axis1 dist: %.1f arcsec" % (
		        s.mount.ra_j2000_hours,
		        s.mount.dec_j2000_degs,
		        s.mount.axis0.dist_to_target_arcsec,
		        s.mount.axis1.dist_to_target_arcsec
		    ))

		#if not s.mount.is_slewing:
		#    break
		sleep(0.01)

	#print("Slew complete. Tracking...")

	#pwi4.mount_tracking_off()
	#pwi4.mount_stop()



obj_name = "Chandrayaan-3"
obj_id = -158

INTERVAL_SECONDS = 15#*60
STEPS = 4*15

while True:
	t_0 = datetime.utcnow() - timedelta(seconds=INTERVAL_SECONDS)#"2023-07-14 16:00"

	print(f"Loading ephemerides for {obj_name}...")
	epochs = [(Time(t_0)+TimeDelta(INTERVAL_SECONDS*i, format="sec")).jd for i in range(-1, STEPS)]

	obj = Horizons(id=obj_id, location="X07", epochs=epochs)

	#print(dir(obj.ephemerides()))

	eph = obj.ephemerides()
	#eph.show_in_browser()

	columns = eph.columns.keys()

	trackeph = {}

	for i in range(len(eph)):
		utctime = datetime.strptime(eph["datetime_str"][i][:-4], "%Y-%b-%d %H:%M:%S")
		ra = eph["RA"][i]
		dec = eph["DEC"][i]
		#print(ra,dec)
		coord = SkyCoord(ra, dec, unit=(u.deg, u.deg))
		#print(utctime, coord)
		trackeph[utctime] = coord
	print("Loaded ephemerides.")#TODO print first and last time

	try:
		track(trackeph, False)
	except Exception as e:
		print(e)
		# if this was even smarter it would preload the next ephemerides in a separate thread
		print("Exception encountered, loading new ephemerides...")