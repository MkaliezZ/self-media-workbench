"""Functional method library: independent of names, accounts and tutorial links."""
LOGICS=[
 {'id':'faceless_reference','name':'不露脸资料解说','logic':'命题→资料主画面→解释→限定结论','operations':['资料优先布局','局部资料高亮','旁白独立音轨'],
  'boundary':'示意不能冒充具体事件证据；不以无关配图消灭所有空白','runtime':'visual_plan + native_timeline'},
 {'id':'science_evidence','name':'科普资料串联','logic':'现象问题→资料支持→机制解释→不确定性','operations':['文案画面并行规划','原图区域提示','字幕与材料绑定'],
  'boundary':'画面上的数据仍要核实；没有证据先做明确示意','runtime':'visual_plan + native_timeline'},
 {'id':'life_story','name':'生活与旅行场景叙事','logic':'建立空间→动作衔接→细节→感受','operations':['多源镜头编排','原声保留','无旁白画面停留','选择性音乐打点'],
  'boundary':'不相关镜头不能伪造动作或事件因果；无声不等于可删','runtime':'native_timeline'},
 {'id':'game_event','name':'游戏/录屏事件回看','logic':'交代前因→关键事件→局部回看→解释','operations':['事件区间选择','画面区域提示','原声与解释分轨'],
  'boundary':'保留重要UI与完整操作；曲线变速、对象跟踪仍未实现','runtime':'visual_plan + native_timeline; speed/tracking excluded'},
 {'id':'first_person','name':'第一人称经历解说','logic':'处境与视角→事件→反应→结果与边界','operations':['多源画面','旁白独立起止','原声与音乐分轨','明确的J/L音画衔接'],
  'boundary':'不制造亲历或原片因果，不提供他人声音克隆','runtime':'native_timeline'},
 {'id':'region_explanation','name':'资料区域逐步解释','logic':'整体定位→指出区域→解释关系→回到整体','operations':['等比布局','原图坐标变换','分时静态矩形高亮'],
  'boundary':'静态区域不等于跟踪；关键帧形变尚未实现','runtime':'visual_plan; complex animation excluded'},
 {'id':'layer_intro','name':'片头多元素组合','logic':'明确主信息→建立人物/文字层级→协调进入顺序','operations':['独立元素分组与遮挡设计'],
  'boundary':'复杂组动画、动态抠像与透明视频叠层仍待实现；不把设计当成运行能力','runtime':'planning_only for unsupported layer motion'},
 {'id':'audio_roles','name':'按作用安排声音','logic':'人声可懂→保留场景原声→音乐/音效有明确作用','operations':['独立音轨','增益','入出点','淡入淡出','混音限幅','瞬态候选与审阅打点'],
  'boundary':'瞬态不是所有真实节拍；混音技术检查不代替听审或生成音乐','runtime':'native_timeline; no music generation'}]


def register(w):
    @w.app.get('/api/visual/logics')
    def library():return {'version':'1.0','logics':LOGICS,
        'scope':'reconciled functional mechanisms and explicit execution limits; not a claim of full-video research or production aesthetics'}
