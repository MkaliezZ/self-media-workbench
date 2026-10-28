"""Source-linked shooting guidance; electrical watts are never inferred from lux."""
VERSION = 'tutorial-rules-v2-20261028'
SOURCES = [
    {'id':'R1','title':'ARRI中文灯光手册：光源面积、溢光、曝光与主辅光',
     'url':'https://www.arri.com/resource/blob/83990/9d652bdf4480124850df62b824f2d47e/arri-lighting-handbook-chinese-data.pdf',
     'license':'copyright; public reference only','reviewed':'2026-10-28; pages 5-15 read; no media copied'},
    {'id':'R2','title':'神牛／Simon Cade：室内单灯纪录访谈与自然光稳定性',
     'url':'https://www.godox.com/solutions-video/1032.html',
     'license':'copyright; public reference only','reviewed':'2026-10-28; publisher tutorial text read, not full video playback'},
    {'id':'R4','title':'Richard Adams & Ahmed Sagarwala · Web Design Primer, Chapter 14',
     'url':'https://pressbooks.library.torontomu.ca/webdesign/chapter/chapter-15-digital-photography-for-web-and-cross-media/',
     'license':'CC BY 4.0; except separately credited material',
     'license_url':'https://pressbooks.library.torontomu.ca/webdesign/',
     'reviewed':'2026-10-28; chapter and book license read; independently written rules, no images copied'},
    {'id':'R5','title':'Aputure／Tom Shaw：先定构图、环境曝光，再加入主光',
     'url':'https://aputure.com/en-US/articles/a-guide-to-videography-lighting-with-tom-shaw',
     'license':'copyright; manufacturer case studies, not universal minimums',
     'reviewed':'2026-10-28; full article text read; includes daylight and night counterexamples'},
]


def status():
    return {'method':'tutorial_rules','policy_version':VERSION,'watts_from_simulation':False,
            'radiance_in_planning':False,'references':SOURCES}


def guidance(scene, tier, role, kind, fixture):
    """Case examples and suitability checks, deliberately separate from fixture nameplates."""
    if kind != 'lamp':
        return {'method':'no_electrical_light','summary':'窗光/反光/负补光无需用电',
                'suggested_input_watts':None,'suitability':'not_applicable','rule_ids':[]}
    checks=['在实际附件、灯距和色温下试拍；固定曝光与白平衡，再看面部、背景与反光',
            '对比同附件同距离的厂家测光或实测；机型名称中的W级别与铭牌最大输入功率分别核对',
            '保留调亮、改变构图和拍摄时间的余量；当前档位能曝光不代表长时间或换机位仍够用']
    rules=['exposure_first','apparent_size','actual_assembly','headroom']
    if role != 'key':
        summary='分离光按人物边缘和背景亮度选，不照搬主灯瓦数；检查眩光、过曝和是否真的需要'
        refs=['R1','R5']
    elif scene.ambient_condition == 'bright_daylight':
        summary='强日光/亮窗：先遮光、换机位或时段；仍需对抗日光时参考600–700W级主灯案例，不保证该级别一定足够'
        refs=['R1','R5'];rules.append('daylight_control')
        checks.insert(0,'先按需要保留的窗外/背景曝光试拍，再加主光；不能用室内小功率案例承诺压住日光')
    elif scene.ambient_condition == 'window_mixed':
        summary='有窗混合光：先决定利用还是压住窗光；普通室内单灯案例不能证明够用，明亮窗口条件参考600–700W级案例并实测'
        refs=['R2','R5'];rules.append('daylight_control')
        checks.insert(0,'记录拍摄时段与日光变化；需要连拍稳定时先控制窗光，而不是随天气反复改曝光')
    elif scene.ambient_condition == 'controlled':
        summary='可控室内：先挂实际柔光附件试已有灯；UL150单灯访谈仅作案例，拉远/大柔光/小光圈时需更高输出余量，不直接照搬瓦数'
        refs=['R1','R2','R5']
    else:
        summary='环境光未确认：不默认给低瓦数结论；先区分可控室内与亮窗/强日光，再按实际附件和曝光选择灯具'
        refs=['R1','R2','R5']
        checks.insert(0,'补充是否白天、有无亮窗入镜、能否拉帘、需要保留多少背景亮度')
    if scene.modifier_strategy == 'bounce':
        checks.insert(0,'反射/二次柔光路径损耗与距离更大；不能拿裸灯正面数据定瓦数，先布实际路径试拍')
        rules.append('bounce_path')
    elif scene.modifier_strategy == 'softbox':
        checks.insert(0,'按装上实际柔光布、网格后的表现留余量，裸灯/反光罩数据不能代替该组合')
    if scene.framing == 'wide':
        checks.insert(0,'宽景要覆盖更大区域并避免灯架穿帮；不能以近距离头像案例保证同瓦数足够')
        rules.append('wide_coverage')
    if fixture:
        checks.insert(0,'已有灯'+fixture.label+'的登记功率仅是资产信息；当前没有判定它足够，也未要求仅按W升级')
    return {'method':'source_linked_cases_and_field_checks','summary':summary,
            'suggested_input_watts':None,'suitability':'needs_field_test',
            'reference_ids':refs,'rule_ids':rules,'checks':checks,
            'scope':'案例级别不是计算所需W、最低采购规格或保证；灯具类别/附件效率不同不可只按W横比'}


