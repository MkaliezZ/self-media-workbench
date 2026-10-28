"""Source-linked shooting guidance; electrical watts are never inferred from lux."""
VERSION = 'tutorial-context-v3-20261028'
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
    {'id':'R6','title':'Oklahoma State University Extension · Light and Color',
     'url':'https://extension.okstate.edu/fact-sheets/light-and-color',
     'license':'copyright; public educational reference only',
     'reviewed':'2026-10-28; source color and incandescent section read; no default fixture CCT inferred'},
]


def status():
    return {'method':'tutorial_rules','policy_version':VERSION,'watts_from_simulation':False,
            'radiance_in_planning':False,'existing_light_context':True,'references':SOURCES}


def assess_existing(scene):
    results=[]
    for index,light in enumerate(scene.existing_lights,1):
        checks=['在相同机位、快门、光圈、ISO和白平衡下，先拍顶灯关/开两版，主灯保持关闭',
                '检查人脸亮暗、眼窝/鼻下阴影和肤色，不以桌面或地面变亮代替面部有效补光',
                '再逐步开启主光，检查目标效果和可调余量；简版若只用窗光，不涉及降低主灯W']
        decision='needs_comparison'
        summary='还不能据此降低主光规格：已有光源对面部的有效贡献、阴影和混色尚未确认'
        if light.state=='off':
            decision='excluded'
            summary='该光源计划关闭，不计入主光减负；按关闭后的场景规划'
        elif light.face_effect in ('harsh_shadows','color_conflict'):
            decision='control_or_switch_off'
            summary='先控制或关闭该光源：已声明它造成不利阴影或混色，不能将它当作可抵扣的主光'
        elif light.state=='on' and light.face_effect=='background_only':
            decision='background_only'
            summary='它主要服务背景，不能据此减少照亮人脸所需的主光输出'
        elif light.state=='on' and light.face_effect=='useful_fill':
            decision='may_reduce_operating_output'
            summary='按已声明的观察，它可能降低主光实际调光输出；不等于已经可以购买更低额定W的主灯'
        if light.mounting=='ceiling':
            checks.append('顶灯从上方投射时，特别检查眼窝和鼻下阴影；平面位置接近人物不代表照脸有效')
        if light.kind=='incandescent':
            checks.append('白炽灯通常偏暖；本灯具体色温未知则保持未知，不自动填写2700K或3200K；与窗光/主光混用要检查两侧肤色')
        if light.cct_k is not None:
            checks.append('已登记色温'+str(light.cct_k)+'K，只是声明；与主光和窗光是否能混用仍需白平衡与肤色对照')
        if light.basis=='assumed':
            checks.insert(0,'这是情景假设，不是现场已确认的顶灯或实测效果')
        results.append({'id':'C'+str(index),'label':light.label,'decision':decision,'summary':summary,
            'declaration':light.model_dump(),'key_fixture_downsize':'not_established',
            'watt_reduction':None,'dimmer_reduction_percent':None,'independently_verified':False,
            'checks':checks,'reference_ids':['R1','R5','R6'],
            'scope':'不同光源电功率不能相减；有帮助的环境光可降低工作输出，但额定功率、调光百分比和采购余量需要另行验证'})
    return results


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
    if scene.existing_lights:
        checks.insert(0,'先看已有光源上下文评估；顶灯电功率不能从主灯W中扣除，先验证有效补光和混色')
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
    if scene.existing_lights:
        rules.append({'id':'existing_light_context','reference_ids':['R1','R5','R6'],
            'reason':'房间变亮不一定改善人脸；已有灯可能提供有用补光，也可能制造阴影、色偏或只照背景',
            'action':'记录顶灯种类、位置、开关和面部效果，固定曝光做关/开对照，再决定保留、控制或关闭',
            'verify':'可减少工作输出不等于可降低额定采购W；无证据不抵扣瓦数，不自动填色温或减光百分比'})
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
