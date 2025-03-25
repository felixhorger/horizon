import os
import yaml
import hashlib


def write_yaml(filename, obj):
	with open(filename, "w") as f:
		yaml.dump(vars(obj), f)

def read_yaml(filename, obj_class):
	with open(filename, "r") as f:
		obj_dict = yaml.safe_load(f)
	obj = obj_class(**obj_dict)
	return obj


def md5sum(path):
	hash_md5 = hashlib.md5()
	f = open(path, "rb")
	for chunk in iter(lambda: f.read(4096), b""): hash_md5.update(chunk)
	f.close()
	return hash_md5.hexdigest()

def get_filestats(path):
	d = {}
	d["mtime"] = os.path.getmtime(path)
	d["size"] = os.path.getsize(path)
	d["md5"] = md5sum(path)
	return d

def file_did_not_change(a, b):
	if a["mtime"] == b["mtime"]: return True
	if a["size"] == b["size"] and a["md5"] == b["md5"]: return True
	return False

