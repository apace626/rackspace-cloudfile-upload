#!/usr/bin/python
import sys
import cloudfiles
import os
#import ssl

#Establish connection to cloud files
try:
		conn = cloudfiles.get_connection('username', 'apikey')
		containers = conn.get_all_containers()
		containerName = 'container name'
		cont = conn.get_container(containerName)
except:
		sys.stderr.write('API connection failed!')

#Get listing of all files in specified directory
try:
		path = 'path to backup directory'
		fileListing = os.listdir(path)
		fileCount = len(fileListing)
except:
		sys.stderr.write('Could not load directory!')

#Upload files to cloud
count = 0
for filename in fileListing:
	try:
			fileSize = os.path.getsize(path + filename)
			if fileSize > 0:
				print "Upload Started: " + filename
				obj  = cont.create_object(filename)
				obj.load_from_filename(path + filename)
				print "Upload Successful: " + filename
				os.remove(path + filename)
				print "File Removed: " + filename
				print ""
				count += 1
	except cloudfiles.errors.ResponseError, err:
			print filename + ': ' + err
	#except ssl.SSLError:
	#cannot use the above exception b/c this version of python does not contain the ssl module
	#the default exception below will try to restablish a connection
	except:
			print ""
			print "******************************************************************"
			print "ERROR uploading: " + filename
			print "Deleting Connection Objects..."
			del conn
			del containers
			print "Establishing New Connection..."
			conn = cloudfiles.get_connection('username', 'apikey')
			containers = conn.get_all_containers()		
			print "******************************************************************"
			print ""

print "*****************************"			
print "Files Uploaded: " + str(count) + "/" + str(fileCount)
print "*****************************"		