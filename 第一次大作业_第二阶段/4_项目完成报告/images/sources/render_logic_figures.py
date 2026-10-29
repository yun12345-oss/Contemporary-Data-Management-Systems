from pathlib import Path
import runpy,json,html
from PIL import Image
HERE=Path(__file__).resolve().parent
if (HERE/'render_figures.py').exists(): OUT=HERE.parent
else: OUT=Path.cwd()/'第二阶段/4_项目完成报告/images'
base=runpy.run_path(str(OUT/'sources/render_figures.py'))
C=base['Canvas'];card=base['card'];W=base['W']
NEW=[]
def add(i,ch,title,kind,data):NEW.append(dict(id=i,chapter=ch,title=title,kind=kind,data=data))
add('18-1',4,'跳转全过程与填写路径处理','flow',[
 ['配置条件与目标','创建者编排规则和默认目标','old'],['发布检查','引用、题型、数值与前向目标','old'],['按快照开始填写','只用路径中的有效答案判断','old'],['保存与恢复','遇无效题停下，重算合理位置','old'],['提交重新计算','不信任客户端路径，逐题校验','old'],['生成正式结果','只有路径答案进入答卷','old']])
add('18-2',4,'一条规则的结构拆解','table',{'headers':['配置部位','示例','决定什么'],'rows':[
 ['引用 condition.question_id','q1','读取当前或前面题目的答案'],['运算符 condition.operator','eq','按单选“等于”判断'],['比较值 condition.value','no','必须为存在的选项 ID'],['命中目标 target','q3','命中后跳过 q2'],['兜底 default_target','null','规则都不成立则顺序继续 q2']]})
add('18-3',4,'组合条件怎样逐层判断','combo',{})
add('18-4',4,'规则匹配与默认目标决策','decision',{})
add('19-1',4,'题目升级后的规则修复流程','flow',[
 ['预览新版本','比较内容，列出失效规则','new'],['确认上下文一致','切题、改草稿后必须重预览','changed'],['保留待修复草稿','原实例 ID、必答和规则保留','new'],['完整发布校验','仍引用已删选项则拒绝发布','changed'],['修正规则再发布','检查通过后生成新快照','changed'],['旧内容继续使用','原发布和旧填写过程不变','old']])
add('20-1',5,'分层校验的职责','flow',[
 ['前端组件','即时提示、输入与交互保护','old'],['请求结构','字段、类型、数量与安全数值','old'],['业务与领域','归属、状态、规则、来源和权限','changed'],['MongoDB 写入','Schema、唯一索引和事务','changed']])
add('20-2',5,'必答题是否存在合法答案','feasible',{})
add('21-1',5,'恢复填写与只读状态判断','recovery',{})
add('22-1',5,'不同来源操作的权限判断','table',{'headers':['操作','先检查什么','允许与拒绝'],'rows':[
 ['普通保存／发布','原来源、实例绑定、版本内容','一致才接受；不能随意增删来源'],['导入确定版本','问卷归属、revision、当前使用权','服务端创建新实例与来源'],['升级实例','同系列、目标使用权、revision','内容替换；保留必答和规则'],['解除来源','自有问卷与题目所有权','自有题可解除；共享题拒绝'],['保存为常用题','实例有来源时检查题目所有者','共享题不能另存为自有系列'],['填写读取','过程归属、原发布定义','移除返回定义中的内部 source']]})
add('22-2',5,'统计参数与授权范围校验','flow',[
 ['参数合法','时区、起止顺序、安全递增边界','changed'],['确定问卷范围','自有或有效 aggregate 授权','new'],['确定版本与时间','快照来源和正式 submitted_at','new'],['匹配有效答案','不按题干猜来源，不混合版本','new'],['分别计数','答卷按 ID，作答按实例','new'],['只返回允许汇总','不输出跨卷去重人数或文本原文','new']])
add('22-3',5,'并发保存与迟到请求处理','sequence',{'actors':['页面 A／B','后端服务','MongoDB'],'events':[
 [0,1,'A、B 都读取到 revision＝1'],[0,1,'A 携带 revision＝1 保存'],[1,2,'条件更新成功，将 revision 增加到 2'],[1,0,'A 获确认；期间新输入仍需后续同步'],[0,1,'B 仍携带 revision＝1 保存'],[1,0,'返回 409；保留页面输入，核对后处理'],[0,0,'另一路保护：旧预览、旧统计响应不能覆盖当前上下文']]})

def save(self,f):
 stem='fig-'+str(f['id']).zfill(2)
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{self.h}" viewBox="0 0 {W} {self.h}" role="img"><title>{html.escape(f["title"])}</title><rect width="100%" height="100%" fill="white"/>'+''.join(self.svg)+'</svg>'
 (OUT/'svg'/f'{stem}.svg').write_text(svg,'utf-8');self.im.save(OUT/'png'/f'{stem}.png',optimize=True)
 f.update(width=W,height=self.h,text_runs=len(self.text_bounds))
C.save=save
def edge(c,a,b,label=''):
 c.line([a,b],True)
 if label:c.txt((a[0]+b[0])/2+12,(a[1]+b[1])/2-24,label,20,width=230)
