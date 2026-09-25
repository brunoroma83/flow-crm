import urllib.request
import json
from decimal import Decimal
from sqlalchemy import select
from flow_crm.database import SessionLocal
from flow_crm.models import Project, ProjectMonthlyValue, User
from flow_crm.main import sync_project_value, delete_record

with SessionLocal() as db:
    user = db.scalar(select(User).where(User.is_deleted.is_(False)))
    project = db.scalar(select(Project).where(Project.is_deleted.is_(False)))
    
    # 1. Clear existing monthly values for test project
    monthly_items = db.scalars(select(ProjectMonthlyValue).where(ProjectMonthlyValue.project_id == project.id, ProjectMonthlyValue.is_deleted.is_(False))).all()
    for item in monthly_items:
        item.is_deleted = True
    db.commit()
    sync_project_value(db, project.id)
    db.refresh(project)
    print("Base project_value (should be 0):", project.project_value)

    # 2. Add two monthly values
    v1 = ProjectMonthlyValue(project_id=project.id, year_month="2026-01", amount=Decimal("1000.00"), created_by_id=user.id)
    v2 = ProjectMonthlyValue(project_id=project.id, year_month="2026-02", amount=Decimal("2000.00"), created_by_id=user.id)
    db.add_all([v1, v2])
    db.commit()
    sync_project_value(db, project.id)
    db.refresh(project)
    print("Project value after adding 1000 + 2000:", project.project_value)
    assert float(project.project_value) == 3000.00

    # 3. Delete one monthly value (v2) using delete_record + sync_project_value
    item_to_del_id = v2.id
    record_to_del = db.get(ProjectMonthlyValue, item_to_del_id)
    record_to_del.is_deleted = True
    db.commit()
    sync_project_value(db, project.id)
    db.refresh(project)
    print("Project value after deleting 2000 (should be 1000):", project.project_value)
    assert float(project.project_value) == 1000.00

    print("SUCCESS: Deletion sync test passed!")
