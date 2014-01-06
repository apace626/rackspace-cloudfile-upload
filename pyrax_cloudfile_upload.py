#!/usr/local/bin/python

import sys, argparse, os, zipfile, tarfile
import Image, random, re
import time
import urllib
import shutil
from lxml import etree
from jinja2 import Environment, FileSystemLoader
import pyrax

pyrax.set_setting("identity_type", "rackspace")
pyrax.set_credentials("user", "key")

cf = pyrax.cloudfiles
cont = cf.get_container(containerName)

def main(argv):
	parser = argparse.ArgumentParser(description='Simple Cloudfile Uploader')
	parser.add_argument('-f', '--file', help='SQL Backup file', required=True)
	parser.add_argument('-c', '--container', help='Name of container', required=True)
	args = parser.parse_args()

	global inputFile
	global containerName
	

	#Verify file type
	if os.path.isfile(args.file):
		ext = os.path.splitext(args.file)[-1].lower()
		if ext in compressedFileTypes:

			#define globals
			inputFile = args.input
			albumName = args.name
			albumDescription = args.description
			albumYear = args.year
			albumDate = args.timestamp
			albumCamera = args.camera
			outputDirectory = CreateUnpackFolder()
			thumbsDirectory = outputDirectory + "/thumbs/"

			UnpackPhotos()
			ResizePhotos()
			GenerateThumbnails()
			CreateMetadata()
			UploadPhotosToCloudFiles()
			GenerateAlbumHTML()
			GenerateHomePageHTML()
			CleanTempFolders()
		else:
			print "%s is not a compressed file (.gz or .zip)." % args.input

	else:
		print "%s does not exist" % args.input

def CreateUnpackFolder():
	print "Creating unpack folder..."
	outDirectory = tempBuildFolder + albumName
	outputThumbsDirectory = outDirectory + "/thumbs/"
	
	#Create folder in it does not exist
	if not os.path.exists(outDirectory):
    		os.makedirs(outDirectory)

    #Create thumbnail filder
	if not os.path.exists(outputThumbsDirectory):
    		os.makedirs(outputThumbsDirectory)

	return outDirectory

def UnpackPhotos():
	ext = os.path.splitext(inputFile)[-1].lower()

	if ext == ".zip":
		print "Unpacking ZIP..."
		zf = zipfile.ZipFile(inputFile, "r")
		zf.extractall(outputDirectory)
		return

	if ext == ".gz":
		print "Unpacking TAR..."
		tfile = tarfile.open(inputFile)
		 
		if tarfile.is_tarfile(inputFile):
		    # list all contents
		    #print "Tar file contents:"
		    #print tfile.list(verbose=False)
		    # extract all contents
		    tfile.extractall(outputDirectory)
		    return
		else:
		    print inputFile + " is not a tarfile."
		    return

	print "Unable to unpack %s" % inputFile

def ResizePhotos():
	print "Resizing photos..."
	size = 2048, 2048
	for infile in os.listdir(outputDirectory):
		ext = os.path.splitext(infile)[-1].lower()
		if ext in photoFileTypes:
			outfile = outputDirectory + "/" + infile
			print outfile

			try:
				im = Image.open(outputDirectory + "/" + infile)
				im.resize(size, Image.ANTIALIAS)
				im.save(outfile, "JPEG")
			except IOError:
				print "cannot resize photo for", infile

def GenerateThumbnails():
	print "Generating thumbnails..."
	size = 200, 200
	for infile in os.listdir(outputDirectory):
		if os.path.isfile(outputDirectory + "/" + infile):
			ext = os.path.splitext(infile)[-1].lower()
			if ext in photoFileTypes:
				outfile = thumbsDirectory + os.path.splitext(infile)[0] + ".thumb"
				print outfile

				try:
					im = Image.open(outputDirectory + "/" + infile)
					im.thumbnail(size, Image.ANTIALIAS)
					im.save(outfile, "JPEG")
				except IOError:
					print "cannot create thumbnail for", infile

def CreateMetadata():
	print "Creating metadata..."
	# create XML 
	album = etree.Element('album')

	date = etree.Element('date')
	date.text = albumDate
	album.append(date)
	
	name = etree.Element('name')
	name.text = albumName
	album.append(name)

	description = etree.Element('description')
	description.text = albumDescription
	album.append(description)

	year = etree.Element('year')
	year.text = albumYear
	album.append(year)

	camera = etree.Element('camera')
	camera.text = albumCamera
	album.append(camera)	

	builddate = etree.Element('builddate')
	builddate.text = time.strftime("%d/%m/%Y") + " " + time.strftime("%H:%M:%S")
	album.append(builddate)	

	output_file = open(outputDirectory + "/" + configFile, 'w')
	output_file.write('<?xml version="1.0"?>\r\n')
	output_file.write(etree.tostring(album, pretty_print=True))
	output_file.close()
	print output_file

