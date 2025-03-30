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
		cmd = None
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
				cmd = None
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

# Returns title, text, code
def get_title_text_code(path, name, entrytype, readme):

	if os.path.isdir(path):

		filename = readme

		code = ""
		if entrytype == "code": code = "" # TODO: read codefiles

		# Is there a readme with text in this dir?
		if filename is None:
			# No
			title = name
			text = ""
			return title, text, code

		# Yes, there is a readme, get contents based on file extension
		_, ext = os.path.splitext(filename)
		ext = ext.lower() # TODO: is this done everywhere?
		if len(ext): ext = ext[1:]
		filename = os.path.join(path, filename)

		if ext == "pdf": # extension of readme file
			title, text = pdf2text(filename)
		elif ext == "txt" or len(ext) == 0:
			text = read_text_file(filename)
			title = get_title_from_text(text)
		elif ext == "html":
			html = read_text_file(filename)
			text = html2text(html)
			title = get_title_from_text(text)
		elif ext == "md":
			# Note: actually a markdown file should not be put as readme. Better is the rendered html
			text = read_text_file(filename)
			print("Warning: you should not put a markdown file as a readme, but the rendered html (e.g. with pandoc)")
		else:
			raise Exception(f"Not implemented, unknown file extension {ext}")

	elif os.path.isfile(path):

		is_text = entrytype == "text"
		is_code = entrytype == "code"
		text = ""
		code = ""
		title = "Unknown"
		if is_text or is_code:
			filecontent = read_text_file(path)
			if is_text:
				text = filecontent
				title = get_title_from_text(text)
			elif is_code: code = filecontent
		else:
			raise Exception("Not implemented, need to do for PDF at least")
	else:
		raise FileNotFoundError(f"Could not find entry's file {path}")

	return title, text, code

