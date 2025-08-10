"""Fix module unique constraint to include grade_level

Revision ID: a0a02b6cac87
Revises: e753b30421b6
Create Date: 2025-08-09 20:06:50.342451

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a0a02b6cac87'
down_revision = 'e753b30421b6'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the old constraint that only includes title and subject
    with op.batch_alter_table('modules', schema=None) as batch_op:
        batch_op.drop_constraint('uq_module_title_subject', type_='unique')
        # Add new constraint that includes grade_level
        batch_op.create_unique_constraint('uq_module_title_subject_grade', ['title', 'subject', 'grade_level'])


def downgrade():
    # Revert back to old constraint
    with op.batch_alter_table('modules', schema=None) as batch_op:
        batch_op.drop_constraint('uq_module_title_subject_grade', type_='unique')
        batch_op.create_unique_constraint('uq_module_title_subject', ['title', 'subject'])
