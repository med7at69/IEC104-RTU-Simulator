# ******************************************************
#  	         IEC 104 RTU simulator
#  	By M. Medhat - 7 Feb 2020 - Ver 1.0
# ******************************************************

IEC 104 RTU simulator is a program to simulate the operation of RTU (remote terminal unit) or server as defined by protocol IEC 60870-5-104. It can simulate any number of RTUs or servers. Simulated RTUs could be connected to different or same SCADA master station. IO signals are indexed and grouped by using index numbers. You can send IO signals from all RTUs to the connected SCADA master stations at once by using index number.
I wrote this program when at my company we replaced our legacy ABB SCADA system with new OSI SCADA system, so we wanted to test the new system in comparison with the old legacy system without taking shutdown on the power stations.
So, by indexing the IO signals in the IOA database files we succeeded to send same IO signals to both of the SCADA systems (old and new) in the same time and compare between them:
-	IOA address of the signals.
-	Signals’ values for SPI, DPI, AMI.
-	Testing commands and send back the status to both systems.
-	Compare time tags and time synchronization between the two systems.
-	Test IEC 104 protocol on the new system such as startdt, stopdt, GI, time tags, etc.
-	Measure test frame period. For that reason, the simulator will not send “Testfr act” but it will wait until receiving “testfr act” from the connected SCADA system and will reply by “testfr con” and log the test frame period in the RTU log file.

Program is distributed under GPL license and could be found on GitHub:
https://github.com/med7at69/IEC104-RTU-Simulator
It is written in python3 language and code is supporting both Windows and Linux OS.

Package contains the following files:
iec104rs.py: The code in python 3 language.
iec104rs.csv: ini file in comma separated values. Must be in the same folder where program starts in.
“data” folder with samples “iodata.csv” files which are IOA data files in comma separated values. Must be kept in "data" folder. “data” folder must be in the same folder where program starts in.
Iec104rs.pdf: Help file in pdf format.
Readme.txt
LICENSE file.

Program arguments:
 -h or --help				display help message.
 -i or --ini				specify init file name.
 -t or --ntp_update_every_sec		NTP update interval (seconds).
 -s or --ntp_server			NTP server (may repeated for multiple servers).

Program operation

Program operation depends on providing huge data either for RTUs that the program to simulate or for the IOA signals provided for each RTU. To make the program operation as simple as possible I tried to use the comma separated values file (csv) format to provide the data to the program for the following reasons:
1-	“csv” format is simple and well known since long time.
2-	Besides supported by Microsoft Excel, there are many freeware programs supporting editing “csv” files.
3-	It is easy to add, delete, copy and paste large number of data entries to the “csv” files without complications.

Program operation is based on the following files:
1-	Initial file (default name is iec104rs.csv): It is a comma separated values file format or “.csv” which should be available in the same folder where program starts in. In the file you can define the following:
	a. NTP servers to update local time of the PC (requires admin/root privilege).
	b. Number of seconds to periodically update local time from NTP servers.
	c. Any number of RTUs or systems to be simulated by the program.
2-	IOA database file (for example iodata.csv): It is a comma separated values file format or “.csv” which should be in folder “data”. Folder “Data” should be in the same folder where the program starts in. In the file you can define the IOA signals such that SPI, DPI, NVA, SVA, FLT, SCO, DCO, RCO. Each RTU may have separated IOA data file or multiple RTUs can share the same IOA signals data file. In the IOA database file, IO signals are indexed and grouped by index numbers. You can send IO signals from all RTUs to the connected SCADA master stations at once by using index numbers.
3-	Log files for all RTUs are saved in folder “log”. Folder “log” will be created in the same folder where the program starts in.

When the program starts it will:
1-	Read the program arguments if provided by user.
2-	If initial file is not provided in program arguments, then the program will use the default iec104rs.csv
3-	Read the initial file to get the NTP servers and RTUs as described later.
4-	Each RTU should have name, RTU number, port number to listen on and IOA data file (in "data" folder).
5-	To speed up the loading of RTUs, program will not start any RTU connection until load all RTUs in memory.
6-	If user type index number and press “send” button, then the program will send all IO signals grouped by this index number in all IOA database files of different RTUs to the connected master stations. This function is helpful specially when you want to compare between two SCADA master stations, for example one new and the other is the legacy working system.
7-	The simulator will not send “Testfr act” but it will wait until receiving “testfr act” from the connected SCADA system and will reply by “testfr con” and log the test frame period in the RTU log file.
8-	If idle time (configured in the initial file for each RTU in seconds) passed without send/receive data then the program simulator will disconnect the connection to restart working connection again.

===========================================================================

Initial file format

General notes:
-	Initial file format is comma separated values format (csv).
-	Initial file default name is iec104rs.csv
-	You can provide another name as program argument with “-i” or “--ini”
-	Initial file should be in the same folder where the program starts in.
-	If first character of first column in any row is “!” Then program will stop reading the initial file and cancel the rest of the rows.
-	Initial file will start by defining the following parameters:
	o “ntp_server”: it could be repeated in multiple rows for multiple NTP servers. If program has admin/root privilege then it will try all the servers one by one to synchronize the local time.
	o “ntp_update_every_sec”: seconds to periodically update local time. If not provided, then the default is 900 seconds.
