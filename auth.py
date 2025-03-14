import getpass
import gnupg

def open_gpg(path="/home/" + getpass.getuser() + "/.gnupg"):
	user = getpass.getuser()
	gpg = gnupg.GPG(gnupghome=path)
	return gpg

def get_user():
	return getpass.getuser()

def get_pubkey(gpg, keyid):
	pubkeys = gpg.list_keys(keyid)
	if len(pubkeys) > 1: raise Exception(f"More than one key found for key ID {keyid}")
	return pubkeys[0]

