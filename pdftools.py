import fitz

def pdf2text(path):
	with fitz.open(path) as doc:
		text = ""
		for page in doc: text += page.get_text() + " "
		text = text[:-1] 
		title = doc.metadata["title"]
	return title, text

# Maybe useful
#def sanitize(filename):
#    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
#    return "".join([c for c in filename if c in valid_chars])
