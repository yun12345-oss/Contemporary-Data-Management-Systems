r"""可重复的真实API调用链：只使用本次随机临时数据库，不连接业务库。
在1_代码目录执行：.\.runtime\Scripts\python.exe ..\3_测试用例\测试证据\API调用链示例.py
依赖：项目已安装、MongoDB副本集运行于27019；输出不计入既有260项测试。
"""
from pathlib import Path
from copy import deepcopy
import argparse, hashlib, json, os, sys
from uuid import uuid4
from bson import json_util

MATERIALS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MATERIALS / '1_代码/backend'))
from fastapi.testclient import TestClient
from pymongo import MongoClient
from app.main import create_app
from app.database import initialize


def run(output):
    suffix = uuid4().hex[:16]
    names = ['survey_lab_materials_' + suffix, 'survey_lab_materials_validation_' + suffix]
    mongo = MongoClient(os.getenv('TEST_MONGO_URI', 'mongodb://127.0.0.1:27019/?replicaSet=survey-rs'), tz_aware=True, serverSelectionTimeoutMS=5000)
    db, validation = [mongo[n] for n in names]
    events = []
    try:
        mongo.admin.command('ping')
        app = create_app(db, 'materials-demo-test-secret-not-production-32-chars')
        with TestClient(app) as a, TestClient(app) as b:
            def call(c, method, path, body=None, status=200):
                r = c.request(method, '/api' + path, json=body) if body is not None else c.request(method, '/api' + path)
                assert r.status_code == status, (method, path, r.status_code, r.text)
                data = r.json()
                safe_body = {k: ('<测试密码省略>' if k == 'password' else v) for k,v in (body or {}).items()}
                events.append({'step':len(events)+1,'method':method,'path':'/api'+path,'input':safe_body if body is not None else None,'status':r.status_code,'output':data})
                return data
            a_user = call(a,'POST','/auth/register',{'username':'material_owner_'+suffix[:8],'password':'TestPass123!'},201)
            b_user = call(b,'POST','/auth/register',{'username':'material_peer_'+suffix[:8],'password':'TestPass123!'},201)
            content = {'type':'number','title':'年龄（周岁）','options':[],'validation':{'min':0,'max':120,'integer_only':True}}
            q1 = call(a,'POST','/questions',{'content':content,'change_note':'材料示例初版'},201)
            qid=q1['question']['_id'];v1=q1['version']['_id']
            content2=deepcopy(content);content2['title']='年龄（填写时的周岁）'
            q2=call(a,'POST',f'/questions/{qid}/versions',{'revision':q1['question']['revision'],'parent_version_id':v1,'content':content2,'change_note':'明确填写时点'},201)
            v2=q2['version']['_id']
            lib=call(a,'POST','/libraries',{'name':'基础信息题库','description':'固定版本示例'},201)
            call(a,'POST',f"/libraries/{lib['_id']}/items",{'revision':lib['revision'],'question_version_id':v1,'position':0},201)
            call(a,'POST','/grants',{'kind':'use','question_version_id':v1,'username':b_user['username'],'survey_id':None},201)
            s=call(a,'POST','/surveys',{'title':'材料演示问卷'},201);sid=s['_id']
            s=call(a,'POST',f'/surveys/{sid}/questions/import',{'revision':s['revision'],'question_version_id':v1})
            draft=deepcopy(s['draft']);draft['allow_anonymous']=True;draft['allow_repeat']=True
            s=call(a,'PUT',f'/surveys/{sid}/draft',{'revision':s['revision'],'draft':draft})
            call(a,'POST',f'/surveys/{sid}/publish',{'revision':s['revision']})
            s=call(a,'GET',f'/surveys/{sid}')
            attempt=call(a,'POST',f"/public/{s['share_code']}/attempt",{'anonymous':True})
            iid=s['draft']['questions'][0]['id']
            preview=call(a,'POST',f'/surveys/{sid}/questions/upgrade-preview',{'revision':s['revision'],'instance_id':iid,'question_version_id':v2})
            assert preview['diff']
            s=call(a,'POST',f'/surveys/{sid}/questions/upgrade',{'revision':s['revision'],'instance_id':iid,'question_version_id':v2})
            call(a,'POST',f'/surveys/{sid}/publish',{'revision':s['revision']})
            attempt=call(a,'PUT',f"/attempts/{attempt['_id']}",{'revision':attempt['revision'],'answers':{iid:'25'}})
            call(a,'POST',f"/attempts/{attempt['_id']}/submit",{'revision':attempt['revision']})
            response=db.responses.find_one({'survey_id':sid})
            assert response['version']==1
            stat=call(a,'GET',f'/question-versions/{v1}/statistics')
            assert stat['valid_answers']==1 and stat['average']==25
            stat2=call(a,'GET',f'/question-versions/{v2}/statistics')
            assert stat2['valid_answers']==0 and stat2['coverage_surveys']==1
            # Keep one unfinished attempt to demonstrate the existing recovery structure.
            call(a,'POST',f"/public/{s['share_code']}/attempt",{'anonymous':False})
            call(a,'GET',f'/questions/{qid}/usage')
            schemas=json.loads((MATERIALS/'1_代码/database/collection_validators.json').read_text('utf-8'))
            examples={name:list(db[name].find()) for name in schemas}
            for user in examples['users']:user['password_hash']='example_hash_not_a_real_password'
            for i,session in enumerate(examples['sessions']):session['token_hash']=hashlib.sha256(('nonfunctional_documentation_session_'+str(i)).encode()).hexdigest()
            initialize(validation)
            checked={}
            for name,docs in examples.items():
                assert docs, 'Missing collection example: '+name
                validation[name].insert_many(deepcopy(docs))
                checked[name]={'documents':len(docs),'schema_insert':'passed'}
            rejected=False
            try:validation.responses.insert_one({'_id':'invalid_example'})
            except Exception as exc:
                from pymongo.errors import WriteError
                assert isinstance(exc,WriteError) and exc.code==121
                rejected=True
            assert rejected
            output.mkdir(parents=True,exist_ok=True)
            (output/'MongoDB设计示例.json').write_text(json_util.dumps({'说明':'临时数据库真实API生成；密码哈希和会话哈希替换为不可用示例，替换后再次经真实MongoDB校验；Extended JSON的$date表示BSON Date。','collections':examples},ensure_ascii=False,indent=2),'utf-8')
            (output/'接口静态定义.openapi.json').write_text(json.dumps(app.openapi(),ensure_ascii=False,indent=2),'utf-8')
            (output/'API调用链执行记录.json').write_text(json.dumps({'date':'2026-10-26','kind':'材料示例验证，不计入260项','events':events},ensure_ascii=False,indent=2),'utf-8')
            (output/'MongoDB设计核对.json').write_text(json.dumps({'date':'2026-10-26','version':'2.0.2','collections':checked,'invalid_document_rejected':True,'old_attempt_submitted_after_v2_publish':True,'statistics_v1_average':25,'statistics_v2_valid_answers':0,'validation_scope':'结构校验真实插入；不宣称数据库自动验证外键、业务权限或全部兼容场景','temporary_databases_removed':True},ensure_ascii=False,indent=2),'utf-8')
    finally:
        for name in names:
            assert name.startswith('survey_lab_materials_')
            mongo.drop_database(name)
            assert name not in mongo.list_database_names()
        mongo.close()
    print('API调用链、十一集合示例真实写库校验通过；两个临时库均已清理。')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
    run(parser.parse_args().output)
