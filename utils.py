import os
import subprocess
import mimetypes
import html2text as HTML2Text

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
		if len(ext) == 0: return "vim", "text", ext
		mime = mimetypes.guess_type(filename, strict=False)[0]
		cmd = f"echo Don't know how to open (MIME {mime}):"
		if mime is None: return cmd, "data", ext
		isbinary = False

	category, subtype = mime.split("/")

	# Infer entrytype and cmd
	if category == "text":
		cmd = "vim"
		if subtype == "plain":
			if len(ext) == 0 or ext == "txt": entrytype = "text"
			else:                             entrytype = "code"
		elif subtype in ("csv",): entrytype = "data"
		else:                     entrytype = "code"
	elif category == "application":
		if subtype == "pdf":
			cmd = "evince"
			entrytype = "text"
		elif subtype == "csv" and not isbinary:
			cmd = "vim"
			entrytype = "data"
		else:
			if isbinary:
				cmd = "echo No command specified to view this file:"
				entrytype = "data"
			else:
				cmd = "vim"
				entrytype = "code"

	return cmd, entrytype, ext


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

def html2text(html):
	h = HTML2Text.HTML2Text()
	h.ignore_links = True
	return h.handle(html)

def get_preview(path, entry):
	if entry.preview is not None: return entry.preview

	if os.path.isdir(path):
		if entry.readme is None: return "No preview provided for this directory, set the readme field"
		path = os.path.join(path, entry.readme)

	_, ext = os.path.splitext(path)
	ext = ext.lower()
	if len(ext): ext = ext[1:]

	# TODO: this code repeats three times in horizon.py ... should go into separate function
	if entry.Type == "code":
		preview = read_text_file(path)
	elif entry.Type == "text":
		if ext == "pdf":
			_, preview = pdf2text(path)
		elif ext == "txt" or len(ext) == 0:
			preview = read_text_file(path) # TODO: this might be slow for large files, but do they get so large?
		elif ext == "html":
			html = read_text_file(path)
			preview = html2text(html)
		elif ext == "md":
			preview = read_text_file(path)
		else:
			raise Exception(f"Not implemented, unknown file extension {ext}")
	else:
		# TODO: should not happen -> error
		preview = "Could not determine preview"

	return preview





