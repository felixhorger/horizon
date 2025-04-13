import xapian
import unicodedata

# Stemmer
def normalise_unicode(u):
	return unicodedata.normalize("NFKC", u)


def decode_bytes(s):
	return s.decode("utf-8")


def get_stemmer():
	stemmer = xapian.Stem("en")
	return stemmer

def get_termgenerator(stemmer):
	termgenerator = xapian.TermGenerator()
	termgenerator.set_stemmer(stemmer)
	return termgenerator


def open_database(path):
	try:
		db = xapian.WritableDatabase(path, xapian.DB_CREATE_OR_OPEN)
	except xapian.DatabaseError as e:
		raise Exception("Error creating/opening database:", e)
		return
	return db

def add_document(
		db,
		uid,
		filename,
		extension,
		entrytype,
		text,
		code,
		title,
		author,
		institution,
		abstract,
		keywords,
		contributors
):
	# TODO: order of args? or make dict?

	# Add to database
	doc = xapian.Document()
	termgenerator = get_termgenerator(get_stemmer())
	termgenerator.set_document(doc)
	# TODO: how costly is it to set this up? make it a global? or make it a global in horizon.py
	# TODO: on a similar note, could make the database global in here? bad practice?

	doc.set_data(uid)

	# Add entry type as value
	#doc.add_value(0, entrytype) # Need a match decider for this ... easier way? https://xapian.org/docs/bindings/python/examples.html
	# Also check out https://github.com/invisibleroads/invisibleroads-tutorials/blob/master/xapian-search-pylons.rst
	# Currently just make it a field
	termgenerator.index_text(entrytype, 1, "XT")

	# Add terms
	# Q: id (which is identification+pubkey+random+ext)
	# A: author (creator, can be used for matching the entry too)
	# B: abstract
	# E: extension (txt, pdf, python/C etc, ...)
	# G: institution of author
	# K: keywords
	# O: contributors? How to find these? or better from whom you got it
	# S: title

	termgenerator.index_text(normalise_unicode(author),       1, "A") # number is word frequency, i.e. a weight for match ranking? chatgpt...
	termgenerator.index_text(normalise_unicode(abstract),     1, "B")
	termgenerator.index_text(normalise_unicode(extension),     1, "E")
	termgenerator.index_text(normalise_unicode(filename),     1, "F")
	termgenerator.index_text(normalise_unicode(institution),  1, "G")
	termgenerator.index_text(normalise_unicode(keywords),     1, "K")
	termgenerator.index_text(normalise_unicode(contributors), 1, "O")
	termgenerator.index_text(normalise_unicode(title),        1, "S")

	# TODO: similar to author, it would be good not to stem this? Would be good to know what the overhead is of stemming
	# Otherwise I'm afraid I need to look into query parser/stemmer?
	if len(code): termgenerator.index_text(normalise_unicode(code), 1, "X")

	# Text for general search
	termgenerator.index_text(text)
	#termgenerator.increase_termpos()
	#terms = text.split()  # Split text into terms (just for illustration)
	#for term in terms:
	#	doc.add_term(term.lower())  # Add terms to make it searchable

	uid = u"Q" + uid
	doc.add_boolean_term(uid)

	# Replace doc
	try: db.replace_document(uid, doc)
	except xapian.DatabaseError as e:
		print(f"Error adding document to Xapian: {e}")
		db.close()

	return

def remove_document(db, uid):
	uid = u"Q" + uid

	if db.term_exists(uid):
		db.delete_document(uid)
	else:
		print(f"Warning: tried to delete document \"{uid}\" which was not present in the database")

	return


def search(db, querystring, offset=0, pagesize=10):
	# offset - defines starting point within result set
	# pagesize - defines number of records to retrieve

	#db = xapian.Database(dbpath)

	queryparser = xapian.QueryParser()
	queryparser.set_stemmer(get_stemmer())
	queryparser.set_stemming_strategy(queryparser.STEM_SOME)

	queryparser.add_prefix("uid", "Q")
	queryparser.add_prefix("author", "A")
	queryparser.add_prefix("abstract", "B")
	queryparser.add_prefix("extension", "E")
	queryparser.add_prefix("filename", "F")
	queryparser.add_prefix("institution", "G")
	queryparser.add_prefix("keywords", "K")
	queryparser.add_prefix("contributors", "O")
	queryparser.add_prefix("title", "S")
	queryparser.add_prefix("code", "X")
	queryparser.add_prefix("type", "XT")

	query = queryparser.parse_query(querystring) #, xapian.QueryParser.FLAG_WILDCARD)
	enquire = xapian.Enquire(db)
	enquire.set_query(query)

	matches = []
	for match in enquire.get_mset(offset, pagesize):
		#match.docid
		# TODO: all info that needs to be displayed here has to be saved in data ... otherwise crap
		path = decode_bytes(match.document.get_data())
		#print("{}: {} {}".format(match.rank + 1, path, "any title"))
		matches.append(path)

	if len(matches) == 0: print("Nothing found")

	# TODO: need to return list of horizon entries, not xapian matches
	return matches


# TODO: note on searching: if the first letter is uppercase, unstemmed words are searched!
# Custom matchdeciders
# Term prefixes can be converted to field names QueryParser, upper case letter in Xapian. There are some default prefixes too like author (A) and subject/title (S)
# Suggested to use xapian.TermGenerator and then xapian.QueryParser
# Suggested to add term with document identifier (my random string?), term prefix should be Q:
# Values (stored in slots) associated to documents can be used to sort docs, what would this be used for here? (suggested to use xapian.sortable_serialise() because values are stored in binary form, and need to make sure that this matches sorting)
# Deleted doc ids are not reused, so need to compact database occasionally, how?
# There is an and_maybe matching operator
# Matching can use values (slots)
# Matching "near" and "phrase"
# Match all
# Queries: https://getting-started-with-xapian.readthedocs.io/en/latest/concepts/search/queryparser.html
# Should try and parse PDF as well as possible, extracting author, title etc. as term fields, Maybe from bibtex? For horizon entries most of this information is available (e.g. author, think about title too)
# wildcard is available * for any number of characters trailing only? Need to enable in parser with flag. Can limit max wildcard expansions
# (There is partial search, while the user is entering their stuff)
# Need to enable search operators via parser flags, default is BOOL, Phrase, +-
# There is an option to design a custom weighting scheme for ranking results, based on values? Or can tell the searcher this to sort by value
# There are match sets, i.e. x <= match rank <= y (like google search pages)
# Common prefixes: https://xapian.org/docs/omega/termprefixes
# xapian-delve db for validating index
# xapian.Database.delete_document(idterm)
