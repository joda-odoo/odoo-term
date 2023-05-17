#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
import atexit
import os
import readline
import requests
import sys
import re
from getpass import getpass

from dataclasses import dataclass
from enum import auto, Enum

cookies = []
url = ""

class FlagType(Enum):
    NUMBER = auto()
    STRING = auto()
    BOOL = auto()
    MODEL = auto()
    DICT = auto()
    LIST = auto()


@dataclass 
class Flag:
    short: str
    long: str
    type: FlagType
    help: str
    mendatory: bool = False

    def __str__(self):
        if self.mendatory:
            return f"<-{self.short}, --{self.long} [{self.type.name}]>\n      {self.help}"
        else:
            return f"[-{self.short}, --{self.long} [{self.type.name}]]\n      {self.help}"


@dataclass
class LazyDict:
    d = {}

    def __getitem__(self, key):
        if key in self.d:
            return self.d[key]
        else:
            return None
    
    def __setitem__(self, key, value):
        self.d[key] = value

    def __len__(self):
        return len(self.d)

    def get_or(self, keys, default=None):
        for key in keys:
            if key in self.d:
                return self.d[key]

        if callable(default):
            return default()
        else:
            return default

    def get(self, keys):
        for key in keys:
            if key in self.d:
                return self.d[key]
        raise KeyError(f"Key not found in {keys}")

class Command:
    def __init__(self, name, flags, helper, example, func):
        self.__name = name
        self.__flags = flags
        self.__helper = helper
        self.__func = func
        self.__example = example

    def __call__(self, args, *_, **kwargs):
        arguments = LazyDict()

        i = 0
        while i < len(args):
            if args[i].startswith("--"):
                key = args[i][2:]
                flag = list(filter(lambda x: x.long == key, self.__flags))[0]

                match flag.type:
                    case FlagType.NUMBER:
                        arguments[key] = int(args[i+1])
                    case FlagType.STRING:
                        s = ""

                        if args[i+1].startswith("\'") or args[i+1].startswith("\""):
                            j = 0

                            while True:
                                if i + j + 1 >= len(args):
                                    break

                                s += ' ' + args[i + j + 1]

                                if args[i + j + 1].endswith("\'") or args[i + j + 1].endswith("\""):
                                    break

                                j += 1
                            
                            s = s.lstrip()[1:-1]
                        else:
                            s = args[i+1]

                        arguments[key] = s
                    case FlagType.BOOL:
                        if args[i+1] != "-":
                            arguments[key] = bool(args[i+1])
                        else:
                            arguments[key] = True
                    case FlagType.MODEL:
                        arguments[key] = args[i+1]
                    case FlagType.DICT:
                        j = 0
                        dic = ""

                        while True:
                            if i + j + 1 >= len(args):
                                break

                            dic += ' ' + args[i + j + 1]

                            if args[i + j + 1].endswith("}"):
                                break

                            j += 1

                        arguments[key] = ast.literal_eval(dic)
                    case FlagType.LIST:
                        arguments[key] = [int(x) if x.isdigit() else x for x in args[i+1].split(",")]

            elif args[i].startswith("-"):
                key = args[i][1]
                flag = list(filter(lambda x: x.short == key, self.__flags))[0]

                match flag.type:
                    case FlagType.NUMBER:
                        arguments[key] = int(args[i+1])
                    case FlagType.STRING:
                        s = ""

                        if args[i+1].startswith("\'") or args[i+1].startswith("\""):
                            j = 0

                            while True:
                                if i + j + 1 >= len(args):
                                    break

                                s += ' ' + args[i + j + 1]

                                if args[i + j + 1].endswith("\'") or args[i + j + 1].endswith("\""):
                                    break

                                j += 1
                            
                            s = s.lstrip()[1:-1]
                        else:
                            s = args[i+1]

                        arguments[key] = s
                    case FlagType.BOOL:
                        if args[i+1] != "-":
                            arguments[key] = bool(args[i+1])
                        else:
                            arguments[key] = True
                    case FlagType.MODEL:
                        arguments[key] = args[i+1]
                    case FlagType.DICT:
                        j = 0
                        dic = ""

                        while True:
                            if i + j + 1 >= len(args):
                                break

                            dic += ' ' + args[i + j + 1]

                            if args[i + j + 1].endswith("}"):
                                break

                            j += 1

                        arguments[key] = ast.literal_eval(dic)
                    case FlagType.LIST:
                        arguments[key] = [int(x) if x.isdigit() else x  for x in args[i+1].split(",")]

            i += 2

        self.__func(arguments, *_, **kwargs)

    @property
    def description(self):
        return self.__helper

    @property
    def name(self):
        return self.__name

    @property
    def helper(self):
        flag = "\n\n    ".join([str(i) for i in self.__flags])
        return f"""
NAME
    {self.__name} - {self.__helper}     

ARGUMENTS
    {flag if flag else "No arguments"}

EXAMPLE
    {self.__example}
"""

