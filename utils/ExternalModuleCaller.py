import subprocess
import logging
import sys

__author__ = 'Roberto Palamaro'
__version__ = '1.1'


my_logger = 'BuildListGenerator'

logger = logging.getLogger(my_logger)


def generate_build_xml(jar_executable, svn_base, build_list_file, build_xml_path, cnf_folder=None):
    try:
        if cnf_folder:
            p = subprocess.Popen(['java', '-jar', jar_executable, svn_base, build_list_file, build_xml_path,
                                  cnf_folder], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, shell=True)
            v, err = p.communicate()
            if err:
                logger.error("An error occurs while launching command for BuildList.xml : %s " %
                             str(err.decode('utf-8')))
                sys.exit(-1)

        else:
            p = subprocess.Popen(['java', '-jar', jar_executable, svn_base, build_list_file, build_xml_path],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, shell=True)
            v, err = p.communicate()
            if err:
                logger.error("An error occurs while launching command for BuildList.xml : %s " %
                             str(err.decode('utf-8')))
                sys.exit(-1)
    except subprocess.CalledProcessError as e:
        logger.error("An error occurs while launching command for BuildList.xml : %s " % str(e))
        sys.exit(-1)
