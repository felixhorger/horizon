import os
import shutil
import subprocess
import simple_term_menu as stm
import argparse
import random

from auth import *
from database import *
from pdftools import *
from utils import *

# TODO: yaml file with config for e.g. gnupg path or pubkey name and editor/viewer etc
# TODO: need to keep a list of all ever created random strings, so that it is impossible to ever create the
# same random string twice
# TODO: add value private/public (and make previously published papers private)
# TODO: add type as xapian value (text, code, data)
# TODO: command to open the last open entry for editing/cd



def add_entry(db, path, move, directory):
	# TODO: need a mechanism that prints the file path in case of an error, the user can save it
	# TODO: think about outsourcing all the xapian stuff to database.py, and remove xapian dep here

	print(f"Adding entry {path}")

	# TODO: initialise horizon entry (make class for this)
	# U: link to data or code TODO: this should be a field in the horizon data, not in the data base ...
	# TODO: author needs to be double saved, once in database (lower case...) and once in horizon entry

	# Try to get filename, title and text
	if path is not None: # TODO: this if statement needs refactoring, put each branch in func
		if directory: print("Warning: --directory option without effect")

		filename = os.path.basename(path)
		ui = input("Filename (default is provided name, space replaced by underscore): ")
		if len(ui): filename = ui
		filename.strip().replace(" ", "_")
		filename, ext = os.path.splitext(filename)

		if os.path.isfile(path):
			if len(ext): filetype = ext[1:].lower()
			else:        filetype = "txt"
		else: filetype = "" # TODO: need to figure out how to get this, count files/lines in dir

		# Title and text
		if   filetype == "pdf": title, text = pdf2text(path)
		elif filetype == "txt":
			f = open(path)
			text = f.read()
			f.close()
			title = get_title_from_text(text)
		else:
			title = "" # TODO
			text = ""
		title = title
		text = text

	else:

		filename = input("Filename: ").strip().replace(" ", "_")

		if directory:
			ext = ""
			filetype = ""
		else:
			filename, ext = os.path.splitext(filename)
			if ext == "": filetype = "txt"
			else:         filetype = ext[1:]

		title = ""
		text = ""


	author = pubkey["uids"][0].lower() # TODO: why is uids a list? and why uidS and not uid
	abstract = "" # TODO: input("Abstract (can add later TODO): ") probably better to add later or get from PDF/readme automatically
	institution = "" # TODO same ... add horizon edit
	keywords = "" # TODO input("Keywords: ").split()
	contributors = "" # TODO

	fingerprint = get_pubkey(gpg, pubkey)["fingerprint"]
	prefix = filename + "_" + fingerprint

	# Generate a new path for within the horizon archive
	num_bits = 4*4
	max_int = 2**num_bits
	start = random.randint(0, max_int-1)
	for i in range(max_int):
		r = (start + i) % max_int
		uid = prefix + ("%0.4x" % r) + ext
		new_path = os.path.join(horizon_archive, uid)
		if not os.path.exists(new_path): break
	if i == max_int-1: raise Exception("Could not find a non-existing filename, this should not happen!?")

	# Create/move file/symlink at new path
	if path is None:
		if move: raise Exception("Path not provided for option --move")
		f = open(new_path, "x")
		f.close()
		open_entries([new_path]) # TODO: don't use path here but horizon entry?
		f = open(new_path, "r")
		text = f.read()
		f.close()
		title = get_title_from_text(text)
	elif move: shutil.move(path, new_path)
	else: os.symlink(path, new_path)

	add_document(db, uid, author, abstract, filetype, filename, institution, keywords, contributors, title, text)

	return


def delete_entries(db, entries):
	#try:
	#	db.delete_document(1)
	#except xapian.DatabaseError as e:
	#	print("error:", e)
	#finally:
	#	db.close()
	#return
	for entry in entries:
		print(f"Deleting {entry}")
	return


def open_entries(entries):
	for entry in entries:
		print(f"Opening {entry}")
		# TODO: pick right program for this entry
		subprocess.run(["vim", entry])
	return


def cd_to_entry(entry):
	print(f"cd to entry {entry}")
	# TODO: if file, ask twice because otherwise you're in the horizon home folder
	return


def find_entries(db, query):
	if query is None:
		print("Listing the whole database")
		return
	
	entries = search(db, " ".join(query), offset=0, pagesize=10)
	if len(entries) == 0: return

	terminal_menu = stm.TerminalMenu(
		entries,
		multi_select=True,
		accept_keys=("enter", "backspace"),
		preview_command="echo Need to implement this into SimpleTerminalMenu",
		preview_size=0.5
	)
	selection = terminal_menu.show()

	if selection is None: return

	key = terminal_menu.chosen_accept_key
	if   key == "enter" or len(selection) > 1:
		open_entries([os.path.join(horizon_archive, entries[i]) for i in selection])
	elif key == "backspace":
		cd_to_entry(entries[selection[0]])



# Parse cmdline args
parser = argparse.ArgumentParser(description="Expand yours")

subparsers = parser.add_subparsers(dest="cmd", metavar="COMMAND", required=True)

add_parser = subparsers.add_parser("add", help="Expands your horizon")
add_parser.add_argument("path", metavar="PATH", nargs="?", help="Optional path to existing file or folder")
add_parser.add_argument("--move", action="store_true", help="Move file to location managed by horizon")
add_parser.add_argument("--dir", action="store_true", help="Create a directory not a file")

delete_parser = subparsers.add_parser("delete", help="Delete entry by ID")
delete_parser.add_argument("entries", metavar="ID", nargs="+", help="The item to delete")
delete_parser.add_argument("--keepfiles", action="store_true", help="Only delete database entry, not files")
delete_parser.add_argument("--force", action="store_true", help="Do not ask")

find_parser = subparsers.add_parser("find", help="Search for entries")
find_parser.add_argument("query", metavar="QUERY", nargs="*", help="Words to search for")

open_parser = subparsers.add_parser("open", help="Open entry by ID")
open_parser.add_argument(dest="entry", metavar="ID", nargs="+", help="Entries to open")
# TODO: run update on this entry after doc is closed (even for pdf, could have added comments!)

update_parser = subparsers.add_parser("update", help="Update the database, in case the files got out of sync, this might take a while")
# TODO: compute file fingerprints, check with with entry, and only update in case of change

edit_parser = subparsers.add_parser("edit", help="Edit an entry's meta data, use 'open' to edit the file(s)")
edit_parser.add_argument(dest="entry", metavar="ID", help="Entry to edit")

args = parser.parse_args()
#print(args)



# Setup

# Change to horizon directory
if hasattr(args, "path") and args.path is not None: args.path = os.path.abspath(args.path)
horizon_root = os.path.dirname(__file__)
os.chdir(horizon_root)

# Check archive folder
horizon_archive = os.path.join(horizon_root, "archive")
if not os.path.exists(horizon_archive): os.makedirs(horizon_archive)

# Public key
gpg = open_gpg()
PUBKEY = "Felix" # TODO, how? need horizon config
pubkey = get_pubkey(gpg, PUBKEY)

# Database
db = open_database("db")

# Execute commands
if   args.cmd == "add":    add_entry(db, args.path, args.move, args.dir)
elif args.cmd == "delete": delete_entries(db, args.entries)
elif args.cmd == "find":   find_entries(db, args.query)
elif args.cmd == "open":   open_entries(args.entry)

# Clean up
db.close()

