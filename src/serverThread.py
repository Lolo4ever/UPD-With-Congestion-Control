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






#--------------------------------------------------------------------------------------------
#                                   CONGESTION PROTOCOLS
#--------------------------------------------------------------------------------------------
#Client 1 : a lot of delay, timeout time plays important role! No slow start ontherwise always cwnd of 1 : we send fast but receive slowly


#Global Varialbes
sstresh = 1000
acks = []
cwnd = 1000 #Slow start : start with cwnd = 1

#--------------------------------------------------------------------------
#Fast retransmit : retransmit smallest seq num segment if 4 same acks received
#PAMAMETERS : 
#   Do we reset timeclock?
#   How many consecutive acks to ressend?
#   Do we ressend just once?
def fast_rtx(ackSegSeqNum,send_base,nextseqnum,dataSock,addr):
    """
    • Retransmit lost packet
    • Calculate FlightSize= min(rwnd,cwnd)
    • ssthresh = FlightSize/2
    • Enter Slow Start: cwnd = 1
    """
    global acks
    if ackSegSeqNum == send_base-1:
        acks.append(ackSegSeqNum)
    elif ackSegSeqNum >= send_base :
        acks.clear()
    if acks.count(ackSegSeqNum) == 2: #==
        segment = segments[send_base-1]#send_base-1
        dataSock.sendto(segment, addr )
        print("PACKET LOST DETECTION : FAST RETRANSMIT | Segment Received:"+str(ackSegSeqNum)+" | Segment To reSend:"+str(segment[0:6]) )
        lost_packet_handler(nextseqnum,send_base)
        #reset time_out timer???????
    
    


def lost_packet_handler(nextseqnum,send_base):
    """
    If a packet is considered lost(options):
        1) enter slow start
    """
    global sstresh
    global cwnd
    sstresh = int((nextseqnum-send_base)/2)
    cwnd = 1



def slow_start(send_base,nextseqnum, ackSegSeqNum):
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
    global sstresh
    if (cwnd <= sstresh) & (ackSegSeqNum >= send_base):
        cwnd = cwnd + 1
        print("DEBUG : SLOW START | cwnd:"+str(cwnd)+" | sstrsh:"+str(sstresh))


    

def congestion_avoidance(send_base,nextseqnum, ackSegSeqNum):
    """
    • Once a congestion has been detected, the transmitter
    tries to avoid reaching the congested state once again
    • The slow cwnd increase can delay the next
    congestion, while still testing for transmission
    opportunities
    • The TCP host enters in this mode when cwnd > ssthresh
    • cwnd = cwnd + 1/cwnd
    """
    global cwnd
    global sstresh
    if (cwnd > sstresh) & (ackSegSeqNum >= send_base):
        cwnd = cwnd + 1/cwnd
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


#----------------------------------------------------------------------------------------
#                           TCP PROTOCOLS
#----------------------------------------------------------------------------------------


#------------------------------SHARED MEMORY --------------------------------------------
data_lock = threading.Lock()

#to know if there is still data to send
envoieFin = False
dataToSend = True

#pointers to seq number
send_base = 1 # first segment that is in flight
nextseqnum = 1 # first usable segment not yet sent

#timer stuff
#RTT_time = [int for i in range(len(segments))]
RTT_time = 0
inTime = time.perf_counter() #PB
timeout_time = 10
#-----------------------------------------------------------------------------------------

#SENDING SEGMENTS THREAD
class sendSegments(threading.Thread):
    def __init__(self, addr, segments, dataSock):
        threading.Thread.__init__(self)
        self.addr = addr
        self.segments = segments
        self.dataSock = dataSock
        
    def run(self):
        global nextseqnum
        global dataToSend
        global RTT_time
        global inTime#PB
        
        #while dataToSend:
        if envoieFin : #si tout les segments ont été reçu ---> on envoye "FIN"
            message = b"FIN"
            self.dataSock.sendto(message, self.addr )
            dataToSend = False
            print("SEGMENT SENT: FIN sent")

        elif nextseqnum == len(self.segments) + 1: #si tou les segments ont été envoyés
            pass

        elif nextseqnum < send_base + min(N,cwnd): #si le prochain segment à envoyer est inférieur à la taille de fenêtre + premier seq de in flight seg : on envoye
            segment = self.segments[nextseqnum-1]
            self.dataSock.sendto(segment, addr )
            #RTT_time[nextseqnum-1] = time.perf_counter()
            RTT_time = time.perf_counter()
            if(send_base == nextseqnum): #si le sgment avant de celui qu'on va envoyer a été ecquité (aucun in flight segment) : restart clock
                with data_lock:
                    inTime = time.perf_counter()
            nextseqnum = nextseqnum + 1
            print("SEGMENT SENT: Nextseqnum:"+str(nextseqnum))

        else:
            pass#refuse data



