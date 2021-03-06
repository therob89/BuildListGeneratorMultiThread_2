import logging
from string import Template
from shutil import copy
import sys
import os
import time

__author__ = 'Roberto Palamaro'
__version__ = '1.0'

my_logger = 'BuildListGenerator'

logger = logging.getLogger(my_logger)


class ReleaseNoteCreator:
    tag_list = {'tagName': 'TAGNAME_',
                'today': 'TODAY_',
                'prevTag': 'PREVIOUS_TAG',
                'buildListName': 'BUILD_LIST_FILE_NAME',
                'artifacts': 'ARTIFACTS_LIST_',
                'provider': 'E_PROVIDER_',
                'httpEndpoint': 'HTTP_CONSUMER_',
                'httpsEndpoint': 'HTTPS_CONSUMER_',
                'global_var': 'GV_LIST',
                'cache': 'CACHES_LIST',
                'config': 'CUSTOM_CONFIG_',
                'config_h': 'HEADER_CUSTOM_CONFIG_',
                'acls': 'ACLS_LIST',
                'packages': 'IS_PACKAGES_',
                'packages_h': 'HEADER_PACKAGES_',
                'database': 'DB_SCRIPTS_',
                'database_r': 'DB_R_SCRIPTS_',
                'database_h': 'HEADER_DB_',
                'bpmProjects': 'BPM_PROJECTS_',
                'bamProjects': 'BPM_PROJECTS_',
                'bpmProjects_h': 'HEADER_PROJECTS_',
                'bamProjects_h': 'HEADER_PROJECTS_',
                'caf': 'CAF_',
                'caf_h': 'HEADER_MWS_',
                'optimize': 'Optimize_',
                'optimize_h': 'HEADER_OPTIMIZE_',
                }
    tag_flag = {'tagName': False,
                'today': False,
                'prevTag': False,
                'buildListName': False,
                'artifacts': False,
                'provider': False,
                'httpEndpoint': False,
                'httpsEndpoint': False,
                'global_var': False,
                'cache': False,
                'config': False,
                'config_h': False,
                'acls': False,
                'packages': False,
                'packages_h': False,
                'database': False,
                'database_r': False,
                'database_h': False,
                'bpmProjects': False,
                'bpmProjects_h': False,
                'bamProjects': False,
                'bamProjects_h': False,
                'caf': False,
                'caf_h': False,
                'optimize': False,
                'optimize_h': False,
                }

    def __init__(self, data_types, template_file, destination_path, file_name, target_tag, svn_point,
                 build_list_file, artifact_list=None, is_full=False):

        self.template_file = template_file
        self.destination_path = destination_path
        self.template_file = file_name
        head, tail = os.path.split(svn_point)
        self.svn_point = tail
        self.ds_size = 0
        self.ob_name_size = 0
        self.ser_size = 0
        self.data_types = data_types
        self.dimension_by_type = dict()
        for d_t in self.data_types:
            self.dimension_by_type[d_t] = (0, 0, 0, 0)
        self.is_full = is_full
        self.build_list_file_name = os.path.basename(build_list_file)
        self.format = None
        self.v_size = 0
        self.table_padding = '{:31}'
        self.target_tag = target_tag
        self.path_to_new_file = os.path.join(destination_path, file_name)
        d = {}
        try:
            copy(template_file, self.path_to_new_file)
            curr_time = time.strftime("%d_%m_%Y", time.gmtime(time.time() + 3600))
            template = self.get_template_from_release()
            _f = open(self.path_to_new_file, 'w')
            d[self.tag_list['tagName']] = self.target_tag
            d[self.tag_list['buildListName']] = self.build_list_file_name
            if not self.is_full:
                d[self.tag_list['prevTag']] = self.svn_point
                res_artifact = ''
                for el in artifact_list:
                    res_artifact += "%s \n" % el
                d[self.tag_list['artifacts']] = res_artifact
            d[self.tag_list['today']] = curr_time
            res = template.safe_substitute(d)
            _f.write(res)
            _f.close()
        except OSError:
            logger.error('Error while creating Release note at this path %s ' % str(self.path_to_new_file))
            sys.exit(-2)
        except KeyError as e:
            logger.error('An error occurs during setup of the release note %s' % str(e))
            sys.exit(-2)

    def __del__(self):
        logger.debug('Cleaning release note from useless values')
        template = self.get_template_from_release()
        _f = open(self.path_to_new_file, 'w')
        d = dict()
        for el in self.tag_list:
            tag_el = str(el)
            if tag_el.endswith('_h') and self.tag_flag[el] is False:
                d[self.tag_list[el]] = "No Records Below"
                continue
            if self.tag_flag[el] is False:
                if el == 'prevTag':
                    d[self.tag_list[el]] = "None..it's a full release"
                elif el == 'artifacts':
                    d[self.tag_list[el]] = "None"
                else:
                    d[self.tag_list[el]] = 'NoAction'
            else:
                d[self.tag_list[el]] = ''
        res = template.safe_substitute(d)
        _f.write(res)
        _f.close()

    def get_template_from_release(self):
        _f = open(self.path_to_new_file, 'r')
        release_note = Template(_f.read())
        _f.close()
        return release_note

    def set_format_size_by_type(self, data_type, x, y, z, v=0):
        # To be fixed in future
        x = max(x, len('Deployment set'))
        self.dimension_by_type[data_type] = (x, y, z, v)

    def get_format_by_type(self, data_type):
        (x, y, z, v) = self.dimension_by_type[data_type]
        return "{:" + str(x) + "}", "{:" + str(y) + "}", "{:" + str(z) + "}", "{:" + str(v) + "}"

    def set_format_size(self, x, y, z, v=0):
        self.ds_size = "{:" + str(x) + "}"
        self.ob_name_size = "{:" + str(y) + "}"
        self.ser_size = "{:" + str(z) + "}"
        self.v_size = "{:" + str(v) + "}"

    def add_global_var_to_release_note(self, template, global_vars, global_vars_values, server):
        _f = open(self.path_to_new_file, 'w')
        res = ''
        for el in global_vars:
            res += self.table_padding.format(str(server))
            res += self.table_padding.format(str(el))
            res += self.table_padding.format(str(global_vars_values[el]))
            res += '\n'
        res += '$' + self.tag_list['global_var']
        self.tag_flag['global_var'] = True
        d = {self.tag_list['global_var']: res}
        res = template.safe_substitute(d)
        _f.write(res)
        _f.close()

    def add_acls_to_release_note(self, template, acls, server):
        _f = open(self.path_to_new_file, 'w')
        res = ''
        for el in acls:
            res += self.table_padding.format(str(server))
            res += self.table_padding.format(str(el))
            res += '\n'
        res += '$' + self.tag_list['acls']
        self.tag_flag['acls'] = True
        d = {self.tag_list['acls']: res}
        res = template.safe_substitute(d)
        _f.write(res)
        _f.close()

    def add_cache_to_release_note(self, template, cache, server):
        _f = open(self.path_to_new_file, 'w')
        res = ''
        for el in cache:
            res += self.table_padding.format(str(server))
            res += self.table_padding.format(str(el))
            res += self.table_padding.format('true')
            res += '\n'
        res += '$' + self.tag_list['cache']
        self.tag_flag['cache'] = True
        d = {self.tag_list['cache']: res}
        res = template.safe_substitute(d)
        _f.write(res)
        _f.close()

    def add_consumer_to_release_note(self, template, endpoint, server, https=False):
        _f = open(self.path_to_new_file, 'w')
        res = ''
        for el in endpoint:
            res += self.table_padding.format(str(server))
            res += self.table_padding.format(str(el))
            res += self.table_padding.format('true')
            res += '\n'
        if https:
            res += '$' + self.tag_list['httpsEndpoint']
            self.tag_flag['httpsEndpoint'] = True
            d = {self.tag_list['httpsEndpoint']: res}
        else:
            res += '$' + self.tag_list['httpEndpoint']
            self.tag_flag['httpEndpoint'] = True
            d = {self.tag_list['httpEndpoint']: res}
        res = template.safe_substitute(d)
        _f.write(res)
        _f.close()

    def add_provider_to_release_note(self, template, provider, server):
        _f = open(self.path_to_new_file, 'w')
        res = ''
        for el in provider:
            res += self.table_padding.format(str(server))
            res += self.table_padding.format(str(el))
            res += self.table_padding.format('true')
            res += '\n'
        res += '$' + self.tag_list['provider']
        self.tag_flag['provider'] = True
        d = {self.tag_list['provider']: res}
        res = template.safe_substitute(d)
        _f.write(res)
        _f.close()

    def add_analytic_engine_to_release_note(self, template, optimize, server):
        _f = open(self.path_to_new_file, 'w')
        res = ''
        for el in optimize:
            res += self.table_padding.format(str(server))
            res += self.table_padding.format(str(el))
            res += '\n'
        res += '$' + self.tag_list['optimize']
        self.tag_flag['optimize'] = True
        d = {self.tag_list['optimize']: res}
        res = template.safe_substitute(d)
        _f.write(res)
        _f.close()

    def add_no_cnf_to_release_note(self, data_type, template, release_lines):
        out_string = ''
        _f = open(self.path_to_new_file, 'w')
        res = ''
        database_string, database_rbk = '', ''
        d = {}
        # Added here
        ds_size, ob_name_size, ser_size, v_size = self.get_format_by_type(data_type)
        header_data_type = self.get_header_by_data_type(data_type)
        if data_type == 'analyticEngine':
            data_type = 'optimize'
        try:
            header_tag = str(data_type) + '_h'
            d[self.tag_list[header_tag]] = header_data_type
            self.tag_flag[header_tag] = True
            for el in release_lines:
                string_to_write = ''
                element = str(el)
                tokens = element.strip().split('\t')
                t_len = len(tokens)
                tok_0 = str(tokens[0]).strip()
                tok_1 = str(tokens[1]).strip()
                tok_2 = str(tokens[2]).strip()
                _a = ds_size.format(tok_0)
                _b = ob_name_size.format(tok_1)
                if '.cnf' in _b:
                    continue
                _c = ser_size.format(tok_2)
                _v = ''
                string_to_write += _a + '  ' + _b + '  ' + _c
                if t_len == 4:
                    tok_3 = str(tokens[3]).strip()
                    _v = v_size.format(tok_3)
                string_to_write += '  ' + _v
                out_string += string_to_write + '\n'
                database_header = tok_0
                if database_header == 'bpm_sql_rbck' and data_type == 'database':
                    database_rbk += string_to_write + '\n'
                elif database_header == 'bpm_sql' and data_type == 'database':
                    database_string += string_to_write + '\n'
            if data_type == 'database':
                if len(database_string) > 0:
                    self.tag_flag['database'] = True
                    d[self.tag_list['database']] = database_string
                    res = template.safe_substitute(d)
                if len(database_rbk) > 0:
                    self.tag_flag['database_r'] = True
                    d[self.tag_list['database_r']] = database_rbk
                    res = template.safe_substitute(d)
            else:
                d[self.tag_list[data_type]] = out_string
                res = template.safe_substitute(d)
            if len(res) > 0:
                _f.write(res)
            _f.close()
        except KeyError as e:
            logger.error('Invalid data type passed %s...%s ' % data_type, str(e))
        except IOError as e:
            logger.error('Invalid file while writing to the release note %s ' % str(e))

    def get_header_by_data_type(self, data_type):
        (x, y, z, v) = self.get_format_by_type(data_type)
        if data_type == 'database':
            obj_descr = 'Script Path'
        elif data_type == 'packages':
            obj_descr = 'Package Name'
        elif data_type in ['bpmProjects', 'bamProjects']:
            obj_descr = 'BAM/BPM Project'
        else:
            obj_descr = 'Resource Path'
        return x.format('Deployment set') + '  ' + y.format(obj_descr) + '  ' + z.format('Logical Instance')

    def add_object_to_release_note(self, data_type, server=None, objects_key=None, objects_value=None):
        _template = self.get_template_from_release()
        if not _template:
            logger.warning("No template found....check the template file if it's correct")
            return
        if not objects_key:
            logger.warning('Passed None objects key for data type %s' % data_type)
            return
        if data_type in ['packages', 'bpmProjects', 'caf', 'bamProjects', 'config', 'database', 'analyticEngine']:
            self.add_no_cnf_to_release_note(data_type=data_type, template=_template, release_lines=objects_key)
        elif data_type == 'globalVariables':
            if not objects_value:
                logger.warning('Passed None for objects value for data type global vars')
                return
            self.add_global_var_to_release_note(_template, objects_key, objects_value, server)
        elif data_type == 'consumerHTTP':
            self.add_consumer_to_release_note(_template, objects_key, server)
        elif data_type == 'consumerHTTPS':
            self.add_consumer_to_release_note(_template, objects_key, server, https=True)
        elif data_type == 'cache':
            self.add_cache_to_release_note(_template, objects_key, server)
        elif data_type == 'acls':
            self.add_acls_to_release_note(_template, objects_key, server)
        elif data_type == 'providerHTTP':
            self.add_provider_to_release_note(_template, objects_key, server)
        #elif data_type == 'analyticEngine':
         #   self.add_analytic_engine_to_release_note(_template, objects_key, server)
        else:
            logger.warning('Unknown data type for release note')