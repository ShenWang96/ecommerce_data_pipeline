"""
信号分类器 — 公共关键词提取 + 领域分类 + 信号类型判定。

所有 Collector 共用，确保分类逻辑一致。
"""
import re
from typing import Optional

# ─── Layer 1: 需求萌芽识别规则 ───

PAIN_PATTERNS = [
    (re.compile(r"(怎么|如何|怎样)(解决|处理|去掉|去除|防止|避免|清理|收纳|整理)"), "pain_point"),
    (re.compile(r"(太|很|好|真)(麻烦|不方便|难用|难闻|吵|贵|占地方|浪费)"), "pain_point"),
    (re.compile(r"(头疼|崩溃|烦死了|受不了|忍不了|要命|无语)"), "pain_point"),
    (re.compile(r"(越来越|每天|天天|总是|经常).*(问题|麻烦|困扰|头疼)"), "pain_point"),
]

SEEKING_PATTERNS = [
    (re.compile(r"(有没有|求推荐|求|求安利|推荐一下|安利|种草)"), "seeking_help"),
    (re.compile(r"(避雷|避坑|别买|不要买|千万别|踩雷)"), "seeking_help"),
    (re.compile(r"(哪个|哪些|什么).*(好用|值得|靠谱|推荐|适合)"), "seeking_help"),
]

COMPLAINT_PATTERNS = [
    (re.compile(r"(后悔|买错|被骗|上当了|不值|翻车)"), "complaint"),
    (re.compile(r"(吐槽|曝光|差评|垃圾|智商税|千万别买)"), "complaint"),
]

# ─── Layer 2: 理念形成识别规则 ───

LIFESTYLE_PATTERNS = [
    (re.compile(r"(极简|断舍离|收纳|整理|布置|改造|租房|独居|小户型|一人住)"), "lifestyle"),
    (re.compile(r"(露营|徒步|骑行|CityWalk|自驾|旅行|旅居)"), "lifestyle"),
    (re.compile(r"(健身|跑步|瑜伽|冥想|减脂|增肌|自律|早起)"), "lifestyle"),
    (re.compile(r"(养猫|养狗|宠物|铲屎|遛狗|猫砂|狗粮)"), "lifestyle"),
    (re.compile(r"(护肤|化妆|穿搭|OOTD|换季|防晒|美白)"), "lifestyle"),
    (re.compile(r"(做饭|烘焙|便当|食谱|减脂餐|轻食|早餐)"), "lifestyle"),
    (re.compile(r"(居家办公|远程办公|HomeOffice|自由职业|数字游民)"), "lifestyle"),
    (re.compile(r"(养生|泡脚|艾灸|睡眠|熬夜|失眠|补气血)"), "lifestyle"),
]

CONCEPT_PATTERNS = [
    (re.compile(r"(AI|人工智能|智能|自动化|机器人|ChatGPT|AI办公)"), "concept"),
    (re.compile(r"(可持续|环保|无废|零浪费|二手|循环|绿色)"), "concept"),
    (re.compile(r"(宠物拟人|情感陪伴|疗愈|解压|治愈|心理健康)"), "concept"),
    (re.compile(r"(智能家居|全屋智能|IoT|语音控制)"), "concept"),
]

# ─── Layer 3: 内容传播识别规则 ───

TRENDING_PATTERNS = [
    (re.compile(r"(热搜|热榜|热门|爆火|刷屏|走红|冲上|登顶)"), "trending"),
    (re.compile(r"(新|首发|独家|第一|首次|终于)"), "trending"),
]

# ─── 消费领域分类关键词 ───

