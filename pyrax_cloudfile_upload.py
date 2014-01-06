#!/usr/local/bin/python

import sys, argparse, os, zipfile, tarfile
import pyrax

pyrax.set_setting("identity_type", "rackspace")
pyrax.set_credentials("user", "key")

cf = pyrax.cloudfiles

compressedFileTypes = [".zip", ".gz"]

def main(argv):
	parser = argparse.ArgumentParser(description='Simple Cloudfile Uploader')
	parser.add_argument('-f', '--file', help='SQL Backup file', required=True)
	parser.add_argument('-c', '--container', help='Name of container', required=True)
	args = parser.parse_args()

	inputFile = args.file
	containerName = args.container
	
	#Verify file type
	if os.path.isfile(args.file):
		ext = os.path.splitext(args.file)[-1].lower()
		if ext in compressedFileTypes:
			cont = cf.get_container(containerName)				
			print "Uploading: {0}".format(inputFile)
			fileName = os.path.basename(inputFile)
			uploadFile = open(inputFile)
			obj = cont.store_object(fileName, uploadFile.read())
			print "Stored Object Name:", obj.name
			print "Size:", obj.total_bytes
			print ""
		else:
			print "%s is not a compressed file (.gz or .zip)." % args.input

	else:
		print "%s does not exist" % args.input

if __name__ == "__main__":
   main(sys.argv[1:])
