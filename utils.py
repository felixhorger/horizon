
def get_title_from_text(text):
	# Find first non-empty line
	i = 0
	l = ""
	lines = text.splitlines() # TODO: ouch performance, better to jump from one \n to the next
	while i < len(lines) and len(l) == 0:
		l = lines[i].strip()
		i += 1
	if i == len(lines): title = ""
	else:               title = l

	return title

