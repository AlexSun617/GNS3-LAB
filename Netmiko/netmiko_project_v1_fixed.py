
from netmiko import ConnectHandler
from netmiko import redispatch
import time
import os
import logging

'''
Fixed version as previous was unstable.

Changes:

1. Manually update base_prompt after every new ssh because netmiko wasnt doing it by default
2. removed get hostname function as it was more efficient to grab the hostname ahead of time  
   during the show cdp neighbors output. 

Code works now and is stable.

'''
#tracks visited hosts by hostname so that we dont waste time on 
#routers that we already visited.
VISITED_HOSTS = {}

#This is to capture debug log and save as a txt
logging.basicConfig(
    filename="netmiko_session_log.txt",
    filemode="w",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s: %(message)s",
)

def send_command_safe(conn, command):
    return conn.send_command(
        command,
        expect_string=r"[>#]",
        strip_prompt=True,
        strip_command=True,
        delay_factor=0,
        read_timeout=60
    )

def send_command_timing_safe(conn, command):
    return conn.send_command_timing(
        command,
        strip_prompt=True,
        strip_command=True,
        delay_factor=0
    )

def getNeighborAddresses(output):
    lines = output.splitlines()
    neighbors = []
    current_hostname = None
    current_ip = None
    capture = False
    for line in lines:
        line = line.strip()

        if line.startswith("Device ID: "):
            line = line.split("Device ID: ")[1].strip()
            current_hostname = line.split(".")[0]

        elif "IP address: " in line:
            current_ip = line.split("IP address: ")[1].strip()

        elif "Capabilities: " in line:
            if "Router" in line:
                capture = True

        if current_hostname and current_ip and capture:
            neighbors.append((current_hostname, current_ip))
            current_hostname = None
            current_ip = None
            capture = False

    return neighbors


def checkIfConfigured(output):
    return len(output.strip()) > 0

def configurations(conn):
    print("Configuring OSPF on all active interfaces")
    try:
        conn.send_config_set(["router ospf 10", "end"])
    except Exception as e:
        print(f"Error during configuration: {e}")

def write_to_inventory(hostname, ip):
    script_dir = os.path.dirname(__file__)
    file_path = os.path.join(script_dir, "router_inventory.txt")

    print(f"Writing to file: {file_path}")
    print(f"Writing: {hostname},{ip}")

    try:
        with open(file_path, "a") as file:
            file.write(f"{hostname},{ip}\n")
    except Exception as e:
        print(f"Failed to write to inventory file: {e}")

def configureAllRouters(conn, ipAddress):
    if conn.host != ipAddress:

        conn.write_channel(f'ssh -l admin {ipAddress}\n')
        conn.read_until_pattern(pattern=r"[Pp]assword: ")
        conn.write_channel('admin123\n')

        # flush banner or MOTD
        conn.write_channel('\n')
        conn.read_until_pattern(pattern=r"[>#]")
        redispatch(conn, device_type="cisco_ios")

        # The critical fix: reinitialize session to update base_prompt
        conn.base_prompt = conn.find_prompt().strip().strip("#>")
        conn.session_preparation = lambda: None  # disable auto prep
        conn.host = ipAddress
        print(f"Updated base_prompt to: {conn.base_prompt}")

    send_command_safe(conn, "terminal length 0")
    conn.write_channel('\n')
    conn.read_until_pattern(pattern=r"[>#]")

    
    output = send_command_timing_safe(conn, 'show running-config | section router ospf')
    if not checkIfConfigured(output):
        configurations(conn)

    neighbor_output = send_command_timing_safe(conn, "show cdp neighbors detail")
    neighbors = getNeighborAddresses(neighbor_output)

    for neighbor in neighbors:
        if neighbor[0] not in VISITED_HOSTS:
            print(f"SSHing onto {neighbor[1]}")
            VISITED_HOSTS[neighbor[0]] = neighbor[1]
            configureAllRouters(conn, neighbor[1])
        

    if conn.host != "192.168.2.240":
        conn.write_channel("exit\n")
        conn.read_until_pattern("#")
        redispatch(conn, device_type="cisco_ios")
        conn.session_preparation = lambda: None
        print(f"Redispatched and enabled on {ipAddress}")


def main():

    print(">>> RUNNING FIXED VERSION V1.3 <<<")
    inventory_path = os.path.join(os.path.dirname(__file__), "router_inventory.txt")
    open(inventory_path, "w").close()

    router = ConnectHandler(
        device_type='cisco_ios',
        host='192.168.2.240',
        username='admin',
        password='admin123',
        session_log="netmiko_session_log.txt"
    )
    print(f"SSHing onto 192.168.2.240")

    router.enable()
    router.find_prompt()
    VISITED_HOSTS["R1"] = "192.168.2.240"
    configureAllRouters(router, "192.168.2.240")
    
    router.disconnect()
    for key, value in VISITED_HOSTS.items():
        write_to_inventory(key, value)

if __name__ == "__main__":
    main()