def help_command(args):
    global COMMANDS

    cmd = args.get_or(("c", "cmd"), None)

    if not args:
        print()
        print("\n".join([f"{c.name} - {c.description}" for c in COMMANDS]))
        print()
        return

    for c in COMMANDS:
        if c.name == cmd:
            print(c.helper)
            return

def connector(args):
    global cookies
    global url

    username = args.get_or(("u", "user"), lambda: input("Username: "))
    password = args.get_or(("w", "password"), lambda: getpass("Password: "))
    port = args.get_or(("p", "port"), 8069)
    hostname = args.get(("h", "host"))
    ssl = args.get_or(("S", "ssl"), False)
    url = f"http{'s' if ssl else ''}://{hostname}:{port}/"

    r = requests.get(f"{url}/web/login")

    if not 'csrf' in r.content.decode():
        print("Failed to fetch the homepage. Check your configuration.", file=sys.stderr)
        return

    csrf = re.search(r'name="csrf_token" value="([^"]*)"', r.content.decode()).groups()[0]
    data = {'csrf_token': csrf, 'login': username, 'password': password}

    resp = requests.post(f"{url}/web/login", data=data, cookies=r.cookies)
    if resp.ok:
        print("Connected to Odoo instance")
    else:
        print("Failed to connect to Odoo instance", file=sys.stderr)
        return

    cookies = resp.cookies

def write_record(args):
    global url, cookies

    model = args.get(("m", "model"))
    values = args.get(("v", "values"))
    identifiers = args.get(("i", "id"))

    json_data = {
        "id": 20,
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "args": [identifiers, values],
            "model": model,
            "method": "write",
            "kwargs": {},
        },
    }

    resp = requests.post(f"{url}/web/dataset/call_kw", json=json_data, cookies=cookies)

    if resp.status_code == 200:
        print("Record updated")
    else:
        print("Failed to update record", file=sys.stderr)
        print(resp.content.decode(), file=sys.stderr)

def create_record(args):
    global url, cookies

    model = args.get(("m", "model"))
    values = args.get(("v", "values"))

    json_data = {
        "id": 16,
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "args": [values],
            "model": model,
            "method": "create",
            "kwargs": {},
        },
    }

    resp = requests.post(f"{url}/web/dataset/call_kw", json=json_data, cookies=cookies)

    if resp.status_code == 200:
        print("Record created")
    else:
        print("Failed to create record", file=sys.stderr)
        print(resp.content.decode(), file=sys.stderr)

def read_record(args):
    global url, cookies

    model = args.get(("m", "model"))
    identifiers = args.get(("i", "id"))
    fields = args.get_or(("f", "fields"), [])

    json_data = {
        "id": 60,
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "args": [identifiers, fields],
            "model": model,
            "method": "read",
            "kwargs": {},
        },
    }

    resp = requests.post(f"{url}/web/dataset/call_kw", json=json_data, cookies=cookies)

    if resp.status_code == 200:
        print(resp.json())
    else:
        print("Failed to read record", file=sys.stderr)
        print(resp.content.decode(), file=sys.stderr)

