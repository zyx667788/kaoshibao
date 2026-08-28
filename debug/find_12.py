import re
from openpyxl import load_workbook

cur_wb = load_workbook('output/考试宝题库_13573440_hybrid.xlsx', read_only=True)
cur_ws = cur_wb.active
cur = []
for i, row in enumerate(cur_ws.iter_rows(values_only=True)):
    if i == 0 or not row[2]:
        continue
    cur.append({
        'idx': len(cur),
        'type': str(row[1] or ''),
        'title': str(row[2] or ''),
        'ans': (str(row[9] or '')).strip() if len(row) > 9 else '',
    })
cur_wb.close()

# 12题历史未匹配的关键词
targets = {
    589: ['频率就是概率', '频率', '概率'],
    632: ['Hudi', 'Lambda', 'Kappa'],
    655: ['不均衡', '4', '样本'],
    656: ['RBF', '零均值', '正则化'],
    677: ['全部为大写英文', '批量梯度下降'],
    683: ['FP', 'Apriori', 'FP-growth', 'FPgrowth'],
    693: ['经典', '降维', '一一对应'],
    694: ['朴素贝叶斯', '连接'],
    695: ['特征选择', '一一对应', '对应'],
    697: ['数据治理', '匹配'],
    698: ['关联分析', '连接'],
    699: ['大数据平台系统架构', '匹配'],
}

for qnum, kws in targets.items():
    print(f'=== 历史题{qnum} 关键词: {kws} ===')
    for c in cur:
        title = c['title']
        # 只匹配题干，去掉可能的题号前缀
        score = sum(1 for kw in kws if kw.lower() in title.lower())
        if score >= 1:
            t = c['type']
            a = c['ans']
            disp = title[:55].replace('\n', ' ')
            print(f'  [cur#{c["idx"]}] ({t}, ans={a}) {disp}')
    print()
