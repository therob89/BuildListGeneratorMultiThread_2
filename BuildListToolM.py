import logging.config
import logging
import shutil
import argparse
import queue
import os
import utils.ParsingOperations as ParserTool
import utils.SvnOperations as SvnTool
import utils.ExternalModuleCaller as ModuleCaller
import utils.BpmDataType as BpmData
import utils.ReleaseNoteCreator as Rnc
import re
from collections import defaultdict
import time
import threading
import sys

__author__ = 'Roberto Palamaro'
__version__ = '1.0'

# Internal Maps
bpm_c_point = 'bpm_c_point'
bpm_p_point = 'bpm_p_point'

bam_c_point = 'bam_c_point'
bam_p_point = 'bam_p_point'

# Key Parameters
bpm_root = 'BpmSvnRoot'
bam_root = 'BamSvnRoot'
artf_list = 'artifactList'
bpm_data_type = 'BpmDataType'
ReportsFolder = 'ReportsFolder'
template_file = 'template_file'
xml_jar = 'xml_jar'
cnf_list = 'cnf_list'

# Logger name
my_logger = 'BuildListGenerator'

logger = None
failed_threads = queue.Queue()


def thread_log_routine(url, output_file, full=False, artifacts=None):
    thread_name = str(threading.current_thread().getName())
    try:
        if url is None or output_file is None:
            logger.error('%s: invalid url %s or output file %s' % (thread_name, url, output_file))
            sys.exit(-2)
        if not full:
            if artifacts is None:
                logger.error(
                    "%s: Error into log routine, in delta mode there must be at least one artifact %s"
                    % thread_name)
                sys.exit(-2)
            # Delta Mode
            logger.debug('%s Request log file in delta mode on %s' % (thread_name, url))
            ret = SvnTool.get_svn_log_to_file(url, output_file, True, artifacts)
        else:
            # Full mode
            logger.debug('%s Request log file in full mode' % thread_name)
            ret = SvnTool.get_svn_log_to_file(url, output_file)
        if ret:
            logger.error('%s: Error at svn log %s...exit with error' % (thread_name, ret))
            sys.exit(-3)
    except SystemExit:
        logger.error("%s end WITH ERROR : %s" % thread_name)
        failed_threads.put(thread_name)


def thread_list_routine(data_type, data_types, server_list, log_file, list_file, translator,
                        curr_svn_link, full_mode, output_for_thread, release_note_objs):
    thread_name = str(threading.current_thread().getName())
    try:
        wrapper = BpmData.BpmWrapper(data_type,
                                     data_types,
                                     log_file,
                                     list_file,
                                     server_list,
                                     translator=translator,
                                     base_url=curr_svn_link,
                                     is_full=full_mode)
        object_data = wrapper.get_object_data_holder()
        for el in object_data.get_output():
            output_for_thread.append(el)
        rn_objs = object_data.get_release_note_objects()
        for obj in rn_objs:
            release_note_objs.append(obj)
        logger.debug('%s  end correctly' % thread_name)
    except SystemExit:
        failed_threads.put(thread_name)


def write_cnf_to_file(cnf_f, cnf_type_with_ext, release_note_creator):
    try:
        if cnf_f:
            file_only_name = cnf_type_with_ext.split(".cnf")[0]
            _cnf_to_write = ParserTool.parse_cnf_file(file_only_name, cnf_f)
            if not _cnf_to_write:
                release_note_creator.signal_no_cnf(file_only_name)
                if os.path.exists(cnf_f):
                    os.remove(cnf_f)
                    return
            release_note_creator.write_cnf_to_release_note(file_only_name, _cnf_to_write)
            with open(cnf_f, 'w') as _f:
                for el in _cnf_to_write:
                    _f.write(el + "\n")
            _f.close()
    except IOError as er:
        logger.error("[ERROR]: Error for cnf file " + cnf_f + "strerror" + str(er.strerror))
        sys.exit(-1)


