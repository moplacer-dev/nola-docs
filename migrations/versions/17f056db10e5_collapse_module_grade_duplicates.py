"""collapse module grade duplicates

Revision ID: 17f056db10e5
Revises: a0a02b6cac87
Create Date: 2026-05-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '17f056db10e5'
down_revision = 'a0a02b6cac87'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Step A: find merge groups (portable across Postgres + SQLite)
    pairs = conn.execute(sa.text("""
        SELECT title, subject, MIN(id) AS survivor_id, COUNT(*) AS row_count
        FROM modules
        GROUP BY title, subject
        HAVING COUNT(*) > 1
    """)).fetchall()

    repointed = 0
    skipped_conflicts = 0
    deleted_modules = 0

    for pair in pairs:
        survivor = pair.survivor_id
        all_ids = [r.id for r in conn.execute(sa.text(
            "SELECT id FROM modules WHERE title = :t AND subject = :s ORDER BY id"
        ), {'t': pair.title, 's': pair.subject}).fetchall()]
        duplicates = [i for i in all_ids if i != survivor]

        for dup in duplicates:
            # Count conflicts FIRST, before the INSERT below mutates survivor's
            # mapping set. If reordered, the EXISTS clause would match the rows
            # we just inserted and inflate skipped_conflicts.
            conflict_count = conn.execute(sa.text("""
                SELECT COUNT(*) FROM module_standard_mappings m
                WHERE m.module_id = :dup
                  AND EXISTS (
                      SELECT 1 FROM module_standard_mappings s
                      WHERE s.module_id = :survivor
                        AND s.standard_id = m.standard_id
                  )
            """), {'survivor': survivor, 'dup': dup}).scalar()
            skipped_conflicts += conflict_count

            # Repoint mappings, skipping any standard already mapped to survivor.
            result = conn.execute(sa.text("""
                INSERT INTO module_standard_mappings
                    (module_id, standard_id, source, created_at)
                SELECT :survivor, m.standard_id, m.source, m.created_at
                FROM module_standard_mappings m
                WHERE m.module_id = :dup
                  AND NOT EXISTS (
                      SELECT 1 FROM module_standard_mappings s
                      WHERE s.module_id = :survivor
                        AND s.standard_id = m.standard_id
                  )
            """), {'survivor': survivor, 'dup': dup})
            repointed += result.rowcount

            # Delete the duplicate's mappings (now redundant or merged)
            conn.execute(sa.text(
                "DELETE FROM module_standard_mappings WHERE module_id = :dup"
            ), {'dup': dup})

            # Delete the duplicate module
            conn.execute(sa.text("DELETE FROM modules WHERE id = :dup"), {'dup': dup})
            deleted_modules += 1

    # Step B + C: replace unique constraint and drop column.
    # The prior migration a0a02b6cac87 wrapped its constraint operations in
    # try/except, so prod's actual constraint state is uncertain. Inspect first.
    inspector = inspect(conn)
    existing_constraints = {c['name'] for c in inspector.get_unique_constraints('modules')}
    existing_columns = {c['name'] for c in inspector.get_columns('modules')}

    with op.batch_alter_table('modules', schema=None) as batch_op:
        if 'uq_module_title_subject_grade' in existing_constraints:
            batch_op.drop_constraint('uq_module_title_subject_grade', type_='unique')
        if 'uq_module_title_subject' in existing_constraints:
            # Could exist if a0a02b6cac87's drop step was swallowed. We're about
            # to recreate it on the correct columns below, so drop the old one.
            batch_op.drop_constraint('uq_module_title_subject', type_='unique')
        batch_op.create_unique_constraint('uq_module_title_subject', ['title', 'subject'])
        if 'grade_level' in existing_columns:
            batch_op.drop_column('grade_level')

    print(f'Repointed mappings: {repointed}')
    print(f'Skipped conflict mappings: {skipped_conflicts}')
    print(f'Deleted duplicate module rows: {deleted_modules}')


def downgrade():
    # Intentionally not implemented. The per-grade module split cannot be
    # reconstructed from the post-merge schema; recovery requires restoring
    # from the pre-migration database backup.
    raise NotImplementedError(
        "Migration 17f056db10e5 is one-way; the per-grade module split "
        "cannot be reconstructed from post-merge schema. To revert, "
        "restore the database from the pre-migration backup."
    )
