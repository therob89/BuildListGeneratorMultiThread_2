import sys
from collections import defaultdict
import logging
import xml.etree.ElementTree as ET
import re

__author__ = 'Roberto Palamaro'
__version__ = '1.0'

my_logger = 'BuildListGenerator'

logger = logging.getLogger(my_logger)


#//record[@javaclass='com.wm.app.b2b.server.ACLGroup']/@name

cnf_xpath_map = {'consumerHTTP': "./record",
                 'consumerHTTPS': "./record",
                 'providerHTTP': "./record",
                 'providerHTTPS': "./record",
                 'globalVariables': ".//value[@name='key']",
                 'acls': ".//record[@javaclass='com.wm.app.b2b.server.ACLGroup']"}


def parse_config_file(path):
    res = {}
    try:
        with open(path, 'r') as f:
            for line in f:
                if '#' in line:
                    # Ignore Comments
                    continue
                tokens = line.split('=')
                sx_part = tokens[0].replace(' ', '')
                dx_part = tokens[1].replace(' ', '').strip()
                if ',' in dx_part:
                    res[sx_part] = dx_part.split(',')
                else:
                    res[sx_part] = dx_part.strip()
        f.close()
        return res
    except FileNotFoundError as err:
        sys.exit("[FATAL]: %s while parsing config file check this file %s" % (str(err), path))
    except KeyError as err:
        sys.exit("[FATAL]: %s while parsing config file check this file %s and ensure it's correctness" % (str(err),
                                                                                                           path))


def get_data_type_set(log_f, regex, xpath, outfile=None, translator=None,
                      version_holder=None, handle_delete=True, is_full=False):
    try:
        log_f = open(log_f, 'r')
        root = ET.parse(log_f).getroot()
        log_elements = root.findall(".//logentry")
        res = dict()
        delete_set_file = dict()
        delete_set_folder = dict()
        _artifact = None
        obj_to_artifact = None
        artifact_to_objs = None
        if not is_full:
            obj_to_artifact = defaultdict(set)
            artifact_to_objs = defaultdict(set)
        for log in log_elements:
            rev = log.attrib["revision"]
            if not is_full:
                msg = log.find('msg')
                if msg is not None:
                    _artifact = re.findall('artf\d+', msg.text)[0]
            for path in log.findall(xpath):
                data = re.findall(r"%s" % '.*', path.text)
                if data:
                    data_el = data[0]
                    if 'trunk' in data_el:
                        data_el = data_el.split('trunk/')[1]
                    elif 'tags' in data_el:
                        data_el = data_el.split('tags/')[1]
                        data_el = data_el[data_el.find('/')+1:]
                    action = path.attrib["action"]
                    kind = path.attrib["kind"]
                    if handle_delete:
                        # It's a delete
                        if action == 'D':
                            if kind == 'dir':
                                try:
                                    # Update revision for deleted object and add it to delete folder set
                                    temp = delete_set_folder[data_el]
                                    delete_set_folder[data_el] = max(temp, rev)
                                except KeyError:
                                    delete_set_folder[data_el] = rev
                            elif kind == 'file':
                                try:
                                    data = re.findall(r"%s" % regex, path.text)
                                    if data:
                                        # Update revision for deleted object and add it to delete file set
                                        data_el = data[0]
                                        temp = delete_set_file[data_el]
                                        delete_set_file[data_el] = max(temp, rev)
                                except KeyError:
                                    delete_set_file[data_el] = rev
                        # It'a modify or an ADD
                        else:
                            if kind == 'file':
                                try:
                                    data = re.findall(r"%s" % regex, path.text)
                                    if data:
                                        data_el = data[0]
                                        if _artifact is not None:
                                            obj_to_artifact[data_el].add(_artifact)
                                            artifact_to_objs[_artifact].add(data_el)
                                        temp = res[data_el]
                                        res[data_el] = max(temp, rev)
                                except KeyError:
                                    res[data_el] = rev
        log_f.close()
        if handle_delete:
            # We must handle deletion
            keys_to_delete = set()
            for del_folder in delete_set_folder:
                for el in res:
                    if del_folder in el and delete_set_folder[del_folder] >= res[el]:
                        keys_to_delete.add(el)
            # Getting the result keys
            res_keys = res.keys()
            for del_file in delete_set_file:
                if del_file in res_keys and delete_set_file[del_file] >= res[del_file]:
                    keys_to_delete.add(del_file)
            # Delete all elements
            for el in keys_to_delete:
                del res[el]
            # Output Result
            output_res = res.keys()
            if outfile is not None and translator is not None:
                # Getting servers-object maps
                obj_keys = translator.keys()
                if not is_full:
                    # So we proceed with artifacts
                    for art in artifact_to_objs.keys():
                        out_string = 'ARTIFACT: %s \n' % art
                        for element in artifact_to_objs[art]:
                            out_string += " %s  : Info %s \n" % \
                                          (element, version_holder.get_version_for_object(element))
                        outfile.write(out_string)
                else:
                    for el in output_res:
                        if el in obj_keys:
                            outfile.write(el+'\t'+version_holder.get_version_for_object(el)+'\n')
            return set(output_res)
    except ET.ParseError as p_e:
        sys.exit('Parsing error %s ... get this error %s' % (str(log_f), str(p_e)))
    except IOError as io_e:
        sys.exit('I/O error on file %s ... get this error %s' % (str(log_f), str(io_e)))
    except RuntimeError as e:
        sys.exit('Get data-set for file %s ... get this error %s' % (str(log_f), str(e)))


