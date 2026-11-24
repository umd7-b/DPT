"""PowerShell: python -m database import-v2|search|image|info|backup."""
import argparse
from contextlib import closing
import json
from pathlib import Path

from database import store


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    for name in ('import-v2','search','image','info','backup'):
        p = sub.add_parser(name)
        p.add_argument('--db',type=Path,default=store.DEFAULT_DB)
        if name == 'search':
            p.add_argument('--image',required=True)
            p.add_argument('--mode',choices=('all','A','B','AB'),default='all')
            p.add_argument('--top-k',type=int,default=5)
            p.add_argument('--weight-a',type=float,default=.5)
            p.add_argument('--weight-b',type=float,default=.5)
            p.add_argument('--no-save',action='store_true')
        if name == 'image':
            p.add_argument('--image-id',required=True)
        if name == 'backup':
            p.add_argument('--destination',type=Path,required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'import-v2':
            result = store.import_v2(args.db)
        elif args.command == 'backup':
            result = store.backup(args.db,args.destination)
        else:
            with closing(store.connect(args.db,readonly=args.command!='search' or args.no_save)) as c:
                if args.command == 'search':
                    result = store.search(c,args.image,mode=args.mode,top_k=args.top_k,
                        weight_a=args.weight_a,weight_b=args.weight_b,persist=not args.no_save)
                elif args.command == 'image':
                    result = store.get_image(c,args.image_id)
                else:
                    result = store.counts(c)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    except (ValueError,OSError,KeyError,store.sqlite3.Error) as error:
        parser.exit(2,f'Database error: {error}\n')


if __name__ == '__main__':
    main()
