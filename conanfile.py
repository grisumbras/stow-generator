# import calendar
import os
import stat
# import shutil
# import time

from conans.model import Generator
from conans import ConanFile
from conans.errors import ConanException
from conans.paths import (
    BUILD_INFO_DEPLOY,
    CONAN_MANIFEST,
    CONANINFO,
)
# from conans.model.manifest import FileTreeManifest
# from conans.util.files import mkdir, md5sum

_FILTERED_FILES = [CONAN_MANIFEST, CONANINFO]


_LINKDIR=1
_LINKFILE=2
_MKDIR=3
_KEEPDIR=4
_KEEPFILE=5


class StowGeneratorPackage(ConanFile):
    name = "stow-generator"
    version = "0.1.0"
    url = "https://github.com/conan-stow-generator"
    license = "BSL-1.0"


class stow(Generator):
    # def deploy_manifest_content(self, copied_files):
    #     date = calendar.timegm(time.gmtime())
    #     file_dict = {}
    #     for f in copied_files:
    #         abs_path = os.path.join(self.output_path, f)
    #         file_dict[f] = md5sum(abs_path)
    #     manifest = FileTreeManifest(date, file_dict)
    #     return repr(manifest)

    @property
    def filename(self):
        return BUILD_INFO_DEPLOY

    @property
    def content(self):
        root_action = MkDir(
            self.conanfile.output, self.output_path, _FILTERED_FILES
        )
        for dep_name in self.conanfile.deps_cpp_info.deps:
            root_action.merge(self.conanfile.deps_cpp_info[dep_name].rootpath)

        # for rootpath in rootpaths:
        #     dep_root = Link(rootpath, excludes=_FILTERED_FILES)
        #     # dep_root = DirEntry(rootpath, link=True, excludes=_FILTERED_FILES)
        #     root = root.merge(dep_root, rootpaths)
        #
        # root.actualize(os.path.dirname(self.output_path))

        root_action.execute()

        return ""


class Action(object):
    def __init__(self, output, target):
        super(Action, self).__init__()
        self.output = output
        self._target = target

        self.basename = os.path.basename(target)

    def merge(self, path):
        raise ConanException(
            "%s.merge method is not implemented" % self.__class__.__name__
        )

    def execute(self):
        raise ConanException(
            "%s.execute method is not implemented" % self.__class__.__name__
        )


class MkDir(Action):
    def __init__(self, output, target, ignore=None):
        super(MkDir, self).__init__(output, target)
        self._ignore = ignore or []
        self._children = {}

    def merge(self, path):
        if not os.path.exists(path):
            raise ConanException("Source path %s does not exist" % path)

        filtered_children = (
            child for child in os.listdir(path) if child not in self._ignore
        )
        for child in filtered_children:
            if child not in self._children:
                action = link_from(child, self._target, path, self.output)
            else:
                full_path = os.path.join(path, child)
                action = self._children[child].merge(full_path)
            self._children[action.basename] = action

        return self

    def execute(self):
        if os.path.exists(self._target):
            self.output.info("skipped existing directory %s" % self._target)
        else:
            self.output.info("mkdir -p %s" % self._target)
            os.mkdir(self._target)
        for child in self._children.values():
            child.execute()


class Link(Action):
    def __init__(self, output, target, source):
        super(Link, self).__init__(output, target)
        self._source = source

    def execute(self):
        self.output.info("ln -s %s %s" % (self._source, self._target))
        os.symlink(self._source, self._target, self.is_dir())


    def check_self(self, path, info):
        return stat.S_ISLNK(info.st_mode) and self._source == os.readlink(path)

    @classmethod
    def is_dir(cls):
        raise ConanException(
            "%s.is_dir method is not implemented" % cls.__name__
        )


class LinkDir(Link):
    def merge(self, path):
        info = os.stat(path, follow_symlinks=False)
        if self.check_self(path, info):
            return self

        if not stat.S_ISDIR(info.st_mode):
            raise ConanException(
                "Cannot split %s into directory, merged %s is not a directory"
                % (self._target, path)
            )

        replacement = MkDir(self.output, self._target)
        replacement = replacement.merge(self._source)
        replacement = replacement.merge(path)
        return replacement

    @classmethod
    def is_dir(cls):
        return True


class LinkFile(Link):
    @classmethod
    def is_dir(cls):
        return False

    def merge(self, path):
        if self.check_self(path, os.stat(path, follow_symlinks=False)):
            return self

        raise ConanException(
            "Cannot split %s into directory, merged %s is not a directory"
            % (self._target, path)
        )

def link_from(child, target, source, output):
    source = os.path.join(source, child)
    info = os.stat(source, follow_symlinks=False)
    if stat.S_ISDIR(info.st_mode):
        Class = LinkDir
    else:
        Class = LinkFile

    target = os.path.join(target, child)
    action = Class(output, target, source)
    if os.path.exists(target):
        action = action.merge(target)
    return action


