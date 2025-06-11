from netmiko import ConnectHandler

#startup:
#source venv/bin/activate

#running:
#python netmiko_test.py

#closing:
#pip freeze > requirements.txt
#deactivate

# Define the device details
device = {
    'device_type': 'cisco_ios',
    'ip': '192.168.2.240',        # Update to match your router IP
    'username': 'admin',
    'password': 'admin123',
}


# Connect to the device
net_connect = ConnectHandler(**device)

# Send a simple command
output = net_connect.send_command("show ip interface brief")
output2 = net_connect.send_command("ping 192.168.2.191")
print(output)
print(output2)

# Close the connection
net_connect.disconnect()