-	Then initial file should contain all RTUs information one by one (each row contains one complete RTU information) such that each RTU is define the following parameters in separated rows:
	o ID:
		 Better to be a unique sequential number for each RTU.
		 If “id” field is not number, then it will be considered as comment and will be neglected by the program.
		 If first character of “id” column in any row is “!” Then program will stop reading the rest of the initial file and will cancel the rest of the rows.
	o System/RTU name: Name with maximum of 16 characters length.
	o RTU number: RTU number (1-65535). RTU number is not unique and multiple RTUs can have the same RTU number. If multiple RTUs have the same RTU number, then it is supposed to be connected to different SCADA systems or IEC 104 clients.
	o Port number: Unique port number (1-65535). Program will listen to this port to accept connection for the specified RTU.
	o Accept hosts/network list: Accepted hosts or networks filters separated by “;”. example: 192.168.1.0/24;10.10.1.2".
	o IEC 104 “k”: IEC 104 “k” constant which represent maximum number of packets could be transmitted without receiving acknowledge from the receiver. If not provided, then default value is “12” packets.
	o Idle time: Idle time in seconds before disconnecting RTU connection. Default is “60” seconds.
	o IOA signal database file: File contains the IOA signals for the specified RTU in comma separated values format (csv). Multiple RTU can share same IOA data file.

===========================================================================

IOA signal database file format

General notes:
-	IOA signal database file format is comma separated values format (csv).
-	For each RTU, an existing file should be provided.
-	Multiple RTUs can share the same IOA signal database file.
-	All IOA database files should be in folder “data”. Folder “data” should be in the same folder where the program starts in.
-	If first character of first column in any row is “!” Then program will stop sending general interrogation “GI” signals and cancel the rest of the rows.
-	IOA signal database file should define the following parameters for each signal row:
	o Index number:
		 This index will be used to submit the signals from the file to the SCADA connected system.
		 Multiple signals could be grouped by same “index” number to submitted together when the specified index number given to the iec104rs program.
		 If first character of this column in any row is “!” Then program will stop sending general interrogation “GI” signals and cancel the rest of the rows.
	o GI: If this field contains “Y” then the specified signal will be submitted during general interrogation to the connected SCADA system.
	o Type ID: IEC 104 type ID of the signal in numeric value. All supported values are mentioned in the provided sample IOA database files:
		 SPI (single point indication) without time tag: 1
		 SPI (single point indication) with time tag: 30
		 DPI (double point indication) without time tag: 3
		 DPI (double point indication) with time tag: 31
		 NVA (normalized meas.) without time tag: 9
		 NVA (normalized meas.) with time tag: 34
		 SVA (Scaled meas.) without time tag: 11
		 SVA (Scaled meas.) with time tag: 35
		 FLT (Float meas.) without time tag: 13
		 FLT (Float meas.) with time tag: 36
		 SCO (single command) without time tag: 45
		 SCO (single command) without time tag: 45
		 SCO (single command) with time tag: 58
		 DCO (double command) without time tag: 46
		 DCO (double command) with time tag: 59
		 RCO (regulation command) without time tag: 47
		 DCO (regulation command) with time tag: 60
		 Only “CP56Time2a “ time tag is used.
	o IOA address: Signal object address.
	o Signal value: For command, the value should contain the status (SPI, DPI, or AMI) IOA address to be submitted as a response to the connected SCADA system when receiving the command. This way, full command simulation could be achieved.
	o Comment: Sequential columns (maximum 53 characters) could be used to represent signal and feeder names or any other comments to be written in the RTU log file.

===========================================================================

Troubleshooting

Program did not load one or more configured RTU(s) in the initial file:
-	If first character of “ID” field equal “!” then current row and all subsequent rows (RTUs) will not be loaded.
-	If the “ID” field is not number, then RTU will not be loaded.
-	If RTU has no name, then RTU will not be loaded. Program will read the first 16 characters of the name field.
-	RTU number field should be in range 1 to 65535.
-	Port number field should be unique (not used for any already loaded RTU) and in range 1 to 65535.
-	IOA database file (example: iodata.csv) should be in folder “data” in the folder where the program starts in.

Some IO signals not submitted during general interrogation or during index sending process although the signal is configured in the IOA database file of the specific RTU.
-	During general interrogation, if first character of “index” field equal “!” then current row and all subsequent rows (signals) will not be submitted, and general interrogation will stop.
-	If “index” of the signal is not digits (numbers) then it will be considered as a comment and will not be submitted.
-	If the “GI” field is not equal “Y” then the signal will not be submitted during GI.
-	If signal “type ID” field is not in the supported type IDs then it will not be submitted.
-	If signal value is not valid then it will not be submitted.

Local time not updated although NTP servers configured, and it is tested normally.
-	Updating local time required admin/root privilege under both Windows and Linux so please be sure to start the application with admin/root privilege so it can update the local time normally.
-	Program will try the NTP servers one by one then will sleep for the specified period (ntp_update_every_sec = 900 seconds by default) before trying again. So, maybe software couldn’t reach to the servers at the first try so please wait until the software try next time.
-	Please notice the local time update status.

===========================================================================

Windows binary files

Windows binary file is generated by nuitka Python compiler:
https://nuitka.net/
By using the following command:
python -m nuitka --windows-file-description="IEC104 RTU Simulator" --windows-file-version="1.0" --windows-product-version="1.0" --windows-company-name="M.M" --onefile --plugin-enable=tk-inter --standalone --mingw64 iec104rs.py

===========================================================================

ini file (iec104rs.csv) example with explanations

# ini file - iec104rs.csv,,,,,,,
# If first character of first column in any row is ! Then program will cancel the rest of the rows.,,,,,,,
#,,,,,,,
# starting by general settings in comma separated values.,,,,,,,
# parameter of ntp_server could be repeated multiple times in separated lines for multiple servers.,,,,,,,
ntp_server,10.1.1.15,,,,,,
ntp_server,time.windows.com,,,,,,
ntp_server,pool.ntp.org,,,,,,
ntp_update_every_sec,900,,,,,,
#,,,,,,,
# then all RTUs settings in comma separated values.,,,,,,,
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

#" IOA data file in comma separated values (.csv). Should be in folder ""data"" under main folder of the program iec104rs",,,,,,
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






