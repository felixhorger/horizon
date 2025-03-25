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
from meta import *


# TODO: most important is triggering an update to the database entry if file is changed and offering mechanism to do it manually


# TODO: for text based files, the preview does not need to be stored, can just be `head ...`, how to implement this?


# TODO: for updating code repos, which are stored outside of horizon, and have a different name, it would be good to have a list of real paths in horizon, so that the user can do `horizon update .` and it knows which uid this has
# TODO: yaml file with config for e.g. gnupg path or pubkey name and editor/viewer etc
# TODO: add value private/public (and make previously published papers private)
# TODO: command to open the last open entry for editing/cd

# TODO: is a good strategy to have good defaults, and ask at the end if that's ok?
# Or just add and the user can edit if necessary?

# Database fields:
# text (can be text file, can be pdf file, optionally with tex): store content of text file/pdf in general, and store tex code in X: field  TODO: what about markdown
# code (code repos, scripts): store content of readme in general, and code in X: field
# data: store content of readme in general

# PDFs are commited in the tex repo
# Figures used in the pdf are part of another repo in another entry, but can be referenced via the horizon archive,
# which should also work if the actual files are located elsewhere thanks to the symlinks

# Can use git rebase to get rid of old commits

# TODO: for data: one entry per dataset, because they share a description.
# Add the possibility to not to load the data files, but they can be downloaded via a link



class Entry:
	def __init__(
		self,
		uid,
		title,
		Type, # uppercase not to overwrite type()
		cmd="echo No command to open entry provided",
		readme="",
		private=True,
		datafiles={},
		preview=""
	):
		self.uid = uid
		self.title = title
		self.Type = Type
		self.cmd = cmd
		self.readme = readme
		self.private = private
		self.datafiles = datafiles
		self.preview = preview
		return

	def __repr__(self):
		return (
			f"Horizon Entry:\n"
			f"\tUID:\t\t{self.uid}\n"
			f"\tTitle:\t\t\"{self.title}\"\n"
			f"\tType:\t\t{self.Type}\n"
			f"\tCMD:\t\t\"{self.cmd}\"\n"
			f"\tPrivate:\t{self.private}\n"
			f"\tData:\t\t{self.datafiles}\n"
			f"\tPreview:\t{repr(self.preview[:32])}"
		)


# TODO: should make it so that files are only moved once everything is settled. Maybe even let the user create new files in /tmp, so that they can be deleted, and the horizon archive is not corrupted
def add_entry(db, path, move, directory):
	# TODO: need a mechanism that prints the file path in case of an error, the user can save it

	print(f"Adding entry {path}")

	# Get a name
	# TODO: Could do: don't ask for ui, make it part of cmdline cmd. If no path given, no name. If path given and exists do add it ... and if path does not exist then make new
	if path is None: filename = input("Name: ").strip().replace(" ", "_")
	else:
		if not os.path.exists(path): raise FileNotFoundError(f"Provided path does not exist: \"{path}\"")
		filename = os.path.basename(path)
		ui = input("Filename (default is provided name, space replaced by underscore): ")
		if len(ui): filename = ui
		filename.strip().replace(" ", "_")
	
	name, ext = os.path.splitext(filename)


	# Generate new UID
	fingerprint = get_pubkey(gpg, pubkey)["fingerprint"]
	prefix = (name + "_" if len(name) else "") + fingerprint

	# Generate a new path for within the horizon archive
	num_bits = 4*4
	max_int = 2**num_bits
	start = random.randint(0, max_int-1)
	for i in range(max_int):
		r = (start + i) % max_int
		uid = prefix + ("%0.4x" % r) + ext
		new_path = os.path.join(horizon_archive, uid)
		if not os.path.exists(new_path): break
	if i == max_int-1: raise Exception("Could not find a non-existing file name for the horizon archive, this should not happen!?")


	# Create file or directory
	if not directory and (path is None or os.path.isfile(path)): # is file?
		# Is a file
		cmd, entrytype, ext = interpret_mime(filename)
		if path is None: subprocess.run([cmd, new_path])
	else:
		# Is a directory
		cmd, entrytype, ext = "cd", "unknown", ""
		if directory: os.makedirs(new_path)


	# 'path' exists (checked at beginning of this func),
	# so can move if required. 'new_path' is valid because of the above.
	# If 'move' is not true, but path is provided, create a symlink (also know that path exists)
	if move:               shutil.move(path, new_path)
	elif path is not None: os.symlink(path, new_path)


	# Get code/text/title
	title = ""
	code = ""
	text = ""
	if   entrytype == "code":
		code = read_text_file(new_path)
		title = name
	elif entrytype == "text":
		if ext == "pdf":
			title, text = pdf2text(new_path)
			code = "TODO read tex files if there" # TODO: check for tex, maybe add option for this
		elif ext == "txt":
			text = read_text_file(new_path)
			title = get_title_from_text(text)
		else:
			print(f"Warning: text file extension not recognised, dunno what to do with it ({ext})")
	elif entrytype == "data":
		print("Sorry not implemented for data files yet")


	# Get info for database
	author = pubkey["uids"][0].lower() # TODO: why is uids a list? and why uidS and not uid
	institution = ""
	abstract = ""
	keywords = ""
	contributors = ""

	# Add to database
	add_document(
		db,
		uid,
		filename,
		ext,
		entrytype,
		text,
		code,
		title,
		author,
		institution,
		abstract,
		keywords,
		contributors
	)

	# Create entry for meta info
	preview = ""
	if   entrytype == "text": preview = text
	elif entrytype == "code": preview = code
	entry = Entry(uid, title, entrytype, cmd, preview=preview)

	write_yaml(os.path.join(horizon_meta, uid) + ".yml", entry)

	return


