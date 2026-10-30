"""Import maintained examples into an already-migrated, isolated Dify test DB.

Requires the selected Dify API Python environment. No models/plugins are called.
"""
import argparse
import json
import os
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dify-source', required=True, type=Path)
parser.add_argument('--report', required=True, type=Path)
args = parser.parse_args()
if os.environ.get('DB_HOST') not in {'127.0.0.1', 'localhost', '::1'} or not os.environ.get('DB_DATABASE', '').startswith('dify_skill_'):
    parser.error('Use a loopback DB_HOST and an isolated DB_DATABASE starting with dify_skill_.')
if os.environ.get('REDIS_HOST') not in {'127.0.0.1', 'localhost', '::1'}:
    parser.error('Use an isolated Redis with an explicit loopback REDIS_HOST.')
if not os.environ.get('STORAGE_LOCAL_PATH'):
    parser.error('Set STORAGE_LOCAL_PATH to an isolated temporary directory.')
# Dify defaults to OpenDAL, which would otherwise ignore STORAGE_LOCAL_PATH.
os.environ['STORAGE_TYPE'] = 'local'
sys.path.insert(0, str(args.dify_source.resolve() / 'api'))
from app_factory import create_app
from extensions.ext_database import db
from models.account import Account, Tenant, TenantAccountJoin, TenantAccountRole
from models.model import App
from models.workflow import Workflow
from services.app_dsl_service import AppDslService
from sqlalchemy import select
_, app = create_app()
root=Path(__file__).resolve().parents[2]
results=[]
with app.app_context(), app.test_request_context('/'):
    account=Account(name='Skill validation',email='skill-test@example.invalid',interface_language='en-US',timezone='UTC')
    tenant=Tenant(name='Isolated DSL validation')
    db.session.add_all([account,tenant]);db.session.flush()
    db.session.add(TenantAccountJoin(tenant_id=tenant.id,account_id=account.id,role=TenantAccountRole.OWNER))
    db.session.commit()
    account.set_current_tenant_with_session(tenant,session=db.session)
    for path in sorted((root/'examples/dify-1.16.0').glob('*.yml'))+sorted((root/'examples/dify-1.18.0').glob('*.yml')):
        try:
            result=AppDslService(db.session).import_app(account=account,import_mode='yaml-content',yaml_content=path.read_text())
            db.session.commit()
            record={'file':str(path.relative_to(root)),'status':str(result.status),'error':result.error,'warnings':[w.model_dump(mode='json') for w in result.warnings]}
            if result.app_id:
                persisted=db.session.get(App,result.app_id)
                record['persisted']=persisted is not None
                if persisted and persisted.mode in ('workflow','advanced-chat'):
                    workflow=db.session.scalar(select(Workflow).where(Workflow.app_id==persisted.id, Workflow.version=='draft'))
                    record['persisted_nodes']=len(workflow.graph_dict['nodes']) if workflow else None
            results.append(record)
        except Exception as exc:
            db.session.rollback();results.append({'file':str(path.relative_to(root)),'status':'exception','error':str(exc)})
        print(json.dumps(results[-1],ensure_ascii=False),flush=True)
args.report.write_text(json.dumps(results,ensure_ascii=False,indent=2))
raise SystemExit(0 if all(r['status'] in ('completed','completed-with-warnings') and r.get('persisted') for r in results) else 1)
