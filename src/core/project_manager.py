"""Project management system for organizing papers."""
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from src.utils.database import Paper, Project, PaperProject, get_session

logger = logging.getLogger(__name__)


class ProjectError(Exception):
    """Base exception for project management errors."""
    pass


class ProjectNotFoundError(ProjectError):
    """Raised when project is not found."""
    pass


class ProjectManager:
    """Manage projects for organizing papers."""

    def __init__(self, session: Optional[Session] = None):
        """Initialize project manager."""
        self.session = session or get_session()

    def create_project(self, name: str, description: Optional[str] = None) -> int:
        """Create a new project."""
        logger.info(f"Creating project: {name}")
        try:
            project = Project(name=name, description=description)
            self.session.add(project)
            self.session.commit()
            return project.id
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create project: {e}")
            raise ProjectError(f"Failed to create project: {e}")

    def get_project(self, project_id: int) -> Project:
        """Get a project by ID."""
        project = self.session.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ProjectNotFoundError(f"Project with ID {project_id} not found")
        return project

    def get_project_by_name(self, name: str) -> Optional[Project]:
        """Get a project by name."""
        return self.session.query(Project).filter(Project.name == name).first()

    def list_projects(self) -> List[Project]:
        """List all projects."""
        return self.session.query(Project).order_by(Project.created_at.desc()).all()

    def update_project(
        self,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Project:
        """Update project details."""
        project = self.get_project(project_id)
        if name:
            project.name = name
        if description is not None:
            project.description = description
        if notes is not None:
            project.notes = notes
        
        try:
            self.session.commit()
            return project
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update project: {e}")
            raise ProjectError(f"Failed to update project: {e}")

    def delete_project(self, project_id: int) -> None:
        """Delete a project."""
        project = self.get_project(project_id)
        try:
            self.session.delete(project)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to delete project: {e}")
            raise ProjectError(f"Failed to delete project: {e}")

    def add_paper_to_project(self, paper_id: int, project_id: int) -> None:
        """Add a paper to a project."""
        # Check if already added
        exists = self.session.query(PaperProject).filter_by(
            paper_id=paper_id, project_id=project_id
        ).first()
        
        if exists:
            return

        try:
            paper_project = PaperProject(paper_id=paper_id, project_id=project_id)
            self.session.add(paper_project)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to add paper to project: {e}")
            raise ProjectError(f"Failed to add paper to project: {e}")

    def remove_paper_from_project(self, paper_id: int, project_id: int) -> None:
        """Remove a paper from a project."""
        link = self.session.query(PaperProject).filter_by(
            paper_id=paper_id, project_id=project_id
        ).first()
        
        if not link:
            return

        try:
            self.session.delete(link)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to remove paper from project: {e}")
            raise ProjectError(f"Failed to remove paper from project: {e}")

    def get_papers_in_project(self, project_id: int) -> List[Paper]:
        """Get all papers in a specific project."""
        project = self.get_project(project_id)
        return [pp.paper for pp in project.paper_projects]

    def get_projects_for_paper(self, paper_id: int) -> List[Project]:
        """Get all projects a paper belongs to."""
        paper = self.session.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            return []
        return [pp.project for pp in paper.paper_projects]