def search_record(args):
    global url, cookies

    model = args.get(("m", "model"))
    domain = args.get_or(("d", "domain"), [])
    offset = args.get_or(("of", "offset"), 0)
    limit = args.get_or(("l", "limit"), 80)
    order = args.get_or(("o", "order"), "")
    fields = args.get_or(("f", "fields"),[])

    json_data = {
        "id": 25,
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "args": [],
            "model": model,
            "method": "search_read",
            "kwargs": {
                "limit": limit,
                "offset": offset,
                "order": order,
                "fields": fields,
                "domain": domain,
            },
        },
    }

    resp = requests.post(f"{url}/web/dataset/call_kw", json=json_data, cookies=cookies)

    if resp.status_code == 200:
        print(resp.json())
    else:
        print("Failed to search record", file=sys.stderr)
        print(resp.content.decode(), file=sys.stderr)


COMMANDS = [
    Command("help", [Flag("c", "cmd", FlagType.STRING, "The command to consult")], "Print this help or command info", "help -c create", help_command),

    Command("exit", [], "Exit from odoo-term", "exit", lambda x: exit(0)),

    Command("connect", [
        Flag("h", "host", FlagType.STRING, "Hostname of the Odoo instance", True), 
        Flag("p", "port", FlagType.NUMBER, "Port of the Odoo instance (default: 8069)"),
        Flag("u", "user", FlagType.STRING, "Username of the Odoo instance"),
        Flag("w", "password", FlagType.STRING, "Password of the Odoo instance"),
        Flag("S", "ssl", FlagType.BOOL, "Use SSL to connect to the Odoo instance (default: False)")
    ], "Connect to Odoo server", "connect -h localhost -p 8069 -u admin -w admin", connector),

    Command("write", [
        Flag("m", "model", FlagType.MODEL, "Model to write to", True),
        Flag("i", "id", FlagType.LIST, "ID of the record to write to", True),
        Flag("v", "value", FlagType.DICT, "Values to write to the record", True),
    ], "Update a record", "write -m res.partner -i 1 -v {'name': 'John Doe'}", write_record),

    Command("create", [
        Flag("m", "model", FlagType.MODEL, "Model to create a record in", True),
        Flag("v", "value", FlagType.DICT, "Values to write to the record", True),
    ], "Create a record", "create -m res.partner -v {'name': 'John Doe'}", create_record), 

    Command("read", [
        Flag("m", "model", FlagType.MODEL, "Model to read from", True),
        Flag("i", "id", FlagType.LIST, "ID of the record to read from", True),
        Flag("f", "fields", FlagType.LIST, "Fields to read from the record"),
    ], "Read a record", "read -m res.partner -i 1 -f ['name', 'email']", read_record),
    
    Command("search", [
        Flag("m", "model", FlagType.MODEL, "Model to search in", True),
        Flag("f", "fields", FlagType.LIST, "Fields to search in"),
        Flag("d", "domain", FlagType.LIST, "Domain to search in"),
        Flag("l", "limit", FlagType.NUMBER, "Limit of records to return (default: 80)"),
        Flag("of", "offset", FlagType.NUMBER, "Offset of records to return (default: 0))"),
        Flag("o", "order", FlagType.STRING, "Order of records to return"),
    ], "Launch orm search query", "search -m res.partner -f * -l 100 -of 5 -o 'id DESC, name'", search_record)
        
]

if __name__ == "__main__":
    HIST_FILE = os.path.join(os.path.expanduser("~"), ".odoo-term-history")

    if os.path.exists(HIST_FILE):
        readline.read_history_file(HIST_FILE)

    atexit.register(readline.write_history_file, HIST_FILE)

    while True:
        try:
            line = input("> ")

            if line:
                command, args = line.split()[0], line.split()[1:]
                list(filter(lambda x: x.name == command, COMMANDS))[0](args)

        except EOFError:
            print()
            exit(0)
        except KeyboardInterrupt:
            print()
            continue
    