def write_delta_cnf_to_file(cnf_file_current,
                            cnf_file_previous, cnf_type_with_ext, out_file, release_note_creator):
    try:
        file_only_name = cnf_type_with_ext.split(".cnf")[0]
        if cnf_file_current and cnf_file_previous:
            _cnf_current = set(ParserTool.parse_cnf_file(file_only_name, cnf_file_current))
            _cnf_previous = set(ParserTool.parse_cnf_file(file_only_name, cnf_file_previous))
            if _cnf_current is None and _cnf_previous is None:
                release_note_creator.signal_no_cnf(file_only_name)
                return
            diff = _cnf_current.difference(_cnf_previous)
            if len(diff) == 0:
                return 0
            else:
                release_note_creator.write_cnf_to_release_note(file_only_name, diff)
                with open(out_file, 'w') as f:
                    for el in diff:
                        if el:
                            f.write(el + "\n")
                f.close()
        else:
            release_note_creator.signal_no_cnf(file_only_name)
            logger.warning('there is one file missing check ' + cnf_file_current + ' | ' + cnf_file_previous)
    except IOError as io_e:
        logger.warning("Error for cnf file " + cnf_file_current + " or " + cnf_file_previous +
                       " strerror" + str(io_e.strerror))
        sys.exit(-1)