def delete_entry(db, uid):
	#try:
	#	db.delete_document(1)
	#except xapian.DatabaseError as e:
	#	print("error:", e)
	#finally:
	#	db.close()
	#return
	print(f"Deleting {uid}")
	return


def open_entry(uid):
	entry = meta[uid]
	filename = os.path.join(uid, entry.readme) if len(entry.readme) else uid
	subprocess.run([entry.cmd, os.path.join(horizon_archive, filename)])
	# Check if need to update database
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

	while True:
		terminal_menu = stm.TerminalMenu(
			[
				#f"[{get_alphabet(i)}] " +
				meta[uid].title +
				"|" +
				(uid if len(meta[uid].preview) else "")
				for i, uid in enumerate(entries)
			],
			accept_keys=("enter", "backspace", "tab"),
			preview_command=lambda uid: (f"\033[33m{uid}\033[0m", meta[uid].preview),
			preview_size=0.4,
			preview_title="Preview"
		)
		selection = terminal_menu.show()

		if selection is None: return

		key = terminal_menu.chosen_accept_key
		uid = entries[selection]
		if key == "tab":
			cd_to_entry(uid)
			break
		else: 
			open_entry(uid)
			if   key == "enter":     break
			elif key == "backspace": continue

	return



# Parse cmdline args
parser = argparse.ArgumentParser(description="Expand yours")

subparsers = parser.add_subparsers(dest="cmd", metavar="COMMAND", required=True)

add_parser = subparsers.add_parser("add", help="Expands your horizon")
add_parser_group = add_parser.add_mutually_exclusive_group()
add_parser_group.add_argument("path", metavar="PATH", nargs="?", help="Optional path to existing file or folder")
add_parser_group.add_argument("--dir", action="store_true", help="Create a directory not a file")
add_parser.add_argument("--move", action="store_true", help="Move file to location managed by horizon")

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
if hasattr(args, "path"):
	if args.path is not None: args.path = os.path.abspath(args.path)
	elif args.move: raise Exception("Path not provided for option --move")
horizon_root = os.path.dirname(__file__)
os.chdir(horizon_root)
# Note: horizon_root might lie somewhere else, but for now it is kept simple,
# in general the devs should use os.path.join(horizon_root, "...")

# Check archive folder
horizon_archive = os.path.join(horizon_root, "archive")
horizon_meta    = os.path.join(horizon_root, "meta")
if not os.path.exists(horizon_archive): os.makedirs(horizon_archive)
if not os.path.exists(horizon_meta):    os.makedirs(horizon_meta)

# Database
db = open_database("db")

# Metadata
meta = {}
for f in os.listdir(horizon_meta):
	meta[os.path.splitext(f)[0]] = read_yaml(os.path.join(horizon_meta, f), Entry)

# Public key
gpg = open_gpg()
PUBKEY = "Felix" # TODO, how? need horizon config
pubkey = get_pubkey(gpg, PUBKEY)

# Execute commands
if   args.cmd == "add":    add_entry(db, args.path, args.move, args.dir)
elif args.cmd == "delete": delete_entry(db, args.entries)
elif args.cmd == "find":   find_entries(db, args.query)
elif args.cmd == "open":   open_entry(args.entry)

# Clean up
db.close()