# class Action(object):
#     def __init__(self, name):
#         super(Action, self).__init__()
#         self.name = name
#
#     def is_dir(self):
#         return False
#
#     def conflict(self):
#         raise Exception("conflict at %s" % self.name)
#
#
# class PotentialDir(object):
#     def __init__(self):
#         super(PotentialDir, self).__init__()
#         self.excludes = []
#         self._children = None
#
#     @property
#     def children(self):
#         if self._children is None:
#             self._children = dict((
#                 self._make_child(name)
#                 for name in os.listdir(self.source)
#                 if name not in self.excludes
#             ))
#         return self._children
#
#     def child_class(self):
#         return self.__class__
#
#     def _make_child(self, name):
#         source = os.path.join(self.source, name)
#         return name, self.child_class()(source)
#
#     def merge_children(self, other, roots):
#         for child in other.children.values():
#             if not child.name in self.children:
#                 self.children[child.name] = child
#             else:
#                 target_child = self.children[child.name]
#                 self.children[child.name] = target_child.merge(child, roots)
#         return self
#
#     def actualize_children(self, target):
#         for child in self.children.values():
#             child.actualize(target)
#
#
# class FromSource(Action, PotentialDir):
#     def __init__(self, source, excludes=[]):
#         super(FromSource, self).__init__(os.path.basename(source))
#         self.source = source
#         self.excludes = excludes
#         self.info = os.stat(source, follow_symlinks=False)
#
#     def is_dir(self):
#         return 0 != stat.S_ISDIR(self.info.st_mode)
#
#
# class Skip(FromSource):
#     def __init__(self, source):
#         super(Skip, self).__init__(source)
#         self._linked_path = None
#
#     def conflict(self):
#         raise Exception("conflict at %s" % self.source)
#
#     @property
#     def linked_path(self):
#         if self._linked_path is None:
#             if not stat.S_ISLNK(self.info.st_mode):
#                 self._linked_path = ""
#             else:
#                 result = os.readlink(self.source)
#                 if not os.path.isabs(result):
#                     result = os.path.join(os.path.dirname(self.source), result)
#                 self._linked_path = result
#
#         return self._linked_path
#
#     def is_owned_by(self, roots):
#         path = self.linked_path
#         return any((path.startswith(root) for root in roots))
#
#     def merge(self, other, roots):
#         if isinstance(other, Skip):
#             self.conflict()
#
#         linked_path = self.linked_path
#         if linked_path:
#             if isinstance(other, Link) and linked_path == other.source:
#                 return self
#             elif self.is_owned_by(roots):
#                 dir = Split(linked_path)
#                 return dir.merge(other, roots)
#         elif self.is_dir() and other.is_dir():
#             return self.merge_children(other, roots)
#
#         self.conflict()
#
#     def actualize(self, output_path):
#         print("exists %s" % self.source)
#         if self.is_dir():
#             self.actualize_children(self.source)
#
#
# class Link(FromSource):
#     def merge(self, other, roots):
#         if isinstance(other, Skip):
#             self.conflict()
#         elif isinstance(other, Link):
#             if self.source == other.source:
#                 return self
#
#             if not self.is_dir():
#                 self.conflict()
#
#         dir = MkDir(self.name, source=self.source)
#         return dir.merge(other, roots)
#
#     def actualize(self, output_path):
#         target = os.path.join(output_path, self.name)
#         print("ln -s %s %s" % (self.source, target))
#         os.symlink(self.source, target, self.is_dir())
#
#
# class MkDir(Action, PotentialDir):
#     def __init__(self, name, source=None):
#         super(MkDir, self).__init__(name)
#         self.source = source
#         if source is not None:
#             self.info = os.stat(self.source, follow_symlinks=False)
#         else:
#             self.info = None
#             self._children = {}
#
#     def is_dir(self):
#         return True
#
#     def child_class(self):
#         return Link
#
#     def mode(self):
#         if self.info is None:
#             return None
#         else:
#             return stat.S_IMODE(self.info.st_mode)
#
#     def merge(self, other, roots):
#         if isinstance(other, Skip):
#             self.conflict()
#         elif isinstance(other, Link):
#             if not other.is_dir():
#                 self.conflict()
#
#         return self.merge_children(other, roots)
#
#     def actualize(self, output_path):
#         target = os.path.join(output_path, self.name)
#         print("mkdir %s" % target)
#         mode = self.mode()
#         if mode is not None:
#             os.mkdir(target, mode=self.mode())
#         else:
#             os.mkdir(target)
#         self.actualize_children(target)
#
#
# class Split(MkDir):
#     def __init__(self, source):
#         super(Split, self).__init__(os.path.basename(source), source)
#
#     def actualize(self, output_path):
#         target = os.path.join(output_path, self.name)
#         print("rm %s && mkdir %s" % (target, target))
#         os.remove(target)
#         os.mkdir(target)
#         self.actualize_children(target)