class BpmDataHolder:

    def __init__(self, config, tag, environment,  current_point, previous_point=None, artifacts=None):
        self.prev_svn_link = previous_point
        self.curr_svn_link = current_point
        self.target_tag = tag
        self.env = environment
        self.artifacts = artifacts
        self.thread_output_for_buildList = dict()
        self.release_note_objects = dict()
        self.config = config
        self.is_full = False
        self.wrapper = None
        self.cache_list = list()
        self.cnf_flag = False
        self.cnf_folder = None
        try:
            reports_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', self.config[ReportsFolder]))
            template_name = self.config[template_file]
            template_position = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', 'config/'+template_name))
            if not os.path.exists(reports_folder):
                os.makedirs(reports_folder)
            curr_time = time.strftime("%d_%m_%Y_%H_%M", time.gmtime(time.time()+3600))
            only_day = time.strftime("%d_%m_%Y", time.gmtime(time.time()+3600))
            if self.prev_svn_link is None and self.artifacts is None:
                self.is_full = True
                release_folder_name = "Release_Full_" + curr_time
            else:
                curr_point_normalized = self.curr_svn_link.split('/')[-1]
                prev_point_normalized = self.prev_svn_link.split('/')[-1]
                release_folder_name = "Release_Delta_" + curr_point_normalized + "_" \
                                      + prev_point_normalized + "_" + curr_time
            self.release_folder = os.path.join(reports_folder, release_folder_name)
            self.build_list_folder = os.path.join(self.release_folder, 'buildLists')
            self.data_type = list(config[bpm_data_type])
            self.cnf_list = list(config[cnf_list])
            logger.debug(
                'BpmDataHolder init for these data types : %s..reports will be created into folder %s'
                % (str(self.data_type), str(self.release_folder)))
            self.list_for_dh = defaultdict(list)
            self.log_files = dict()
            self.list_files = dict()
            self.build_list_list_file = os.path.join(self.build_list_folder, 'buildList_'+str(self.env) + '.list')
            self.build_list_xml_file = os.path.join(self.build_list_folder, 'buildList_'+str(self.env) + '.xml')
            os.makedirs(self.release_folder)
            os.makedirs(self.build_list_folder)
            if self.is_full:
                _svn_link = self.curr_svn_link
            else:
                _svn_link = self.prev_svn_link
            # -------------- Create Release note template ---------------------------
            self.release_note = Rnc.ReleaseNoteCreator(template_position,
                                                       self.release_folder,
                                                       'ReleaseNote_' + str(only_day) + '_' + self.env+'.txt',
                                                       target_tag=self.target_tag,
                                                       svn_point=_svn_link,
                                                       build_list_file=self.build_list_xml_file,
                                                       artifact_list=self.artifacts,
                                                       is_full=self.is_full)
            # ------------------------------------------------------------------------

            for d_h in self.data_type:
                self.log_files[d_h] = os.path.join(self.release_folder, "%s.xml" % d_h)
                self.list_files[d_h] = os.path.join(self.release_folder, "%s.list" % d_h)
                self.thread_output_for_buildList[d_h] = list()
                self.release_note_objects[d_h] = list()
            logger.info('Creating Log Files')
            self.create_log_files()
            self.translator_file_name = self.config['server_map']
            self.translator_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                                'config/', self.translator_file_name))
            logger.info('Creating List files')
            self.create_list_files()
            logger.debug('Generating buildList XML')
            build_xml_jar = self.config[xml_jar]
            base_svn_root = self.config[bpm_root]
            jar_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', 'externalModules/'+build_xml_jar))
            ModuleCaller.generate_build_xml(jar_path, base_svn_root + self.target_tag,
                                            self.build_list_list_file, self.build_list_xml_file, self.cnf_folder)
            logger.debug('BuildList Generator end succesfully, generate .list and .xml and release note')
        except KeyError as k_err:
            logger.error('Invalid Property from file %s' % str(k_err))
            sys.exit(-1)
        except OSError as o_err:
            logger.error('Cannot Generate Some file or folder: %s' % str(o_err))
            sys.exit(-1)

    def create_log_files(self):
        thread_list = []
        for d_t in self.data_type:
            th = threading.Thread(target=thread_log_routine, name="Log_Thread__%s" % d_t,
                                  args=(self.curr_svn_link+'/' + d_t + '/',
                                        self.log_files[d_t], self.is_full, self.artifacts))
            thread_list.append(th)
            th.start()
        for th in thread_list:
            th.join()
            logger.debug("%s complete his job!!!!!" % th.getName())
        global failed_threads
        if not failed_threads.empty():
            fails = ''
            for el in iter(failed_threads.get(), None):
                fails += str(el) + ' '
            logger.error('An error occurs during creating list files..the failed threads are %s' % fails)
            sys.exit(-1)
        logger.info('Log Files created Successfully')

    def process_cnf_files(self, cnf_set):
        temp_curr = None
        temp_prev = None
        if self.is_full:
            self.cnf_folder = os.path.join(self.release_folder, "FULL_CNF")
            logger.debug('Processing CNF in full mode')
        else:
            self.cnf_folder = os.path.join(self.release_folder, "DELTA_CNF")
            temp_curr = os.path.join(self.cnf_folder, "temp_curr")
            temp_prev = os.path.join(self.cnf_folder, "temp_prev")
            logger.debug('Processing CNF in delta mode')
        try:
            if os.path.exists(self.cnf_folder):
                logger.warning('Cnf folder already exists...')
            os.makedirs(self.cnf_folder)
            if not self.is_full:
                os.makedirs(temp_curr)
                os.makedirs(temp_prev)
            for server in iter(cnf_set):
                cnf_server_folder = os.path.join(self.cnf_folder, server)
                os.makedirs(cnf_server_folder)
                for _cnf in cnf_set[server]:
                    file_with_ext = re.findall(r'\w+.cnf', _cnf)[0]
                    svn_curr_cnf_path = self.curr_svn_link + '/' + str(_cnf)
                    if is_a_full:
                        SvnTool.check_out_file(svn_curr_cnf_path, cnf_server_folder)
                        if not file_with_ext:
                            logger.warning('Invalid CNF PATH')
                            continue
                        current_file_path = os.path.join(cnf_server_folder, file_with_ext)
                        write_cnf_to_file(current_file_path, file_with_ext, self.release_note)
                    else:
                        svn_prev_cnf_path = self.prev_svn_link + '/' + str(_cnf)
                        SvnTool.check_out_file(svn_curr_cnf_path, temp_curr)
                        SvnTool.check_out_file(svn_prev_cnf_path, temp_prev)
                        path_to_curr = os.path.join(temp_curr, file_with_ext)
                        path_to_prev = os.path.join(temp_prev, file_with_ext)
                        path_to_out_file = os.path.join(cnf_server_folder, file_with_ext)
                        if write_delta_cnf_to_file(path_to_curr, path_to_prev, file_with_ext,
                                                   path_to_out_file, self.release_note) == 0:
                            os.removedirs(cnf_server_folder)
            if not self.is_full:
                shutil.rmtree(temp_curr)
                shutil.rmtree(temp_prev)
            if not os.listdir(self.cnf_folder):
                logger.info('No difference found with the tag %s ' % str(self.prev_svn_link))
                os.removedirs(self.cnf_folder)
        except OSError as os_e:
            logger.error('An error occurs while creating CNF folders or file: %s' % os.strerror(os_e.errno))
            sys.exit(-1)

    def create_list_files(self):
        logger.debug('Creating wrappers for objects')
        thread_list = []
        for d_t in self.data_type:
            server_list_key = d_t + '_server'
            server_list = self.config[server_list_key]
            if isinstance(server_list, str):
                server_list = [server_list]
            th = threading.Thread(target=thread_list_routine, name="List_Thread__%s" % d_t,
                                  args=(d_t,
                                        self.data_type,
                                        server_list,
                                        self.log_files[d_t],
                                        self.list_files[d_t],
                                        self.translator_file,
                                        self.curr_svn_link,
                                        self.is_full,
                                        self.thread_output_for_buildList[d_t],
                                        self.release_note_objects[d_t]))
            thread_list.append(th)
            th.start()
        for th in thread_list:
            th.join()
            logger.debug("%s complete his job!!!!!!!!" % th.getName())
        global failed_threads
        if not failed_threads.empty():
            fails = ''
            for el in iter(failed_threads.get(), None):
                fails += str(el) + ' '
            logger.error('An error occurs during creating list files..the failed threads are %s' % fails)
            sys.exit(-1)
        logger.info('List Files created Successfully!!!!!!!')
        logger.info('Creating BuildList file and Release note')
        _x, _y, _z, _v = 0, 0, 0, 0
        with open(self.build_list_list_file, 'w') as f:
            for d_t in self.data_type:
                if d_t == 'config':
                    output_config, cnf_res, cache_list = self.thread_output_for_buildList[d_t]
                    if not cnf_res:
                        logger.info('No CNF changes found go ahead')
                        self.release_note.signal_no_cnfs(self.cnf_list)
                    else:
                        logger.debug('CNF Found...processing files')
                        self.cnf_flag = True
                        self.process_cnf_files(cnf_res)
                    if cache_list:
                        logger.debug('Found Cache configuration')
                        self.cache_list = cache_list
                    for el in output_config:
                        f.write(el)
                elif d_t == 'packages':
                    _def, no_def = self.thread_output_for_buildList[d_t]
                    for el in no_def:
                            f.write(el)
                    for el in _def:
                        f.write(el)
                elif d_t == 'bpmProjects':
                    _db_list = self.thread_output_for_buildList[d_t]
                    for el in _db_list:
                        f.write(el)
                elif d_t == 'caf':
                    _db_list = self.thread_output_for_buildList[d_t]
                    for el in _db_list:
                        f.write(el)
                for line_of_objs in self.release_note_objects[d_t]:
                    l = str(line_of_objs)
                    tokens = l.split('\t')
                    token_len = len(tokens)
                    if token_len < 3:
                        logger.warning('There can be problem on rendering on release note for element %s ' % d_t)
                        break
                    _x = max(len(tokens[0]), _x)
                    _y = max(len(tokens[1]), _y)
                    _z = max(len(tokens[2]), _z)
                    if token_len == 4:
                        _v = max(len(tokens[3]), _v)

            self.release_note.set_format_size(_x, _y, _z, _v)
            for d_t in self.data_type:
                self.release_note.add_list_of_obj_to_release_note(d_t, self.release_note_objects[d_t])
                logger.debug('Added %s to release note file' % d_t)
            if self.cache_list:
                self.release_note.write_cache_to_release(self.cache_list)
        logger.info('BuildList.list created succesfully!!!')
        f.close()


