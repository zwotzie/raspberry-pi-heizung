import socket

from pyblnet import BLNETDirect

hostname = "heizung.lan"
ip = socket.gethostbyname(hostname)

bld = BLNETDirect(ip, reset=True)

# latest_values = bld.get_latest()
# print(latest_values)

bld.get_count()
data = bld._get_data()

print(data)
print(len(data))
