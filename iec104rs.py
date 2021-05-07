#!/usr/bin/env python3
#
# ******************************************************
#  	         IEC 104 RTU simulator
#  	By M. Medhat - MJEC - 7 Feb 2020 - Ver 1.0
# ******************************************************
# Revision history:
#  Ver 0.0 - Tested startdt, GI and dummy dpi.
#  Ver 0.1 - spi, dpi, NVA meas., SVA meas., time tag.
#  Ver 0.2 - FLT meas., sco and dco simulation,
#	     millisec to time stamp, time sync.
#  Ver 0.3 - Performance enhancements.
#  Ver 0.4 - rco simulation.
#	     Logging for all signals.
#            Signals attributes such as:
#		Command select/execute.
#		Command pulse information.
#		Time saving.
#	    Fixing bugs related to:
#			- Commands.
#			- Time sync.
#  Ver 0.5 - re-write socket, ieee754, microseconds
#	     in python
#  Ver 0.6 - Parallel operation, now can send GI, DPI,
#			 SPI, AMI, receive commands, time sync,
#			 etc. simultaneously.
#		   - Fixing some bugs related to network socket.
#  Ver 1.0 - Windows GUI, myltithreading operation.
#			 local clock time update via NTP server(s).
#			 RTU can have unique accepted net/hosts.
#			 Support for unlimited number of RTUs.
#			 RTUs may have same RTU no. but unique port.
#			 RTUs can share same iodata.csv file or have
#			 separated file for each RTU.
#
# python:
#	iec104rs.py - socket, ieee754, microseconds
#
# File: iodata.csv
#     IO database as comma separated values (csv).
#	  all RTUs can share same iodata.csv file or have
#	  separated file for each RTU.
#
# This file: Read and write packets.
#			 Handle network sockets.
#			 Calculate Ieee 754 float points.
#			 Add microseconds to timetag.
#			 Windows GUI
# *****************************************************
#                       Imports
# ------------------------------------------------------
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font
from tkinter import messagebox
import ctypes
from getopt import getopt
from ipaddress import ip_address,ip_network
import threading
from os import remove,stat,mkdir,system
from datetime import datetime
from socket import socket,AF_INET,SOCK_STREAM,SOL_SOCKET,SO_REUSEADDR,SHUT_RDWR,error,timeout,SOCK_DGRAM
from binascii import hexlify
from signal import signal,SIGTERM
from struct import unpack,pack
from select import select
from sys import argv,byteorder,exit
from time import time,sleep
from os.path import isfile,getsize
from csv import reader
from win32api import SetSystemTime
from atexit import register

# ******************************************************
#                       Variables
# ------------------------------------------------------
PYTHONUNBUFFERED='disable python buffer'
# program argument - see below
# define help message
help1="usage iec104rs [[-h][--help]] [[-i][--ini] init-file] [[-t][--ntp_update_every_sec seconds] sec] [[-s][--ntp_server ntpserver] server]\n"
help2="example1: iec104rs -i iec104rs1.csv\n"
help3="example2: iec104rs --ntp_server pool.ntp.org --ntp_server time.windows.com\n"
help4="-s or --ntp_server could be included multiple times for multiple servers.\n"
help5="\t -h or --help\t\t\t\thelp message.\n"
help6="\t -i or --ini\t\t\t\tinit file (comma separated values), default iec104rs.csv.\n"
help7="\t -t or --ntp_update_every_sec\t\tNTP update interval, default=900 seconds (requires admin privilege).\n"
help8="\t -s or --ntp_server\t\t\tNTP server, could be included multiple times (requires admin privilege).\n"
helpmess=help1+help2+help3+help4+help5+help6+help7+help8
dir='log\\'
datadir='data\\'
initfile='iec104rs.csv'
ntpserver=[]
timeupdated=''
updatetimegui=0
timeupdateevery=900		# in seconds

exitprogram=0
pulsemess='No pulseShort   Long    Persist '
valuemess='OFFON '
regmess='DECREMENTINCREMENT'

is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

# cmd program files
cmdtime=0
cmdvalue=0
cmdtype=0
ioacmdv=0

# index program files
indextime=0
indexvalue=0
# iec 104 supported types for index send
types = [1,3,9,11,13,30,31,34,35,36]

bufsize=100
mainth=[]
th=[]
portnolist=[]
window=0
txtbx1thid=0
txtbx2thid=1
updatetoframe1=0
updatetoframe2=0
noofrtu=0
programstarted=0

# *****************************************************
#                       Functions
# -----------------------------------------------------
def signal_term_handler(signal, frame):
	exit()

def cleanup():
	global exitprogram,mainth,th,window
	exitprogram=1
	fh=[]
	for a in mainth:
		if a:
			a.dataactive=0
			fh.append(a.logfhw)
			fh.append(a.logfhr)
	for a in th:
		if a:
			a.join(0.1)
	for a in mainth:
		if a:
			deletertu(a)
			a.join(0.1)
	for a in fh:
		if a:
			a.close()
	if window:
		window.destroy()

def deletertu(self):
	tab_parent.select(0)
	canvas.yview_moveto('0.0')
	self.lbl_seqno.destroy()
	self.lbl_sys.destroy()
	self.lbl_status.destroy()
	self.lbl_rtuno.destroy()
	self.lbl_portno.destroy()
	self.lbl_gi.destroy()
	self.lbl_index.destroy()
	self.lbl_connectedat.destroy()
	self.cbx_action.destroy()
	self.btn_apply.destroy()
	window.update()

def opensocket(port):
	# open socket
	s=socket(AF_INET, SOCK_STREAM)
	s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
	s.bind(('', port))
	s.listen(1)
	return s
		
def closesocket(s):
	try:
		s.close()
	except (error, OSError, ValueError):
		pass
	return 0

def openconn(self):
	# open connection
	if self.s:
		try:
			self.conn, addr = self.s.accept()
			self.timeidle=time()
		except (error, OSError, ValueError):
			self.conn = 0
		if self.conn:
			self.conn.setblocking(False)
			self.s=closesocket(self.s)
			acceptedaddr=0
			for i in self.acceptnetsys:
				try:
					if ip_address(addr[0]) in ip_network(i):
						acceptedaddr=1
						break
				except (ValueError):
					pass
			if acceptedaddr or not ''.join(self.acceptnetsys):
				self.logfhw.write(str(datetime.now()) + ' : Connected to IP: ' + str(addr[0]) + ', Port: ' + str(addr[1]) + '\n')
				self.logfilechanged=1
			else:
				self.conn=closeconn(self,0)
				self.s=opensocket(self.PORT)
	return self.conn
	
def closeconn(self,setdisconnet=1):
	if self.conn:
		try:
			self.conn.shutdown(SHUT_RDWR)    # 0 = done receiving, 1 = done sending, 2 = both
			self.conn.close()
		except (error, OSError, ValueError):
			pass
		incseqno(self,'I')
		if setdisconnet:
			self.disconnected=1
	return 0

# read data
def readdata(self):
	global bufsize
	if self.conn:
		if (self.wrpointer+1) != self.rdpointer:
			try:
				data = self.conn.recv(2)
				if data:
					dt = datetime.now()
					packetlen=b'0'
					if data[0] == 104:
						packetlen=data[1]
					elif data[1] == 104:
						packetlen=self.conn.recv(1)
					if packetlen != b'0':
						data = hexlify(self.conn.recv(packetlen))
						self.databuffer[self.wrpointer + 1] = [data.decode(), str(dt)]
						self.sentnorec=0
						self.timeidle=time()
						if self.wrpointer == (bufsize - 1):
							self.wrpointer=-1
						else:
							self.wrpointer += 1
					return packetlen
			except (BlockingIOError, error, OSError, ValueError):
				pass

def senddata(self,data,addtime=0):
	while not len(self.ready_to_write):
		pass
	while self.insenddata:
		pass
	self.insenddata=1
	# wait if exceeded k packets send without receive.
	while self.sentnorec > self.kpackets:
		pass
	dt = datetime.now()
	if addtime:
		# prepare CP56Time2a time
		ml = int((int(dt.second) * 1000) + (int(dt.microsecond) / 1000))
		min = int(dt.minute)
		hrs = int(dt.hour)
		day = int(((int(dt.weekday()) + 1) * 32) + int(dt.strftime("%d")))
		mon = int(dt.month)
		yr = int(dt.strftime("%y"))
		data = data + ml.to_bytes(2,'little') + min.to_bytes(1,'little') + hrs.to_bytes(1,'little') + day.to_bytes(1,'little') + mon.to_bytes(1,'little') + yr.to_bytes(1,'little')
	try:
		# add seq numbers to data packet if it is I format
		if (int.from_bytes(data[2:3], byteorder='little') & 1) == 0:
			data1 = data[0:2] + (self.txlsb*2).to_bytes(1,'little') + self.txmsb.to_bytes(1,'little') + (self.rxlsb*2).to_bytes(1,'little') + self.rxmsb.to_bytes(1,'little') + data[6:]
			self.conn.sendall(data1)
			incseqno(self,'TX')
			self.sentnorec += 1
		else:
			self.conn.sendall(data)
	except (error, OSError, ValueError, AttributeError):
		pass
	self.timeidle=time()
	self.insenddata=0
	return str(dt)

def incseqno(self,txrx):
	if txrx == 'I':
		self.txlsb=0
		self.txmsb=0
		self.rxlsb=0
		self.rxmsb=0
	if txrx == 'TX':
		self.txlsb += 1
		if self.txlsb == 128:
			self.txlsb=0
			self.txmsb += 1
			if self.txmsb == 256:
				self.txmsb=0
	if txrx == 'RX':
		self.rxlsb += 1
		if self.rxlsb == 128:
			self.rxlsb=0
			self.rxmsb += 1
			if self.rxmsb == 256:
				self.rxmsb=0