def scene_rules(scene):
    rules=[
        {'id':'exposure_first','reference_ids':['R4','R5'],
         'reason':'构图与背景曝光决定需要补多少光，先开主灯会掩盖环境问题',
         'action':'先关补灯记录环境画面，确定构图、景深和曝光；锁定白平衡后再逐项加灯',
         'verify':'同机位与固定曝光保存主光关闭/开启对照；不复制静态摄影教材的f8或慢快门作为视频默认'},
        {'id':'apparent_size','reference_ids':['R1'],
         'reason':'阴影软硬取决于人物看到的发光面积与距离，瓦数本身不决定柔和程度',
         'action':'自然口播先尝试足够大的柔光面；在构图、反光和占地允许范围内调整距离',
         'verify':'检查鼻影、眼窝和眼镜反光；不是一律加大功率或抬高灯'},
        {'id':'actual_assembly','reference_ids':['R1','R4'],
         'reason':'柔光、反射路径、距离与相机设置会改变可用光输出',
         'action':'整套灯具与附件一起试拍并核对测光条件，电功率只记录铭牌值',
         'verify':'不得用lux、模拟器中的光源W或裸灯参数反推推荐输入W'},
        {'id':'headroom','reference_ids':['R2','R5'],
         'reason':'刚够曝光与有调整余量不同，日光、宽景和附件变化会改变需求',
         'action':'已有灯先试，余量不足先控环境或调整布局，再比较更高输出的实际机型',
         'verify':'按计划时段/景别/附件复测；不固定套用60/150/300W三档或统一调光百分比'},
    ]
    if scene.ambient_condition in ('window_mixed','bright_daylight'):
        rules.append({'id':'daylight_control','reference_ids':['R2','R5'],
            'reason':'日光强度和时间变化可能远大于普通室内条件',
            'action':'决定用窗光还是压窗光；先拉帘、改变取景或时段，必要时核对高输出主灯与实际附件',
            'verify':'主光关闭时拍背景对照；高输出案例不能当压过太阳的承诺'})
    if scene.modifier_strategy == 'bounce':
        rules.append({'id':'bounce_path','reference_ids':['R1'],
            'reason':'反射后实际发光面和光路发生变化，墙面颜色还可能影响肤色',
            'action':'用中性白色反射面并试实际双段光路，不按灯到人物的直线算输出',
            'verify':'白平衡与面部曝光对照，不伪造统一损耗百分比'})
    if scene.framing == 'wide':
        rules.append({'id':'wide_coverage','reference_ids':['R1','R5'],
            'reason':'覆盖范围和器材避画限制会改变距离和输出要求',
            'action':'先确定最宽画面，再安排灯和附件；无法覆盖时缩小景别或调整位置',
            'verify':'检查边缘亮度和活动范围，不把头像样例当全身方案'})
    return rules
