### THIS MODULE RENDERS THE TEMPLATES FROM THE JINJA2 FILES
### AND PACKAGES THEM INTO A LIST OF LISTS. IT ONLY LOOKS AT THE 
### SELECTED INDEXES (INIITIALIZE.ELEMENT) OF THE NODE_OBJECT. 
### THE CONFIGURATIONS ARE STORED IN THE GLOBAL VARIABLE CALL 
### INITIALIZE.CONFIGURATION.

from jinja2 import Environment, FileSystemLoader
from ciscoconfparse import CiscoConfParse
from collections import Counter
from multithread import multithread_engine
from get_property import get_directory
from get_property import get_template
from get_property import get_syntax
import re
import initialize

def auditdiff_engine(template_list,node_object,auditcreeper,output,remediation):

	redirect = [] 
	command = ''

	### PUSH_CONFIGS IS A LIST OF THE FINAL CONFIGS TO BE PUSHED
#	push_configs = []

	### INDEX_POSITION IS THE INDEX OF ALL THE MATCHED FILTER_CONFIG AGAINST THE BACKUP_CONFIGS. THE INDEX IS COMING FROM THE BACKUP_CONFIG
	index_position = 0

	### NODE_INDEX KEEPS TRACK OF THE INDEX IN INITIALIZE.NTW_DEVICE. IF REMEDIATION IS NOT REQUIRED (CONFIGS MATCHES TEMPLATE), THEN THE NODE IS POPPED OFF
	### INITIALIZE.NTW_DEVICE AND NOTHING IS CHANGED ON THAT DEVICE
	node_index = 0 

	### AUDIT_FILTER_RE IS THE REGULAR EXPRESSION TO FILTER OUT THE AUDIT FILTER IN EVERY TEMPLATE
	AUDIT_FILTER_RE = r"\[.*\]"

	### TEMPLATE_LIST_COPY TAKE A COPY OF THE CURRENT TEMPLATE_LIST
	template_list_original = template_list[:]
	template_list_copy = template_list

	if(auditcreeper):
		template_list = template_list_copy[0]

	### THIS SECTION OF CODE WILL GATHER ALL RENDERED CONFIGS FIRST AS IT'S REQUIRED FOR ALL PLATFORMS (CISCO & JUNIPER)
	### JUNIPER DOES NOT REQUIRE BACKUP-CONFIGS IN ORDER TO BE DIFFED SO INSTEAD IT WILL JUST PUSH (PUSH_CFGS) THE TEMPLATE AND PERFORM THE DIFF ON THE DEVICE ITSELF.
	### CISCO WILL REQUIRE BACKUP-CONFIGS (GET_CONFIG)
	for index in initialize.element:

		for template in template_list:

			### THIS SECTION OF CODE WILL PROCESS THE TEMPLATE AND OUTPUT TO A *.CONF FILE
			directory = get_directory(node_object[index]['platform'],node_object[index]['os'],node_object[index]['type'])
			env = Environment(loader=FileSystemLoader("{}".format(directory)))
			baseline = env.get_template(template)
			f = open("/rendered-configs/{} - {}".format(node_object[index]['hostname'],template.strip('jinja2')) + ".conf", "w") 

			### GENERATING TEMPLATE BASED ON NODE OBJECT
			config = baseline.render(nodes = node_object[index])

			f.write(config) 
			f.close 

		template_list = get_template(template_list_copy)

		if(node_object[index]['platform'] == 'cisco'):
			redirect.append('get_config')
		elif(node_object[index]['platform'] == 'juniper'):
			redirect.append('push_cfgs')

	print("[+] [COMPUTING DIFF. STANDBY...]")
	multithread_engine(initialize.ntw_device,redirect,command)
	
	### RESETING TEMPLATE_LIST TO ORIGINAL LIST

	###UN-COMMENT THE BELOW PRINT STATEMENT FOR DEBUGING PURPOSES
#	print("ORIGINAL_LIST: {}".format(template_list_original))
	template_list = template_list_original

	###UN-COMMENT THE BELOW PRINT STATEMENT FOR DEBUGING PURPOSES
