import os
import csv
import glob
import shutil
import difflib
import configparser
import tkinter as tk
from tkinter import filedialog as fd
from tkinter import messagebox as mb
from tkinter import simpledialog as sd

CWD = os.getcwd()
CONFIG_FILE = 'AssetConfig.ini'
DEFAULT_CONFIG = { "whitelist": ['"Asset Name"','"Credentials"','"FQDN"','"IP Addresses"','"Sensor"','"Asset Type"']}
TEMP_OLD = "temp.old"
TEMP_NEW = "temp.new"
HTML_FILE = "differ.html"

#move file to archive path
# shutil.move("path/to/current/file.foo", "path/to/new/destination/for/file.foo"

#compare 2 csvs
#show difference



def checkConfigFile(configFile):
	configLocation = os.path.join(CWD, configFile)
	try:
		open(configLocation).close()
		return checkConfigContent(configLocation)
	except IOError:
		open(configLocation, 'w+').close()
		return generateConfigContent(configLocation)

def checkConfigContent(configFile):
	config = configparser.ConfigParser()
	config.read(configFile)
	if DEFAULT_CONFIG == config.defaults():
		config = generateConfigContent(configFile)
		return config
	if (set(DEFAULT_CONFIG.keys()) >= set(config['DEFAULT'].keys())) == False:
		mb.showinfo(master=None, message='Unknow config file content, exiting.\nEither fix or remove the config file.')
		exit(2)
	# check if entries are correctly configured
	return config

def generateConfigContent(configFile):
	config = configparser.SafeConfigParser()
	config['DEFAULT'] = DEFAULT_CONFIG
	with open(configFile, 'w') as cfile:
		config.write(cfile)
	return config

def getNewestFile(path):
	files = os.listdir(path)
	paths = [os.path.join(path, basename) for basename in files]
	return max(paths, key=os.path.getctime).replace("\\", "/")

def getFileByString(path, match):
	files = os.listdir(path)
	for file in files:
		if match in file:
			return path + "/" + file

def replacer(s, newstring, index, nofail=False):
    if not nofail and index not in range(len(s)):
        raise ValueError("index outside given string")
    if index < 0:
        return newstring + s
    if index > len(s):
        return s + newstring
    return s[:index] + newstring + s[index + 1:]


class AssetReportEntry():
	def __init__(self, name, archivePath, sourcePath, nameRegex):
		self.name = name
		self.archivePath = archivePath
		self.sourcePath = sourcePath
		self.nameRegex = nameRegex


class Manager():
	def __init__(self):
		self.root = tk.Tk().withdraw()
		self.entries = []
		self.config = checkConfigFile(CONFIG_FILE)

		if len(self.config) == 1:
			self.createNewEntry()
		self.loadEntries()

		while True:
			self.chooseAction()

	def loadEntries(self):
		for entry in self.config.sections():
			self.entries.append(AssetReportEntry(
				entry,
				self.config[entry]["archivePath"],
				self.config[entry]["sourcePath"],
				self.config[entry]["nameRegex"]))

	def saveEntries(self):
		for entry in self.entries:
			if entry.name not in self.config.sections():
				self.config[entry.name] = {'archivePath': entry.archivePath,
										   'sourcePath': entry.sourcePath,
										   'nameRegex':entry.nameRegex}
		configLocation = os.path.join(CWD, CONFIG_FILE)
		with open(configLocation, 'w') as cfile:
			self.config.write(cfile)

	def createNewEntry(self):
		name = sd.askstring("New entry", "What is the name of this entry?")
		mb.showinfo(master=None, message='Select old csv')
		archivePath = fd.askdirectory()
		mb.showinfo(master=None, message='Select new csv')
		sourcePath = fd.askdirectory()
		nameRegex = sd.askstring("Name regex", "How can we locate the source file (enter a unique string)?")
		self.entries.append(AssetReportEntry(name, archivePath, sourcePath, nameRegex))

	def chooseAction(self):
		if mb.askyesno("What to do", "Run compare on all entries?"):
			self.compareCSV()
			exit()
		if mb.askyesno("What to do", "Add a new entry?"):
			self.createNewEntry()
			self.saveEntries()
			exit()
		if mb.askyesno("What to do", "Want to quit?"):
			exit()

	def compareCSV(self):
		for entry in self.entries:
			newCsv = getFileByString(entry.sourcePath, entry.nameRegex)
			newCsv = self.prepareNewCSV(newCsv)
			oldCsv = getNewestFile(entry.archivePath)
			shutil.move(newCsv, entry.archivePath + "/" + newCsv.split("/")[-1])
			newCsv = entry.archivePath + "/" + newCsv.split("/")[-1]
			oldContent = self.readCSV(oldCsv)
			newContent = self.readCSV(newCsv)
			self.writeCSV(oldContent, TEMP_OLD)
			self.writeCSV(newContent, TEMP_NEW)
			self.diffTempFiles()
			breakpoint()
			os.remove(TEMP_OLD)
			os.remove(TEMP_NEW)
			os.remove(HTML_FILE)

	def diffTempFiles(self):
		differ = difflib.HtmlDiff(wrapcolumn=81)
		old = self.readTempFile(TEMP_OLD)
		new = self.readTempFile(TEMP_NEW)
		html = differ.make_file(old, new)
		self.writeFile(html, HTML_FILE)

	def writeFile(self, content, fileName):
		with open(fileName, "w+") as source:
			source.write(content)

	def readTempFile(self, temp_File):
		with open(temp_File, "r") as source:
			content = source.readlines()
		return content

	def writeCSV(self, content, csvFile):
		with open(csvFile, "w+", newline='') as OpenFile:
			writer = csv.writer(OpenFile, dialect='unix')
			for row in content:
				writer.writerow(row)


	def readCSV(self, csvFile):
		content = []
		first = True
		ipField = None
		with open(csvFile, "r") as source:
			reader = csv.reader(source, dialect='unix')
			for row in reader:
				if first:
					ipField = row.index("IP Addresses")
					content.append(row)
					first = False
				else:
					newRow = row
					IPs = sorted(newRow[ipField].split(";"))
					newRow[ipField] = IPs
					content.append(newRow)
		return content

	def prepareNewCSV(self, csvLocation):
		self.removeColumns(csvLocation)
		csvLocation = self.replaceSpace(csvLocation)
		return csvLocation

	def replaceSpace(self, csvLocation):
		count = 0
		reverse = csvLocation[::-1]
		for index, char in enumerate(reverse):
			if char == " ":
				reverse = replacer(reverse, "_", index)
				count += 1
			if count == 2:
				break
		os.rename(csvLocation, reverse[::-1])
		return reverse[::-1]

	def removeColumns(self, csvLocation):
		header = open(csvLocation).readline().replace("\n","").split(",")
		toRemove = []
		for index, head in enumerate(header):
			if head not in self.config.defaults()['whitelist']:
				toRemove.append(index)
		toRemove = toRemove[::-1]

		with open(csvLocation, "r") as source:
			reader = csv.reader(source, dialect='unix')
			with open(csvLocation + ".new", "w+", newline='') as result:
				writer = csv.writer(result, dialect='unix')
				for row in reader:
					for index in toRemove:
						del row[index]
					writer.writerow(row)

		os.remove(csvLocation)
		os.rename(csvLocation + ".new", csvLocation)


if __name__ == '__main__':
	run = Manager()
