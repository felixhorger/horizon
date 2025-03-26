import os
import subprocess
import mimetypes

# TODO: make this proper with config file
mimetypes.add_type("text/x-julia", ".jl")


def interpret_mime(filename): # Only takes files
	if os.path.isdir(filename): raise Exception("Path to directory was provided but need path to a file")

	# Get file extension
	_, ext = os.path.splitext(filename)
	if len(ext): ext = ext[1:].lower()

	# Get MIME info
	if os.path.isfile(filename):
		result = subprocess.run(["file", "-bi", filename], capture_output=True, text=True, check=True)
		mime, encoding = result.stdout.split("; charset=")
		isbinary = True if encoding == "binary" else False
	else:
		if len(ext) == 0: return "vim", "vim", "text", ext
		mime = mimetypes.guess_type(filename, strict=False)[0]
		cmd = f"echo Don't know how to open (MIME {mime}):"
		if mime is None: return cmd, cmd, "data", ext
		isbinary = False

	category, subtype = mime.split("/")

	# Infer entrytype and cmd
	if category == "text":
		edit_cmd = "vim"
		view_cmd = "vim"
		if subtype == "plain":
			if len(ext) == 0 or ext == "txt": entrytype = "text"
			else:                             entrytype = "code"
		elif subtype in ("csv",): entrytype = "data"
		else:                     entrytype = "code"
	elif category == "application":
		if subtype == "pdf":
			edit_cmd = "echo No command specified to edit this file:"
			view_cmd = "evince"
			entrytype = "text"
		elif subtype == "csv" and not isbinary:
			edit_cmd = "vim"
			view_cmd = "vim"
			entrytype = "data"
		else:
			if isbinary:
				edit_cmd = "echo No command specified to edit this file:"
				view_cmd = "echo No command specified to view this file:"
				entrytype = "data"
			else:
				edit_cmd = "vim"
				view_cmd = "vim"
				entrytype = "code"

	return edit_cmd, view_cmd, entrytype, ext


def read_text_file(path):
	with open(path, "r") as f:
		text = f.read()
	return text

def get_title_from_text(text):
	# Find first non-empty line
	i = 0
	l = ""
	lines = text.splitlines() # TODO: ouch performance, better to jump from one \n to the next
	while i < len(lines) and len(l) == 0:
		l = lines[i].strip()
		i += 1
	return l


#def get_alphabet(i):
#	assert(i >= 0)
#	assert(i < 26)
#	return chr(97+i)
