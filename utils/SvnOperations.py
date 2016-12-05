import subprocess
import logging
import sys
import unicodedata

__author__ = 'Roberto Palamaro'
__version__ = '1.1'

list_command = 'ls'
info_command = 'info'
log_command = 'log'
export_command = 'export'
svn = 'svn'

# Our Logger
my_logger = 'BuildListGenerator'

logger = logging.getLogger(my_logger)


def check_svn_url(url):
    try:
        p = subprocess.Popen([svn, info_command, url], stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        if err:
            sys.exit('SVN_CHECK call error, get this error: ' + str(err.decode('utf8')))
    except ValueError as e:
        sys.exit('Svn check run with invalid command' + str(e))


def get_svn_log(url, incremental=False, search_arg=None):
    try:
        if incremental:
            if search_arg is None:
                raise RuntimeError('Cannot get log incremental without an artifact')
            p = subprocess.Popen([svn, log_command, '-v', '--xml', '--incremental', url, '--search=', search_arg],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        else:
            p = subprocess.Popen([svn, log_command, '--xml', '-v', url],
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        if err:
            sys.exit('Svn Log Call error: ' + str(err.decode('utf8')))
    except ValueError as e:
        sys.exit('Svn Log Cal run with invalid command' + str(e))


def get_svn_log_to_file(url, outfile, incremental=False, search_args=None):
    try:
        with open(outfile, 'w') as f:
            if incremental:
                if search_args is None:
                    raise ValueError('Cannot get log incremental without an artifact')
                f.write("<svnLog> \n")
                for artf in search_args:
                    p = subprocess.Popen(
                        [svn, log_command, '-v', url, '--xml', '--incremental', "--search=%s" % artf],
                        stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
                    (output, err) = p.communicate()
                    if err:
                        f.close()
                        return 'Svn Log Call error: ' + str(err.decode('utf8'))
                    f.write(output.decode('utf-8', errors='Ignore'))
                f.write("</svnLog>")
                f.close()
            else:
                p = subprocess.Popen([svn, log_command, '--xml', '-v', url],
                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
                (output, err) = p.communicate()
                if err:
                    return 'Svn Log Call error: ' + str(err.decode('utf8'))
                f.write(output.decode('utf-8', errors='Ignore'))
                f.close()
    except ValueError as e:
        raise RuntimeError('Svn Log Cal run with invalid command' + str(e))
    except OSError as e:
        raise RuntimeError('Svn Log Cal error with output file' + str(outfile) + 'error: ' + str(e))


def get_list_repository(url, depth='immediates'):
    try:
        p = subprocess.Popen([svn, list_command, '--depth', depth, url],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        if err:
            logger.error("Error while listing this path -> %s" % url)
        else:
            return list(output.decode('utf-8').splitlines())
    except ValueError as e:
        raise RuntimeError('Svn Log Cal run with invalid command' + str(e))


def check_out_file(url, path=None):
    try:
        _path = '.'
        if path:
            _path = path
        p = subprocess.Popen([svn, export_command, '--force', url, _path],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        if err:
            logger.error("Error while export the file -> %s" % url)
            raise RuntimeError('Cannot check out file at this url %s \n error: %s ' % (url, str(err.decode('utf-8'))))

    except ValueError as e:
        raise RuntimeError('Svn Log Cal run with invalid command' + str(e))