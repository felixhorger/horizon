import os
import shutil
import subprocess
import shlex
import simple_term_menu as stm
import argparse
import random

from auth import *
from database import *
from pdftools import *
from utils import *
from meta import *


# Multiple instances of horizon can be run in parallel, but it is assumed that the user interacts sequentially,
# i.e. multiple updates to the database are not requested simultaneously


# TODO: most important is triggering an update to the database entry if file is changed and offering mechanism to do it manually


# TODO: for text based files, the preview does not need to be stored, can just be `head ...`, how to implement this?

# TODO: the preview of text files should not be saved in yml, it can be read from file on the fly

# TODO: add command to update database entry, maybe just a key in TermMenu


# TODO: for updating code repos, which are stored outside of horizon, and have a different name, it would be good to have a list of real paths in horizon, so that the user can do `horizon update .` and it knows which uid this has
# TODO: yaml file with config for e.g. gnupg path or pubkey name and editor/viewer etc
# TODO: add value private/public (and make previously published papers private)
# TODO: command to open the last open entry for editing/cd

# TODO: is a good strategy to have good defaults, and ask at the end if that's ok?
# Or just add and the user can edit if necessary?

# TODO: it is possible to enable syntax highlighting in preview of TermMenu

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

# Markdown: f=`mktemp` && pandoc test.md --mathml > $f && firefox $f && rm $f

# TODO: automatic determination of entry fields can overwrite user input, for example title in text files.
# No idea how to deal with it, either improve the meta-update function, and only present those fields the user can
# change, and maybe also add a "protected" field which prevents automatic overwriting

# TODO: program status bar to show errors like "command not specificied"

# TODO: generate text/code from preview file



#1) view: ENTER
#2) delete: BACKSPACE?
#3) cd: SPACE
#4) edit meta: TAB


class Entry:
	def __init__(
		self,
		title,
		Type, # uppercase not to overwrite type()
		filestats,
		cmd="echo No command to view entry provided",
		readme=None,
		private=True,
		codefiles=[],
		preview=None,
		name = "",
		ext = "",
		author = "",
		institution = "",
		abstract = "",
		keywords = "",
		contributors = ""
	):
		self.title = title
		self.Type = Type
		self.filestats = filestats
		self.cmd = cmd
		self.readme = readme
		self.private = private
		self.codefiles = codefiles
		self.preview = preview
		self.name = name
		self.ext = ext
		self.author = author
		self.institution = institution
		self.abstract = abstract
		self.keywords = keywords
		self.contributors = contributors
		return

	def __repr__(self):
		# TODO: DONT DELETE THIS, CAN BE USED TO INITIALISE vim if an entry is to be edited!
		return (
			f"Horizon Entry:\n"
			f"\tTitle:\t\t\"{self.title}\"\n"
			f"\tType:\t\t{self.Type}\n"
			f"\tCMD:\t\t\"{self.cmd}\"\n"
			f"\tPrivate:\t{self.private}\n"
			f"\tData:\t\t{self.datafiles}\n"
			f"\tPreview:\t{None if self.preview is None else repr(self.preview[:32])}\n",
			f"\tStats:\t{self.filestats}\n\n"
			# TODO the rest
		)


PUBKEY = "Felix" # TODO, how? need horizon config

