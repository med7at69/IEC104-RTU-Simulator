# ******************************************************
#  	         IEC 104 RTU simulator
#  	By M. Medhat - MJEC - 7 Feb 2020 - Ver 1.0
# ******************************************************
https://github.com/med7at69/IEC104-RTU-Simulator

This is an IEC 104 RTU simulator. It can simulate any number of RTUs or servers.
The project contains the following files:

iec104rs.py: The code in python language.
iec104rs.csv: ini file in comma separated values. Must be in the same folder of iec104rs.py
iodata.csv: IOA data files in comma separated values. Must be in "data" folder.

Command arguments:
# -h or --help					help message
# -i or --ini					init file
# -t or --ntp_update_every_sec			NTP update interval
# -s or --ntp_server				NTP server

When the iec104rs.py program starts it will:
1- Read the command arguments.
2- if ini file is not provided in command arguments then the default is iec104rs.csv
3- Read the ini file to get the NTP servers and RTUs as descriped below.
4- Eah RTU should have name, RTU number, port number to listen on and IOA data file (in "data" folder)

===========================================================================

ini file (iec104rs.csv) example with explanations

# ini file - iec104rs.csv,,,,,,,
# If first character of first column in any row is ! Then program will cancel the rest of the rows.,,,,,,,
#,,,,,,,
# starting by general settings in comma delimited format.,,,,,,,
# parameter of ntp_server could be repeated multiple times in separated lines for multiple servers.,,,,,,,
ntp_server,10.1.1.15,,,,,,
ntp_server,time.windows.com,,,,,,
ntp_server,pool.ntp.org,,,,,,
ntp_update_every_sec,900,,,,,,
#,,,,,,,
# then all RTUs settings in comma delimited format.,,,,,,,
# RTU number may be repeated for some RTUs.,,,,,,,
# port number should be unique for each RTU.,,,,,,,
# hosts: a list of hosts/net separated by ; which will only be accepted to connect to the specific RTU.,,,,,,,
# k: the IEC 104 k constant. Default is 12 packets.,,,,,,,
# idletime: time in seconds. If no data for idletime seconds the RTU connection will be disconnected.,,,,,,,
"# io data files (iodata.csv) should be in ""data"" folder in the same folder of the program iec104rs",,,,,,,
# id,sys name,rtu no,port no,hosts, k,idletime, iodata.csv
1,ABB,32,2404,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata1.csv
#,ABB,32,2405,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata1.csv
3,OSI,105,2406,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata2.csv
#,OSI,105,2407,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata2.csv
!5,Siemens,178,2408,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata1.csv
6,PSI,251,2409,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata1.csv
7,SELTA,324,2410,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata1.csv
8,Lucy,397,2411,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata1.csv
9,Schnieder,470,2412,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata1.csv
10,Multaqa,543,2413,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata1.csv
!11,Owinat,616,2414,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata1.csv
12,DAS,689,2415,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata1.csv
13,Shinas,762,2416,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata1.csv
14,Tareef,835,2417,192.168.1.16;127.0.0.0/24;10.1.1.0/24,12,60,iodata1.csv
15,ABB,908,2418,,12,60,iodata1.csv

===========================================================================

IOA data (iodata.csv) example with explanations

#" IOA data file in comma delimited format (.csv). Should be in folder ""data"" under main folder of the program iec104rs",,,,,,
# If first character of first column in any row is ! Then GI will cancel rest of the rows.,,,,,,,
# Supported types:,,,,,,
#,"SPI (1,30)",OFF = 0,ON = 1,,,
#,"DPI(3,31)",OFF = 01,ON = 02,XX = 00/11,,
#,"NVA(9,34)","Example, if you want to send 11Kv then value=(11000/max. value) = (11000/13200) = 0.83",,,,
#,"SVA(11,35)","Example, if you want to send 11Kv then value = 11",,,,
#,"FLT(13,36)","Example, if you want to send 11.23Kv then value = 11.23",,,,
#,"SCO(45,58) - value should equal the IOA of its status.",,,,,
#,"DCO(46,59) - value should equal the IOA of its status.",,,,,
#,"RCO(47,60) - value should equal the IOA of its status.",,,,,
#,,,,,,
#,GI,typeid,IOA,Value,Comment,
#,--,------,---,-----,-----,
#------------------------,,SCO command ------------------------------,,,,
#,,,,,,
#------------------------,,DCO command + status --------------------,,,,
100000,N,46,21001,301,dummy (DCO),dummy (DCO)
100001,N,31,301,1,dummy (dpi),dummy (dpi)
100002,N,46,21035,343,KLN01-Q0 (DCO),KLN01-Q0 (DCO)
100003,N,47,21007,15001,TX-(RCO),TX-(RCO)
100004,N,46,21039,355,KLN03-Q0 (DCO),KLN03-Q0 (DCO)
100005,N,46,21041,361,KLN05-Q0 (DCO),KLN05-Q0 (DCO)
100006,N,46,21043,367,KLN07-Q0 (DCO),KLN07-Q0 (DCO)
100007,N,46,21017,307,TH01-Q0 (DCO),TH01-Q0 (DCO)
100008,N,46,21045,377,TL01-Q1 (DCO),TL01-Q1 (DCO)
#------------------------,,SCO command with time tag --------------,,,,
#, , , , , , 
#------------------------,,DCO command with time tag ---------------,,,,
#, , , , , , 
#------------------------,,DPI ------------------------------,,,,
301,Y,31,301,1,DUMP,DUMP
301,Y,31,303,1,spare,spare
301,Y,31,305,1,H-TH01BAY CTRL,H-TH01BAY CTRL
301,Y,31,307,1,H-TH01Q0,H-TH01Q0
301,Y,31,309,1,H-TH01Q1,H-TH01Q1
301,Y,31,311,1,H-TH01Q4,H-TH01Q4
301,Y,31,313,1,H-LN01BAY CTRL,H-LN01BAY CTRL
#!Eng GI,N,31,,,,
301,Y,31,315,1,H-LN01Q0,H-LN01Q0
317,Y,31,317,2,H-LN01Q1,H-LN01Q1
319,Y,31,319,2,H-LN01Q3,H-LN01Q3

===========================================================================






