from shutil import copy
import logging
import os
import sys
import re
import time

my_logger = 'BuildListGenerator'

logger = logging.getLogger(my_logger)


class ReleaseNoteCreator:
    var_subs = {'packages': '\$IS_PACKAGES_',
                'bpmProjects': '\$BPM_PROJECTS_',
                'config': '\$CUSTOM_CONFIG_',
                'caf': '\$CAF_',
                'database': '\$DB_SCRIPTS_',
                'tag_name': '\$TAGNAME_',
                'date': '\$TODAY_',
                'prev_tag': '\$PREVIOUS_TAG',
                'buildFile': '\$BUILD_LIST_FILE_NAME',
                'buildFull': '\$BUILD_LIST_FULL_FILE_F',
                'packages_f': '\$FULL_PACKAGES',
                'bpmProjects_f': '\$FULL_PROJECTS',
                'config_f': '\$FULL_CONFIG',
                'caf_f': '\$FULL_CAF',
                'database_f': '\$FULL_DB',
                'full_point': '\$FULL_POINT_',
                'art_list': '\$ARTIFACTS_LIST_',
                'acls': '\$ACLS_',
                'cache_full': '\$CACHE_FULL_',
                'cache_delta': '\$CACHE_DELTA_'
                }

    def __init__(self, template_file, destination_path, file_name, target_tag, svn_point,
                 build_list_file, artifact_list=None, is_full=False):
        self.template_file = template_file
        self.destination_path = destination_path
        self.template_file = file_name
        head, tail = os.path.split(svn_point)
        self.svn_point = tail
        self.ds_size = 0
        self.ob_name_size = 0
        self.ser_size = 0
        self.is_full = is_full
        self.build_list_file_name = os.path.basename(build_list_file)
        self.format = None
        self.v_size = 0
        self.target_tag = target_tag
        self.path_to_new_file = os.path.join(destination_path, file_name)
        try:
            copy(template_file, self.path_to_new_file)
            original_string = str(open(self.path_to_new_file, 'r').read())
            curr_time = time.strftime("%d_%m_%Y", time.gmtime(time.time() + 3600))
            if not self.is_full:
                new_string = re.sub(self.var_subs['tag_name'], self.target_tag, original_string)
                new_string = re.sub(self.var_subs['prev_tag'], self.svn_point,
                                    new_string)
                res_artifact = ''
                for el in artifact_list:
                    res_artifact += "%s \n" % el
                new_string = re.sub(self.var_subs['art_list'], res_artifact, new_string)
                new_string = re.sub(self.var_subs['buildFile'], self.build_list_file_name, new_string)
                new_string = re.sub(self.var_subs['full_point'], 'NA', new_string)
                new_string = re.sub(self.var_subs['buildFull'], 'NA', new_string)
                new_string = re.sub(self.var_subs['packages_f'], 'NA', new_string)
                new_string = re.sub(self.var_subs['bpmProjects_f'], 'NA', new_string)
                new_string = re.sub(self.var_subs['config_f'], 'NA', new_string)
                new_string = re.sub(self.var_subs['caf_f'], 'NA', new_string)
                new_string = re.sub(self.var_subs['database_f'], 'NA', new_string)
                new_string = re.sub(self.var_subs['cache_full'], 'NA', new_string)

            else:
                new_string = re.sub(self.var_subs['full_point'], self.svn_point, original_string)
                new_string = re.sub(self.var_subs['buildFull'], self.build_list_file_name, new_string)
                new_string = re.sub(self.var_subs['buildFile'], 'NA', new_string)
                new_string = re.sub(self.var_subs['art_list'], 'NA', new_string)
                new_string = re.sub(self.var_subs['packages'], 'NA', new_string)
                new_string = re.sub(self.var_subs['bpmProjects'], 'NA', new_string)
                new_string = re.sub(self.var_subs['config'], 'NA', new_string)
                new_string = re.sub(self.var_subs['caf'], 'NA', new_string)
                new_string = re.sub(self.var_subs['database'], 'NA', new_string)
                new_string = re.sub(self.var_subs['cache_delta'], 'NA', new_string)
            new_string = re.sub(self.var_subs['date'], curr_time, new_string)
            release_note_file = open(self.path_to_new_file, 'w')
            release_note_file.write(new_string)
            release_note_file.close()
            logger.debug('Created Release Note at this path: %s ' % str(self.path_to_new_file))
        except OSError:
            logger.error('Error while creating Release note at this path %s ' % str(self.path_to_new_file))
            sys.exit(-2)
        except KeyError as e:
            logger.error('An error occurs during setup of the release note %s' % str(e))
            sys.exit(-2)

    def set_format_size(self, x, y, z, v=0):
        self.ds_size = "{:"+str(x)+"}"
        self.ob_name_size = "{:"+str(y)+"}"
        self.ser_size = "{:"+str(z)+"}"
        self.v_size = "{:"+str(v)+"}"

    def add_list_of_obj_to_release_note(self, data_type, release_lines):
        try:
            original_string = str(open(self.path_to_new_file, 'r').read())
            out_string = ''
            if self.is_full:
                data_type += '_f'
            if not release_lines:
                new_string = re.sub(self.var_subs[data_type], 'NA', original_string)
                release_note_file = open(self.path_to_new_file, 'w')
                release_note_file.write(new_string)
                release_note_file.close()
                return
            for el in release_lines:
                element = str(el)
                tokens = element.strip().split('\t')
                t_len = len(tokens)
                string_to_write = ''
                _a = self.ds_size.format(tokens[0])
                _b = self.ob_name_size.format(tokens[1])
                _c = self.ser_size.format(tokens[2])
                _v = ''
                string_to_write += _a + ' ' + _b + ' ' + _c
                if t_len == 4:
                    _v = self.v_size.format(tokens[3])
                string_to_write += _v
                out_string += string_to_write + '\n'
            new_string = re.sub(self.var_subs[data_type], out_string, original_string)
            release_note_file = open(self.path_to_new_file, 'w')
            release_note_file.write(new_string)
            release_note_file.close()
        except KeyError:
            logger.warning("Try to add a line to a release note file but isn't supported : %s " % data_type)

    def write_cnf_to_release_note(self, cnf_type, list_of_objs):
        res = ''
        for el in list_of_objs:
            res += el+'\n'
        if cnf_type == 'acls':
            original_string = str(open(self.path_to_new_file, 'r').read())
            new_string = re.sub(self.var_subs[cnf_type], res, original_string)
            release_note_file = open(self.path_to_new_file, 'w')
            release_note_file.write(new_string)
            release_note_file.close()

    def signal_no_cnf(self, cnf_type):
        if cnf_type in ['acls']:
            original_string = str(open(self.path_to_new_file, 'r').read())
            new_string = re.sub(self.var_subs[cnf_type], 'NA', original_string)
            release_note_file = open(self.path_to_new_file, 'w')
            release_note_file.write(new_string)
            release_note_file.close()

    def signal_no_cnfs(self, cnfs_list):
        try:
            for cnf_type in cnfs_list:
                original_string = str(open(self.path_to_new_file, 'r').read())
                new_string = re.sub(self.var_subs[cnf_type], 'NA', original_string)
                release_note_file = open(self.path_to_new_file, 'w')
                release_note_file.write(new_string)
                release_note_file.close()
        except KeyError:
            logger.warning('cnf_type: %s with an unknown position into release note')

    def write_cache_to_release(self, cache_entries):
        original_string = str(open(self.path_to_new_file, 'r').read())
        string_to_write = ''
        for el in cache_entries:
            tokens = str(el).split(':')
            if len(tokens) == 3:
                _a = self.ds_size.format(tokens[0])
                _b = self.ob_name_size.format(tokens[1])
                _c = self.ser_size.format(tokens[2])
                string_to_write += _a + ' ' + _b + ' ' + _c + '\n'
        if self.is_full:
            new_string = re.sub(self.var_subs['cache_full'], string_to_write, original_string)
        else:
            new_string = re.sub(self.var_subs['cache_delta'], string_to_write, original_string)
        release_note_file = open(self.path_to_new_file, 'w')
        release_note_file.write(new_string)
        release_note_file.close()