DOMAIN_KEYWORDS = {
    "家居收纳": ["收纳", "整理", "布置", "租房", "小户型", "极简", "书桌", "装备墙", "独居", "租屋", "卧室", "客厅", "厨房收纳", "桌面收纳", "衣柜", "阳台"],
    "宠物用品": ["猫", "狗", "宠物", "铲屎", "猫砂", "狗粮", "遛狗", "猫咪", "狗狗", "喵", "汪", "养猫", "养狗", "毛孩子", "主子"],
    "数码3C": ["手机", "电脑", "平板", "耳机", "蓝牙", "音箱", "充电", "数据线", "华为", "苹果", "小米", "数码", "电子", "3C", "笔记本", "相机"],
    "办公效率": ["办公", "书桌", "书房", "HomeOffice", "远程", "效率", "笔记本", "文具", "桌面", "站立办公", "人体工学"],
    "美妆护肤": ["护肤", "化妆", "面膜", "防晒", "美白", "精华", "粉底", "口红", "卸妆", "洗脸", "清洁", "毛孔", "痘痘", "敏感肌"],
    "健康养生": ["养生", "健康", "睡眠", "熬夜", "失眠", "减脂", "减肥", "泡脚", "艾灸", "中医", "补气血", "维生素", "体检"],
    "食品饮料": ["美食", "零食", "饮料", "咖啡", "茶", "牛奶", "酸奶", "水果", "早餐", "便当", "食谱", "烘焙", "轻食", "减脂餐"],
    "健身运动": ["健身", "跑步", "瑜伽", "运动", "跳绳", "哑铃", "拉伸", "训练", "增肌", "健身房", "户外"],
    "服饰穿搭": ["穿搭", "衣服", "鞋子", "包包", "帽子", "配饰", "OOTD", "换季", "秋冬", "春夏", "外套", "卫衣", "裙子"],
    "母婴育儿": ["宝宝", "孩子", "妈妈", "婴儿", "幼儿园", "早教", "辅食", "尿布", "育儿", "怀孕", "坐月子"],
    "智能家居": ["智能", "AI", "自动", "扫拖", "扫地机", "洗碗机", "烘干机", "净水器", "空气净化", "智能锁", "监控"],
    "户外露营": ["露营", "户外", "帐篷", "徒步", "骑行", "登山", "野餐", "天幕", "睡袋"],
}

ALL_DOMAIN_KEYWORDS = {kw: domain for domain, kws in DOMAIN_KEYWORDS.items() for kw in kws}


def classify_signal_type(title: str, content: str, source: str, source_signal: str = "") -> str:
    """
    根据 SOP 规则判定信号类型。
    
    优先级: 内容传播(L3) > 需求萌芽(L1) > 理念形成(L2)
    因为热搜/热榜等高层信号比底层信号更确定。
    """
    text = f"{title} {content}"

    # Layer 3: 内容传播
    for pat, stype in TRENDING_PATTERNS:
        if pat.search(text):
            return stype

    # Layer 1: 需求萌芽 (更高优先级，因为更早期)
    for pat, stype in PAIN_PATTERNS:
        if pat.search(text):
            return stype
    for pat, stype in COMPLAINT_PATTERNS:
        if pat.search(text):
            return stype
    for pat, stype in SEEKING_PATTERNS:
        if pat.search(text):
            return stype

    # Layer 2: 理念形成
    for pat, stype in LIFESTYLE_PATTERNS:
        if pat.search(text):
            return stype
    for pat, stype in CONCEPT_PATTERNS:
        if pat.search(text):
            return stype

    # 默认: 根据来源 + source_signal 判定
    source_map = {
        "bilibili": "trending" if source_signal in ("popular", "ranking") else "lifestyle",
        "weibo": "trending",
        "zhihu": "pain_point",
        "xiaohongshu": "lifestyle",
    }
    return source_map.get(source, "trending")


def classify_domain(title: str, content: str) -> str:
    """根据关键词分类消费领域，返回 best match 或 '其他'"""
    text = f"{title} {content}".lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[domain] = score
    if scores:
        return max(scores, key=scores.get)
    return "其他"


def extract_keywords(title: str, content: str, min_len: int = 2, max_count: int = 10) -> list[str]:
    """从文本中提取匹配的关键词"""
    text = f"{title} {content}"
    found = []
    for kw, domain in ALL_DOMAIN_KEYWORDS.items():
        if len(kw) >= min_len and kw in text and kw not in found:
            found.append(kw)
    return found[:max_count]
