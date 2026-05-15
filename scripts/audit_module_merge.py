#!/usr/bin/env python
"""Audit module rows that share (title, subject). Read-only."""
from collections import defaultdict
from app import app
from models import db, Module, Standard, ModuleStandardMapping

def main():
    with app.app_context():
        groups = defaultdict(list)
        for m in Module.query.all():
            groups[(m.title.strip(), m.subject)].append(m)

        merges = {k: v for k, v in groups.items() if len(v) > 1}
        print(f'Total modules: {Module.query.count()}')
        print(f'Distinct (title, subject) pairs: {len(groups)}')
        print(f'Pairs with >1 row (will merge): {len(merges)}')
        print()

        conflicts_total = 0
        for (title, subject), rows in sorted(merges.items()):
            survivor = min(rows, key=lambda r: r.id)
            duplicates = [r for r in rows if r.id != survivor.id]

            survivor_stds = {sm.standard_id for sm in
                             ModuleStandardMapping.query.filter_by(module_id=survivor.id).all()}
            dup_stds = set()
            for d in duplicates:
                dup_stds.update(sm.standard_id for sm in
                    ModuleStandardMapping.query.filter_by(module_id=d.id).all())

            conflicts = survivor_stds & dup_stds
            conflicts_total += len(conflicts)

            print(f'{subject:8s} {title!r:40s} '
                  f'survivor=id{survivor.id}(g{survivor.grade_level}) '
                  f'duplicates={[(d.id, d.grade_level) for d in duplicates]} '
                  f'union={len(survivor_stds | dup_stds)} stds  '
                  f'conflicts={len(conflicts)}')

        print()
        print(f'Total mapping conflicts (would dedupe to single row): {conflicts_total}')
        print(f'Mapping rows before merge: {ModuleStandardMapping.query.count()}')
        print(f'Mapping rows after merge:  {ModuleStandardMapping.query.count() - conflicts_total}')

if __name__ == '__main__':
    main()
