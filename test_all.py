"""考试宝项目 - 综合测试（CDP模式）"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

passed = 0
failed = 0
errors = []


def test(name, fn):
    global passed, failed, errors
    try:
        fn()
        passed += 1
        print(f"  [PASS] {name}")
    except Exception as e:
        failed += 1
        errors.append((name, str(e)))
        print(f"  [FAIL] {name}: {e}")


def assert_eq(a, b, msg=""):
    if a != b:
        raise AssertionError(f"{msg} expected {b!r}, got {a!r}")


def assert_true(v, msg=""):
    if not v:
        raise AssertionError(f"{msg} expected truthy, got {v!r}")


def assert_in(item, collection, msg=""):
    if item not in collection:
        raise AssertionError(f"{msg} {item!r} not in {collection!r}")


# ============================================================
# 1. scraper_core
# ============================================================
print("\n=== scraper_core ===")

from scraper_core import (
    validate_paper_id, sanitize_text, save_to_excel,
    load_progress, save_progress, OUTPUT_DIR, DATA_DIR,
    is_port_open, get_chrome_status, ensure_chrome_debug,
    open_cdp_page, CDP_PORT, _BROWSER_PROFILES,
    check_login_required, wait_for_question, click_next_question,
    navigate_with_retry
)


def test_validate_empty():
    pid, err = validate_paper_id("")
    assert_true(pid is None)
    assert_in("请输入", err)


def test_validate_spaces():
    pid, err = validate_paper_id("  13573440  ")
    assert_eq(pid, "13573440")


def test_validate_number():
    pid, err = validate_paper_id("17940685")
    assert_eq(pid, "17940685")


def test_validate_url():
    pid, err = validate_paper_id("https://www.kaoshibao.com/ti/13573440/")
    assert_eq(pid, "13573440")


def test_validate_url_no_slash():
    pid, err = validate_paper_id("https://www.kaoshibao.com/ti/9999")
    assert_eq(pid, "9999")


def test_validate_bad_url():
    pid, err = validate_paper_id("https://www.kaoshibao.com/other/123")
    assert_true(pid is None)


def test_validate_non_digit():
    pid, err = validate_paper_id("abc")
    assert_true(pid is None)


def test_validate_too_long():
    pid, err = validate_paper_id("1" * 21)
    assert_true(pid is None)


def test_sanitize_normal():
    assert_eq(sanitize_text("hello"), "hello")


def test_sanitize_html():
    result = sanitize_text("<script>alert(1)</script>")
    assert_in("&lt;", result)
    assert_true("<script>" not in result)


def test_sanitize_none():
    assert_eq(sanitize_text(None), "")


def test_sanitize_number():
    assert_eq(sanitize_text(123), "123")


def test_save_load_progress():
    data = [{'序号': 1, '题目': '测试', '正确答案': 'A'}]
    save_progress("test_88888", data)
    loaded = load_progress("test_88888")
    assert_eq(len(loaded), 1)
    assert_eq(loaded[0]['题目'], '测试')
    (DATA_DIR / "progress_test_88888.json").unlink()


def test_load_progress_missing():
    assert_eq(load_progress("nonexistent_99999"), [])


def test_load_progress_corrupt():
    pid = "test_corrupt"
    with open(DATA_DIR / f"progress_{pid}.json", 'w') as f:
        f.write("not json{{{")
    assert_eq(load_progress(pid), [])
    (DATA_DIR / f"progress_{pid}.json").unlink()


def test_save_excel():
    qs = [{'序号': 1, '题目类型': '单选', '题目': 'Q1', '选项': 'A\nB', '正确答案': 'A', '解析': ''}]
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    try:
        save_to_excel(qs, path)
        assert_true(os.path.getsize(path) > 0)
        from openpyxl import load_workbook
        ws = load_workbook(path).active
        assert_eq(ws.cell(1, 1).value, "序号")
        assert_eq(ws.cell(2, 3).value, "Q1")
        assert_true(ws.freeze_panes is not None)
    finally:
        os.unlink(path)


def test_constants():
    assert_eq(CDP_PORT, 9222)
    assert_true(len(_BROWSER_PROFILES) >= 2, "应支持至少2种浏览器")


def test_ensure_chrome_returns_tuple():
    """ensure_chrome_debug返回3元组"""
    result = ensure_chrome_debug()
    assert_eq(len(result), 3, "应返回(ok, msg, restarted)")
    assert_true(isinstance(result[0], bool))
    assert_true(isinstance(result[1], str))
    assert_true(isinstance(result[2], bool))


test("validate: 空输入", test_validate_empty)
test("validate: 带空格", test_validate_spaces)
test("validate: 纯数字", test_validate_number)
test("validate: URL", test_validate_url)
test("validate: URL无尾斜杠", test_validate_url_no_slash)
test("validate: 错误URL", test_validate_bad_url)
test("validate: 非数字", test_validate_non_digit)
test("validate: 过长", test_validate_too_long)
test("sanitize: 普通文本", test_sanitize_normal)
test("sanitize: HTML标签", test_sanitize_html)
test("sanitize: None", test_sanitize_none)
test("sanitize: 数字", test_sanitize_number)
test("save/load progress", test_save_load_progress)
test("load progress: 不存在", test_load_progress_missing)
test("load progress: 损坏JSON", test_load_progress_corrupt)
test("save_to_excel", test_save_excel)
test("constants", test_constants)
test("ensure_chrome_debug返回3元组", test_ensure_chrome_returns_tuple)


# ============================================================
# 2. Flask API
# ============================================================
print("\n=== Flask API ===")

from app import app
import app as app_module

client = app.test_client()
app.config['TESTING'] = True


def reset_rl():
    with app_module._rate_limit_lock:
        app_module._rate_limit.clear()


def test_index():
    r = client.get('/')
    assert_eq(r.status_code, 200)
    assert_in('考试宝', r.data.decode('utf-8'))


def test_chrome_status():
    r = client.get('/api/chrome-status')
    d = json.loads(r.data)
    assert_in('online', d)


def test_chrome_start():
    reset_rl()
    r = client.post('/api/chrome-start')
    d = json.loads(r.data)
    assert_in('ok', d)
    assert_in('message', d)


def test_tasks_empty():
    r = client.get('/api/tasks')
    assert_eq(r.status_code, 200)
    assert_true(isinstance(json.loads(r.data), list))


def test_start_empty_id():
    reset_rl()
    r = client.post('/api/start', data=json.dumps({'paper_id': ''}), content_type='application/json')
    assert_eq(r.status_code, 400)


def test_start_bad_id():
    reset_rl()
    r = client.post('/api/start', data=json.dumps({'paper_id': 'abc'}), content_type='application/json')
    assert_eq(r.status_code, 400)


def test_start_no_json():
    reset_rl()
    r = client.post('/api/start', data='not json')
    assert_eq(r.status_code, 400)


def test_start_no_chrome():
    reset_rl()
    # Chrome likely not running in test, so this should fail with 400
    r = client.post('/api/start', data=json.dumps({'paper_id': '12345'}), content_type='application/json')
    # Either 400 (no chrome) or 200 (chrome happens to be running)
    assert_true(r.status_code in (200, 400))


def test_stop_nonexistent():
    r = client.post('/api/stop/nope')
    assert_eq(r.status_code, 404)


def test_remove_nonexistent():
    r = client.post('/api/remove/nope')
    assert_eq(r.status_code, 404)


def test_files():
    r = client.get('/api/files')
    assert_true(isinstance(json.loads(r.data), list))


def test_download_traversal():
    r = client.get('/api/download/..%2F..%2Fetc%2Fpasswd')
    assert_true(r.status_code in (400, 404))


def test_download_missing():
    r = client.get('/api/download/nonexistent.xlsx')
    assert_eq(r.status_code, 404)


def test_delete_traversal():
    reset_rl()
    r = client.post('/api/delete-file', data=json.dumps({'name': '../../bad'}), content_type='application/json')
    assert_eq(r.status_code, 400)


def test_batch_empty():
    reset_rl()
    r = client.post('/api/batch-start', data=json.dumps({'ids': []}), content_type='application/json')
    assert_eq(r.status_code, 400)


def test_batch_too_many():
    reset_rl()
    r = client.post('/api/batch-start', data=json.dumps({'ids': list(range(11))}), content_type='application/json')
    assert_eq(r.status_code, 400)


def test_batch_mixed():
    reset_rl()
    r = client.post('/api/batch-start', data=json.dumps({'ids': ['12345', 'abc']}), content_type='application/json')
    d = json.loads(r.data)
    # Chrome not running in test: returns error. Chrome running: returns results.
    if 'results' in d:
        assert_eq(len(d['results']), 2)
    else:
        assert_in('error', d)


def test_rate_limit():
    reset_rl()
    for _ in range(5):
        client.post('/api/start', data=json.dumps({'paper_id': '11111'}), content_type='application/json')
        time.sleep(0.01)
    r = client.post('/api/start', data=json.dumps({'paper_id': '22222'}), content_type='application/json')
    assert_eq(r.status_code, 429)
    reset_rl()


test("GET /", test_index)
test("GET /api/chrome-status", test_chrome_status)
test("POST /api/chrome-start", test_chrome_start)
test("GET /api/tasks", test_tasks_empty)
test("POST /api/start 空ID", test_start_empty_id)
test("POST /api/start 错误ID", test_start_bad_id)
test("POST /api/start 非JSON", test_start_no_json)
test("POST /api/start 无Chrome", test_start_no_chrome)
test("POST /api/stop 不存在", test_stop_nonexistent)
test("POST /api/remove 不存在", test_remove_nonexistent)
test("GET /api/files", test_files)
test("GET /api/download 路径穿越", test_download_traversal)
test("GET /api/download 不存在", test_download_missing)
test("POST /api/delete-file 路径穿越", test_delete_traversal)
test("POST /api/batch-start 空列表", test_batch_empty)
test("POST /api/batch-start 超限", test_batch_too_many)
test("POST /api/batch-start 混合", test_batch_mixed)
test("速率限制", test_rate_limit)


# ============================================================
# 3. scrape.py
# ============================================================
print("\n=== scrape.py ===")


def test_scrape_imports():
    import scrape
    assert_true(hasattr(scrape, 'main'))
    assert_true(hasattr(scrape, 'validate_paper_id'))


test("scrape.py 导入", test_scrape_imports)


# ============================================================
# 4. 模板
# ============================================================
print("\n=== templates ===")


def test_tpl_chrome():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('chrome-status', c)
    assert_in('/api/chrome-status', c)
    assert_in('/api/chrome-start', c)
    # 确认不再有cookie相关UI
    assert_true('cookieValue' not in c, "不应有cookie输入框")


def test_tpl_esc():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('function esc(', c)
    assert_in('esc(line)', c)
    assert_in('esc(t.paper_id)', c)


def test_tpl_features():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('showToast', c)
    assert_in('/api/download/', c)
    assert_in('batchStart', c)
    assert_in('encodeURIComponent', c)


test("模板: Chrome相关", test_tpl_chrome)
test("模板: XSS转义", test_tpl_esc)
test("模板: 功能完整性", test_tpl_features)


# ============================================================
# 5. 文件结构
# ============================================================
print("\n=== 文件结构 ===")


def test_files_exist():
    for f in ['app.py', 'scrape.py', 'scraper_core.py', 'templates/index.html', '启动.bat', 'README.md']:
        assert_true(Path(f).exists(), f"缺少: {f}")


def test_exports():
    import scraper_core
    for name in ['collect_questions', 'save_to_excel', 'load_progress', 'save_progress',
                 'validate_paper_id', 'sanitize_text', 'ensure_chrome_debug', 'open_cdp_page',
                 'check_login_required', 'wait_for_question', 'click_next_question',
                 'navigate_with_retry']:
        assert_true(hasattr(scraper_core, name), f"缺少: {name}")


test("必需文件", test_files_exist)
test("模块导出", test_exports)


# ============================================================
print(f"\n{'='*50}")
print(f"测试结果: {passed} 通过, {failed} 失败, 共 {passed + failed} 项")
if errors:
    print(f"\n失败详情:")
    for name, err in errors:
        print(f"  - {name}: {err}")
print(f"{'='*50}")
sys.exit(1 if failed > 0 else 0)
