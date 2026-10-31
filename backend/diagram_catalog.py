"""Original, bounded explanatory diagrams; independent of the pinned upstream catalog."""

DIAGRAMS = [
    {'id': 'concept-network', 'name': '中心关系图', 'status': 'native_executable',
     'purpose': '把中心概念与参与者、输入或服务对象逐项连接',
     'operations': ['节点错峰进入', '关系线描画', '汇聚或发散箭头'],
     'boundary': '关系线为作者编排，不自动证明因果、同期关系或实际数据流'},
    {'id': 'concept-matrix', 'name': '重复图标与结论', 'status': 'native_executable',
     'purpose': '从一个概念过渡到重复集合，再压暗集合突出结论',
     'operations': ['逐行铺开', '背景降权', '结论落定'],
     'boundary': '图标数量必须声明示意或实测依据，不自动等于市场规模或用户数'},
    {'id': 'layered-rings', 'name': '层层能力圈', 'status': 'native_executable',
     'purpose': '保留中心对象，逐层补充能力、保护条件或服务范围',
     'operations': ['同心椭圆描画', '标签递进', '中心持续保留'],
     'boundary': '圈层大小表示结构层级，不代表可测壁垒强度或占比'},
    {'id': 'process-chain', 'name': '流程链与累积风险', 'status': 'native_executable',
     'purpose': '逐步建立端到端流程，可另示意失败分支或独立同概率模型',
     'operations': ['节点和连接线递进', '失败路径', '明确假设后的概率乘积'],
     'boundary': 'p^n只用于明确独立且同概率的示意模型；确定失败路径与概率模型分镜呈现'},
]

DIAGRAM_KINDS = {item['id'] for item in DIAGRAMS}