# TODO: should make it so that files are only moved once everything is settled. Maybe even let the user create new files in /tmp, so that they can be deleted, and the horizon archive is not corrupted
# TODO: needs refactoring, quite long
def add_entry(path, move, directory):
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
	gpg = open_gpg()
	pubkey = get_pubkey(gpg, PUBKEY)
	fingerprint = pubkey["fingerprint"]
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
		if path is None:
			subprocess.run([*shlex.split(cmd), new_path])
			if not os.path.isfile(new_path): return
	else:
		# Is a directory
		cmd, entrytype, ext = "echo No command specified for directory: ", "text", ""
		if directory: os.makedirs(new_path)


	# 'path' exists (checked at beginning of this func),
	# so can move if required. 'new_path' is valid because of the above.
	# If 'move' is not true, but path is provided, create a symlink (also know that path exists)
	if move: shutil.move(path, new_path)
	elif path is not None:
		os.symlink(path, new_path)
		new_path = path # Need to do this for the file stats, the symlink has its own stats


	# Get code/text/title
	title = ""
	code = ""
	text = ""
	if os.path.isdir(new_path):
		if path is not None: print("TODO: Not implemented, need to ask user what file readme is etc, entry still added")
		text = ""
		title = name
		code = ""
	elif entrytype == "code":
		code = read_text_file(new_path)
		title = name
	elif entrytype == "text":
		if ext == "pdf":
			title, text = pdf2text(new_path)
			code = "TODO read tex files if there" # TODO: check for tex, maybe add option for this
		elif ext == "txt" or len(ext) == 0:
			text = read_text_file(new_path)
			title = get_title_from_text(text)
		else:
			print(f"Warning: text file extension not recognised, dunno what to do with it ({ext})")
	elif entrytype == "data":
		print("Sorry not implemented for data files yet")


	# Get info for database
	author = pubkey["uids"][0] # TODO: why is uids a list? and why uidS and not uid
	institution = ""
	abstract = ""
	keywords = ""
	contributors = ""

	# TODO: make dict of all the meta data, to make the below two function calls prettier
	# TODO: think about removing the entry type, and just using a dictionary,
	# could be nice to keep class bc of defaults and repr for printing?

	# Add to database
	db = open_database("db")
	add_document(
		db,
		uid,
		name,
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
	db.close()

	# Create entry for meta info
	preview = None
	readme = None
	private = True
	codefiles = []
	entry = Entry(
		title,
		entrytype,
		get_filestats(new_path),
		cmd,
		readme,
		private,
		codefiles,
		preview,
		name,
		ext,
		author,
		institution,
		abstract,
		keywords,
		contributors
	)

	write_yaml(os.path.join(horizon_meta, uid) + ".yml", entry)

	return


def update_entry(uid, entry):

	path = os.path.realpath(os.path.join(horizon_archive, uid)) # Resolves symlinks

	if os.path.isdir(path):

		filename = entry.readme
		if filename is None: raise Exception(f"No readme provided for directory {uid}")
		_, ext = os.path.splitext(filename)
		ext = ext.lower() # TODO: is this done everywhere?
		if len(ext): ext = ext[1:]
		filename = os.path.join(path, filename)

		if entry.Type == "code":
			code = read_text_file(filename)
			text = ""
		elif entry.Type == "text":
			if ext == "pdf":
				entry.title, text = pdf2text(filename)
				code = "TODO read tex files if there" # TODO: check for tex, maybe add option for this
			elif ext == "txt" or len(ext) == 0:
				text = read_text_file(filename)
				entry.title = get_title_from_text(text)
				code = ""
			elif ext == "html":
				html = read_text_file(filename)
				text = html2text(html)
				entry.title = get_title_from_text(text)
				code = ""
			elif ext == "md":
				code = read_text_file(filename)
				text = code
			else:
				raise Exception(f"Not implemented, unknown file extension {ext}")
		else:
			# TODO: should not happen -> error
			text = ""
			code = ""

	else:
		is_text = entry.Type == "text"
		is_code = entry.Type == "code"
		text = ""
		code = ""
		if is_text or is_code:
			filecontent = read_text_file(path)
			if is_text:
				text = filecontent
				entry.title = get_title_from_text(text)
			elif is_code: code = filecontent
		else:
			raise Exception("Not implemented, need to do for PDF at least")
		

	db = open_database("db") # TODO: think about putting this in add_document? less modular, but if it's always used like this it'll make sense to put together
	add_document(
		db,
		uid,
		entry.name,
		entry.ext,
		entry.Type,
		text,
		code,
		entry.title,
		entry.author,
		entry.institution,
		entry.abstract,
		entry.keywords,
		entry.contributors
	)
	db.close()

	write_yaml(os.path.join(horizon_meta, uid) + ".yml", entry)

	return


def delete_entry(uid):
	#try:
	#	db.delete_document(1)
	#except xapian.DatabaseError as e:
	#	print("error:", e)
	#finally:
	#	db.close()
	#return
	print(f"Deleting {uid}")
	return


def edit_entry_meta(uid):

	yml = os.path.join(horizon_meta, uid + ".yml")
	subprocess.run(["vim", yml])
	# TODO: check yaml for consistency
	entry = read_yaml(yml, Entry)

	update_entry(uid, entry)

	return


def open_entry(uid):

	meta = read_meta(horizon_meta, Entry)

	entry = meta[uid] # TODO: also only read the specific uid entry

	if len(entry.cmd) == 0: raise Exception("No command to view entry was provided")

	path = os.path.realpath(os.path.join(horizon_archive, uid))
	if os.path.isdir(path):
		if entry.readme is None: raise Exception("Entry is a directory but no readme file was provided")
		path = os.path.join(path, entry.readme)
	subprocess.run([*shlex.split(entry.cmd), path])

	# Check if need to update database
	new_filestats = get_filestats(path)
	if file_did_not_change(entry.filestats, new_filestats): return
	entry.filestats = new_filestats

	update_entry(uid, entry)

	return


def cd_to_entry(uid):
	path = os.path.join(horizon_archive, uid)

	if os.path.islink(path):
		path = os.path.realpath(path)
		if os.path.isfile(path):
			os.chdir(os.path.dirname(path))
		elif not os.path.exists(path): raise Exception(f"File not found {path}")
	elif os.path.isfile(path):
		return

	if os.path.isdir(path):
		os.chdir(path)

	subprocess.run("bash")

	os.chdir(horizon_root)

	# Check if need to update database
	meta = read_meta(horizon_meta, Entry)
	entry = meta[uid] # TODO: also only read the specific uid entry
	if entry.readme is not None: path = os.path.join(path, entry.readme)
	new_filestats = get_filestats(path)
	if file_did_not_change(entry.filestats, new_filestats): return
	entry.filestats = new_filestats

	update_entry(uid, entry)

	return


def find_entries(query):
	if query is None:
		print("Listing the whole database")
		return
	
	db = open_database("db")
	entries = search(db, " ".join(query), offset=0, pagesize=10)
	db.close()
	if len(entries) == 0: return


	selection = 0
	while True:

		meta = read_meta(horizon_meta, Entry) # TODO: only read the required ones

		terminal_menu = stm.TerminalMenu(
			[
				# TODO: improve this by creating a list beforehand, same for entries above
				#f"[{get_alphabet(i)}] " + # TODO: this could be used for shortcuts
				(meta[uid].title if len(meta[uid].title) else "Unknown") + " (" +
				" ".join(meta[uid].author.split()[:2]) + ") " +
				("[dir]" if os.path.isdir(os.path.realpath(os.path.join(horizon_archive, uid))) else "[file]") +
				"|" + uid
				for i, uid in enumerate(entries)
			],
			cursor_index=selection,
			accept_keys=("enter", "space", "backspace", "tab"),
			title=f"Search results for \"{''.join(query)}\"",
			title_style=("fg_green", "underline", "italics"),
			status_bar="", # TODO: Could be used to display some other info, can be function with selection as arg
			status_bar_style=("bg_black",),
			#status_bar_below_preview=False,
			preview_command=lambda uid: (
				(
					os.path.realpath(os.path.join(horizon_archive, uid))
					if os.path.islink(os.path.join(horizon_archive, uid))
					else uid
				),
				get_preview(os.path.realpath(os.path.join(horizon_archive, uid)), meta[uid])
			),
			preview_title_style=("fg_yellow",),
			#preview_size=0.5, # Not needed, preview uses the available space
			#clear_screen=True
		)
		selection = terminal_menu.show()

		if selection is None: return

		key = terminal_menu.chosen_accept_key
		uid = entries[selection]
		if key == "enter": # view
			open_entry(uid)
		elif key == "backspace": # edit
			print(f"deleting {uid}, but not implemented")
		elif key == "tab": # meta
			edit_entry_meta(uid)
		elif key == "space": # cd
			cd_to_entry(uid)

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

# Execute commands
if   args.cmd == "add":    add_entry(args.path, args.move, args.dir)
elif args.cmd == "delete": delete_entry(args.entries)
elif args.cmd == "find":   find_entries(args.query)
elif args.cmd == "open":   open_entry(args.entry)

