from time import sleep, time
from datetime import datetime, timedelta, UTC

from astropy.time import Time, TimeDelta
from astropy.coordinates import SkyCoord, AltAz, EarthLocation
import astropy.units as u

location = EarthLocation(lat=-30.52630901637761*u.deg, lon=-70.85329602458852*u.deg, height=1710*u.m)

#set this to false if you want to test this locally, without actually importing/moving anything
ACTUALLYTRACK = False

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

SPEED_ARCSEC_SEC = 1

def track(prod=True):

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
	nlines = 2
	print("\n"*nlines, end="")

	time_start = datetime.now(UTC)

	while True:
		time_now = datetime.now(UTC)#datetime.strptime(t_0, "%Y-%m-%d %H:%M") + (datetime.utcnow() - fakestart)# + timedelta(hours=4.4)#XXX#SUBTRACT

		time_delta = time_now - time_start
		time_delta_seconds = time_delta.total_seconds()

		# https://en.wikipedia.org/wiki/CR_Bo%C3%B6tis
		starcoord = SkyCoord("13h48m55.2s 7d57m35.7s", unit=(u.hourangle, u.deg))

		position_angle = 0 * u.deg
		separation = time_delta_seconds * (SPEED_ARCSEC_SEC/60/60) * u.deg
		coord = starcoord.directional_offset_by(position_angle, separation)

		altaz = coord.transform_to(AltAz(obstime=time_now, location=location))

		mountstr = ""
		if prod:
		    #pwi4.mount_goto_ra_dec_j2000(ra/15, dec)

		    s = pwi4.status()

		    mountstr = f"Actual RA: {s.mount.ra_j2000_hours:.5f} hours;  Actual Dec: {s.mount.dec_j2000_degs:.4f} degs, Axis0 dist: {s.mount.axis0.dist_to_target_arcsec:.1f} arcsec, Axis1 dist: {s.mount.axis1.dist_to_target_arcsec:.1f} arcsec"

		if every:
			
			print("\033[A                             \033[A\n"*nlines, end="")
			print(f"{time_now} RA: {coord.ra:.4f} DEC: {coord.dec:.4f} ALT: {altaz.alt:.4f} AZ: {altaz.az:.4f}")
			print(mountstr)


		#if not s.mount.is_slewing:
		#    break
		sleep(0.01)

	#print("Slew complete. Tracking...")




try:
	track(ACTUALLYTRACK)
except Exception as e:
	print(e)

#pwi4.mount_tracking_off()
#pwi4.mount_stop()