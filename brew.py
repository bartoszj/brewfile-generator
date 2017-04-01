#! /usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
import os.path
import collections

class Brew(object):
    def __init__(self, data):
        super(Brew, self).__init__()

        self.groups = []
        self.configurations = []

        self.parse_data(data)
        self.generate()

        # print(self.groups)
        # print(self.configurations)

    def parse_data(self, data):
        groups = data.get("groups", {}) or {}
        configurations = data.get("configurations", {}) or {}
        self.groups = [Group(g) for g in groups.iteritems()]
        self.configurations = [Configuration(c) for c in configurations.iteritems()]

    def generate(self):
        for c in self.configurations:
            c.groups = [self.group_with_name(g) for g in c.groups_names]
            c.generate()

    def group_with_name(self, name):
        return next((g for g in self.groups if g.name == name), None)

    def __str__(self):
        return "Groups: {}, configurations: {}".format(len(self.groups), len(self.configurations))

    def __repr__(self):
        return "<Groups:{}, configurations:{}>".format(len(self.groups), len(self.configurations))


class Group(object):
    def __init__(self, data):
        super(Group, self).__init__()
        self.name = data[0]

        self.taps = []
        self.privileged = None
        self.brews = []
        self.casks = []
        self.mas_apps = []

        self._parse(data[1])

    def _parse(self, data):
        if data is None:
            return
        self.taps = unique_sort(data.get("taps", []))
        privileged = data.get("privileged")
        self.privileged = Privileged(privileged) if privileged else None
        self.brews = unique_sort(data.get("brews", []))
        self.casks = unique_sort(data.get("casks", []))
        self.mas_apps = unique_sort(data.get("mas_apps", []))

    def __str__(self):
        return "Group: {}, taps: {}, brews: {}, casks: {}, mas: {}".format(self.name, len(self.taps), len(self.brews), len(self.casks), len(self.mas_apps))

    def __repr__(self):
        return "<Group:'{}', taps:{}, brews:{}, casks:{}, mas:{}>".format(self.name, len(self.taps), len(self.brews), len(self.casks), len(self.mas_apps))


class Privileged(object):
    def __init__(self, data):
        super(Privileged, self).__init__()
        self.brews = []
        self.casks = []
        self.mas_apps = []

        self._parse(data)

    def _parse(self, data):
        if data is None:
            return
        self.brews = unique_sort(data.get("brews", []))
        self.casks = unique_sort(data.get("casks", []))
        self.mas_apps = unique_sort(data.get("mas_apps", []))

    def __str__(self):
        return "Privileged: brews: {}, casks: {}, mas: {}".format(len(self.brews), len(self.casks), len(self.mas_apps))

    def __repr__(self):
        return "<Privileged:'brews:{}, casks:{}, mas:{}>".format(len(self.brews), len(self.casks), len(self.mas_apps))
        

