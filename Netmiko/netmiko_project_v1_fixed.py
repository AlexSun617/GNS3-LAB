
from netmiko import ConnectHandler
from netmiko import redispatch
import time
import os
import logging
logging.basicConfig(
    filename="netmiko_session_log.txt",
    filemode="w",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s: %(message)s",
)

VISITED_HOSTS = {}

def send_command_safe(conn, command):
    return conn.send_command(
        command,
        expect_string=r"[>#]",
        strip_prompt=True,
        strip_command=True,
        delay_factor=2,
        read_timeout=60
    )

def send_command_timing_safe(conn, command):
    return conn.send_command_timing(
        command,
        strip_prompt=True,
        strip_command=True,
        delay_factor=2
    )

def getNeighborAddresses(output):
    lines = output.splitlines()
    ip_list = []
    capture_ip = False

    for line in lines:
        if 'Capabilities:' in line:
            if 'Router' in line:
                capture_ip = True
            else:
                capture_ip = False
        elif capture_ip and 'IP address:' in line:
            parts = line.split('IP address:')
            if len(parts) > 1:
                ip = parts[1].strip()
                ip_list.append(ip)
                capture_ip = False
    return ip_list

def getHostname(conn):
    try:
        if not conn.is_alive():
            print(f"Connection to {conn.host} is dead.")
            return None

        conn.send_command("terminal length 0", expect_string=r"[>#]")
        output = send_command_safe(conn, "show run | include ^hostname")

        print(f"Hostname output on {conn.host}: {output}")

        for line in output.splitlines():
            line = line.strip()
            if line.startswith("hostname "):
                hostname = line.split()[-1]
                print(f"Extracted hostname: {hostname}")
                return hostname

        print(f"Hostname not found in output: {output}")
        return None

    except Exception as e:
        print(f"Failed to get hostname from {conn.host}: {e}")
        return None

def checkIfConfigured(output):
    return len(output.strip()) > 0

def configurations(conn):
    print("Configuring OSPF on all active interfaces")
    try:
        conn.conn.send_config_set("router ospf 10", "end")
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

    output = conn.read_channel()
    print(f"debugging RAW OUTPUT from {ipAddress}]:\n{output}")
    hostname = getHostname(conn)
    if hostname is None:
        print(f"Skipping router at {ipAddress} due to hostname retrieval failure.")
        return

    if hostname in VISITED_HOSTS:
        print(f"Already visited {hostname}, skipping.\n")
        return
    else:
        VISITED_HOSTS[hostname] = ipAddress
        write_to_inventory(hostname, ipAddress)

    output = send_command_timing_safe(conn, 'show running-config | section router ospf')
    if not checkIfConfigured(output):
        configurations(conn)

    neighbor_output = send_command_timing_safe(conn, "show cdp neighbors detail")
    neighbors = getNeighborAddresses(neighbor_output)

    for ip in neighbors:
        print(f"SSHing onto {ip}")
        configureAllRouters(conn, ip)

    if conn.host != "192.168.2.240":
        conn.write_channel("exit\n")
        conn.read_until_pattern("#")
        redispatch(conn, device_type="cisco_ios")
        conn.session_preparation = lambda: None
        print(f"Redispatched and enabled on {ipAddress}")
        time.sleep(3)

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
    time.sleep(1.5)
    router.find_prompt()
    configureAllRouters(router, "192.168.2.240")
    router.disconnect()

if __name__ == "__main__":
    main()
