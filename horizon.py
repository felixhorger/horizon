import argparse
import simple_term_menu as stm


def add_entry(path):
	print(f"Adding entry {path}")
	return

def delete_entries(entries):
	for entry in entries:
		print(f"Deleting {entry}")
	return

def open_entries(entries):
	for entry in entries:
		print(f"Opening {entry}")
	return

def cd_to_entry(entry):
	print(f"cd to entry {entry}")
	return

def search_database(query):
    entries = ["entry 1", "entry 2", "entry 3"]
    return entries

def find_entries(query):
	if query is None:
		print("Listing the whole database")
		return
	
	entries = search_database(query)

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
	if   key == "enter" or len(selection) > 1: open_entries([entries[i] for i in selection])
	elif key == "backspace":                   cd_to_entry(entries[selection[0]])



# Parse cmdline args
parser = argparse.ArgumentParser(description="Expand yours")

subparsers = parser.add_subparsers(dest="cmd", metavar="COMMAND", required=True)

add_parser = subparsers.add_parser("add", help="Expands your horizon")
add_parser.add_argument("path", metavar="PATH", help="Optional path to file or folder")

delete_parser = subparsers.add_parser("delete", help="Delete entry by ID")
delete_parser.add_argument("entries", metavar="ID", nargs="+", help="The item to delete")
delete_parser.add_argument("--keepfiles", action="store_true", help="Only delete database entry, not files")
delete_parser.add_argument("--force", action="store_true", help="Do not ask")

find_parser = subparsers.add_parser("find", help="Search for entries")
find_parser.add_argument("query", metavar="QUERY", nargs="*", help="Words to search for")

open_parser = subparsers.add_parser("open", help="Open entry by ID")
open_parser.add_argument(dest="entry", metavar="ID", nargs="+", help="Entries to open")

args = parser.parse_args()
print(args)


# Run horizon
if   args.cmd == "add":    add_entry(args.path)
elif args.cmd == "delete": delete_entries(args.entries)
elif args.cmd == "find":   find_entries(args.query)
elif args.cmd == "open":   open_entries(args.entry)

