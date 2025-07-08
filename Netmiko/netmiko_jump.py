from netmiko import ConnectHandler
from netmiko import redispatch

#testing nested ssh


# Connect to router\
router = ConnectHandler (
    device_type= 'cisco_ios',
    host = '192.168.2.240',        # Update to match your router IP
    username = 'admin',
    password = 'admin123',
)

print(router.send_command("show run | include hostname"))

r2_ip = "192.168.5.2"

#entering ssh command to R2
router.write_channel('ssh -l admin ' + r2_ip + ' \n')
#waiting for password prompt
router.read_until_pattern(pattern = r"Password:")
#entering password
router.write_channel('admin123\n')
#waiting for user exec prompt 
router.read_until_pattern(pattern=r"#")

hostname_output = router.send_command("show run | include hostname")
#output will be 'hostname R2'
hostname = hostname_output.strip().split()[-1] #'R2'

print("We are now on: ", hostname)

redispatch(router, device_type = "cisco_ios")

print(router.send_command("show ip int brief"))

router.disconnect()
