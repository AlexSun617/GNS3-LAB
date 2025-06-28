from netmiko import ConnectHandler
from netmiko import redispatch
import time

#startup:
#source venv/bin/activate

#running:
#python netmiko_test.py

#closing:
#pip freeze > requirements.txt
#deactivate
# Connect to router\
VISITED = set()  #keeping track of all visited routers

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

def checkIfConfigured(output):

    if len(output) > 1:
        print("ospf 10 already configured")
        return True

    return False

def configurations(conn):
    print("Configuring OSPF 10")
    conn.write_channel('config t\n')
    conn.write_channel('router ospf 10\n')
    conn.write_channel('end\n')

def configureAllRouters(conn, ipAddress):
    
    if ipAddress in VISITED:
        return
    VISITED.add(ipAddress)


    if conn.host != ipAddress:
        conn.write_channel(f'ssh -l admin {ipAddress}\n')
        conn.read_until_pattern("Password: ")
        conn.write_channel('admin123\n')
        conn.read_until_pattern("#")
        redispatch(conn, device_type="cisco_ios")
        time.sleep(1) 
        conn.find_prompt() 

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
    if conn.host != "192.168.2.240":  # initial router
        conn.write_channel("exit\n")
        conn.read_until_pattern("#")
        redispatch(conn, device_type="cisco_ios")
        time.sleep(1) 

        



def main():
    router = ConnectHandler (
    device_type= 'cisco_ios',
    host = '192.168.2.240',        
    username = 'admin',
    password = 'admin123',
    )
    print(f"SSHing onto 192.168.2.240")
    configureAllRouters(router, "192.168.2.240")
    router.disconnect()


if __name__ == "__main__":
    main()
