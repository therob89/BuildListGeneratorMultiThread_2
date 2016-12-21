import logging
import utils.ParsingOperations as Pt
import utils.VersioningTool as Vt
from collections import defaultdict
import sys

__author__ = 'Roberto Palamaro'
__version__ = '1.0'

my_logger = 'BuildListGenerator'

logger = logging.getLogger(my_logger)


# Generic Bpm Class Type
class BpmDataType(object):
    def __init__(self, data_type, server_list, log_file, list_file, is_full=False):
        self.data_type = data_type
        self.list_file = list_file
        self.log_file = log_file
        self.list_output = set()
        self.release_note_objects_by_server = defaultdict(set)
        self.release_note_all_objs = list()
        self.server_list = server_list
        self.is_full = is_full

    def get_list_file(self):
        logger.info('Called Get List on generic class BpmDataType... do nothing')
        return self.list_file

    def get_data_type(self):
        return self.server_list

    def get_output(self):
        logger.info('Called Get Output on generic class BpmDataType...do nothing')
        return self.list_output

    def fill_list_file(self):
        logger.info('Called Get Output on generic class BpmDataType...do nothing')

    def get_release_note_objects(self):
        logger.info('Called Get Release note objects on generic class BpmDataType...do nothing')


# Class for Config
class Config(BpmDataType):
    config_regex_properties = ".*\.properties"
    config_regex_cnf = ".*\.cnf"
    config_regex_send_email = ".*sendEmail.+"
    config_xpath = ".paths//path"
    cache_element_regex = ".*Caching/\w+.xml"

    def __init__(self, data_type, server_list, log_file, list_file, is_full=False):
        super(Config, self).__init__(data_type, server_list, log_file, list_file, is_full)
        self.cnf_list = None
        self.output_config = list()
        self.output_config_res = defaultdict(set)
        self.config_by_server = defaultdict(set)
        self.cache_list = defaultdict(set)
        self.cache_list_output = list()
        # To process later
        self.cnf_res = defaultdict(set)
        self.fill_list_file()

    def get_server_from_property_and_return_element(self, prop_element):
        for server in self.server_list:
            server_name = "/" + server.split("_")[-1] + "/"
            s = server_name[1:-1].lower() + ":"
            s_v = s[:-1]
            prop_lower = prop_element.lower()
            if server_name in prop_lower:
                l_x = len("config" + server_name + prop_lower.split(server_name)[-1])
                _substring = prop_element[-l_x:]
                if prop_element.endswith('.cnf'):
                    self.cnf_res[server].add(_substring)
                if prop_element.endswith('.xml') and '/caching/' in prop_lower:
                    self.cache_list[server].add(_substring)
                release_note_string = ("%s \t %s \t %s " % (s_v, _substring, server))
                return server, s + _substring + ":" + server, release_note_string
        logger.warning("Found a property file with no known target server: %s" % prop_element)

    def fill_list_file(self):
        logger.debug('Creating list file for %s' % self.data_type)
        # Config are not wrote to list file
        custom_config_ds = sorted(Pt.get_data_type_set(self.log_file, self.config_regex_properties,
                                                       self.config_xpath, is_full=self.is_full))
        self.cnf_list = sorted(Pt.get_data_type_set(self.log_file, self.config_regex_cnf,
                                                    self.config_xpath, is_full=self.is_full))
       # send_email_ds = Pt.get_data_type_set(self.log_file, self.config_regex_send_email,
                                           #  self.config_xpath, is_full=self.is_full)

        cache_ds = sorted(Pt.get_data_type_set(self.log_file, self.cache_element_regex,
                                               self.config_xpath, is_full=self.is_full))
        try:
            with open(self.list_file, 'w') as list_file:
                # 1. Return first custom config
                for custom_conf in custom_config_ds:
                    server, _property, rel_string = self.get_server_from_property_and_return_element(custom_conf)
                    self.config_by_server[server].add("bpm_cstcfg_" + _property)
                    self.release_note_objects_by_server[server].add("bpm_cstscfg_" + rel_string)
                #for s_mail in send_email_ds:
                  #  server, _prop, rel_string = self.get_server_from_property_and_return_element(s_mail)
                  #  self.config_by_server[server].add("bpm_cstcfg_" + _prop)
                    #self.release_note_objects_by_server[server].add("bpm_cstscfg_" + rel_string)
                for _cnf in self.cnf_list:
                    server, _cnf, rel_string = self.get_server_from_property_and_return_element(_cnf)
                    self.config_by_server[server].add("bpm_cf_is_" + _cnf)
                    self.release_note_objects_by_server[server].add("bpm_cf_is_" + rel_string)
                for _cache in cache_ds:
                    server, _cnf, rel_string = self.get_server_from_property_and_return_element(_cache)
                    self.config_by_server[server].add("bpm_cf_is_" + _cnf)
                    self.cache_list_output.append("bpm_cf_is_" + rel_string)
                    #self.release_note_objects_by_server[server].add("bpm_cf_is_" + rel_string)
                for server in self.server_list:
                    for el in sorted(self.config_by_server[server]):
                        list_file.write(el + "\n")
                        self.output_config.append("%s\n" % el)
                    for el in sorted(self.release_note_objects_by_server[server]):
                        self.release_note_all_objs.append("%s\n" % el)
            list_file.close()
        except IOError as e:
                logger.error('Problem occurs for output file for config %s ' % str(e))

    def get_output(self):
        return self.output_config, self.cnf_res, self.cache_list, self.cache_list_output

    def get_release_note_objects(self):
        return self.release_note_all_objs


