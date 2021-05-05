#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os

import prometheus_client

from tinvest_collector import TinvestCollector


class EnvDefault(argparse.Action):
    def __init__(self, envvar, required=True, default=None, **kwargs):
        if not default and envvar:
            if envvar in os.environ:
                default = os.environ[envvar]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required,
                                         **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", type=str, required=True, action=EnvDefault, envvar="TINVEST_API_TOKEN",
                        help="Tinkoff Invest API token (TINVEST_API_TOKEN)")
    parser.add_argument("--account", type=str, required=True, action=EnvDefault, envvar="TINVEST_ACCOUNT_ID",
                        help="Tinkoff Invest Account ID (TINVEST_ACCOUNT_ID")
    parser.add_argument("--listen-host", type=str, default="0.0.0.0", action=EnvDefault, envvar="LISTEN_HOST",
                        help="Host to listen (LISTEN_HOST)")
    parser.add_argument("--listen-port", type=int, default=9993, action=EnvDefault, envvar="LISTEN_PORT",
                        help="Port to listen (LISTEN_PORT)")
    return parser.parse_args()


def main():
    args = parse_args()
    collector = TinvestCollector(args.token, args.account)
    prometheus_client.start_http_server(args.listen_port, args.listen_host, registry=collector)
    while True:
        pass


if __name__ == '__main__':
    main()