def initiate(self):
	self.dataactive=0
	self.statusvalue="NO"
	self.statuscolor='red'
	self.connectedatvalue=' '
	self.updatestatusgui=1
	self.sentnorec=0
	self.rcvtfperiodmin=1000000
	self.time1=0
	# set initialize flag
	self.initialize=1
	self.logfilechanged=1

def readpacket(self):
	global ioacmdv,cmdtype,cmdvalue,cmdtime,bufsize,pulsemess,regmess,valuemess
	packet=''
	# read the packet from buffer
	if self.rdpointer != self.wrpointer:
		packet, dt=self.databuffer[self.rdpointer+1]
		seqnotxlsb=int(packet[0:2],16)
		if self.rdpointer == (bufsize - 1):
			self.rdpointer=-1
		else:
			self.rdpointer += 1
		# decode U format packets
		if packet[0:2] == '07':			# startdt act packet
			# send startdt con
			sendpacket=b'\x68\x04\x0B\x00\x00\x00'
			senddata(self,sendpacket)
			self.logfhw.write(dt + ' : startdt act/con done.' + '\n')
			if not self.dataactive:
				# send end of initialization
				sendpacket=b'\x68\x0E\x00\x00\x00\x00\x46\x01\x04\x00' + int(self.rtuno).to_bytes(2,'little') + b'\x00\x00\x00\x00'
				senddata(self,sendpacket)
				self.logfhw.write(dt + ' : End of initialization transmitted.' + '\n')
				self.dataactive=1
				self.statusvalue="YES"
				self.statuscolor='green'
				self.connectedatvalue=dt
				self.updatestatusgui=1
		elif  packet[0:2] == '43':		 	# testfr act packet
			rcvtf=time()
			rcvtfperiod=round(rcvtf - self.time1,1)
			# send testfr con packet
			sendpacket=b'\x68\x04\x83\x00\x00\x00'
			senddata(self,sendpacket)
			if rcvtfperiod < self.rcvtfperiodmin and self.time1 != 0:
				self.rcvtfperiodmin=rcvtfperiod
				self.logfhw.write(dt + ' : Received testfr act minimum period: ' + "{:04.1f}".format(float(rcvtfperiod)) + ' seconds.' + '\n')
			self.time1=rcvtf
		elif  packet[0:2] == '13':		 	# stopdt act packet
			# send stopdt con
			sendpacket=b'\x68\x04\x23\x00\x00\x00'
			senddata(self,sendpacket)
			self.logfhw.write(dt + ' : stopdt act/con done.' + '\n')
			# initialize
			initiate(self)
		# check if it is I format (bit 0=0 of 3rd byte or 4 and 5 digits of databuffer) then increase RX
		if (seqnotxlsb & 1) == 0:
			incseqno(self,'RX')
			# decode I format packets
			if packet[8:8+12] == ('64010600' + self.rtunohex) or packet[8:8+12] == '64010600ffff':		# GI act packet
				sendpacket=b'\x68\x0E\x00\x00\x00\x00\x64\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + b'\x00\x00\x00\x14'
				senddata(self,sendpacket)
				self.logfhw.write(dt + ' : GI received.' + '\n')
				f=open(self.logfilenamegi,"a")
				f.write(dt + ' : GI received.' + '\n')
				f.close()
				self.sendgi=1
			elif  packet[8:8+12] == ('67010600' + self.rtunohex) or packet[8:8+12] == '67010600ffff':		# Time sync act packet
				sendpacket=b'\x68\x14\x00\x00\x00\x00\x67\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + b'\x00\x00\x00'
				senddata(self,sendpacket,addtime=1)
				ts=((int(packet[32:32+2],16) & 0x80)>>7)*3
				ms=packet[28:28+2] + packet[26:26+2]
				self.logfhw.write(dt + ' : Time sync. received with date (dd-mm-yy): ' + "{:02d}".format(int(packet[34:34+2],16)&0x1f) + '-' + "{:02d}".format(int(packet[36:36+2],16)&0x0f) + '-' + "{:02d}".format(int(packet[38:38+2],16)&0x7f) + ',\n\t\t\t     time (HH:MM:SS.ms): ' + "{:02d}".format(int(packet[32:32+2],16)&0x1f) + ':' + "{:02d}".format(int(packet[30:30+2],16)&0x3f) + ':' + "{:09.6f}".format(float(int(ms,16))/1000) + ', Time saving ' + valuemess[ts:ts+3] + '\n')
			elif  packet[8:8+12] == ('2d010600' + self.rtunohex):				# sco command without time tag.
				ioacmd=bytearray.fromhex(packet[20:20+6])
				pulse=((int(packet[26:26+2],16) & 0x7c)>>2)*8
				valuem=(int(packet[26:26+2],16) & 0x03)*3
				# if select? then acknowledge only otherwise ack and term then prepare for sending back the status
				if (int(packet[26:26+2],16) & 0x80) != 0:	# check select bit 1000 0000
					# send cmd ack
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket)
					logmess=dt + ' : SCO without time tag received, IOA=' + str(int.from_bytes(ioacmd,'little')) + ', Select set, Pulse=' + pulsemess[pulse:pulse+8] + ', Val=' + valuemess[valuem:valuem+3]
				else:
					# send actconf.
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket)
					# send actterm.
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x0a\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket)
					ioacmdv=str(int.from_bytes(ioacmd,'little'))
					cmdvalue=(int(packet[26:26+2],16) & 0x03)
					cmdtype=1	# sco - cmdtype=${packet:8:2}
					logmess=dt + ' : SCO without time tag received, IOA=' + ioacmdv + ', Execute set, Pulse=' + pulsemess[pulse:pulse+8] + ', Val=' + valuemess[valuem:valuem+3]
					cmdtime=time()
				self.logfhw.write(logmess + '\n')
			elif  packet[8:8+12] == ('2e010600' + self.rtunohex):				# dco command without time tag.
				ioacmd=bytearray.fromhex(packet[20:20+6])
				pulse=((int(packet[26:26+2],16) & 0x7c)>>2)*8
				valuem=((int(packet[26:26+2],16) & 0x03)-1)*3
				# if select? then acknowledge only otherwise ack and term then prepare for sending back the status
				if (int(packet[26:26+2],16) & 0x80) != 0:	# check select bit 1000 0000
					# send cmd ack
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket)
					logmess=dt + ' : DCO without time tag received, IOA=' + str(int.from_bytes(ioacmd,'little')) + ', Select set, Pulse=' + pulsemess[pulse:pulse+8] + ', Val=' + valuemess[valuem:valuem+3]
				else:
					# send actconf.
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket)
					# send actterm.
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x0a\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket)
					ioacmdv=str(int.from_bytes(ioacmd,'little'))
					cmdvalue=(int(packet[26:26+2],16) & 0x03)
					cmdtype=2	# dco - cmdtype=${packet:8:2}
					logmess=dt + ' : DCO without time tag received, IOA=' + ioacmdv + ', Execute set, Pulse=' + pulsemess[pulse:pulse+8] + ', Val=' + valuemess[valuem:valuem+3]
					cmdtime=time()
				self.logfhw.write(logmess + '\n')
			elif  packet[8:8+12] == ('2f010600' + self.rtunohex):				# rco command without time tag.
				ioacmd=bytearray.fromhex(packet[20:20+6])
				pulse=((int(packet[26:26+2],16) & 0x7c)>>2)*8
				valuem=((int(packet[26:26+2],16) & 0x03)-1)*9
				# if select? then acknowledge only otherwise ack and term then prepare for sending back the status
				if (int(packet[26:26+2],16) & 0x80) != 0:	# check select bit 1000 0000
					# send cmd ack
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket)
					logmess=dt + ' : RCO without time tag received, IOA=' + str(int.from_bytes(ioacmd,'little')) + ', Select set, Pulse=' + pulsemess[pulse:pulse+8] + ', Val=' + regmess[valuem:valuem+9]
				else:
					# send actconf.
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket)
					# send actterm.
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x0a\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket)
					ioacmdv=str(int.from_bytes(ioacmd,'little'))
					cmdvalue=(int(packet[26:26+2],16) & 0x03)
					cmdtype=2	# rco - cmdtype=${packet:8:2}
					logmess=dt + ' : RCO without time tag received, IOA=' + ioacmdv + ', Execute set, Pulse=' + pulsemess[pulse:pulse+8] + ', Val=' + regmess[valuem:valuem+9]
					cmdtime=time()
				self.logfhw.write(logmess + '\n')
			elif  packet[8:8+12] == ('3a010600' + self.rtunohex):				# sco command with time tag.
				ioacmd=bytearray.fromhex(packet[20:20+6])
				pulse=((int(packet[26:26+2],16) & 0x7c)>>2)*8
				valuem=(int(packet[26:26+2],16) & 0x03)*3
				ts=((int(packet[34:34+2],16) & 0x80)>>7)*3
				ms=packet[30:30+2] + packet[28:28+2]
				logtime='with date (dd-mm-yy): ' + "{:02d}".format(int(packet[36:36+2],16)&0x1f) + '-' + "{:02d}".format(int(packet[38:38+2],16)&0x0f) + '-' + "{:02d}".format(int(packet[40:40+2],16)&0x7f) + ' & time (HH:MM:SS.ms): ' + "{:02d}".format(int(packet[34:34+2],16)&0x1f) + ':' + "{:02d}".format(int(packet[32:32+2],16)&0x3f) + ':' + "{:09.6f}".format(float(int(ms,16))/1000) + ', Time saving ' + valuemess[ts:ts+3]
				# if select? then acknowledge only otherwise ack and term then prepare for sending back the status
				if (int(packet[26:26+2],16) & 0x80) != 0:	# check select bit 1000 0000
					# send cmd ack
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket,addtime=1)
					logmess=dt + ' : SCO with time tag received, IOA=' + str(int.from_bytes(ioacmd,'little')) + ', Select set, Pulse=' + pulsemess[pulse:pulse+8] + ', Val=' + valuemess[valuem:valuem+3]
				else:
					# send actconf.
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket,addtime=1)
					# send actterm.
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x0a\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket,addtime=1)
					ioacmdv=str(int.from_bytes(ioacmd,'little'))
					cmdvalue=(int(packet[26:26+2],16) & 0x03)
					cmdtype=1	# sco - cmdtype=${packet:8:2}
					logmess=dt + ' : SCO with time tag received, IOA=' + ioacmdv + ', Execute set, Pulse=' + pulsemess[pulse:pulse+8] + ', Val=' + valuemess[valuem:valuem+3]
					cmdtime=time()
				self.logfhw.write(logmess + '\n\t\t\t     ' + logtime + '\n')
			elif  packet[8:8+12] == ('3b010600' + self.rtunohex):				# dco command with time tag.
				ioacmd=bytearray.fromhex(packet[20:20+6])
				pulse=((int(packet[26:26+2],16) & 0x7c)>>2)*8
				valuem=((int(packet[26:26+2],16) & 0x03)-1)*3
				ts=((int(packet[34:34+2],16) & 0x80)>>7)*3
				ms=packet[30:30+2] + packet[28:28+2]
				logtime='with date (dd-mm-yy): ' + "{:02d}".format(int(packet[36:36+2],16)&0x1f) + '-' + "{:02d}".format(int(packet[38:38+2],16)&0x0f) + '-' + "{:02d}".format(int(packet[40:40+2],16)&0x7f) + ' & time (HH:MM:SS.ms): ' + "{:02d}".format(int(packet[34:34+2],16)&0x1f) + ':' + "{:02d}".format(int(packet[32:32+2],16)&0x3f) + ':' + "{:09.6f}".format(float(int(ms,16))/1000) + ', Time saving ' + valuemess[ts:ts+3]
				# if select? then acknowledge only otherwise ack and term then prepare for sending back the status
				if (int(packet[26:26+2],16) & 0x80) != 0:	# check select bit 1000 0000
					# send cmd ack
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket,addtime=1)
					logmess=dt + ' : DCO with time tag received, IOA=' + str(int.from_bytes(ioacmd,'little')) + ', Select set, Pulse=' + pulsemess[pulse:pulse+8] + ', Val=' + valuemess[valuem:valuem+3]
				else:
					# send actconf.
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket,addtime=1)
					# send actterm.
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x0a\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket,addtime=1)
					ioacmdv=str(int.from_bytes(ioacmd,'little'))
					cmdvalue=(int(packet[26:26+2],16) & 0x03)
					cmdtype=2	# dco - cmdtype=${packet:8:2}
					logmess=dt + ' : DCO with time tag received, IOA=' + ioacmdv + ', Execute set, Pulse=' + pulsemess[pulse:pulse+8] + ', Val=' + valuemess[valuem:valuem+3]
					cmdtime=time()
				self.logfhw.write(logmess + '\n\t\t\t     ' + logtime + '\n')
			elif  packet[8:8+12] == ('3c010600' + self.rtunohex):				# rco command with time tag.
				ioacmd=bytearray.fromhex(packet[20:20+6])
				pulse=((int(packet[26:26+2],16) & 0x7c)>>2)*8
				valuem=((int(packet[26:26+2],16) & 0x03)-1)*9
				ts=((int(packet[34:34+2],16) & 0x80)>>7)*3
				ms=packet[30:30+2] + packet[28:28+2]
				logtime='with date (dd-mm-yy): ' + "{:02d}".format(int(packet[36:36+2],16)&0x1f) + '-' + "{:02d}".format(int(packet[38:38+2],16)&0x0f) + '-' + "{:02d}".format(int(packet[40:40+2],16)&0x7f) + ' & time (HH:MM:SS.ms): ' + "{:02d}".format(int(packet[34:34+2],16)&0x1f) + ':' + "{:02d}".format(int(packet[32:32+2],16)&0x3f) + ':' + "{:09.6f}".format(float(int(ms,16))/1000) + ', Time saving ' + valuemess[ts:ts+3]
				# if select? then acknowledge only otherwise ack and term then prepare for sending back the status
				if (int(packet[26:26+2],16) & 0x80) != 0:	# check select bit 1000 0000
					# send cmd ack
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket,addtime=1)
					logmess=dt + ' : RCO with time tag received, IOA=' + str(int.from_bytes(ioacmd,'little')) + ', Select set, Pulse=' + pulsemess[pulse:pulse+8] + ', Val=' + regmess[valuem:valuem+9]
				else:
					# send actconf.
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x07\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket,addtime=1)
					# send actterm.
					sendpacket=b'\x68\x0e\x00\x00\x00\x00' + int(packet[8:8+2],16).to_bytes(1,'little') + b'\x01\x0a\x00' + int(self.rtuno).to_bytes(2,'little') + ioacmd + int(packet[26:26+2],16).to_bytes(1,'little')
					senddata(self,sendpacket,addtime=1)
					ioacmdv=str(int.from_bytes(ioacmd,'little'))
					cmdvalue=(int(packet[26:26+2],16) & 0x03)
					cmdtype=2	# rco - cmdtype=${packet:8:2}
					logmess=dt + ' : RCO with time tag received, IOA=' + ioacmdv + ', Execute set, Pulse=' + pulsemess[pulse:pulse+8] + ', Val=' + regmess[valuem:valuem+9]
					cmdtime=time()
				self.logfhw.write(logmess + '\n\t\t\t     ' + logtime + '\n')
		self.logfilechanged=1