class Configuration(object):
    def __init__(self, data):
        super(Configuration, self).__init__()
        self.name = data[0]
        self.groups_names = data[1]
        self.groups = []

    @property
    def brewfile_name(self):
        if self.name == "main":
            return "Brewfile"
        return "{}.Brewfile".format(self.name)

    @property
    def taps(self):
        return unique_sort(sorted([tap for g in self.groups for tap in g.taps]))

    @property
    def brews(self):
        return unique_sort(sorted([brew for g in self.groups for brew in g.brews]))

    @property
    def privileged_brews(self):
        return unique_sort(sorted([brew for g in self.groups if g.privileged for brew in g.privileged.brews]))
        
    @property
    def casks(self):
        return unique_sort(sorted([cask for g in self.groups for cask in g.casks]))

    @property
    def privileged_casks(self):
        return unique_sort(sorted([cask for g in self.groups if g.privileged for cask in g.privileged.casks]))
    
    @property
    def mas_apps(self):
        return unique_sort(sorted([mas_app for g in self.groups for mas_app in g.mas_apps]))

    @property
    def privileged_mas_apps(self):
        return unique_sort(sorted([mas_app for g in self.groups if g.privileged for mas_app in g.privileged.mas_apps]))

    def generate(self):
        print("Generating: {}".format(self.name))
        with open(self.brewfile_name, "w") as f:
            f.write("""# to run:
# $ brew tap Homebrew/bundle
# $ brew bundle
# // or
# $ brew bundle --file=<name>.Brewfile
#
# Tip:
# $ sudo chmod -R +ai "group:admin allow list,add_file,search,delete,add_subdirectory,delete_child,readattr,writeattr,readextattr,writeextattr,readsecurity,writesecurity,chown,file_inherit,directory_inherit" /usr/local/*

""")
            # Taps
            if len(self.taps) > 0:
                f.write("# Taps:\n")
                for t in self.taps:
                    f.write("tap '{}'\n".format(t))
                f.write("\n")

            # Privileged Brews
            if len(self.privileged_brews):
                f.write("# Privileged Brews:\n")
                for b in self.privileged_brews:
                    f.write(self.brew(b))
                f.write("\n")

            # Privileged Casks
            if len(self.privileged_casks):
                f.write("# Privileged Casks:\n")
                for c in self.privileged_casks:
                    f.write(self.cask(c))
                f.write("\n")

            # Privileged Mas apps
            if len(self.privileged_mas_apps):
                f.write("# Privileged Mac App Store:\n")
                for m in self.privileged_mas_apps:
                    f.write(self.mas(m))
                f.write("\n")

            # Brews
            if len(self.brews):
                f.write("# Brews:\n")
                for b in self.brews:
                    f.write(self.brew(b))
                f.write("\n")

            # Casks
            if len(self.casks):
                f.write("# Casks:\n")
                for c in self.casks:
                    f.write(self.cask(c))
                f.write("\n")

            # Mas apps
            if len(self.mas_apps):
                f.write("# Mac App Store:\n")
                for m in self.mas_apps:
                    f.write(self.mas(m))
                f.write("\n")

    @classmethod
    def brew(cls, b):
        return "brew {}\n".format(cls.brewfile_value(b))

    @classmethod
    def cask(cls, c):
        return "cask {}\n".format(cls.brewfile_value(c))

    @classmethod
    def mas(cls, m):
        return "mas {}\n".format(cls.brewfile_value(m))

    @classmethod
    def brewfile_value(cls, v):
        if isinstance(v, str):
            return "'{}'".format(v)

        # Dictionary:
        name = v.keys()[0]
        values = []
        for k, v in v[name].iteritems():
            value = None
            if isinstance(v, str):
                value = "{}: '{}'".format(k, v)
            elif isinstance(v, int):
                value = "{}: {}".format(k, v)
            elif isinstance(v, list):
                value = "{}: {}".format(k, cls.list(v))

            if value:
                values.append(value)

        return "'{}', {}".format(name, ", ".join(values))

    @classmethod
    def list(cls, l):
        values = ["'{}'".format(v) for v in l]
        return "[{}]".format(", ".join(values))

    def __str__(self):
        return "Configuration: {}, groups: {}".format(self.name, len(self.groups_names))

    def __repr__(self):
        return "<Configuration:'{}', groups:{}>".format(self.name, len(self.groups_names))


def unique_sort(seq):

    def get_key(element):
        if isinstance(element, collections.Hashable):
            return element
        elif isinstance(element, dict):
            return element.keys()[0]
        return None

    def unique(seq):
        values = []
        seen = set()
        for x in seq:
            key = get_key(x)

            if not (key in seen):
                seen.add(key)
                values.append(x)

        return values

    def sort(seq):
        return sorted(seq, key=get_key)

    return sort(unique(seq))

if __name__ == "__main__":
    brew_file = None
    if os.path.exists("brew.yml"):
        brew_file = "brew.yml"
    elif os.path.exists("brew.yaml"):
        brew_file = "brew.yaml"
    else:
        exit(1)

    with open(brew_file, "r") as f:
        brew = Brew(yaml.load(f))
