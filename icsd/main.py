import argparse
from icsd.crawler import main as scrape_all
from icsd.collection_coder import main as enumerate_all
from sys import argv
import sys
from icsd.queryer import Queryer

def command_scrape(args):
    if args.all:
        scrape_all()

    if args.code > 0:
        query = {
            "icsd_collection_code": args.code,
        }
        queryer = Queryer(query=query, structure_source=args.source)
        queryer.perform_icsd_query()

    if args.composition != "":
        query = {
            "composition": args.composition,
        }
        queryer = Queryer(query=query, structure_source=args.source)
        queryer.perform_icsd_query()


def command_enumerate(args):
    enumerate_all()


def command_ls():
    pass

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_scrape = subparsers.add_parser('scrape', help='scrape ICSD')
    parser_scrape.add_argument('-A', '--all', action='store_true',
                               help='scrape everything using ICSD Collection Code')
    parser_scrape.add_argument(
        '--composition', help='scrape everything using ICSD Collection Code', default="", type=str)
    parser_scrape.add_argument(
        '--code', help='scape by ICSD Collection Code (e.g. 2000)', default=-1, type=int)
    parser_scrape.add_argument(
        '--source', help='structure source (E (experiment), T (theory), or A (all, default))', default="A", type=str)
    parser_scrape.set_defaults(handler=command_scrape)

    parser_enumerate = subparsers.add_parser(
        'enumerate', help='make list of all ICSD codes')
    parser_enumerate.set_defaults(handler=command_enumerate)

    parser_ls = subparsers.add_parser(
        'ls', help='report already retrieved entries')
    parser_ls.add_argument(
        '--code', help='ICSD Collection Code (e.g. 2000, 2000-2050)', default="", type=str)

    parser_ls = subparsers.add_parser(
        'coverage', help='show coverge of your database')
    parser_ls.add_argument(
        '--code', help='ICSD Collection Code (e.g. 2000, 2000-2050)', default="", type=str)
    parser_ls.set_defaults(handler=command_ls)

    args = parser.parse_args()
    print(args)
    # self.arg_parser.parse_args(args=argv[1:])
      #  args = self.arg_parser.parse_args(args=argv[1:])
    #
    try:
        getattr(args, "handler")
    except AttributeError:
        parser.print_help()
        sys.exit(0)

    args.handler(args)


if __name__ == '__main__':
    main()