def box(c,x,y,title,body,w=500,h=130,k='old'):card(c,x,y,w,h,title,body,k)
def special(f):
 k=f['kind']
 if k=='combo':
  c=C(950);c.head(f)
  box(c,44,145,'在 Q3 判断：all','左侧与右侧两项必须都成立',1192,120)
  box(c,44,365,'条件 A：Q1 等于 yes','没有有效答案则不成立',480,140)
  box(c,650,365,'条件 B：any','下列至少一个子条件成立',586,140)
  box(c,650,645,'子条件 B1','Q3 学习时间 ≥ 2 小时',270,140)
  box(c,950,645,'子条件 B2','Q2 所选工具包含 MongoDB',286,140)
  c.line([(640,265),(640,315),(284,315),(284,365)],True)
  c.line([(640,315),(943,315),(943,365)],True)
  c.line([(943,505),(943,570),(785,570),(785,645)],True)
  c.line([(943,570),(1093,570),(1093,645)],True)
  c.txt(46,838,'先计算子条件，再计算 any，最后计算 all；引用只能来自当前题或前题。',22,width=1180)
 elif k=='decision':
  c=C(1070);c.head(f)
  rows=[('按顺序取下一条规则','还有规则吗？','有：检查该条件'),('当前条件成立吗？','否：继续下一条','是：采用本条 target'),('全部规则均未命中','检查 default_target','采用默认目标或顺序下一题')]
  for i,(title,body,right) in enumerate(rows):
   y=145+i*255;box(c,44,y,title,body,660,150)
   if i>0:box(c,884,y,right,'后续题或 END；仅默认目标可为空',352,170)
   if i==1:edge(c,(704,y+75),(884,y+75),'是')
   elif i==2:edge(c,(704,y+75),(884,y+75))
  edge(c,(374,295),(374,400),'有规则')
  c.line([(44,475),(20,475),(20,205),(44,205)],True);c.txt(47,332,'不成立则继续循环',20,width=300)
  c.line([(704,220),(805,220),(805,610),(374,610),(374,655)],True);c.txt(814,336,'无规则',20,width=190)
  c.txt(46,948,'第一条命中后立即停止；规则目标需非空，默认目标 null 表示顺序继续。',22,width=1180)
 elif k=='feasible':
  c=C(960);c.head(f)
  box(c,44,145,'先判断配置是否满足结构和上下界要求','再检查必答时是否至少有一种合法答案',1192,130)
  box(c,44,385,'反例一：必答多选','最多允许 0 项：不选违必答，选了又超限',550,170,k='changed')
  box(c,686,385,'反例二：必答整数','范围 0.1～0.9：其中不存在合法整数',550,170,k='changed')
  box(c,44,695,'拒绝发布并说明原因','调整配置后重新校验，不能让填写者无解',1192,130,k='changed')
  c.line([(640,275),(640,325),(319,325),(319,385)],True);c.line([(640,325),(961,325),(961,385)],True)
  c.line([(319,555),(319,625),(640,625),(640,695)],True);c.line([(961,555),(961,625),(640,625)])
 elif k=='recovery':
  c=C(1120);c.head(f)
  box(c,44,145,'读取前：核对本人过程与原快照','不存在／不属于本人 → 404；不支持版本 → 明确错误',1192,145)
  box(c,44,390,'进行中，并且问卷可写','重算路径和合理位置，允许保存与提交',550,165)
  box(c,686,390,'关闭、截止或已进入终态','可读取并标只读；保存／新提交受到限制',550,165,k='changed')
  box(c,44,705,'已有提交或放弃状态','提交返回回执；放弃或提交后的草稿输入已清理',1192,140)
  c.line([(640,290),(640,335),(319,335),(319,390)],True);c.line([(640,335),(961,335),(961,390)],True)
  c.line([(961,555),(961,630),(640,630),(640,705)],True);c.txt(975,575,'若为终态',20,width=240)
  c.txt(46,935,'位置由服务端有效路径约束；关闭只读不等于允许继续写入。',23,width=1180)
 c.foot();c.save(f)

if __name__=='__main__':
 for f in NEW:
  if f['kind'] in ['combo','decision','feasible','recovery']:special(f)
  else:base['render'](f)
 # Improve the five existing numbered figures without renumbering later chapters.
 old=json.loads((OUT/'sources/figures.json').read_text('utf-8'))
 for f in old:
  if f['id']==19:
   f['data']['rows'][-1]=['保存与提交','有效跳转确定绕过的题清除','无效前题后的暂存先保留；提交只写有效路径']
  if f['id']==21:
   f['data']['events'][3]=[1,0,'数据库确认后返回；仅最新修改获确认才显示已同步']
  if f['id'] in [18,19,20,21,22]:base['render'](f)
 (OUT/'sources/logic_figures.json').write_text(json.dumps(NEW,ensure_ascii=False,indent=2),'utf-8')
 (OUT/'sources/figures.json').write_text(json.dumps(old,ensure_ascii=False,indent=2),'utf-8')
 print('新增11张图；完善原图18～22，第四章7图、第五章9图')