def init_log(level):
    logger = logging.getLogger('[Build List Generator]')
    logger.setLevel(logging.DEBUG)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    if level == 'Info':
        _level = logging.INFO
    elif level == 'Error':
        _level = logging.ERROR
    else:
        _level = logging.DEBUG
    ch.setLevel(_level)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)
    return logger


def init_log_from_file(path):
    try:
        global logger
        logging.config.fileConfig(path)
        logger = logging.getLogger(my_logger)
        logger.debug('Log correctly initialized')
    except IOError as io_e:
        sys.exit('[ERROR]: invalid log configuration file ' + str(io_e))


def do_checks_on_urls():
    pass


def start_parser():
    logger.debug('Checking Script Parameters')
    parser = argparse.ArgumentParser(description='BPM BuildList Generator')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--full', action='store_const', const=2, help='Insert trunk | tags/rX-Y.Z')
    group.add_argument('--delta', action='store_const', const=2,
                       help='Insert [trunk | tags/rX-Y.Z] (artifacts)+')
    parser.add_argument('--env', choices=['dev', 'tst', 'uat', 'pre-prod', 'prod'], default='dev', required=True)
    parser.add_argument('--enableVersioning', choices=['true', 'false'], default='false', required=False)
    parser.add_argument('--targetTag', help='target tag option',
                        action='store_const', const=2, required=True)
    parser.add_argument('target_tag', help='Tag to be delivered to the deployer')
    parser.add_argument('startPoint', help='Current Point on which take the packages/projects')
    parser.add_argument('previousPoint', nargs='?', help='Previous point on which make differences (needed for .cnf)')

    parser.add_argument('artifacts', nargs='*', help='List of artifacts')
    args = parser.parse_args()
    _env = args.env
    _parameters = {}
    if args.full == 2:
        current_point = args.startPoint
        logger.debug("Requested a full on %s" % str(current_point))
        _parameters[bpm_c_point] = current_point
        _target_tag = args.target_tag
        return True, _env, _parameters, _target_tag
    if args.delta == 2:
        current_point = args.startPoint
        previous_point = args.previousPoint
        _target_tag = args.target_tag
        if not previous_point:
            parser.error('--delta requires a previous point on which make differences (needed for .cnf)')
        if args.targetTag != 2 or _target_tag is None:
            parser.error('In delta mode is needed the --targetTag option with the relative tag to de delivered '
                         'to the deployer')
        artifact_list = args.artifacts
        if len(artifact_list) == 0:
            parser.error('--delta requires at least one artifact')
        _parameters[bpm_c_point] = current_point
        _parameters[bpm_p_point] = previous_point
        _parameters[artf_list] = artifact_list
        logger.debug(
            "Requested Delta mode on current_point: %s previous_point: %s on target_tag: %s and artifact_list %s"
            % (str(current_point), str(previous_point), str(_target_tag), str(artifact_list)))
        return False, _env, _parameters, _target_tag


