import logging
import utils.SvnOperations as Svn_Tool
import utils.ParsingOperations as ParserTool
from collections import defaultdict
import os

__author__ = 'Roberto Palamaro'
__version__ = '1.0'

my_logger = 'BuildListGenerator'

logger = logging.getLogger(my_logger)


class VersionHolder:

    def __init__(self, url, package_flag=True, full_mode=False, verbose=False):
        self.full_mode = full_mode
        self.verbose = verbose
        self.manifest = '/manifest.v3'
        self.manifest_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'manifest.v3'))
        self.package_flag = package_flag
        self.url = url
        self.versions = defaultdict(str)
        if full_mode:
            if self.package_flag:
                self.get_versions_for_all_packages(self.url)
            else:
                self.get_runtime_version_full(self.url)

    def __del__(self):
        if self.package_flag:
            if os.path.exists(self.manifest_file):
                os.remove(self.manifest_file)

    def get_version_for_package(self, package):
        if self.full_mode:
            try:
                return self.versions[package]
            except KeyError:
                logger.warning("Request a version for a package %s that doesn't exists",
                               str(package))
        else:
            # Single mode
            return self.get_version_single_package(package)

    def get_versions_for_all_packages(self, url):
        elements = Svn_Tool.get_list_repository(url)
        for el in elements:
            self.get_version_single_package(el)
        return self.versions

    def get_version_single_package(self, package):
        try:
            Svn_Tool.check_out_file(self.url + package + self.manifest)
            (version, dep, startup) = ParserTool.parse_manifest(self.manifest_file, self.verbose)
            if self.verbose:
                self.versions[package] = "%s \n Dependencies \n %s \n Startup: \n %s " % (version, dep, startup)
            else:
                self.versions[package] = version
            if os.path.exists(self.manifest_file):
                os.remove(self.manifest_file)
            else:
                logger.warning("Manifest for %s doesn't exits" % package)
            return version
        except RuntimeError:
            logger.error('Error occurs while getting version for process %s ' % package)

    def get_runtime_version(self, process):
        try:
            _process = str(process)
            if not _process.endswith('.process'):
                _process_extension = '.process'
                _process += _process_extension
            Svn_Tool.check_out_file(self.url+_process)
            process_xml = _process.split('/')[-1]
            process_file = os.path.join(os.getcwd(), process_xml)
            runtime_version = ParserTool.parse_process_file(process_file)
            if runtime_version is not None:
                self.versions[_process] = runtime_version
                if os.path.exists(process_file):
                    os.remove(process_file)
                return runtime_version
            else:
                logger.warning("Runtime version not extracted from this file %s", str(_process))
        except RuntimeError:
            logger.error('Error occurs while getting version for process %s ' % process)

    def get_runtime_version_full(self, url):
        repo_list = Svn_Tool.get_list_repository(url, depth='infinity')
        for el in repo_list:
            element = str(el)
            if element.endswith('.process'):
                self.get_runtime_version(element)
        return self.versions

    def get_versions(self):
        return self.versions

    def get_version_for_object(self, obj):
        if obj in self.versions.keys():
            return self.versions[obj]
        else:
            if self.package_flag:
                return self.get_version_single_package(obj)
            else:
                return self.get_runtime_version(obj)