# Class for Process
class Process(BpmDataType):
    bpm_projects_regex = "IttBpm\w+/\w+.(?=.config|.process)"
    bpm_projects_xpath = ".paths//path[@kind='file']"
    process_ds = "bpm_prj_is_"

    def __init__(self, data_type, server_list, log_file, list_file, translator, base_url, is_full=False):
        super(Process, self).__init__(data_type, server_list, log_file, list_file, is_full)
        self.translator_file = translator
        self.prj_to_server = Pt.parse_map_file(self.translator_file, 'target_project_server', 'project')
        logger.debug('Translator file for projects parsed correctly')
        self.output_process_by_server = defaultdict(set)
        self.output_list = list()
        self.base_url = base_url+'/bpmProjects/'
        self.version_holder = Vt.VersionHolder(self.base_url, package_flag=False, full_mode=self.is_full)
        self.fill_list_file()

    def fill_server_processes(self, element):
        out_servers = self.prj_to_server[element]
        version = self.version_holder.get_version_for_object(element)
        if not out_servers:
            logger.warning('There is no mapping between process %s and server' % element)
            return
        for out_server in out_servers:
            s = out_server.split('_')[-1].lower() + ":"
            s_v = s[:-1]
            out_string = str(self.process_ds + s + "bpmProjects/" + element + ":" + str(out_server))
            release_note_string = "%s \t %s \t %s \t Version: %s" \
                                  % (self.process_ds + s_v, element, str(out_server), version)
            self.release_note_objects_by_server[out_server].add(release_note_string)
            self.output_process_by_server[out_server].add(out_string)

    def fill_list_file(self):
        logger.debug('Creating list file for %s' % self.data_type)
        try:
            with open(self.list_file, 'w') as list_file:
                prj_set_from_log = sorted(Pt.get_data_type_set(self.log_file,
                                                               self.bpm_projects_regex,
                                                               self.bpm_projects_xpath,
                                                               list_file,
                                                               self.prj_to_server,
                                                               self.version_holder,
                                                               is_full=self.is_full))
                for prj in prj_set_from_log:
                    self.fill_server_processes(str(prj))
                    # Now process the server
                for server in self.server_list:
                    for prj_e in sorted(self.output_process_by_server[server]):
                        prj_el = "%s\n" % prj_e
                        self.output_list.append(prj_el)
                    for out_v in sorted(self.release_note_objects_by_server[server]):
                        prj_el = "%s\n" % out_v
                        self.release_note_all_objs.append(prj_el)
                list_file.close()
        except IOError as e:
                logger.error('Problem occurs for output file for processes %s ' % str(e))

    def get_output(self):
        return self.output_list

    def get_release_note_objects(self):
        return self.release_note_all_objs