#RECEIVEING SEGMENTS THREAD
class receiveSegments(threading.Thread):
    def __init__(self, segments, dataSock):
        threading.Thread.__init__(self)
        self.segments = segments
        self.dataSock = dataSock
        
    def run(self):
        global send_base
        global envoieFin
        global timeout_time
        global inTime#PB
        SampleRTT = 0
        EstimatedRTT = 0
        DevRTT = 0

        #while dataToSend:
        ackSegment, addr = self.dataSock.recvfrom(9)
        ackSegSeqNum = int(ackSegment[3:])

        #--------------------Additional Protocols for received packets----------------------
        fast_rtx(ackSegSeqNum,send_base,nextseqnum,self.dataSock,addr) #FAST RTX
        #slow_start(send_base,nextseqnum,ackSegSeqNum)
        #congestion_avoidance(send_base,nextseqnum,ackSegSeqNum)
        #-----------------------------------------------------------------------------------

        print(ackSegSeqNum)

        #----------------------------------Normal TCP Protocol------------------------------
        if ackSegSeqNum == len(self.segments)-1: #si l'ackitement reçu est l'avant dernier numéro de seq : On arrête d'envoyer
            envoieFin = True
            print("ACK RECEIVED: Last Segment was acked : %s, file transission completed" % ackSegSeqNum)
        
        elif ackSegSeqNum >= send_base: #Si on reçoit ack avec num seq supérieur ou égal à celui qu'on attend
            send_base = ackSegSeqNum + 1
            print("ACK RECEIVED: received ack:%s | send_base:%s" % (ackSegment[3:],send_base))
            
            #SampleRTT = time.perf_counter() - RTT_time[ackSegSeqNum-1]
            SampleRTT = time.perf_counter() - RTT_time
            
            #-----------------------------TIMEOUT CHANGEMENT----------------------------------------
            #RTT estimation : SampleRTT: measured time from segment transmission until ACK receipt, ignore retransmissions
            EstimatedRTT = (1 - A)*EstimatedRTT + A*SampleRTT
            #safety margin : estimate SampleRTT deviation from EstimatedRTT
            DevRTT = (1-B)*DevRTT +B*abs(SampleRTT-EstimatedRTT)
            #timeout to use is the sum of both : 
            timeout_time = EstimatedRTT + 4*DevRTT
            #---------------------------------------------------------------------------------------

            if send_base == nextseqnum : #si on a tout reçu
                with data_lock:
                    inTime = 0

            else: #si il y a toujours des packet in flight : restart clock
                # PB : SAMPLE RTT FOR SPECIFIC SEQ NUM, NOT INTO ACCOUNT TIMEOUTE(?)
                #two strategies : packet by packet --> if random packet droped by , singular packet pb
                #                   N --> if the globality of packet is shit
                with data_lock:
                    inTime = time.perf_counter()




#TIMEOUT THREAD
class timeoutHandler(threading.Thread):
    def __init__(self, segments, dataSock):
        threading.Thread.__init__(self)
        self.segments = segments
        self.dataSock = dataSock
        
    def run(self):
        global inTime
        global timeout_time

        while dataToSend:
            with data_lock:
                inTime_local = inTime
            offTime = time.perf_counter()
            if offTime - inTime_local > timeout_time :  #Lost packets detected
                print("PACKET LOST DETECTION : TIMEOUT | TimeLimit:"+str(timeout_time)+" | reSend Segment:"+str(send_base)+" to "+str(nextseqnum-1))
                with data_lock:
                    inTime = time.perf_counter()
                for i in range(send_base,nextseqnum): #all in flight packets
                    segment = self.segments[i-1]
                    self.dataSock.sendto(segment, addr )



#---------------------------------------------------------------------------
#Send Each segment and wait for ack or send it again, with TX window (cumulative ack: CBN)
def send_segments_GBN(segments,dataSock, addr ):
    global dataToSend
    
    
    timer = timeoutHandler(segments,dataSock)
    timer.start()


    while dataToSend:
        #print("next to send "+str(nextseqnum))
        #print("receive next "+str(send_base))

        #reset list of file descriptors
        inputs = [ dataSock ]
        outputs = [ dataSock ]

        #unblocking poll of sockets
        readable, writable, _ = select.select(inputs, outputs, [], 0)
        
        #RECEIVING SEGMENTS
        if len(readable)!=0:
            receiver = receiveSegments(segments,dataSock)
            receiver.start()


        #SENDING SEGMENTS
        if len(writable)!=0 & (nextseqnum < send_base + min(N,cwnd)):
            sender = sendSegments(addr,segments,dataSock)
            sender.start()

        #TIMEOUT EVENT
        
        #start timeout thread
        



     

    






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
        #send_segments_stop_go(segments,dataSock,addr)
        send_segments_GBN(segments, dataSock, addr)
        #t1 = sendSegments(addr,segments,dataSock)
        #t2 = receiveSegments(segments,dataSock)
        #t3 = timeoutHandler(segments,dataSock)
        #t2.start()
        #t1.start()
        
        #t3.start()
        # pb : he finishes before receiving the last ack
       

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