if __name__ == '__main__':
    config_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', 'config/properties.conf'))
    log_config_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', 'config/logger.conf'))
    # Parse config file
    conf = ParserTool.parse_config_file(config_file)
    init_log_from_file(log_config_file)
    # Starting parser
    is_a_full, env, parameters, target_tag = start_parser()
    try:
        svn_link = conf[bpm_root] + parameters[bpm_c_point]
        logger.debug("Checking link for current point for bpm %s " % svn_link)
        err_msg = SvnTool.check_svn_url(svn_link)
        if not err_msg:
            if is_a_full:
                logger.debug('Passed...Go Ahead')
                BpmDataHolder(conf, target_tag, env, svn_link)
            else:
                svn_p_link = conf[bpm_root] + parameters[bpm_p_point]
                logger.debug("Checking link for previous point for bpm %s " % str(svn_p_link))
                SvnTool.check_svn_url(svn_p_link)
                logger.debug('Current and Previous point are correct...Go Ahead')
                BpmDataHolder(conf, target_tag, env, svn_link, svn_p_link, parameters[artf_list])
        else:
            logger.error("Invalid Bpm Current point: %s, error %s" % (svn_link, err_msg))
            sys.exit(-2)
        logger.debug('Closing logger')
        logging.shutdown()

    except KeyError as e:
        logger.error('Error with config file...invalid key: %s ' % str(e))
        sys.exit(-2)