def parse_startup_services(manifest_file):
    try:
        tree = ET.parse(manifest_file).getroot()
        startup_services = tree.find(".//record[@name='startup_services']")
        startup_list = list()
        if startup_services is not None:
            start_ups = startup_services.findall(".//null")
            for service in start_ups:
                startup_list.append(service.attrib['name'])
            if len(startup_list) == 0:
                return 'No Startup services for this element'
            res = ''
            for item in startup_list:
                res += str(item) + "\n"
            return "Startup services : \n %s" % res
        else:
            raise IOError('Startup services is null')
    except IOError as e:
        return str(e.strerror)


def parse_process_file(process_file):
    business_diagram = ET.parse(process_file).getroot()
    if business_diagram is not None:
        return business_diagram.attrib['runtimeVersion']
    else:
        logger.warning("Error while parsing process file -> %s" % str(process_file))


def parse_manifest(manifest_file, verbose=False):
    try:
        tree = ET.parse(manifest_file).getroot()
        _version = tree.find(".//value[@name='version']")
        if _version is not None:
            if verbose:
                _requires = tree.find(".//record[@name='requires']")
                requirements = ''
                if _requires is not None:
                    for el in _requires.findall(".//value"):
                        requirements += str(el.attrib['name']) + ' -- ' + el.text + '\n'
                return _version.text, requirements, parse_startup_services(manifest_file)
            else:
                return _version.text, None, None
        else:
            sys.exit(ValueError('Manifest without version'))
    except ET.ParseError as e:
        sys.exit('Parsing error %s ... get this error %s' % (str(manifest_file), str(e)))
    except IOError as e:
        sys.exit('Error with exporting manifest file: -> ' + str(e))
    except ValueError as err:
        sys.exit('Error with exporting manifest file: -> ' + str(err))


def parse_map_file(map_file, element, xpath_find_el):
    try:
        res = defaultdict(set)
        root = ET.parse(map_file).getroot()
        servers = root.findall(element)
        for server in iter(servers):
            objs = server.findall(xpath_find_el)
            for obj in iter(objs):
                res[obj.attrib["name"]].add(server.attrib["name"])
        return res
    except ET.ParseError as e:
        sys.exit('Parsing error %s ... get this error %s' % (str(map_file), str(e)))
    except IOError as e:
        sys.exit("Check map (element to server) target file ->" + map_file + " " + str(e))


def parse_cnf_file(cnf_type, input_file):
    try:
        _cnf_xpath = cnf_xpath_map[cnf_type]
        tree = ET.parse(input_file)
        root = tree.getroot()
        elements = root.findall(_cnf_xpath)
        res = set()
        for el in elements:
            if cnf_type == 'acls':
                res.add(el.attrib['name'])
            elif cnf_type in ['consumerHTTP', 'consumerHTTPS', 'providerHTTP', 'providerHTTPS']:
                res.add(el.attrib['name'])
            else:
                res.add(el.text)
        return res
    except ET.ParseError as e:
        sys.exit('Parsing error %s ... get this error %s' % (str(input_file), str(e)))
    except KeyError:
        logger.warning("[WARN]: .cnf file " + cnf_type + " not yet supported")
    except IOError as e:
        logger.error("Check input file " + input_file + "error:" + str(e.strerror))
        raise IOError()



#print(parse_config_file("C:\\Users\\OCTO\\PycharmProjects\\BuildListToolMultithreading\\config\\properties.conf"))


#print(parse_cnf_file('acls', "C:\\SoftwareAG\\IntegrationServer\\instances\\default\\config\\acls.cnf"))

'''
with open("C:\\Users\\OCTO\\PycharmProjects\\BuildListToolMultithreading\\prova.xml", 'r') as f:
    ET.parse(f).getroot()
f.close()

f = open("C:\\Users\\OCTO\\PycharmProjects\\BuildListToolMultithreading\\prova.xml", 'r')
ET.parse(f).getroot()
f.close()
#ET.parse("C:\\Users\\OCTO\\PycharmProjects\\BuildListToolMultithreading\\prova.xml")

'''