"""Experiment in dependency detection."""

# Three stages:
# 1. Being able to rebuild everything beneath a value that has changed.
# 2. Caching downstream values to avoid rebuilds that are not necessary.
# 3. Using the cache to speed things up?

# key = (<object>, 'attribute'[, args_tuple])
#
# down[key1] = [key2, ...]
# up[key2] = [key1, ...]
# cache[key] = previously_computed_value

from collections import defaultdict
from contextlib import contextmanager
from functools import wraps
from inspect import ismethod
from pprint import pprint

_emptyset = frozenset()
_unavailable = object()

class Graph(object):

    def __init__(self):
        self.down = defaultdict(set)
        self.up = defaultdict(set)
        self.cache = {}
        self.stack = []

    def add(self, thing):
        thing._graph = self

    def push(self, key):
        if self.stack:
            key_beneath = self.stack[-1]
            self.up[key_beneath].add(key)
            self.down[key].add(key_beneath)
        self.stack.append(key)

    def pop(self):
        self.stack.pop()

    def run_consequences_of(self, key):
        todo = {key}
        while todo:
            key = todo.pop()
            old_value = self.cache.get(key, _unavailable)

            if len(key) == 2:
                obj, attr_name = key
                value = getattr(obj, attr_name)
            else:
                obj, method_name, args = key
                value = getattr(obj, method_name)(*args)

            if value == old_value:
                continue

            downs = self.down.get(key, _emptyset)
            todo |= downs
            pprint(downs)


class Thing(object):

    # def __setattr__(self, name, value):
    #     self.__dict__[name] = value

    def __getattribute__(self, name):
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        graph = self._graph
        print '  ' * len(graph.stack), 'getting', name
        key = (self, name)
        graph.push(key)
        try:
            value = object.__getattribute__(self, name)
        finally:
            graph.pop()
        if not ismethod(value) or value.im_self is not self:
            return value
        method = value
        graph = self._graph
        @wraps(method)
        def wrapper(*args, **kw):
            key = (self, name, args)
            graph.push(key)
            try:
                value = method(*args, **kw)
            finally:
                graph.pop()
            graph.cache[key] = value
            return value
        return wrapper

    def watch(self, function):
        @wraps(function)
        def wrapper(*args, **kw):
            self.start(function, args, kw)
            try:
                value = function(*args, **kw)
            finally:
                self.end(function, args, kw)
            return value
        return wrapper

    def start(self, function, args, kw):
        key = (function, args)
        if self.keys:
            edge = (self.keys[-1], key)
            self.edges.append(edge)
        self.keys.append(key)

    def end(self, function, args, kw):
        self.keys.pop()
