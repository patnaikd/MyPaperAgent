"""Verification script for Projects feature."""
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.project_manager import ProjectManager
from src.core.paper_manager import PaperManager
from src.utils.database import init_database, get_session

def verify():
    print("🚀 Initializing database...")
    init_database()
    
    pm = ProjectManager()
    
    print("📝 Creating a test project...")
    name = "Test Project " + str(os.urandom(2).hex())
    project_id = pm.create_project(name, description="# This is a test\nWith **Markdown**.")
    print(f"✅ Created project {project_id}")
    
    print("📄 Fetching project...")
    project = pm.get_project(project_id)
    print(f"✅ Project name: {project.name}")
    print(f"✅ Project description: {project.description}")
    
    print("📒 Updating notes...")
    pm.update_project(project_id, notes="## Research Notes\n1. First note.")
    project = pm.get_project(project_id)
    print(f"✅ Project notes: {project.notes}")
    
    print("📚 Testing paper association...")
    # Get a paper if exists
    paper_manager = PaperManager()
    papers = paper_manager.list_papers(limit=1)
    if papers:
        paper = papers[0]
        print(f"📎 Adding paper '{paper.title}' to project...")
        pm.add_paper_to_project(paper.id, project_id)
        
        project_papers = pm.get_papers_in_project(project_id)
        if any(p.id == paper.id for p in project_papers):
            print("✅ Paper found in project!")
        else:
            print("❌ Paper NOT found in project!")
            
        print("🔗 Checking projects for paper...")
        linked_projects = pm.get_projects_for_paper(paper.id)
        if any(p.id == project_id for p in linked_projects):
            print("✅ Project found for paper!")
        else:
            print("❌ Project NOT found for paper!")
    else:
        print("⏭️ No papers in library, skipping paper association test.")
    
    print("✨ Verification complete!")

if __name__ == "__main__":
    verify()