# Class for Package
class Package(BpmDataType):
    packages_regex = "Itt\w+(?=/)"
    packages_xpath = ".paths//path[@kind='file']"
    package_ds = "bpm_pkg_is_"

    def __init__(self, data_type, server_list, log_file, list_file, translator, base_url, is_full=False):
        super(Package, self).__init__(data_type, server_list, log_file, list_file, is_full)
        self.translator_file = translator
        self.pkg_to_server = Pt.parse_map_file(self.translator_file, 'target_package_server', 'package')
        logger.debug('Translator file for package parsed correctly')
        # output for packages not in default
        self.output_list_for_pkg_no_def = list()
        # output for packages in default
        self.output_list_def = list()
        self.output_packages_by_server = defaultdict(set)
        self.base_url = base_url+'/packages/'
        self.version_holder = Vt.VersionHolder(self.base_url, full_mode=self.is_full)
        self.fill_list_file()

    def fill_server_packages(self, element):
        out_servers = self.pkg_to_server[element]
        version = self.version_holder.get_version_for_object(element)
        if not out_servers:
            logger.warning('There is no mapping between package %s and server' % element)
            return
        for out_server in out_servers:
            s = out_server.split('_')[-1].lower() + ":"
            s_v = s[:-1]
            out_string = str(str(self.package_ds + s + "packages/" + element + ":" + str(out_server)))
            self.output_packages_by_server[out_server].add(out_string)
            release_note_string = "%s \t %s \t  %s \t Version: %s" \
                                  % (self.package_ds + s_v, element, str(out_server), version)
            self.release_note_objects_by_server[out_server].add(release_note_string)

    def fill_list_file(self):
        logger.debug('Creating list file for %s' % self.data_type)
        try:
            with open(self.list_file, 'w') as list_file:
                pkg_set_from_log = sorted(Pt.get_data_type_set(self.log_file,
                                                               self.packages_regex,
                                                               self.packages_xpath,
                                                               list_file,
                                                               self.pkg_to_server,
                                                               self.version_holder,
                                                               is_full=self.is_full))

                for pkg in pkg_set_from_log:
                    self.fill_server_packages(str(pkg))
                # Now process the server
                for server in self.server_list:
                    for pkg in sorted(self.output_packages_by_server[server]):
                        pkg_el = "%s\n" % pkg
                        if server == 'bpm_is_default':
                            self.output_list_def.append(pkg_el)
                        else:
                            self.output_list_for_pkg_no_def.append(pkg_el)
                    for el in sorted(self.release_note_objects_by_server[server]):
                        pkg_el = "%s\n" % el
                        self.release_note_all_objs.append(pkg_el)

            list_file.close()
        except IOError as e:
            logger.error('Problem occurs for output file for package %s ' % str(e))

    def get_output(self):
        return self.output_list_def, self.output_list_for_pkg_no_def

    def get_release_note_objects(self):
        return self.release_note_all_objs


# Class for Package
class Database(BpmDataType):
    db_regex = "/database/.*"
    db_xpath = ".paths//path"

    def __init__(self, data_type, server_list, log_file, list_file, is_full=False):
        super(Database, self).__init__(data_type, server_list, log_file, list_file, is_full)
        self.db_ddl = list()
        self.db_ddl_rbk = list()
        self.db_dml = list()
        self.db_dml_rbk = list()
        self.db_output = list()
        if len(server_list) == 0:
            raise RuntimeError('DB must have at least one target server')
        self.fill_list_file()

    def fill_list_file(self):
        logger.debug('Creating list file for %s' % self.data_type)
        db_res = sorted(Pt.get_data_type_set(self.log_file, self.db_regex, self.db_xpath, is_full=self.is_full))
        for db_el in db_res:
            db_el_lower = str(db_el).lower()
            if 'ddl' in db_el_lower and 'rollback' in db_el_lower:
                self.db_ddl_rbk.append(db_el)
            elif 'ddl' in db_el_lower and 'rollback' not in db_el_lower:
                self.db_ddl.append(db_el)
            elif 'dml' in db_el_lower and 'rollback' in db_el_lower:
                self.db_dml_rbk.append(db_el)
            elif 'dml' in db_el_lower and 'rollback' not in db_el_lower:
                self.db_dml.append(db_el)
        sql_header = 'bpm_sql:'
        sql_header_r = 'bpm_sql'
        sql_rbk_header = 'bpm_sql_rbck:'
        sql_rbk_header_r = 'bpm_sql_rbck'
        if len(self.server_list) > 1:
            logger.warning('Database have more than 1 server target...check it')
        server = ':'+self.server_list[0]
        server_r = self.server_list[0]
        list_file = open(self.list_file, 'w')
        for ddl in self.db_ddl:
            if str(ddl).index('/') == 0:
                ddl = ddl[1::]
            el = sql_header+ddl+server
            el_v = "%s \t %s \t %s" % (sql_header_r, ddl, server_r)
            self.db_output.append("%s\n" % el)
            self.release_note_all_objs.append("%s\n" % el_v)
            list_file.write("%s\n" % el)
        for dml in self.db_dml:
            if str(dml).index('/') == 0:
                dml = dml[1::]
            el = sql_header+dml+server
            el_v = "%s \t %s \t %s" % (sql_header_r, dml, server_r)
            self.db_output.append("%s\n" % el)
            self.release_note_all_objs.append("%s\n" % el_v)
            list_file.write("%s\n" % el)
        for dml_rbk in self.db_dml_rbk:
            if str(dml_rbk).index('/') == 0:
                dml_rbk = dml_rbk[1::]
            el = sql_rbk_header+dml_rbk+server
            el_v = "%s \t %s \t %s" % (sql_rbk_header_r, dml_rbk, server_r)
            self.release_note_all_objs.append("%s\n" % el_v)
            self.db_output.append("%s\n" % el)
            list_file.write("%s\n" % el)
        for ddl_rbk in self.db_ddl_rbk:
            if str(ddl_rbk).index('/') == 0:
                ddl_rbk = ddl_rbk[1::]
            el = sql_rbk_header+ddl_rbk+server
            el_v = "%s \t %s \t %s" % (sql_rbk_header_r, ddl_rbk, server_r)
            self.db_output.append("%s\n" % el)
            self.release_note_all_objs.append("%s\n" % el_v)
            list_file.write("%s\n" % el)

    def get_output(self):
            return self.db_output

    def get_release_note_objects(self):
        return self.release_note_all_objs