#	print("TEMPLATE_LIST: {}".format(template_list))

	### REINITIALIZING TEMPLATE_LIST TO THE ORIGINAL LIST OF TEMPLATES
	if(auditcreeper):
		template_list = template_list_original[0]

	### THIS FOR LOOP WILL LOOP THROUGH ALL THE MATCHED ELEMENTS FROM THE USER SEARCH AND AUDIT ON SPECIFIC TEMPLATE OR IF NO ARGUMENT IS GIVEN, ALL TEMPLATES
	
	for index in initialize.element:

		### NODE_CONFIG IS THE FINALIZED CONFIG TO PUSH TO THE NODE FOR REMEDIATION
		node_configs = []
		ntw_device_pop = True 
		### TEMPLATE_NAME IS SET TO TRUE IN ORDER TO PRINT OUT THE TEMPLATE HEADING WHEN RECURSING
		template_name = True

		if(not remediation):
			print("Only in the device: -")
			print("Only in the generated config: +")

			print ("{}".format(node_object[index]['hostname']))

		###UN-COMMENT THE BELOW PRINT STATEMENT FOR DEBUGING PURPOSES
#		print("TEMPLATE_LIST: {}".format(template_list))

		### THIS WILL LOOP THROUGH ALL THE TEMPLATES SPECIFIED FOR THE PARTICULAR HOST IN NODES.YAML
		for template in template_list:

			### INDEX_LIST IS A LIST OF ALL THE POSITIONS COLLECTED FROM INDEX_POSITION VARIABLE
			index_list = []

			### FILTER_CONFIG IS A LIST OF COLLECTION OF ALL THE AUDIT FILTERS THAT MATCHED THE LINES IN BACKUP_CONFIG. THESE ENTRIES DO NOT CONTAIN DEPTHS/DEEP CONFIGS
			filtered_config = []

			### FILTERED_BACKUP_CONFIG IS THE FINAL LIST OF ALL THE AUDIT FILTERS THAT MATCHES THE LINES IN BACKUP_CONFIG. THESE ENTRIES INCLUDE DEPTHS/DEEP CONFIGS
			filtered_backup_config = []

#			### THIS SECTION OF CODE WILL PROCESS THE TEMPLATE AND OUTPUT TO A *.CONF FILE
#			directory = get_directory(node_object[index]['platform'],node_object[index]['os'],node_object[index]['type'])
#			env = Environment(loader=FileSystemLoader("{}".format(directory)))
#			baseline = env.get_template(template)
#			f = open("/rendered-configs/{}".format(node_object[index]['hostname']) + ".conf", "w") 
#
#			### GENERATING TEMPLATE BASED ON NODE OBJECT
#			config = baseline.render(nodes = node_object[index])
#
#			f.write(config) 
#			f.close 

			### THIS SECTION OF CODE WILL OPEN THE RENDERED-CONFIG *.CONF FILE AND STORE IN RENDERED_CONFIG AS A LIST
			f = open("/rendered-configs/{} - {}".format(node_object[index]['hostname'],template.strip('jinja2')) + ".conf", "r")
			init_config = f.readlines()
			### RENDERED_CONFIG IS A LIST OF ALL THE CONFIGS THAT WAS RENDERED FROM THE TEMPLATES (SOURCE OF TRUTH)
			rendered_config = []

			for config_line in init_config:
				strip_config = config_line.strip('\n')
				### THIS WILL REMOVE ANY LINES THAT ARE EMPTY OR HAS A '!' MARK
				if(strip_config == '' or strip_config == "!"):
					continue	
				else:
					rendered_config.append(strip_config)	

			###UN-COMMENT THE BELOW PRINT STATEMENT FOR DEBUGING PURPOSES
#			print ("RENDERED CONFIG: {}".format(rendered_config))
			
			### THIS SECTION OF CODE WILL OPEN BACKUP-CONFIG *.CONF FILE AND STORE IN BACKUP_CONFIG AS A LIST
			f = open("/backup-configs/{}".format(node_object[index]['hostname']) + ".conf", "r")
			init_config = f.readlines()
			backup_config = []

			for config_line in init_config:
				strip_config = config_line.strip('\n')
				backup_config.append(strip_config)	

			###UN-COMMENT THE BELOW PRINT STATEMENT FOR DEBUGING PURPOSES
#			print ("BACKUP CONFIG: {}".format(backup_config))
			
			### THIS WILL OPEN THE JINJA2 TEMPLATE AND PARSE OUT THE AUDIT_FILTER SECTION VIA REGULAR EXPRESSION
			directory = get_directory(node_object[index]['platform'],node_object[index]['os'],node_object[index]['type'])
			f = open("{}".format(directory) + template, "r")
			parse_audit = f.readline()
			audit_filter = eval(re.findall(AUDIT_FILTER_RE, parse_audit)[0])

			###UN-COMMENT THE BELOW PRINT STATEMENT FOR DEBUGING PURPOSES
