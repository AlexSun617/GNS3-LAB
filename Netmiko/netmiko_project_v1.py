from netmiko import ConnectHandler
from netmiko import redispatch
import time

'''
This code is to test some capabilities of nested SSH, where you ssh onto one router, 
and then ssh again while in that ssh session creating a "nested" ssh session.

Not supported by default in ansible.

This could be useful when all the routes/default routes are not yet configured
#and the cloud cannot access all routers directly but could via nested ssh sessions.
This code currently assumes that all routers share the same ssh login and password.

Goal will setup OSPF on all routers
'''

VISITED_HOSTS = {}  #keeping track of all visited routers


#function to grab neighbor ip addresses based on the "show cdp neighbors detail" output
def getNeighborAddresses(output):
    # Extract IPs only if the neighbor has 'Capabilities: Router'
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
                capture_ip = False  # Reset after capturing one IP
    return ip_list


#function to grab hostname
def getHostname(conn):
    try:
        if not conn.is_alive():
            print(f"[ERROR] Connection to {conn.host} is dead.")
            return None
        output = conn.send_command("show run | include hostname")
        print(f"DEBUG: Hostname output on {conn.host}: {output}")
        return output.strip().split()[-1] if "hostname" in output else None
    except Exception as e:
        print(f"[EXCEPTION] Failed to get hostname from {conn.host}: {e}")
        return None


#function to check if the configuration that we are planning to do has already been configured
def checkIfConfigured(output):

    if len(output) > 1:
        print("ospf 10 already configured")   
        return True

    return False


#function to apply configurations to the device (routers)
def configurations(conn):

    print("Configuring OSPF on all active interfaces")
    config_commands = [
        'router ospf 10',
        'end'
    ]

    conn.send_config_set(config_commands)
    

#function that will SSH onto a router, do a configuration
#and then check if they have any neighbors that are routers and the ssh onto them
def configureAllRouters(conn, ipAddress):
    

    if conn.host != ipAddress:
        conn.write_channel(f'ssh -l admin {ipAddress}\n')
        conn.read_until_pattern(pattern=r"[Pp]assword: ")
        conn.write_channel('admin123\n')
        conn.read_until_pattern("#")
        redispatch(conn, device_type="cisco_ios")
        time.sleep(1) 
        conn.enable() 
        prompt = conn.find_prompt()
        if not prompt or prompt == "":
            print(f"[ERROR] No prompt found after SSH to {ipAddress}. Aborting.")
            return
    
    hostname = getHostname(conn)
    if hostname is None:
        print(f"[SKIP] Skipping router at {ipAddress} due to hostname retrieval failure.")
        return

    if hostname in VISITED_HOSTS:
        print(f"Already visited {hostname}, skipping.\n")
        return
    else:
        VISITED_HOSTS[hostname] = ipAddress

    #check if ospf has been configured
    output = conn.send_command_timing('show running-config | section router ospf')
    isConfigured = checkIfConfigured(output)
    if isConfigured == False:
        configurations(conn)
        
    neighbor_output = conn.send_command_timing("show cdp neighbors detail")


    neighbors = getNeighborAddresses(neighbor_output)


    for ip in neighbors:
        print(f"SSHing onto {ip}")
        configureAllRouters(conn, ip)
    
    #exit back to original router
    if conn.host != "192.168.2.240":  
        conn.write_channel("exit\n")
        conn.read_until_pattern("#")
        redispatch(conn, device_type="cisco_ios")
        time.sleep(3) 
        


def main():
    print(">>> RUNNING UPDATED VERSION V1.2 <<<")
    router = ConnectHandler (
    device_type= 'cisco_ios',
    host = '192.168.2.240',        
    username = 'admin',
    password = 'admin123',
    )
    print(f"SSHing onto 192.168.2.240")
    router.enable() 
    configureAllRouters(router, "192.168.2.240")
    router.disconnect()


if __name__ == "__main__":
    main()