def UploadPhotosToCloudFiles():
	print "Uploading file to cloud..."
	print ""

	for photo in os.listdir(outputDirectory):
		if os.path.isfile(outputDirectory + "/" + photo):
			uploadFile = "{0}/{1}".format(albumName, photo)
			print "Uploading: {0}".format(uploadFile)
			print "File Path: {0}".format(outputDirectory + "/" + photo)
			photoFile = open(outputDirectory + "/" + photo)
			obj = cont.store_object(uploadFile, photoFile.read())
			print "Stored Object Name:", obj.name
			print "Size:", obj.total_bytes
			print ""
			
	for thumb in os.listdir(thumbsDirectory):
		if os.path.isfile(thumbsDirectory + thumb):
			uploadFile = "{0}/{1}".format(albumName, thumb)
			print "Uploading: {0}".format(uploadFile)
			print "File Path: {0}".format(thumbsDirectory + thumb)
			photoFile = open(thumbsDirectory + thumb)
			obj = cont.store_object(uploadFile, photoFile.read(), content_type="image/jpeg")
			print "Stored Object Name:", obj.name
			print "Size:", obj.total_bytes
			print ""

def GenerateAlbumHTML():
	print "Generating HTML for albums..."

	global cloudObjects
	url = ""
	thumbUrl = ""
	photoURI = cont.cdn_uri
	
	THIS_DIR = os.path.dirname(os.path.abspath(__file__))
	j2_env = Environment(loader=FileSystemLoader(THIS_DIR))
	cloudObjects = cont.get_objects()

	albumList = GetAlbums()

	for album in albumList:
		photoList = []
		for obj in cloudObjects:
			ext = os.path.splitext(obj.name)[-1].lower()
			currentAlbumName = obj.name[0:obj.name.index('/')]
			if album == currentAlbumName and ext in photoFileTypes:
					config = GetAlbumConfig(album, False)
					url = photoURI + "/" + urllib.quote(obj.name)
					thumbUrl = photoURI + "/" + urllib.quote(os.path.splitext(obj.name)[0]) + ".thumb"
					photo = dict(photoURL=url, thumbURL=thumbUrl)
					photoList.append(photo)

		albumHTML = j2_env.get_template('galleria_template.html').render(AlbumName=album, AlbumDescription=config["description"], photos=photoList)
		output_file = open('{0}{1}.html'.format(albumFolder, album), 'w')
		output_file.write(albumHTML)
		output_file.close()

def GenerateHomePageHTML():
	print "Generating HTML for home page..."

	THIS_DIR = os.path.dirname(os.path.abspath(__file__))
	j2_env = Environment(loader=FileSystemLoader(THIS_DIR))
	photoURI = cont.cdn_uri
	albumList = []

	for obj in cloudObjects:
		#clear album list for next iteration
		tempList = []

		if configFile in obj.name:
			config = GetAlbumConfig(obj.fetch(), True)
			albumURL = "albums/" + config["name"] + ".html"
			configThumbURL = ""

			#get random photo here
			for obj2 in cloudObjects:

				ext = os.path.splitext(obj2.name)[-1].lower()
				stripAlbumName = obj2.name[0:obj2.name.index('/')]
				if config["name"] == stripAlbumName and ext in thumbFileTypes:
					thumbURL = photoURI + "/" + urllib.quote(obj2.name)
					tempList.append(thumbURL)

			#Get random object from list
			thumbURL = random.choice(tempList)
			album = dict(url=albumURL, thumbURL=thumbURL, name=config["name"], year=config["year"])
			albumList.append(album)

	indexHTML = j2_env.get_template('home_template.html').render(albums=albumList)
	output_file = open('../index.html', 'w')
	output_file.write(indexHTML)
	output_file.close()	
	

def CleanTempFolders():
	print "Cleaning temp folder..."
	for root, dirs, files in os.walk(tempBuildFolder):
	    for f in files:
	    	os.unlink(os.path.join(root, f))
	    for d in dirs:
	    	shutil.rmtree(os.path.join(root, d))

def GetAlbums():
	objList = []
	
	for obj in cloudObjects:
		ext = os.path.splitext(obj.name)[-1].lower()
		currentAlbumName = obj.name[0:obj.name.index('/')]
		if ext in photoFileTypes:
			objList.append(currentAlbumName)
	
	#Get unique items from list
	uniqueList = set(objList)
	return uniqueList


def GetAlbumConfig(config, useXML):
	# <album>
	# <date/>
	# <name>Temp</name>
	# <description>DEV: Christmas Cruise 2013</description>
	# <year>2014</year>
	# <camera/>
	# <builddate>04/01/2014 19:02:43</builddate>
	# </album>

	if useXML:
		configXML = config
	else:
		for obj in cloudObjects:
			currentAlbumName = obj.name[0:obj.name.index('/')]
			if config == currentAlbumName:
				if configFile in obj.name:
					configXML = obj.fetch()

	config = etree.fromstring(configXML)
	configName = config.find("name").text
	configBuildDate = config.find("builddate").text
	
	#year is optional, need to make a empty string if empty
	if config.find("year").text:
		configYear = config.find("year").text
	else:
		configYear = ""

	#description is optional, need to make a empty string if empty
	if config.find("description").text:
		configDescription = config.find("description").text
	else:
		configDescription = ""

	#date is optional, need to make a empty string if empty
	if config.find("date").text:
		configDate = config.find("date").text
	else:
		configDate = ""

	#camera is optional, need to make a empty string if empty
	if config.find("camera").text:
		configCamera = config.find("camera").text
	else:
		configCamera = ""
	
	return dict(date=configDate, name=configName, 
		description=configDescription, year=configYear, camera=configCamera, 
		buildDate=configBuildDate)

if __name__ == "__main__":
   main(sys.argv[1:])
