import socket
import time
import select
import sys



#-------------------------------------------------------------------------------------------
#Open a new socket for data transfer in new port
def open_new_data_socket(PUBLIC_UDP_IP, PRIVATE_PORT):
    print("\n")
    print("--- Creating a Data Socket for data transmition in adress :%s and Port :%s" % (PUBLIC_UDP_IP, PRIVATE_PORT))
    #open socket
    try:
        dataSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error as e:
        print ("Error creating socket: %s" % e)
        sys.exit(1)
    #Bind socket
    try:
        dataSock.bind((PUBLIC_UDP_IP, PRIVATE_PORT))
    except socket.gaierror as e:
        print ("Address-related error connecting to server: %s" % e)
        sys.exit(1)
    except socket.error as e:
        print ("Connection error: %s" % e)
        sys.exit(1)

    return dataSock



#------------------------------------------------------------------------------------------------
# 3 Way Handshake
def three_way_handshake(publicSock,udp_client_addr,PRIVATE_PORT):
    message = ("SYN-ACK"+str(PRIVATE_PORT)).encode()
    notConnected = True

    #Open a new socket for data transfer in new port
    

    while notConnected :
        print("Sending to client the new Connection Port :", PRIVATE_PORT)
        publicSock.sendto(message, udp_client_addr )

        #wait for "ACK"
        data, addr = publicSock.recvfrom(1024)
        if data == b"ACK\x00":
            print("Connection confirmed")
            print("\n")
            notConnected = False







#---------------------------------------------------------------------------------------
#Get the Public Port in which server should listen
def inputPort():
    port = 0
    if len(sys.argv) == 2:
        user_input = sys.argv[1]
        try:
            port = int(user_input)
        except ValueError:
            print("Please, put on a number bro")
            sys.exit()
    else:
        print("Please, put on (exactly) one argument bro")
        sys.exit()
    
    return port
    



#------------------------------------------------------------------------
#Get File, segment it and append a 6 octet sequence number
def segment_file(file_name):
    segments = []
    try :
        with open(file_name,"rb") as f:
            chunck = f.read(1018)
            segment = b"000001"+chunck
            segments.append(segment)
            i=1

            while chunck != b"":
                
                #set up the header
                i = i + 1
                header = b""
                if(i<10):
                    header = b"00000"+str(i).encode()
                elif(i<100):
                    header = b"0000"+str(i).encode()
                elif(i<1000):
                    header = b"000"+str(i).encode()
                elif(i<10000):
                    header = b"00"+str(i).encode()
                elif(i<100000):
                    header = b"0"+str(i).encode()

                #read next chunck and append it on the array
                chunck = f.read(1018)
                segment = header + chunck
                segments.append(segment)

    except EnvironmentError as e:
        print("Not able to open file, error: ",e)
        sys.exit(1)
        
    return segments


#---------------------------------------------------------------------------
#Send Each segment and wait for ack or send it again
def send_segments_stop_go(segments,dataSock, addr ):

    # Send all segments to client
    for segment in segments:

        WaitingAck = True
        while WaitingAck :

            # Sockets from which we expect to read, timeout in seconds
            timeout_in_seconds = 0.1
            inputs = [ dataSock ]

            # Send message, start chronometer
            inTime = time.perf_counter()
            dataSock.sendto(segment, addr )

            # Wait for ack to arrive or timeout
            readable, writable, exceptional = select.select(inputs, [], [], timeout_in_seconds)
            if not (readable or writable or exceptional):
                print('timed out')
            elif readable[0] is dataSock:
                stopTime = time.perf_counter()
                data, addr = dataSock.recvfrom(9)
                ack = data.decode().strip('\x00')
                print("Received ack: ", ack)
                print("time: ", stopTime-inTime)
                WaitingAck = False


    # Send "FIN" to client
    message = b"FIN"
    dataSock.sendto(message, addr )
    


    

    






#----------------------------------------------------------------------------
#./serveurX-NomDuGroupe NuméroPort
#./clientX IPServeur NuméroPortServeur NomFichier
if __name__ == "__main__":


    #Get Port from user
    PUBLIC_UDP_PORT = inputPort()

    #Settings for the public socket
    PUBLIC_UDP_IP = "192.168.122.1"
    PRIVATE_PORT = PUBLIC_UDP_PORT + 1


    #Open socket and bind Socket
    try:
        publicSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error as e:
        print ("Error creating socket: %s" % e)
        sys.exit(1)
    try:
        publicSock.bind((PUBLIC_UDP_IP, PUBLIC_UDP_PORT))
    except socket.gaierror as e:
        print ("Address-related error connecting to server: %s" % e)
        sys.exit(1)
    except socket.error as e:
        print ("Connection error: %s" % e)
        sys.exit(1)
    

    #Handle the connection request (3 way handshake + Creation on new port)
    print("--- Creating Public Socket in IP address: "+ PUBLIC_UDP_IP +" and Port"+ str(PUBLIC_UDP_PORT)+" ---")
    print("Wainting Connection Demand...")
    print("\n")
    data, addr = publicSock.recvfrom(1024)
    print("--- Starting 3 way handshake ---")
    if data == b"SYN\x00":
        print("Connection Request From Client")
        dataSock = open_new_data_socket(PUBLIC_UDP_IP,PRIVATE_PORT)
        three_way_handshake(publicSock, addr, PRIVATE_PORT)

        #Get the name of the file requested
        data, addr = dataSock.recvfrom(1024)
        file_name = data.decode().strip('\x00')
        print("File requested by client: ", str(file_name))

        #fragment the file
        print("framgenting file: ", file_name)
        segments = segment_file(file_name)

        #send each file in "Stop-and-Go" algorithm
        print("sending file to client")
        send_segments_stop_go(segments,dataSock,addr)
        
    
        
        








    #excepetion 
    # Third try-except block -- sending data
    """try:
        s.sendall("GET %s HTTP/1.0\r\n\r\n" % filename)
    except socket.error as e:
        print "Error sending data: %s" % e
        sys.exit(1)"""

    # Fourth tr-except block -- waiting to receive data from remote host
    """    try:
            buf = s.recv(2048)
        except socket.error, e:
            print "Error receiving data: %s" % e
            sys.exit(1)
        if not len(buf):
            break
        # write the received data
        sys.stdout.write(buf)"""