# Class for Caf
class Caf(BpmDataType):
    caf_regex = "(?:/caf)/[A-Z]\w+"
    caf_xpath = ".paths//path[@kind='file']"
    caf_cf_header = 'bpm_cnf_mws:'
    caf_cf_release_header = 'bpm_cnf_mws'
    caf_portlet_header = 'bpm_portlet_mws:'
    caf_portlet_r_header = 'bpm_portlet_mws'

    def __init__(self, data_type, server_list, log_file, list_file, is_full=False):
        super(Caf, self).__init__(data_type, server_list, log_file, list_file, is_full)
        if len(server_list) == 0:
            sys.exit('Config must have at least one target server...abort')
        self.output_caf = list()
        self.fill_list_file()

    def fill_list_file(self):
        logger.debug('Creating list file for %s' % self.data_type)
        caf_ds = sorted(Pt.get_data_type_set(self.log_file, self.caf_regex, self.caf_xpath, is_full=self.is_full))
        caf_server = self.server_list[0]
        try:
            with open(self.list_file, "w") as list_file:
                for caf_record in caf_ds:
                    if 'MWSUserManagement' in caf_record:
                        out_string = self.caf_cf_header + caf_record[1:] + ":" + caf_server
                        out_rel_s = "%s \t %s \t %s" \
                                    % (self.caf_cf_release_header, caf_record[1:], caf_server)
                    else:
                        out_string = self.caf_portlet_header + caf_record[1:] + ":" + caf_server
                        out_rel_s = "%s \t %s \t %s" \
                                    % (self.caf_portlet_r_header, caf_record[1:], caf_server)
                    self.output_caf.append("%s\n" % out_string)
                    self.release_note_all_objs.append("%s\n" % out_rel_s)
                    list_file.write("%s\n" % out_string)
            list_file.close()
        except IOError:
            logger.error("IO ERROR check -> caf list file -> " + self.list_file)

    def get_output(self):
            return self.output_caf

    def get_release_note_objects(self):
        return self.release_note_all_objs


class BpmWrapper:

    def __init__(self, data_type, data_types, log_files, list_files, server_list, translator, base_url, is_full=False):
        self.data_types = data_types
        self.data_type = data_type
        self.server_list = server_list
        self.data_holder = {}
        self.is_full = is_full
        self.log_files = log_files
        self.list_files = list_files
        self.base_url = base_url
        self.translator_file = translator
        try:
            d_t = data_type
            if d_t == 'packages':
                self.data_holder[d_t] = Package(d_t, self.server_list, self.log_files, self.list_files,
                                                self.translator_file, self.base_url, is_full)
            elif d_t == 'bpmProjects':
                self.data_holder[d_t] = Process(d_t, self.server_list, self.log_files, self.list_files,
                                                self.translator_file, self.base_url, is_full)
            elif d_t == 'config':
                self.data_holder[d_t] = Config(d_t, self.server_list, self.log_files, self.list_files, is_full)
            elif d_t == 'caf':
                self.data_holder[d_t] = Caf(d_t, self.server_list, self.log_files, self.list_files, is_full)
            elif d_t == 'database':
                self.data_holder[d_t] = Database(d_t, server_list, self.log_files, self.list_files,
                                                 is_full)
            else:
                logger.warning('Unknown data type: %s passed to wrapper' % d_t)
        except KeyError as k_e:
            raise KeyError('An error occur during wrapper initialization %s ' % str(k_e))

    def get_object_data_holder(self):
        return self.data_holder[self.data_type]
