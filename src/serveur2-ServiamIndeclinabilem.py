import socket
import time
import select
import sys


#PARAMETERS
chunk_size = 1494 #Client2 : 1494 sinon pas bon

N = 30 # window of size N --> given by client's rcvw size --> client drop if more than 30
A = 0.8 #Typical value --> α = 0.125
B = 0.8 #typically, β = 0.25

cwnd = 1 #Slow start : start with cwnd = 1

#for fast rtx
nbdup = 4



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
        data, _ = publicSock.recvfrom(1024)
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
            chunck = f.read(chunk_size)#1018
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
                elif(i<1000000):
                    header = b""+str(i).encode()

                #read next chunck and append it on the array
                chunck = f.read(chunk_size)
                segment = header + chunck
                segments.append(segment)

    except EnvironmentError as e:
        print("Not able to open file, error: ",e)
        sys.exit(1)
        
    return segments





#----------------------------------------------------------------------------------------
#                           TCP PROTOCOLS
#----------------------------------------------------------------------------------------
#Client 1 : a lot of delay, timeout time plays important role! No slow start ontherwise always cwnd of 1 : we send fast but receive slowly


#---------------------------------------------------------------------------
#Send Each segment and wait for ack or send it again, with TX window (cumulative ack: CBN)
def GBN(segments,dataSock, addr ):
    
    #------------------------GLOBAL VARIABLES------------------------------------------------------------------
    #pointers to seq number
    send_base = 1 # first segment that is in flight
    nextseqnum = 1 # first usable segment not yet sent

    #For timeout
    RTT_timeTAB = [time.perf_counter() for i in range(len(segments))]
    #RTT_time = 0
    SampleRTT = 0
    inTime = [time.perf_counter() for i in range(len(segments))]
    EstimatedRTT = 0
    DevRTT = 0
    timeout_time = 0.2
    RTTsamples = []

    #to stop sending once we are done
    dataToSend = True
    envoieFin = False

    #Congestion variables
    sstresh = 1000
    acks = []
    #-----------------------------------------------------------------------------------------------------------

    #enter slow start
    #jump slow star and go directly to congestion avoidance at sstresh if fast rtx
    #tcp vegas : for packet delay:

    #-------------------------------------CONGESTION PROTOCOLS--------------------------------------------------
    
        

            


    def fast_rtx(ackSegSeqNum,nbdup):
        """
        • Retransmit lost packet
        • Calculate FlightSize= min(rwnd,cwnd)
        • ssthresh = FlightSize/2
        • Enter Slow Start: cwnd = 1
        """
        nonlocal inTime

        if ackSegSeqNum == send_base-1:
            acks.append(ackSegSeqNum)
        elif ackSegSeqNum >= send_base :
            acks.clear()
        if acks.count(ackSegSeqNum) == nbdup:
            segment = segments[send_base-1]#send_base-1
            dataSock.sendto(segment, addr )
            #print("PACKET LOST DETECTION : FAST RETRANSMIT | Segment Received:"+str(ackSegSeqNum)+" | Segment To reSend:"+str(segment[0:6]) )
            lost_packet_handler(False) #what to do after packet lost

    
    def timeout_estimation(SampleRTT):
        nonlocal EstimatedRTT
        nonlocal DevRTT
        nonlocal timeout_time
        nonlocal RTTsamples

        RTTsamples.append(SampleRTT)
        #RTT estimation : SampleRTT: measured time from segment transmission until ACK receipt, ignore retransmissions
        EstimatedRTT = (1 - A)*EstimatedRTT + A*SampleRTT
        #safety margin : estimate SampleRTT deviation from EstimatedRTT
        DevRTT = (1-B)*DevRTT +B*abs(SampleRTT-EstimatedRTT)
        #timeout to use is the sum of both : 
        timeout_time = EstimatedRTT + 4*DevRTT
        #print(str(EstimatedRTT)+"//"+str(SampleRTT)+"//"+str(timeout_time))



    def lost_packet_handler(timeout_lost):
        """
        If a packet is considered lost(options):
            1) enter slow start
        """
        nonlocal sstresh
        global cwnd

        #sstresh = int(min(cwnd,N)/2)
        if timeout_lost:
            pass
        else:
            sstresh = int(min(cwnd,N)/2)
            cwnd = sstresh


   
    def slow_start_and_congestion_avoidance():
        """
        • Start with cwnd= 1
        • For every received ACK: cwnd= cwnd+ 1
        ssthresh : Decides the moment when the host goes from Slow Start to Congestion Avoidance
            Arbitrary initial value (usually very high)
            • After a lost segment (detected through a timeout or
            duplicate ACK): ssthresh= FlightSize/2
            • After the retransmission: cwnd = 1
        """
        global cwnd
        if (cwnd <= sstresh):
            cwnd = cwnd + 1
            #print("DEBUG : SLOW START | cwnd:"+str(cwnd)+" | sstrsh:"+str(sstresh))
        if (cwnd > sstresh):
            cwnd = cwnd + 1/cwnd
            #print("DEBUG : CONGESTION AVOIDANCE | cwnd:"+str(cwnd)+" | sstrsh:"+str(sstresh))




        
    #------------------------------------------------------------------------------------------------------------------



    
    while dataToSend:
        #--------------------------------------------------TIMEOUT HANDLER--------------------------------------------------------
        """
        offTime = time.perf_counter()
        if offTime - inTime > timeout_time : #Lost packets detected : 
            print("PACKET LOST DETECTION : TIMEOUT | TimeLimit:"+str(timeout_time)+" | reSend Segment:"+str(send_base))
            inTime=time.perf_counter()
            lost_packet_handler(True)
            segment = segments[send_base-1]
            dataSock.sendto(segment, addr )
            #for i in range(send_base,nextseqnum): #all in flight packets
                #segment = segments[i-1]
                #dataSock.sendto(segment, addr )
        #---------------------------------------------------------------------------------------------------------------------------
        """
        offTime = time.perf_counter()
        for i in range(send_base,nextseqnum): #all in flight packets
            if offTime - inTime[i-1] > timeout_time : #Lost packets detected : 
                #print("PACKET LOST DETECTION : TIMEOUT | TimeLimit:"+str(timeout_time)+" | reSend Segment:"+str(i))
                inTime[i-1] = time.perf_counter()
                lost_packet_handler(True)
                segment = segments[i-1]
                dataSock.sendto(segment, addr )
            
                #segment = segments[i-1]
                #dataSock.sendto(segment, addr )
        

        #reset list of file descriptors
        inputs = [ dataSock ]
        outputs = [ dataSock ]

        #unblocking poll of sockets
        readable, writable, _ = select.select(inputs, outputs, [], 0)
        

        #----------------------------------------------RECEIVING SEGMENTS----------------------------------------------------------
        if len(readable)!=0:
            ackSegment, addr = dataSock.recvfrom(9)
            ackSegSeqNum = int(ackSegment[3:])
            #print(ackSegSeqNum) #DEBUG

            #--------congestion Protocols for received packets---------
            fast_rtx(ackSegSeqNum,nbdup) #FAST RTX
           
            #----------------------------------------------------------
            
           
            #-------tcp base protocol--------------
            if ackSegSeqNum == len(segments)-1: #si l'ackitement reçu est l'avant dernier numéro de seq : On arrête d'envoyer
                envoieFin = True
                #print("ACK RECEIVED: Last Segment was acked : %s, file transission completed" % ackSegSeqNum)
            
            elif ackSegSeqNum >= send_base:
                send_base = ackSegSeqNum + 1
                #print("ACK RECEIVED: received ack:%s | send_base:%s" % (ackSegment[3:],send_base))
                #print("---------------"+str(send_base)+"---------------"+str(nextseqnum)) #DEBUG
                
                #Timeout Stuff:
                SampleRTT = time.perf_counter() - RTT_timeTAB[ackSegSeqNum-1]
                #SampleRTT = time.perf_counter() - RTT_time
                timeout_estimation(SampleRTT)

                #Congestion Control Protocols:
                #vegas(SampleRTT)
                slow_start_and_congestion_avoidance()

            #-----------------------------------------------------------------------------    
        #-------------------------------------------------------------------------------------------------------------------------
                
        




        #------------------------------------SENDING SEGMENTS---------------------------------------------------------------
        if len(writable)!=0:            
            if envoieFin : #si tout les segments ont été reçu
                message = b"FIN"
                #for i in range(10000):
                dataSock.sendto(message, addr )
                dataToSend = False
                print("SEGMENT SENT: FIN sent")

            elif nextseqnum == len(segments) + 1: #si tou les segments ont été envoyés
                pass

            elif nextseqnum < send_base + min(N,cwnd):  #si le prochain segment à envoyer est inférieur à la taille de fenêtre + premier seq de in flight seg : on envoye
                segment = segments[nextseqnum-1]
                dataSock.sendto(segment, addr )
                RTT_timeTAB[nextseqnum-1] = time.perf_counter()
                inTime[nextseqnum-1] = time.perf_counter()
                nextseqnum = nextseqnum + 1
                #print("SEGMENT SENT: Nextseqnum:"+str(nextseqnum))
            
            else: #refuse data
                pass
        #------------------------------------------------------------------------------------------------------------------------
        
    






#----------------------------------------------------------------------------
#./serveurX-NomDuGroupe NuméroPort
#./clientX IPServeur NuméroPortServeur NomFichier
if __name__ == "__main__":


    #Get Port from user
    PUBLIC_UDP_PORT = inputPort()

    #Settings for the public socket
    #PUBLIC_UDP_IP = "192.168.122.1"
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    PUBLIC_UDP_IP = local_ip
    PRIVATE_PORT = PUBLIC_UDP_PORT + 1


    #Open socket and bind Socket
    try:
        publicSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        publicSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
        dataSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        three_way_handshake(publicSock, addr, PRIVATE_PORT)

        data, addr = dataSock.recvfrom(1024)
        file_name = data.decode().strip('\x00')
        print("File requested by client: ", str(file_name))

        print("framgenting file: ", file_name)
        segments = segment_file(file_name)

        print("sending file to client")
        GBN(segments, dataSock, addr)

        dataSock.close()
        publicSock.close()
       