#			print ("AUDIT_FILTER: {}".format(audit_filter))

			### FILTER OUT THE BACKUP_CONFIGS WITH THE AUDIT_FILTER
			### THIS WILL TAKE EACH ELEMENT FROM THE AUDIT_FILTER LIST AND SEARCH FOR THE MATCHED LINES IN BACKUP_CONFIG
			### PARSING THE BACKUP CONFIGS
			parse_backup_configs = CiscoConfParse("/backup-configs/{}".format(node_object[index]['hostname']) + ".conf", syntax=get_syntax(node_object,index))
#			print "SYNTAX: {}".format(get_syntax(node_object,index))

			### MATCHED ENTRIES ARE THEN APPENDED TO FILTER_BACKUP_CONFIG VARIABLE AS A LIST
			### FUNCTION CALL TO PARSE_AUDIT_FILTER() TO FIND ALL THE PARENT/CHILD
			filtered_backup_config = parse_audit_filter(
					node_object,
					index,
					parse_backup_configs,
					audit_filter
			)

			### UN-COMMENT THE BELOW PRINT STATEMENT FOR DEBUGING PURPOSES
#			print("FILTERED BACKUP CONFIG: {}".format(filtered_backup_config))		

			### SYNC_DIFF WILL DIFF OUT THE FILTERED_BACKUP_COFNIG FROM THE RENDERED CONFIG AND STORE WHATEVER COMMANDS THAT
			### COMMANDS THAT NEED TO BE ADDED/REMOVE IN PUSH_CONFIGS VARIABLE
			parse = CiscoConfParse(filtered_backup_config)
			push_configs = parse.sync_diff(
					rendered_config,
					"",
					ignore_order=True, 
					remove_lines=True, 
					debug=False
			)

			if(len(push_configs) == 0):
				if(output):
					print("{}{} (none)".format(directory,template))
					print
			else:
			
				### THIS WILL JUST PRINT THE HEADING OF THE TEMPLATE NAME SO YOU KNOW WHAT IS BEING CHANGED UNDER WHICH TEMPLATE
				if(output):
					print("{}{}".format(directory,template))

				for line in push_configs:
					search = parse_backup_configs.find_objects(r"^{}".format(line))
					if('no' in line):
						line = re.sub("no","",line)
						if(not remediation):
							print("-{}".format(line))
					elif(len(search) == 0):
						if(not remediation):
							print("+ {}".format(line))
					elif(len(search) > 1):
						if(not remediation):
							print("+ {}".format(line))
					else:
						if(not remediation):
							print("  {}".format(line))
					
				print("")
				###UN-COMMENT THE BELOW PRINT STATEMENT FOR DEBUGING PURPOSES
#				print("PUSH_CONFIGS: {}".format(push_configs))
				if(remediation):

					### THIS STEP WILL APPEND REMEDIATION CONFIGS FROM TEMPLATE (EXPECTED RESULTS)
					for config in push_configs:
						node_configs.append(config)
						ntw_device_pop = False
	
					### INITIALIZE.COFIGURATION APPENDS ALL THE REMEDIATED CONFIGS AND PREPARES IT FOR PUSH
					if(auditcreeper == False):
						initialize.configuration.append(node_configs)
					node_index = node_index + 1

		if(auditcreeper):
			initialize.configuration.append(node_configs)
			if(ntw_device_pop == True):
				initialize.ntw_device.pop(node_index)
				initialize.configuration.pop(node_index)
			template_list = get_template(template_list_original)

#	if(remediation):
#		print("[+]: PUSH ENABLED")
#		print("[!]: PUSH DISABLED")
		
			
	return None


### PARSE_AUDIT_FILTER FUNCTION FILTERS OUT THE BACKUP_CONFIGS WITH THE AUDIT_FILTER
### THIS WILL TAKE EACH ELEMENT FROM THE AUDIT_FILTER LIST AND SEARCH FOR THE MATCHED LINES IN BACKUP_CONFIG
### MATCHED ENTRIES ARE THEN APPENDED TO FILTER_BACKUP_CONFIG VARIABLE AS A LIST AND RETURNED
def parse_audit_filter(node_object,index,parse_backup_configs,audit_filter):

	filtered_backup_config = []

	for audit in audit_filter:
		current_template = parse_backup_configs.find_objects(r"^{}".format(audit))
		for audit_string in current_template:
			filtered_backup_config.append(audit_string.text)
			if(audit_string.is_parent):
				for child in audit_string.all_children:
					filtered_backup_config.append(child.text)
			### THE BELOW IF STATEMENT WILL ACCOMODATE JUNIPER PLATFORM SYNTAX AS IT'S MISSING A CLOSING CURLY BRACE AT THE END 
			if(node_object[index]['platform'] == 'juniper'):
				filtered_backup_config.append('}')

	return filtered_backup_config
