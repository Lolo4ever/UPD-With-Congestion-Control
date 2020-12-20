import socket
import time
import select
import sys
import threading

#PARAMETERS
chunk_size = 1494 #Client1 : 1494 sinon pas bon
N = 50 # window of size N --> given by client's rcvw size --> amout of in flight packets allowed
A = 0.125 #Typical value --> α = 0.125
B = 0.25 #typically, β = 0.25

#Debug : mumtithread!!


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


#---------------------------------------------------------------------------
#Send Each segment and wait for ack or send it again
def send_segments_stop_go(segments,dataSock, addr ):
    
    timeout_time = 1

    # Send all segments to client
    for segment in segments:

        WaitingAck = True
        while WaitingAck :

            # Sockets from which we expect to read, timeout in seconds
            timeout_in_seconds = timeout_time
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
#Timeout handler : when timer expires, retransmit all unacked packets and restart timer
class segment_timer(object):

    def __init__(self, interval, segments, dataSock, addr):
        self._interval = interval
        self.segments = segments
        self.dataSock = dataSock
        self.addr = addr
        self.t = threading.Timer(self._interval, self.callback)

    def start(self, send_base, nextseqnum):
        self.t.cancel()
        self.t = threading.Timer(self._interval, self.callback, [send_base, nextseqnum])
        self.t.start()

    def cancel(self):
        self.t.cancel()

    def callback(self, send_base, nextseqnum):
        self.start(send_base, nextseqnum)
        for i in range(send_base,nextseqnum):
            segment = self.segments[i-1]
            self.dataSock.sendto(segment, self.addr )
            print("segment sended after timeout"+str(i))




    






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
    #RTT_time = [int for i in range(len(segments))]
    RTT_time = 0
    inTime = time.perf_counter()
    SampleRTT = 0
    EstimatedRTT = 0
    DevRTT = 0
    timeout_time = 10

    #to stop sending once we are done
    dataToSend = True
    envoieFin = False

    #Congestion variables
    sstresh = 1000
    acks = []
    cwnd = 1000 #Slow start : start with cwnd = 1
    #-----------------------------------------------------------------------------------------------------------





    #-------------------------------------CONGESTION PROTOCOLS--------------------------------------------------
    def fast_rtx(ackSegSeqNum):
        """
        • Retransmit lost packet
        • Calculate FlightSize= min(rwnd,cwnd)
        • ssthresh = FlightSize/2
        • Enter Slow Start: cwnd = 1
        """
        if ackSegSeqNum == send_base-1:
            acks.append(ackSegSeqNum)
        elif ackSegSeqNum >= send_base :
            acks.clear()
        if acks.count(ackSegSeqNum) == 3: #==
            segment = segments[send_base-1]#send_base-1
            dataSock.sendto(segment, addr )
            print("PACKET LOST DETECTION : FAST RETRANSMIT | Segment Received:"+str(ackSegSeqNum)+" | Segment To reSend:"+str(segment[0:6]) )
            lost_packet_handler()
            #reset time_out timer???????
            #reset timer

    
    def timeout_estimation():
        nonlocal EstimatedRTT
        nonlocal SampleRTT
        nonlocal DevRTT
        nonlocal timeout_time

        #RTT estimation : SampleRTT: measured time from segment transmission until ACK receipt, ignore retransmissions
        EstimatedRTT = (1 - A)*EstimatedRTT + A*SampleRTT
        #safety margin : estimate SampleRTT deviation from EstimatedRTT
        DevRTT = (1-B)*DevRTT +B*abs(SampleRTT-EstimatedRTT)
        #timeout to use is the sum of both : 
        timeout_time = EstimatedRTT + 4*DevRTT



    def lost_packet_handler():
        """
        If a packet is considered lost(options):
            1) enter slow start
        """
        GBN.sstresh = int((nextseqnum-send_base)/2)
        #GBN.cwnd = 1


    
    def slow_start(ackSegSeqNum):
        """
        • Start with cwnd= 1
        • For every received ACK: cwnd= cwnd+ 1
        ssthresh : Decides the moment when the host goes from Slow Start to Congestion Avoidance
            Arbitrary initial value (usually very high)
            • After a lost segment (detected through a timeout or
            duplicate ACK): ssthresh= FlightSize/2
            • After the retransmission: cwnd = 1
        """
        if (cwnd <= sstresh) & (ackSegSeqNum >= send_base):
            GBN.cwnd = cwnd + 1
            print("DEBUG : SLOW START | cwnd:"+str(cwnd)+" | sstrsh:"+str(sstresh))



        
    def congestion_avoidance(ackSegSeqNum):
        """
        • Once a congestion has been detected, the transmitter
        tries to avoid reaching the congested state once again
        • The slow cwnd increase can delay the next
        congestion, while still testing for transmission
        opportunities
        • The TCP host enters in this mode when cwnd > ssthresh
        • cwnd = cwnd + 1/cwnd
        """
        if (cwnd > sstresh) & (ackSegSeqNum >= send_base):
            GBN.cwnd = cwnd + 1/cwnd
            print("DEBUG : CONGESTION AVOIDANCE | cwnd:"+str(cwnd)+" | sstrsh:"+str(sstresh))
        
    
    def fast_recovery():
        pass
        """
        • Entering Slow Start is not optimal in reception of duplicate ACKs
        • The mechanism allows for higher throughput in case of moderate congestion
        • Complement of Fast Retransmit
        • Mode entered after 3 duplicate ACKs
        • As usual, set ssthresh= FlightSize/2
        • Retransmit lost packet
        • Window inflation: cwnd= ssthresh + ndup (number of
        duplicate ACKs received)
        • This allows the transmission of new segments
        • Window deflation: after the reception of the missing
        ACK (one RTT later) ??????
        • Skip Slow Start, enter Congestion Avoidance
        """
    #------------------------------------------------------------------------------------------------------------------



    
    while dataToSend:

        #--------------------------------------------------TIMEOUT HANDLER--------------------------------------------------------
        offTime = time.perf_counter()
        if offTime - inTime > timeout_time : #Lost packets detected : 
            print("PACKET LOST DETECTION : TIMEOUT | TimeLimit:"+str(timeout_time)+" | reSend Segment:"+str(send_base)+" to "+str(nextseqnum-1))
            lost_packet_handler()
            inTime = time.perf_counter()
            for i in range(send_base,nextseqnum): #all in flight packets
                segment = segments[i-1]
                dataSock.sendto(segment, addr )
        #---------------------------------------------------------------------------------------------------------------------------


        #reset list of file descriptors
        inputs = [ dataSock ]
        outputs = [ dataSock ]

        #unblocking poll of sockets
        readable, writable, _ = select.select(inputs, outputs, [], 0)
        

        #----------------------------------------------RECEIVING SEGMENTS----------------------------------------------------------
        if len(readable)!=0:
            ackSegment, addr = dataSock.recvfrom(9)
            ackSegSeqNum = int(ackSegment[3:])
            print(ackSegSeqNum) #DEBUG

            #--------congestion Protocols for received packets---------
            #fast_rtx(ackSegSeqNum) #FAST RTX
            #slow_start(ackSegSeqNum)
            #congestion_avoidance(ackSegSeqNum)
            #----------------------------------------------------------
            
           
            #-------tcp base protocol--------------
            if ackSegSeqNum == len(segments)-1: #si l'ackitement reçu est l'avant dernier numéro de seq : On arrête d'envoyer
                envoieFin = True
                print("ACK RECEIVED: Last Segment was acked : %s, file transission completed" % ackSegSeqNum)
            
            elif ackSegSeqNum >= send_base:
                send_base = ackSegSeqNum + 1
                print("ACK RECEIVED: received ack:%s | send_base:%s" % (ackSegment[3:],send_base))
                print("---------------"+str(send_base)+"---------------"+str(nextseqnum)) #DEBUG
                
                #SampleRTT = time.perf_counter() - RTT_time[ackSegSeqNum-1]
                SampleRTT = time.perf_counter() - RTT_time
                timeout_estimation()

                if send_base == nextseqnum : #si on a tout reçu
                    inTime = 0

                else: #si il y a toujours des packet in flight : restart clock
                    inTime = time.perf_counter()
                    # PB : SAMPLE RTT FOR SPECIFIC SEQ NUM, NOT INTO ACCOUNT TIMEOUTE(?)
                    #two strategies : packet by packet --> if random packet droped by , singular packet pb
                    #                   N --> if the globality of packet is shit
            #-----------------------------------------------------------------------------    
        #-------------------------------------------------------------------------------------------------------------------------
                
        




        #------------------------------------SENDING SEGMENTS---------------------------------------------------------------
        if len(writable)!=0:
            if envoieFin : #si tout les segments ont été reçu
                message = b"FIN"
                dataSock.sendto(message, addr )
                dataToSend = False
                print("SEGMENT SENT: FIN sent")

            elif nextseqnum == len(segments) + 1: #si tou les segments ont été envoyés
                pass

            elif nextseqnum < send_base + min(N,cwnd):  #si le prochain segment à envoyer est inférieur à la taille de fenêtre + premier seq de in flight seg : on envoye
                segment = segments[nextseqnum-1]
                dataSock.sendto(segment, addr )
                #RTT_time[nextseqnum-1] = time.perf_counter()
                RTT_time = time.perf_counter()
                if(send_base == nextseqnum): #si le sgment avant de celui qu'on va envoyer a été ecquité (aucun in flight segment) : restart clock
                    inTime = time.perf_counter()
                nextseqnum = nextseqnum + 1
                print("SEGMENT SENT: Nextseqnum:"+str(nextseqnum))
            
            else: #refuse data
                pass
        #------------------------------------------------------------------------------------------------------------------------
        
        



    """
    #OPTION 1
    #send everything in the tx window in a first time, activate timeout in the last seq
    for i,segment in enumerate(transmission_window):
        seqNumber = segment.header()
        dataSock.sendto(segment, addr )
        if i == (len(transmission_window)-1) :
            segment_timeout.start()
        expectedseqnum = seqNumber
    
    while True:
        readable = select(input, 0) #non blockant, polling
            if readable[0] is dataSock :
                ackedSeq = recvfrom()
                ackedSeqNum = ackedSeq.header()
                if ackedSeqNum == expectedseqnum :
                    segment_timeout.cancel()
                    dataSock.sendto(segments[ackedSeqNum], addr )
                    segment_timeout.start()
                    expectedseqnum = ackedSeqNum + 1
                    send_base = ackedSeqNum
    """
        
        
     

    






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

        data, addr = dataSock.recvfrom(1024)
        file_name = data.decode().strip('\x00')
        print("File requested by client: ", str(file_name))

        print("framgenting file: ", file_name)
        segments = segment_file(file_name)

        print("sending file to client")
        GBN(segments, dataSock, addr)
       

        """
        #test timer
        segment_timeout = segment_timer(3, segments, dataSock, addr )
        segment_timeout.start(1,8)
        time.sleep(7)
        segment_timeout.start(3,10)
        
       
        #test client
        dataSock.sendto(segments[0],addr)
        time.sleep(1)
        dataSock.sendto(segments[1],addr)
        time.sleep(1)
        dataSock.sendto(segments[2],addr)
        time.sleep(1)
        dataSock.sendto(segments[3],addr)
        time.sleep(1)
        dataSock.sendto(segments[4],addr)
        time.sleep(1)
        dataSock.sendto(segments[6],addr)
        time.sleep(1)
        dataSock.sendto(segments[7],addr)
        time.sleep(1)
        dataSock.sendto(segments[8],addr)
        time.sleep(1)
        dataSock.sendto(segments[5],addr)
        time.sleep(1)
        """

        
    
        
        








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