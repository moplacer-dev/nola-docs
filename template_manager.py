import os
import shutil
from models import TemplateFile, db
from datetime import datetime

class TemplateManager:
    """Manage template files for cloud deployment"""
    
    TEMPLATE_MAPPINGS = {
        'vocabulary_worksheet_master.docx': 'vocabulary_worksheet_master',
        'pba_worksheet_master.docx': 'pba_worksheet_master',
        'pre_test_worksheet_master.docx': 'pretest_worksheet_master',
        'post_test_worksheet_master.docx': 'posttest_worksheet_master',
        'generic_worksheet_master.docx': 'generic_worksheet_master',
        'family_briefing_master.docx': 'familybriefing_master',
        'rca_worksheet_master.docx': 'rca_worksheet_master',
        'module_guide_master.docx': 'moduleGuide_master',
        'module_ak_master.docx': 'moduleAnswerKey_master',
        'module_activity_sheet_master.docx': 'moduleActivitySheet_master',
        'student_module_workbook_master.docx': 'studentmoduleworkbook_master'
    }
    
    @classmethod
    def migrate_templates_to_db(cls):
        """Migrate local template files to database"""
        templates_dir = 'templates/docx_templates'
        
        for filename, template_name in cls.TEMPLATE_MAPPINGS.items():
            file_path = os.path.join(templates_dir, filename)
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                # Check if template already exists
                template = TemplateFile.query.filter_by(name=template_name).first()
                
                if template:
                    template.file_data = file_data
                    template.file_size = len(file_data)
                    template.updated_at = datetime.utcnow()
                else:
                    template = TemplateFile(
                        name=template_name,
                        display_name=filename.replace('_master.docx', '').replace('_', ' ').title(),
                        file_data=file_data,
                        file_size=len(file_data)
                    )
                    db.session.add(template)
                
                print(f"Migrated template: {filename} -> {template_name}")
        
        db.session.commit()
        print("Template migration completed")
    
    @classmethod
    def extract_template(cls, template_name, output_path):
        """Extract template from database to filesystem"""
        template = TemplateFile.query.filter_by(name=template_name, is_active=True).first()
        
        if not template:
            raise FileNotFoundError(f"Template {template_name} not found in database")
        
        with open(output_path, 'wb') as f:
            f.write(template.file_data)
        
        return output_path 