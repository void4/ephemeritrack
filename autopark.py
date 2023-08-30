from pwi4_client import PWI4
print("Connecting to PWI4...")
pwi4 = PWI4()

s = pwi4.status()
print("Mount connected:", s.mount.is_connected)

if not s.mount.is_connected:
    print("Connecting to mount...")
    s = pwi4.mount_connect()
    print("Mount connected:", s.mount.is_connected)

pwi4.mount_tracking_off()
pwi4.mount_park()