def sendtelegramind (self,row):
	global valuemess
	telegram=''
	if not self.dataactive:
		return
	cot=3	# spont.
	objno=1
	#	GI	typeid	IOA	Value	Comment
	# decode io signals
	if row[2] == '1' or row[2] == '3':	# spi or dpi without time tag
		# length = 4 control fields + ASDU
		len=14
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + int(row[4]).to_bytes(1,'little')
		dt = senddata(self,packet)
		if row[2] == '1':
			v=int(row[4]) * 3
			self.logfhw.write(dt + ' : SPI, IOA=' + row[3][0:12] + ', Val=' + valuemess[v:v+3] + ' ' + row[5][0:53] + '\n')
		else:
			v=(int(row[4]) - 1) * 3
			self.logfhw.write(dt + ' : DPI, IOA=' + row[3][0:12] + ', Val=' + valuemess[v:v+3] + ' ' + row[5][0:53] + '\n')
	elif  row[2] == '30' or row[2] == '31':	# spi or dpi with time tag
		# length = 4 control fields + ASDU
		len=21
		if row[2] == '30':
			v=int(row[4]) * 3
			packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + int(row[4]).to_bytes(1,'little')
			dt = senddata(self,packet,addtime=1)
			self.logfhw.write(dt + ' : SPI, IOA=' + row[3][0:12] + ', Val=' + valuemess[v:v+3] + ' ' + row[5][0:53])
		else:
			v=(int(row[4]) - 1) * 3
			packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + int(row[4]).to_bytes(1,'little')
			dt = senddata(self,packet,addtime=1)
			self.logfhw.write(dt + ' : DPI, IOA=' + row[3][0:12] + ', Val=' + valuemess[v:v+3] + ' ' + row[5][0:53])
		# write date in log file.
		self.logfhw.write('\n\t\t\t     with date&time tag: ' + dt + ', Time saving OFF\n')
	elif  row[2] == '9':				# meas. normalized without time tag
		len=16
		qds=0
		v=int(float(row[4])*32767)
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(2,'little', signed=True) + qds.to_bytes(1,'little')
		dt = senddata(self,packet)
		self.logfhw.write(dt + ' : NORM AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53] + '\n')
	elif  row[2] == '34':				# meas. normalized with time tag
		len=23
		qds=0
		v=int(float(row[4])*32767)
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(2,'little', signed=True) + qds.to_bytes(1,'little')
		dt = senddata(self,packet,addtime=1)
		self.logfhw.write(dt + ' : NORM AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53])
		self.logfhw.write('\n\t\t\t     with date&time tag: ' + dt + ', Time saving OFF\n')
	elif  row[2] == '11':				# meas. scaled without time tag
		len=16
		qds=0
		v=int(row[4])
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(2,'little', signed=True) + qds.to_bytes(1,'little')
		dt = senddata(self,packet)
		self.logfhw.write(dt + ' : SCAL AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53] + '\n')
	elif  row[2] == '35':				# meas. scaled with time tag
		len=23
		qds=0
		v=int(row[4])
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(2,'little', signed=True) + qds.to_bytes(1,'little')
		dt = senddata(self,packet,addtime=1)
		self.logfhw.write(dt + ' : SCAL AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53])
		self.logfhw.write('\n\t\t\t     with date&time tag: ' + dt + ', Time saving OFF\n')
	elif  row[2] == '13':				# meas. float without time tag
		len=18
		qds=0
		v = int(unpack("I", pack("f", float (row[4])))[0])
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(4,'little') + qds.to_bytes(1,'little')
		dt = senddata(self,packet)
		self.logfhw.write(dt + ' : FLT AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53] + '\n')
	elif  row[2] == '36':				# meas. float with time tag
		len=25
		qds=0
		v = int(unpack("I", pack("f", float (row[4])))[0])
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(4,'little') + qds.to_bytes(1,'little')
		dt = senddata(self,packet,addtime=1)
		self.logfhw.write(dt + ' : FLT AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53])
		self.logfhw.write('\n\t\t\t     with date&time tag: ' + dt + ', Time saving OFF\n')
	
def sendtelegramgi (self,row,f):
	global valuemess
	telegram=''
	if not self.dataactive:
		return
	cot=20	# GI
	objno=1
	#	GI	typeid	IOA	Value	Comment
	# decode io signals
	if row[2] == '1' or row[2] == '3' or row[2] == '30' or row[2] == '31':	# spi or dpi /with/without time tag
		# length = 4 control fields + ASDU
		len=14
		if row[2] == '1' or row[2] == '30':
			v=int(row[4]) * 3
			typeid=1
			packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + typeid.to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + int(row[4]).to_bytes(1,'little')
			dt = senddata(self,packet)
			f.write(dt + ' : SPI, IOA=' + row[3][0:12] + ', Val=' + valuemess[v:v+3] + ' ' + row[5][0:53] + '\n')
		else:
			v=(int(row[4]) - 1) * 3
			typeid=3
			packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + typeid.to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + int(row[4]).to_bytes(1,'little')
			dt = senddata(self,packet)
			f.write(dt + ' : DPI, IOA=' + row[3][0:12] + ', Val=' + valuemess[v:v+3] + ' ' + row[5][0:53] + '\n')
	elif  row[2] == '9' or row[2] == '34':				# meas. normalized without time tag
		len=16
		qds=0
		typeid=9
		v=int(float(row[4])*32767)
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + typeid.to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(2,'little', signed=True) + qds.to_bytes(1,'little')
		dt = senddata(self,packet)
		f.write(dt + ' : NORM AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53] + '\n')
	elif  row[2] == '11' or row[2] == '35':				# meas. scaled without time tag
		len=16
		qds=0
		typeid=11
		v=int(row[4])
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + typeid.to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(2,'little', signed=True) + qds.to_bytes(1,'little')
		dt = senddata(self,packet)
		f.write(dt + ' : SCAL AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53] + '\n')
	elif  row[2] == '13' or row[2] == '36':				# meas. float without time tag
		len=18
		qds=0
		typeid=13
		v = int(unpack("I", pack("f", float (row[4])))[0])
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + typeid.to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(4,'little') + qds.to_bytes(1,'little')
		dt = senddata(self,packet)
		f.write(dt + ' : FLT AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53] + '\n')

def sendtelegramcmd (self,row):
	global valuemess
	telegram=''
	if not self.dataactive:
		self.cmdvalue=0
		self.cmdtype=0
		return
	self.sendingcmd=1
	cot=3	# spont.
	objno=1
	#	GI	typeid	IOA	Value	Comment
	# decode io signals
	if row[2] == '1' or row[2] == '3':	# spi or dpi without time tag
		# length = 4 control fields + ASDU
		len=14
		if row[2] == '1' and self.cmdtype == 2:		#spi but cmd was dco; adjust value
			self.cmdvalue -= 1
		if row[2] == '3' and self.cmdtype == 1:		# dpi but cmd was sco; adjust value
			self.cmdvalue += 1
		v=self.cmdvalue
		if row[2] == '1':
			v *= 3
			typeid=1
			packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + typeid.to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(1,'little')
			dt = senddata(self,packet)
			self.logfhw.write(dt + ' : SPI, IOA=' + row[3][0:12] + ', Val=' + valuemess[v:v+3] + ' ' + row[5][0:53] + '\n')
		else:
			v = (v - 1) * 3
			typeid=3
			packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + typeid.to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(1,'little')
			dt = senddata(self,packet)
			self.logfhw.write(dt + ' : DPI, IOA=' + row[3][0:12] + ', Val=' + valuemess[v:v+3] + ' ' + row[5][0:53] + '\n')
	if row[2] == '30' or row[2] == '31':	# spi or dpi with time tag
		# length = 4 control fields + ASDU
		len=21
		if row[2] == '30' and self.cmdtype == 2:		#spi but cmd was dco; adjust value
			self.cmdvalue -= 1
		if row[2] == '31' and self.cmdtype == 1:		# dpi but cmd was sco; adjust value
			self.cmdvalue += 1
		value=self.cmdvalue
		if row[2] == '30':
			v = value * 3
			typeid=30
			packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + typeid.to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + value.to_bytes(1,'little')
			dt = senddata(self,packet,addtime=1)
			self.logfhw.write(dt + ' : SPI, IOA=' + row[3][0:12] + ', Val=' + valuemess[v:v+3] + ' ' + row[5][0:53])
		else:
			v=(value - 1) * 3
			typeid=31
			packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + typeid.to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + value.to_bytes(1,'little')
			dt = senddata(self,packet,addtime=1)
			self.logfhw.write(dt + ' : DPI, IOA=' + row[3][0:12] + ', Val=' + valuemess[v:v+3] + ' ' + row[5][0:53])
		# write date in log file.
		self.logfhw.write('\n\t\t\t     with date&time tag: ' + dt + ', Time saving OFF\n')
	if row[2] == '9':				# meas. normalized without time tag
		len=16
		qds=0
		v=int(float(row[4])*32767)
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(2,'little', signed=True) + qds.to_bytes(1,'little')
		dt = senddata(self,packet)
		self.logfhw.write(dt + ' : NORM AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53] + '\n')
	if row[2] == '34':				# meas. normalized with time tag
		len=23
		qds=0
		v=int(float(row[4])*32767)
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(2,'little', signed=True) + qds.to_bytes(1,'little')
		dt = senddata(self,packet,addtime=1)
		self.logfhw.write(dt + ' : NORM AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53])
		self.logfhw.write('\n\t\t\t     with date&time tag: ' + dt + ', Time saving OFF\n')
	if row[2] == '11':				# meas. scaled without time tag
		len=16
		qds=0
		v=int(row[4])
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(2,'little', signed=True) + qds.to_bytes(1,'little')
		dt = senddata(self,packet)
		self.logfhw.write(dt + ' : SCAL AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53] + '\n')
	if row[2] == '35':				# meas. scaled with time tag
		len=23
		qds=0
		v=int(row[4])
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(2,'little', signed=True) + qds.to_bytes(1,'little')
		dt = senddata(self,packet,addtime=1)
		self.logfhw.write(dt + ' : SCAL AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53])
		self.logfhw.write('\n\t\t\t     with date&time tag: ' + dt + ', Time saving OFF\n')
	if row[2] == '13':				# meas. float without time tag
		len=18
		qds=0
		v = int(unpack("I", pack("f", float (row[4])))[0])
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(4,'little') + qds.to_bytes(1,'little')
		dt = senddata(self,packet)
		self.logfhw.write(dt + ' : FLT AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53] + '\n')
	if row[2] == '36':				# meas. float with time tag
		len=25
		qds=0
		v = int(unpack("I", pack("f", float (row[4])))[0])
		packet = b'\x68' + len.to_bytes(1,'little') + b'\x00\x00\x00\x00' + int(row[2]).to_bytes(1,'little') + objno.to_bytes(1,'little') + cot.to_bytes(1,'little') + b'\x00' + int(self.rtuno).to_bytes(2,'little') + int(row[3]).to_bytes(3,'little') + v.to_bytes(4,'little') + qds.to_bytes(1,'little')
		dt = senddata(self,packet,addtime=1)
		self.logfhw.write(dt + ' : FLT AMI, IOA=' + row[3][0:12] + ', Val=' + row[4][0:12] + ' ' + row[5][0:53])
		self.logfhw.write('\n\t\t\t     with date&time tag: ' + dt + ', Time saving OFF\n')
	self.cmdvalue=0
	self.cmdtype=0
	self.sendingcmd=0

def indexthread (self):
	global indextime,indexvalue,exitprogram
	while True:
		if exitprogram:
			break
		if self.indextime != indextime:
			self.indextime=indextime
			if not self.dataactive:
				continue
			ioindex=indexvalue
			indexfound=0
			self.indexvalue=f'Sending {ioindex}'
			self.updateindexgui=1
			with open(self.iodata) as csv_file:
				#	GI	typeid	IOA	Value	Comment
				self.sendingind=1
				csv_reader = reader(csv_file, delimiter=',')
				for row in csv_reader:
					if not self.dataactive:
						break
					if not row[0].isdigit() or not row[2].isdigit() or not row[3].isdigit() or not row[4]:
						continue
					if (row[0] == ioindex or int(ioindex) == 0) and int(row[2]) in types:
						indexfound=1
						for l in range(6,len(row)):
							row[5] += ' ' + row[l]
						sendtelegramind(self,row)
			#while not self.indrun:
			#	pass
			self.sendingind=0
			if indexfound:
				self.indexvalue=f'{ioindex}'
			else:
				self.indexvalue=f'Missing {ioindex}'
			self.updateindexgui=1
			self.logfilechanged=1

def githread (self):
	global exitprogram
	while True:
		if exitprogram:
			break
		if not self.dataactive:
			self.sendgi=0
		if self.sendgi:
			self.givalue='RUN'
			self.updategigui=1
			f=open(self.logfilenamegi,"a")
			with open(self.iodata) as csv_file:
				#	GI	typeid	IOA	Value	Comment
				csv_reader = reader(csv_file, delimiter=',')
				for row in csv_reader:
					if row[0][0:1] == '!' or not self.dataactive:
						break
					if not row[0].isdigit() or not row[2].isdigit() or not row[3].isdigit() or not row[4]:
						continue
					if row[1] == 'Y':
						for l in range(6,len(row)):
							row[5] += ' ' + row[l]
						sendtelegramgi(self,row,f)
			# send end of GI if not interrupted
			if self.dataactive:
				xlen=14
				packet = b'\x68' + xlen.to_bytes(1,'little') + b'\x00\x00\x00\x00' + b'\x64\x01\x0a\x00' + int(self.rtuno).to_bytes(2,'little') + b'\x00\x00\x00\x14'
				dt = senddata(self,packet)
				self.logfhw.write(dt + ' : GI finished.\n')
				f.write(dt + ' : GI finished.\n')
			else:
				self.logfhw.write(str(datetime.now()) + ' : GI interrupted due to disconnection.\n')
				f.write(str(datetime.now()) + ' : GI interrupted due to disconnection.\n')
			f.close()
			self.givalue=' '
			self.updategigui=1
			#while self.updategigui:
			#	pass
			self.sendgi=0
			self.logfilechanged=1

def cmdthread (self):
	global ioacmdv,cmdtype,cmdvalue,cmdtime,exitprogram
	while True:
		if exitprogram:
			break
		if not self.dataactive:
			self.cmdvalue=0
			self.cmdtype=0
		if self.cmdtime != cmdtime:
			self.cmdtime=cmdtime
			cmdioa=ioacmdv
			self.cmdvalue=cmdvalue
			self.cmdtype=cmdtype
			with open(self.iodata) as csv_file:
				#	GI	typeid	IOA	Value	Comment
				csv_reader = reader(csv_file, delimiter=',')
				for row in csv_reader:
					if not self.dataactive:
						self.cmdvalue=0
						self.cmdtype=0
						break
					if not row[0].isdigit() or not row[2].isdigit() or not row[3].isdigit() or not row[4]:
						continue
					if row[3] == cmdioa:
						objaddress=row[4]
						break
				for row in csv_reader:
					if not self.dataactive:
						self.cmdvalue=0
						self.cmdtype=0
						break
					if not row[0].isdigit() or not row[2].isdigit() or not row[3].isdigit() or not row[4]:
						continue
					if row[3] == objaddress:
						for l in range(6,len(row)):
							row[5] += ' ' + row[l]
						sendtelegramcmd(self,row)
						break
			self.logfilechanged=1

def readpacketthread (self):
	global exitprogram
	initiate(self)
	while True:
		if exitprogram:
			break
		if self.initialize:
			self.logfhw.write(str(datetime.now()) + ' : Initialized ..\n')
			self.initialize=0
		if self.disconnected:
			self.logfhw.write(str(datetime.now()) + ' : Disconnected .. waiting for connection ..\n')
			initiate(self)
			self.initialize=0
			self.disconnected=0
		readpacket(self)

'''
Returns the epoch time fetched from the NTP server passed as argument.
Returns none if the request is timed out (5 seconds).
'''
def gettime_ntp(addr='time.nist.gov'):
    # http://code.activestate.com/recipes/117211-simple-very-sntp-client/
    TIME1970 = 2208988800      # Thanks to F.Lundh
    client = socket( AF_INET, SOCK_DGRAM )
    data = '\x1b' + 47 * '\0'
    try:
        # Timing out the connection after 5 seconds, if no response received
        client.settimeout(5.0)
        client.sendto( data.encode(), (addr, 123))
        data, address = client.recvfrom( 1024 )
        if data:
            epoch_time = unpack( '!12I', data )[10]
            epoch_time -= TIME1970
            return epoch_time
    except timeout:
        return None

def ntpthread():
	global ntpserver,timeupdateevery,exitprogram,timeupdated,updatetimegui
    # Iterates over every server in the list until it finds time from any one.
	while True:
		if exitprogram:
			break
		#timeupdated=''
		for server in ntpserver:
			epoch_time = gettime_ntp(server)
			if epoch_time is not None:
				# SetSystemTime takes time as argument in UTC time. UTC time is obtained using utcfromtimestamp()
				utcTime = datetime.utcfromtimestamp(epoch_time)
				SetSystemTime(utcTime.year, utcTime.month, utcTime.weekday(), utcTime.day, utcTime.hour, utcTime.minute, utcTime.second, 0)
				# Local time is obtained using fromtimestamp()
				localTime = datetime.fromtimestamp(epoch_time)
				timeupdated="Time updated at: " + localTime.strftime("%Y-%m-%d %H:%M:%S") + " from " + server[0:0+50]
				break
		updatetimegui=1
		
		sleep(timeupdateevery)

# define iec104 thread
class iec104thread (threading.Thread):
	global bufsize,dir
	def __init__(self, threadID, name, PORT,logfilename,rtuno,iodata):
		threading.Thread.__init__(self)
		self.threadID = threadID
		self.name = name
		self.PORT = int(PORT)
		self.logfilename = dir + logfilename + '.txt'
		self.logfilenamegi = dir + logfilename + '-gi.txt'
		self.logfhw=0
		self.logfhr=0
		self.logfilechanged=0
		self.iodata = datadir + iodata
		self.iodataent = iodata
		self.rtunohex = "{:04x}".format(int(rtuno))
		self.rtunohex = self.rtunohex[2:2+2] + self.rtunohex[0:2]
		self.rtuno = rtuno
		self.dataactive=0
		self.initialize=0
		self.rcvtfperiodmin=1000000
		self.insenddata=0
		self.sentnorec=0
		self.acceptnetsys=[]
		self.kpackets=12
		# timeidle > t3 (time of testfr packet). if not receiving data during timeidle then disconnect.
		self.tdisconnect=60
		self.waitrestart=0

		# cmd program data
		self.sendingcmd=0
		self.cmdtime=0
		self.cmdvalue=0
		self.cmdtype=0

		# gi program data
		# sendgi, if 1 then send the gi signals.
		self.sendgi=0
		self.girun=0

		# index program data
		self.sendingind=0
		self.indrun=0
		self.indextime=0

		# py will write this variable when connection disconnected.
		self.disconnected=0
		self.txlsb=0
		self.txmsb=0
		self.rxlsb=0
		self.rxmsb=0
		self.conn=0
		self.s=0
		self.time1=0
		# timeidle > t3 (time of testfr packet). if not receiving data during timeidle then disconnect.
		self.timeidle=time()		# after nt3 * t3 disconnect and wait for new connection.
		self.rdpointer=-1
		self.wrpointer=-1
		self.databuffer=[0 for i in range(bufsize+1)]
		self.ready_to_write=[]
		# GUI variables
		self.filternet=''
		self.lbl_seqno=tk.Label(frame, text=f'{1 + self.threadID}', relief=tk.RIDGE, width=5,bg="white", fg="blue")
		self.lbl_seqno.grid(row=self.threadID, column=0)
		self.lbl_sys=tk.Label(frame, text=self.name, relief=tk.RIDGE, width=16,bg="white", fg="red")
		self.lbl_sys.grid(row=self.threadID, column=1)
		self.lbl_status=tk.Label(frame, text='NO', relief=tk.RIDGE, width=6, bg="white", fg="red")
		self.lbl_status.grid(row=self.threadID, column=2)
		self.statusvalue='NO'
		self.statuscolor='red'
		self.updatestatusgui=0
		self.lbl_rtuno=tk.Label(frame, text=self.rtuno, relief=tk.RIDGE, width=5, bg="white", fg="blue")
		self.lbl_rtuno.grid(row=self.threadID, column=3)
		self.lbl_portno=tk.Label(frame, text=self.PORT, relief=tk.RIDGE, width=5, bg="white", fg="blue")
		self.lbl_portno.grid(row=self.threadID, column=4)
		self.lbl_gi=tk.Label(frame, text=' ', relief=tk.RIDGE, width=3, bg="white", fg="green")
		self.lbl_gi.grid(row=self.threadID, column=5)
		self.givalue=' '
		self.updategigui=0
		self.lbl_index=tk.Label(frame, text=' ', relief=tk.RIDGE, width=21, bg="white", fg="blue")
		self.lbl_index.grid(row=self.threadID, column=6)
		CreateToolTip(self.lbl_index,"Last index successfully submitted.")
		self.indexvalue=' '
		self.updateindexgui=0
		self.lbl_connectedat=tk.Label(frame, text=' ',bg="white", relief=tk.RIDGE, width=26, fg="green")
		self.lbl_connectedat.grid(row=self.threadID, column=7)
		self.connectedatvalue=' '
		self.cbx_action=ttk.Combobox(frame, width=21,
									values=[
											"Open log file", 
											"Open iodata file",
											"Open GI log file",
											"Show log in textbox 1",
											"Show log in textbox 2"])
		self.cbx_action.grid(row=self.threadID, column=8)
		CreateToolTip(self.cbx_action,"Select acction to be applied/executed.")
		self.btn_apply=tk.Button(master=frame, text="Apply", command=lambda: applyaction(self))
		self.btn_apply.grid(row=self.threadID, column=9)
		CreateToolTip(self.btn_apply,"Apply acction selected in combo box.")

	def run(self):
		global exitprogram
		ready_to_read=[]
		# wait until starting all threads.
		while not programstarted:
			pass
		while True:
			while self.waitrestart:
				pass
			if exitprogram:
				# close conn
				if self.conn:
					self.conn=closeconn(self)
				elif self.s:
					self.s=closesocket(self.s)
				break
			# timeidle > t3 (time of testfr packet). if not receiving data during timeidle then disconnect.
			if ((time() - self.timeidle) > self.tdisconnect) and self.conn:
				self.logfhw.write(str(datetime.now()) + ' : No received data for ' + str(self.tdisconnect) + ' seconds .. disconnecting ..\n')
				self.logfilechanged=1
				closeconn(self)
				self.s=opensocket(self.PORT)
				self.conn=openconn(self)
			if not self.s and not self.conn:
				self.s=opensocket(self.PORT)
			if not self.conn and self.s:
				self.conn=openconn(self)
			try:
				ready_to_read, self.ready_to_write, in_error = \
					select([self.conn,], [self.conn,], [], 1)
			except (OSError, ValueError):
				closeconn(self)
				self.s=opensocket(self.PORT)
				self.conn=openconn(self)
				# connection error event here, maybe reconnect
			if len(ready_to_read) > 0:
				recv=readdata(self)
				if not recv:
					closeconn(self)
					self.s=opensocket(self.PORT)
					self.conn=openconn(self)
					
def restartaction(self,ind):
	global txtbx1thid,txtbx2thid,updatetoframe1,updatetoframe2
	if ind == 1:
		# take sysname, rtuno, portno and filter from frame1
		sysname = ent_sys1.get()
		rtuno = ent_rtuno1.get()
		portno = ent_portno1.get()
		filternet = ent_filter1.get()
		iodata = ent_iodata1.get()
	else:
		# take sysname, rtuno, portno and filter from frame2
		sysname = ent_sys2.get()
		rtuno = ent_rtuno2.get()
		portno = ent_portno2.get()
		filternet = ent_filter2.get()
		iodata = ent_iodata2.get()
	tmplist=portnolist.copy()
	tmplist[self.threadID]='0'
	if not portno or not rtuno or not sysname:
		messagebox.showerror("Error", 'Port, RTU numbers and System name are required.')
	elif portno in tmplist:
		messagebox.showerror("Error", f'Wrong port {portno}, already used for other RTUs.')
	elif not int(rtuno) or not int(portno):
		messagebox.showerror("Error", f'Wrong port {portno} or rtu {rtuno}, must not equal zero.')
	elif not isfile(datadir + iodata):
		messagebox.showerror("Error", f'IOA data file {datadir + iodata}, is not exist')
	# confirm from user
	elif messagebox.askokcancel("Restart RTU", f'Do you want to restart "{self.threadID + 1}" with:\nName: {sysname}\nRTU: {rtuno}\nPort: {portno}\nAccept filter: {filternet}\nIOA data file: {datadir + iodata}'):
		self.waitrestart=1
		sleep(1)
		# close connection and socket
		if self.conn:
			self.conn = closeconn(self)
		elif self.s:
			self.s = closesocket(self.s)
		self.name=sysname
		self.PORT=int(portno)
		portnolist[self.threadID]=portno
		self.rtunohex = "{:04x}".format(int(rtuno))
		self.rtunohex = self.rtunohex[2:2+2] + self.rtunohex[0:2]
		self.rtuno = rtuno
		self.acceptnetsys.clear()
		self.acceptnetsys=filternet.split(';')
		self.filternet=filternet
		self.iodata = datadir + iodata
		self.iodataent = iodata
		# open connection with new settings
		self.waitrestart=0
		#self.s=opensocket(self.PORT)
		#self.conn=openconn(self)
		self.logfhw.write(str(datetime.now()) + ' : Restarting RTU as per user request.\n')
		self.logfilechanged=1
	if txtbx1thid == self.threadID:
		updatetoframe1=1
	if txtbx2thid == self.threadID:
		updatetoframe2=1

def applyaction(self):
	global updatetoframe1,updatetoframe2,txtbx1thid,txtbx2thid
	cursel=self.cbx_action.current()
	if cursel == 0:
		# open log file
		system(f'start notepad {self.logfilename}')
	elif cursel == 1:
		# open iodata file
		system(f'start {self.iodata}')
	elif cursel == 2:
		# open GI log file
		system(f'start notepad {self.logfilenamegi}')
	elif cursel == 3:
		# Show log in textbox 1
		txtbx1thid=self.threadID
		updatetoframe1=1
	elif cursel == 4:
		# Show log in textbox 2
		txtbx2thid=self.threadID
		updatetoframe2=1

def copytoframe1(self,fileonly=0):
	global txtbx1thid
	self.logfhw.flush()
	txtbx1thid=self.threadID
	if not fileonly:
		lbl_seqno1.configure(text=self.lbl_seqno["text"])
		self.lbl_rtuno.configure(text=self.rtuno)
		ent_rtuno1.delete(0, 'end')
		ent_rtuno1.insert(tk.END, self.rtuno)
		self.lbl_portno.configure(text=str(self.PORT))
		ent_portno1.delete(0, 'end')
		ent_portno1.insert(tk.END, str(self.PORT))
		#str_filter1.set(self.filternet)
		ent_filter1.delete(0, 'end')
		ent_filter1.insert(tk.END, self.filternet)
		ent_iodata1.delete(0, 'end')
		ent_iodata1.insert(tk.END, self.iodataent)
		#print('filter: ',self.filternet)
		btn_restart1.configure(command=lambda: restartaction(self,1))
		# update status
		self.lbl_sys.configure(text=self.name,fg=self.statuscolor)
		ent_sys1.delete(0, 'end')
		ent_sys1.insert(tk.END, self.name)
		ent_sys1.configure(fg=self.statuscolor)
		lbl_status1.configure(text=self.lbl_status["text"],fg=self.lbl_status["fg"])
		lbl_connectedat1.configure(text=self.lbl_connectedat["text"],fg=self.lbl_connectedat["fg"])
		lbl_gi1.configure(text=self.lbl_gi["text"],fg=self.lbl_gi["fg"])
		lbl_index1.configure(text=self.lbl_index["text"],fg=self.lbl_index["fg"])
	self.logfhr.seek(0)
	datatotext = self.logfhr.read()
	text_box1.config(state=tk.NORMAL)
	text_box1.delete('1.0', tk.END)
	text_box1.insert(tk.END, datatotext)
	text_box1.see(tk.END)
	text_box1.config(state=tk.DISABLED)

def copytoframe2(self,fileonly=0):
	global txtbx2thid
	self.logfhw.flush()
	txtbx2thid=self.threadID
	if not fileonly:
		lbl_seqno2.configure(text=self.lbl_seqno["text"])
		self.lbl_rtuno.configure(text=self.rtuno)
		ent_rtuno2.delete(0, 'end')
		ent_rtuno2.insert(tk.END, self.rtuno)
		self.lbl_portno.configure(text=str(self.PORT))
		ent_portno2.delete(0, 'end')
		ent_portno2.insert(tk.END, str(self.PORT))
		#str_filter2.set(self.filternet)
		ent_filter2.delete(0, 'end')
		ent_filter2.insert(tk.END, self.filternet)
		ent_iodata2.delete(0, 'end')
		ent_iodata2.insert(tk.END, self.iodataent)
		btn_restart2.configure(command=lambda: restartaction(self,2))
		# update status
		self.lbl_sys.configure(text=self.name,fg=self.statuscolor)
		ent_sys2.delete(0, 'end')
		ent_sys2.insert(tk.END, self.name)
		ent_sys2.configure(fg=self.statuscolor)
		lbl_status2.configure(text=self.lbl_status["text"],fg=self.lbl_status["fg"])
		lbl_connectedat2.configure(text=self.lbl_connectedat["text"],fg=self.lbl_connectedat["fg"])
		lbl_gi2.configure(text=self.lbl_gi["text"],fg=self.lbl_gi["fg"])
		lbl_index2.configure(text=self.lbl_index["text"],fg=self.lbl_index["fg"])
	self.logfhr.seek(0)
	datatotext = self.logfhr.read()
	text_box2.config(state=tk.NORMAL)
	text_box2.delete('1.0', tk.END)
	text_box2.insert(tk.END, datatotext)
	text_box2.config(state=tk.DISABLED)
	text_box2.see(tk.END)


def onFrameConfigure(canvas):
    #Reset the scroll region to encompass the inner frame
    canvas.configure(scrollregion=canvas.bbox("all"))

def digitvalidation(input,key,name):
	if 'index' in name:
		if len(input) < 13 and (input.isdigit() or input == ""):
			return True
		else:
			return False
	elif 'sysname' in name:
		if len(input) < 17 or input == "":
			return True
		else:
			return False
	elif 'filter' in name:
		if all(c in "0123456789;/.:" for c in input):
			return True
		else:
			return False
	elif 'iodata' in name:
		if any(c in '<>/\\:"|?*' for c in input):
			return False
		else:
			return True
	elif 'rtu' in name or 'port' in name:
		if input == "":
			return True
		elif input.isdigit():
			if int(input) <= 65535:
				return True
			else:
				return False
		else:
			return False

def sendindex():
	global indexvalue,indextime
	value = indexinput.get()
	if value:
		indexinput.delete(0, 'end')
		indexvalue=value
		indextime=time()

def on_closing():
	global exitprogram
	if messagebox.askokcancel("Quit", "Do you want to quit?"):
		exitprogram=1

class ToolTip(object):
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 57
        y = y + cy + self.widget.winfo_rooty() +27
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                      background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

def CreateToolTip(widget, text):
    toolTip = ToolTip(widget)
    def enter(event):
        toolTip.showtip(text)
    def leave(event):
        toolTip.hidetip()
    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)		
		
		
# *****************************************************
#                       Main code
# -----------------------------------------------------

signal(SIGTERM, signal_term_handler)

register(cleanup)

# create log folder
try:
	mkdir(dir)
except FileExistsError:
	pass

# get program arguments
# -h or --help							help message
# -i or --ini							init file
# -t or --ntp_update_every_sec			NTP update interval
# -s or --ntp_server					NTP server
argvl = argv[1:]
try:
	options, args = getopt(argvl, "i:t:s:h",
						["help",
						"ini=",
						"ntp_update_every_sec=",
						"ntp_server="])
except:
	print(helpmess)
	exit()

# parse program aguments
for argname, argvalue in options:
	if argname in ['-h', '--help']:
		print(helpmess)
		exit()
	elif argname in ['-i', '--ini']:
		initfile = argvalue
	elif argname in ['-t','--ntp_update_every_sec']:
		if argvalue.isdigit():
			timeupdateevery=int(argvalue)
	elif argname in ['-s', '--ntp_server']:
		ntpserver.append(argvalue)

# create GUI
window = tk.Tk()
#window.geometry("1270x670+0+0")
window.geometry("1235x630+0+0")
#window.state('zoomed')
window.resizable(False, False)
window.title("IEC-104 RTU Simulator")
listcol=[]
listrow=[]
listcol.extend(range(128))
listrow.extend(range(72))
window.rowconfigure(listrow, minsize=10, weight=1)
window.columnconfigure(listcol, minsize=10, weight=1)

tab_parent = ttk.Notebook(window)

tab_canvas = ttk.Frame(tab_parent)
tab_textbox = ttk.Frame(tab_parent)

tab_parent.add(tab_canvas, text="Full RTU list")
tab_parent.add(tab_textbox, text="Comparisons of log files")

#tab_parent.pack(expand=1, fill='both')
tab_parent.grid(row=3, column=1,columnspan=127,rowspan=64,sticky="nsew")

tab_canvas.rowconfigure(listrow, minsize=10, weight=1)
tab_canvas.columnconfigure(listcol, minsize=10, weight=1)

tab_textbox.rowconfigure(listrow, minsize=10, weight=1)
tab_textbox.columnconfigure(listcol, minsize=10, weight=1)

myFont = Font(family="Courier New", size=10)

dt=str(datetime.now())
lbl_startedat = tk.Label(master=window,relief=tk.GROOVE, borderwidth=3, fg='blue', text=f'Started at: {dt}')
lbl_startedat.grid(row=1, column=1,columnspan=30,rowspan=2,sticky="nw")

lbl_getindex = tk.Label(master=window,fg='blue', text='Index to send')
lbl_getindex.grid(row=1, column=22,columnspan=13,rowspan=2,sticky="ne")

indexinput = tk.Entry(window,name='index')
indexinput.grid(row=1, column=35,columnspan=10,rowspan=2,sticky="nw")
reg = window.register(digitvalidation)
indexinput.config(validate ="key", validatecommand =(reg, '%P', '%S', '%W'))
CreateToolTip(indexinput,'Enter row(s) index number from IOA data csv file\nto be submitted to all online Systems/RTUs.\n"0" will send all entries in the IOA data csv file.')

btn_sendindex = tk.Button(master=window, text="Send", command=sendindex)
btn_sendindex.grid(row=1, column=45,columnspan=5,rowspan=2, sticky="nw")

lbl_adminpriv = tk.Label(master=window,relief=tk.GROOVE, text=' ')
lbl_adminpriv.grid(row=1, column=55,columnspan=60,rowspan=2,sticky="nw")

#      System        Online    RTU    Port  GI    Last index          Connected at           Select action            Apply
# 1234567890123456    Yes     12345  12345  Run  123456789012  2021-04-22 06:27:47.462463  Open GI log file           Apply
#																				      	   Open log file
#																					       Open iodata file
#																					 	   Show log in textbox 1
#																					       Show log in textbox 2
lbl_header = tk.Label(master=tab_canvas, font=myFont, relief=tk.GROOVE, borderwidth=3, fg='blue', text='  No.      System      Online  RTU  Port  GI       Last index            Connected at             Select action       Apply')
lbl_header.grid(row=1, column=1,columnspan=100,rowspan=2,sticky="nw")

canvas = tk.Canvas(tab_canvas, borderwidth=0, background="#ffffff")
frame = tk.Frame(canvas, background="#ffffff")
frame.option_add("*Font", myFont)
vsb = tk.Scrollbar(tab_canvas, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=vsb.set)
vsb.grid(column=100, row=3,rowspan=50,columnspan=2, sticky="nse")
canvas.grid(row=3, column=1,columnspan=100,rowspan=50,sticky="nsew")
canvas.create_window((4,4), window=frame, anchor="nw")
frame.bind("<Configure>", lambda event, canvas=canvas: onFrameConfigure(canvas))

# first frame and textbox1
frame1 = tk.Frame(tab_textbox)
frame1.option_add("*Font", myFont)
frame1.grid(row=3, column=0,columnspan=130,rowspan=2,sticky="nsew")
#lbl_header1 = tk.Label(master=tab_textbox, font=myFont, relief=tk.GROOVE, borderwidth=3, fg='blue', text='  No.      System     Online  RTU  Port  GI       Last index            Connected at                 Filter net        Restart ')
lbl_header1 = tk.Label(master=tab_textbox, font=myFont, relief=tk.GROOVE, borderwidth=3, fg='blue', text='  No.      System     Online  RTU  Port  GI       Last index            Connected at                 Filter net             IOA data file       Restart ')
lbl_header1.grid(row=1, column=0,columnspan=130,rowspan=2,sticky="nw")
row=0
lbl_seqno1=tk.Label(frame1, text=' ', relief=tk.GROOVE, width=5,bg="white", fg="blue")
lbl_seqno1.grid(row=row, column=1)
ent_sys1=tk.Entry(frame1, name='sysname', validate ="key", validatecommand =(reg, '%P', '%S', '%W'), relief=tk.GROOVE, width=16,bg="light yellow", fg="blue")
ent_sys1.grid(row=row, column=2)
CreateToolTip(ent_sys1,"Enter new System/RTU name (max. 16 char).")
lbl_status1=tk.Label(frame1, text=' ', relief=tk.GROOVE, width=6, bg="white", fg="green")
lbl_status1.grid(row=row, column=3)
ent_rtuno1=tk.Entry(frame1, name='rtu', validate ="key", validatecommand =(reg, '%P', '%S', '%W'), relief=tk.GROOVE, width=5, bg="light yellow", fg="blue")
ent_rtuno1.grid(row=row, column=4)
CreateToolTip(ent_rtuno1,"Enter new RTU number (1-65535).")
ent_portno1=tk.Entry(frame1, name='port', validate ="key", validatecommand =(reg, '%P', '%S', '%W'), relief=tk.GROOVE, width=5, bg="light yellow", fg="blue")
ent_portno1.grid(row=row, column=5)
CreateToolTip(ent_portno1,"Enter new unique port number (1-65535).")
lbl_gi1=tk.Label(frame1, text=' ', relief=tk.GROOVE, width=3, bg="white", fg="green")
lbl_gi1.grid(row=row, column=6)
lbl_index1=tk.Label(frame1, text=' ', relief=tk.GROOVE, width=21, bg="white", fg="blue")
lbl_index1.grid(row=row, column=7)
CreateToolTip(lbl_index1,"Last index successfully submitted.")
lbl_connectedat1=tk.Label(frame1, text=' ',bg="white", relief=tk.GROOVE, width=26, fg="green")
lbl_connectedat1.grid(row=row, column=8)
#str_filter1 = tk.StringVar()
ent_filter1 = tk.Entry(frame1, name='filter', validate ="key", validatecommand =(reg, '%P', '%S', '%W'), relief=tk.GROOVE, width=26, bg="light yellow", fg="blue")
ent_filter1.grid(row=row, column=9, sticky="nsew")
CreateToolTip(ent_filter1,"Enter new hosts or networks filters separated by ;\nexample: 192.168.1.0/24;10.10.1.2")
ent_iodata1=tk.Entry(frame1, name='iodata', validate ="key", validatecommand =(reg, '%P', '%S', '%W'), relief=tk.GROOVE, width=25,bg="light yellow", fg="blue")
ent_iodata1.grid(row=row, column=10)
CreateToolTip(ent_iodata1,'Enter new IOA data csv file.\nMust be in "data" folder.')
btn_restart1 = tk.Button(master=frame1, text="Restart")
btn_restart1.grid(row=row, column=11,rowspan=2,sticky="nw")
CreateToolTip(btn_restart1,"Restart\nwith new\nsettings.")

text_box1 = tk.Text(tab_textbox)
text_box1.grid(row=5, column=0,columnspan=120,rowspan=21, sticky="nsew")
sb1 = ttk.Scrollbar(tab_textbox, orient="vertical", command=text_box1.yview)
sb1.grid(column=120, row=5,rowspan=21, columnspan=2, sticky="nse")
text_box1['yscrollcommand'] = sb1.set
#text_box1.delete(1.0, tk.END)
#text_box1.insert(tk.END, f'x={x}, y={y}')
#text_box1.bind("<Key>", lambda a: "break")
text_box1.config(state=tk.DISABLED)
CreateToolTip(text_box1,"Log file of the selected System/RTU is displayed here..")

# second frame and textbox2
frame2 = tk.Frame(tab_textbox)
frame2.option_add("*Font", myFont)
frame2.grid(row=29, column=0,columnspan=130,rowspan=2,sticky="nsew")
#lbl_header2 = tk.Label(master=tab_textbox, font=myFont, relief=tk.GROOVE, borderwidth=3, fg='blue', text='  No.      System     Online  RTU  Port  GI       Last index            Connected at                 Filter net        Restart ')
lbl_header2 = tk.Label(master=tab_textbox, font=myFont, relief=tk.GROOVE, borderwidth=3, fg='blue', text='  No.      System     Online  RTU  Port  GI       Last index            Connected at                 Filter net             IOA data file       Restart ')
lbl_header2.grid(row=27, column=0,columnspan=130,rowspan=2,sticky="nw")
row=0
lbl_seqno2=tk.Label(frame2, text=' ', relief=tk.GROOVE, width=5,bg="white", fg="blue")
lbl_seqno2.grid(row=row, column=1)
ent_sys2=tk.Entry(frame2, name='sysname', validate ="key", validatecommand =(reg, '%P', '%S', '%W'), relief=tk.GROOVE, width=16,bg="light yellow", fg="blue")
ent_sys2.grid(row=row, column=2)
CreateToolTip(ent_sys2,"Enter new System/RTU name (max. 16 char).")
lbl_status2=tk.Label(frame2, text=' ', relief=tk.GROOVE, width=6, bg="white", fg="green")
lbl_status2.grid(row=row, column=3)
ent_rtuno2=tk.Entry(frame2, name='rtu', validate ="key", validatecommand =(reg, '%P', '%S', '%W'), relief=tk.GROOVE, width=5, bg="light yellow", fg="blue")
ent_rtuno2.grid(row=row, column=4)
CreateToolTip(ent_rtuno2,"Enter new RTU number (1-65535).")
ent_portno2=tk.Entry(frame2, name='port', validate ="key", validatecommand =(reg, '%P', '%S', '%W'), relief=tk.GROOVE, width=5, bg="light yellow", fg="blue")
ent_portno2.grid(row=row, column=5)
CreateToolTip(ent_portno2,"Enter new unique port number (1-65535).")
lbl_gi2=tk.Label(frame2, text=' ', relief=tk.GROOVE, width=3, bg="white", fg="green")
lbl_gi2.grid(row=row, column=6)
lbl_index2=tk.Label(frame2, text=' ', relief=tk.GROOVE, width=21, bg="white", fg="blue")
lbl_index2.grid(row=row, column=7)
CreateToolTip(lbl_index2,"Last index successfully submitted.")
lbl_connectedat2=tk.Label(frame2, text=' ',bg="white", relief=tk.GROOVE, width=26, fg="green")
lbl_connectedat2.grid(row=row, column=8)
#str_filter2 = tk.StringVar()
ent_filter2 = tk.Entry(frame2, name='filter', validate ="key", validatecommand =(reg, '%P', '%S', '%W'), relief=tk.GROOVE, width=26, bg="light yellow", fg="blue")
ent_filter2.grid(row=row, column=9, sticky="nsew")
CreateToolTip(ent_filter2,"Enter new hosts or networks filters separated by ;\nexample: 192.168.1.0/24;10.10.1.2")
ent_iodata2=tk.Entry(frame2, name='iodata', validate ="key", validatecommand =(reg, '%P', '%S', '%W'), relief=tk.GROOVE, width=25,bg="light yellow", fg="blue")
ent_iodata2.grid(row=row, column=10)
CreateToolTip(ent_iodata2,'Enter new IOA data csv file.\nMust be in "data" folder.')
btn_restart2 = tk.Button(master=frame2, text="Restart")
btn_restart2.grid(row=row, column=11,rowspan=2, sticky="nw")
CreateToolTip(btn_restart2,"Restart\nwith new\nsettings.")

text_box2 = tk.Text(tab_textbox)
text_box2.grid(row=31, column=0,columnspan=120,rowspan=21, sticky="nsew")
sb2 = ttk.Scrollbar(tab_textbox, orient="vertical", command=text_box2.yview)
sb2.grid(column=120, row=31,rowspan=21, columnspan=2, sticky="nse")
text_box2['yscrollcommand'] = sb2.set
#text_box2.delete(1.0, tk.END)
#text_box2.insert(tk.END, f'x={x}, y={y}')
#text_box2.bind("<Key>", lambda a: "break")
text_box2.config(state=tk.DISABLED)
CreateToolTip(text_box2,"Log file of the selected System/RTU is displayed here..")

window.protocol("WM_DELETE_WINDOW", on_closing)

# read init file
# ntp_server,time.windows.com,,,,,,
# ntp_update,900,,,,,,
# id,sys name,rtuno,portno,hosts, k, idletime, iodata.csv
if isfile(initfile):
	with open(initfile) as csv_file:
		#variable=value
		csv_reader = reader(csv_file, delimiter=',')
		noofrtu=0
		#tmplist=[' ']
		for row in csv_reader:
			# if first character of first column in any row = '!' then break
			if row[0][0:1] == '!' or exitprogram:
				break
			# general settings
			elif row[0] == 'ntp_update_every_sec' and row[1].isdigit():
				timeupdateevery=int(row[1])
			elif row[0] == 'ntp_server' and row[1]:
				ntpserver.append(row[1])
			# RTUs settings - each row should start with integer, has rtuno, portno and exist iodata file.
			elif row[0].isdigit() and row[2].isdigit() and row[3].isdigit() and row[3] not in portnolist and int(row[2]) <= 65535 and int(row[3]) <= 65535 and isfile(datadir + row[7]):
				portnolist.append(row[3])
				# generate unique log file names
				dt=datetime.now()
				currentdate=dt.strftime("%b%d%Y-%H-%M-%S-%f")
				logfilename=f'{row[1]}-{currentdate}-{row[2]}-{row[3]}'
				# identify log files
				with open(dir + logfilename + '-gi.txt',"w") as f:
					f.write(f'{row[1]} GI log file .. RTU: {row[2]}, listen port: {row[3]}\n')
				# create thread class
				tmpth = iec104thread(noofrtu, row[1][0:0+16],int(row[3][0:0+5]),logfilename,row[2][0:0+5],row[7])
				mainth.append(tmpth)
				tmpth.daemon = True
				tmpth.logfhw=open(dir + logfilename + '.txt',"w")
				tmpth.logfhw.write(f'{row[1]} log file .. RTU: {row[2]}, listen port: {row[3]}\n')
				tmpth.logfhr=open(dir + logfilename + '.txt',"r")
				# get accepted hosts
				if row[4]:
					tmpth.acceptnetsys=row[4].split(';')
					tmpth.filternet=row[4]
				#tmplist[0]=row[4]
				#tmp_reader = reader(tmplist, delimiter=';')
				#for tmprow in tmp_reader:
				#	tmpth.acceptnetsys=tmprow
				# get k constant and idletime
				if row[5].isdigit():
					tmpth.kpackets=int(row[5])
				if row[6].isdigit():
					tmpth.tdisconnect=int(row[6])
				# create GUI resources for this rtu - 9 gadgets
				# label:System(16 char) label:Online (Yes/No) label:RTU/Port label:GI(Run) label:last index(sending 12 char) label:connected at(26 char) listbox:Action(30 char) button:Action
				# added to the class construction
				tmpth.start()
				# generate rest of the threads
				tmpth1 = threading.Thread(target=readpacketthread,args=(tmpth,), daemon=True)
				th.append(tmpth1)
				tmpth1.start()
				tmpth1 = threading.Thread(target=indexthread,args=(tmpth,), daemon=True)
				th.append(tmpth1)
				tmpth1.start()
				tmpth1 = threading.Thread(target=githread,args=(tmpth,), daemon=True)
				th.append(tmpth1)
				tmpth1.start()
				tmpth1 = threading.Thread(target=cmdthread,args=(tmpth,), daemon=True)
				th.append(tmpth1)
				tmpth1.start()
				noofrtu += 1
				window.update()

'''
ABB45678 Offline, RTU: 12345, Port: 12345, GI: Running, Index sent: 123456789012, Connected at: 2021-04-17 17:16:48.946776
'''
# starting thread of ntp server update
if	ntpserver:
	if is_admin:
		lbl_adminpriv.configure(text='Trying NTP servers to update local time ..',fg='red')
		tmpth = threading.Thread(target=ntpthread, daemon=True)
		th.append(tmpth)
		tmpth.start()
	else:
		lbl_adminpriv.configure(text='No admin privilege, cannot update time',fg='red')
	
if not noofrtu:
	messagebox.showerror("Error", f'Found {noofrtu} RTUs .. Exiting.\nTry "-h" or "--help"')
	#print(f'\nFound {noofrtu} RTUs .. Exiting.\nTry "-h" or "--help"')
	exit()
elif noofrtu >=2:
	copytoframe1(mainth[0])
	copytoframe2(mainth[1])
else:
	copytoframe1(mainth[0])

# all thread started, ready.
programstarted=1

while True:
	try:
		if exitprogram:
			break

		# update ntp gui
		if timeupdated:
			lbl_adminpriv.configure(text=timeupdated,fg='green')
			timeupdated=''
			updatetimegui=0
		elif updatetimegui:
			updatetimegui=0
			lbl_adminpriv.configure(fg='red')

		for a in mainth:
			if exitprogram:
				break
			# update gui
			# index
			if a.updateindexgui:
				a.updateindexgui=0
				a.lbl_index.configure(text=a.indexvalue,fg="blue")
				if a.threadID == txtbx1thid:
					lbl_index1.configure(text=a.indexvalue,fg="blue")
				if a.threadID == txtbx2thid:
					lbl_index2.configure(text=a.indexvalue,fg="blue")
			# GI
			if a.updategigui:
				a.updategigui=0
				a.lbl_gi.configure(text=a.givalue,fg="green")
				if a.threadID == txtbx1thid:
					lbl_gi1.configure(text=a.givalue,fg="green")
				if a.threadID == txtbx2thid:
					lbl_gi2.configure(text=a.givalue,fg="green")
			# status of connection
			if a.updatestatusgui:
				a.updatestatusgui=0
				a.lbl_sys.configure(fg=a.statuscolor)
				a.lbl_status.configure(text=a.statusvalue,fg=a.statuscolor)
				a.lbl_connectedat.configure(text=a.connectedatvalue,fg='green')
				if a.threadID == txtbx1thid:
					ent_sys1.configure(fg=a.statuscolor)
					lbl_status1.configure(text=a.statusvalue,fg=a.statuscolor)
					lbl_connectedat1.configure(text=a.connectedatvalue,fg='green')
				if a.threadID == txtbx2thid:
					ent_sys2.configure(fg=a.statuscolor)
					lbl_status2.configure(text=a.statusvalue,fg=a.statuscolor)
					lbl_connectedat2.configure(text=a.connectedatvalue,fg='green')
			window.update()

		# print frame1 log file
		if updatetoframe1:
			updatetoframe1=0
			copytoframe1(mainth[txtbx1thid])
		elif mainth[txtbx1thid].logfilechanged:
			mainth[txtbx1thid].logfilechanged=0
			mainth[txtbx1thid].logfhw.flush()
		textsize=len(text_box1.get('1.0',tk.END)) + int(text_box1.index('end').split('.')[0]) - 3
		if getsize(mainth[txtbx1thid].logfilename) != textsize:
			copytoframe1(mainth[txtbx1thid],fileonly=1)

		# print frame2 log file
		if updatetoframe2:
			updatetoframe2=0
			copytoframe2(mainth[txtbx2thid])
		elif mainth[txtbx2thid].logfilechanged:
			mainth[txtbx2thid].logfilechanged=0
			mainth[txtbx2thid].logfhw.flush()
		textsize=len(text_box2.get('1.0',tk.END)) + int(text_box2.index('end').split('.')[0]) - 3
		if getsize(mainth[txtbx2thid].logfilename) != textsize:
			copytoframe2(mainth[txtbx2thid],fileonly=1)
			
		#window.update_idletasks()
		#window.update()
	except KeyboardInterrupt:
		break
exit()
