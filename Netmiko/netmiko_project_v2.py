from netmiko import ConnectHandler
from netmiko import redispatch
import time

'''
This code will be very similar to V1, the main difference will be the configurations.

Current Topology:

Cloud --> R1 --> R2 --> R3 --> R4

The goal of this code will be to actually configure and test the default routes.
The code will use nested ssh sessions, to configure the default routes, and then will test them.

'''

VISITED = set()  #keeping track of all visited routers

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

#function to check if the configuration that we are planning to do has already been configured
def checkIfConfigured(output):

    
    return False

#function to apply configurations to the device (routers)
def configurations(conn):

    #simple configurations to start
    print("Configuring OSPF 10")
    conn.write_channel('config t\n')
    conn.write_channel('router ospf 10\n')
    conn.write_channel('end\n')

#function that will SSH onto a router, do a configuration
#and then check if they have any neighbors that are routers and the ssh onto them
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
    if conn.host != "192.168.2.240":  
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
