import yaml

def write_yaml(filename, obj):
	with open(filename, "w") as f:
		yaml.dump(vars(obj), f)

def read_yaml(filename, obj_class):
	with open(filename, "r") as f:
		obj_dict = yaml.safe_load(f)
	obj = obj_class(**obj_dict)
	return obj

