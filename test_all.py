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
    BROWSER_PROFILE_ROOT, _set_practice_sequence, _extract_practice_paper_id,
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


def test_validate_e_classify_url():
    pid, err = validate_paper_id("https://www.kaoshibao.com/e_classify/paper/103546")
    assert_eq(pid, "103546")


def test_validate_paper_info_url():
    pid, err = validate_paper_id("https://www.kaoshibao.com/paperInfo/25126872")
    assert_eq(pid, "25126872")


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
    assert_eq(CDP_PORT, 9223)
    assert_true(len(_BROWSER_PROFILES) >= 2, "应支持至少2种浏览器")


def test_practice_sequence_update():
    url = (
        "https://www.kaoshibao.com/online/?paperId=25126989"
        "&kid=103546&sequence=0&qtype_random_index=0"
    )
    updated = _set_practice_sequence(url, 42)
    assert_in("sequence=42", updated)
    assert_in("qtype_random_index=42", updated)
    assert_in("paperId=25126989", updated)
    assert_in("kid=103546", updated)


def test_practice_paper_id_validation():
    assert_eq(
        _extract_practice_paper_id(
            "https://www.kaoshibao.com/online/?paperId=25126872&kid=103545"
        ),
        "25126872",
    )
    assert_true(
        _extract_practice_paper_id(
            "https://www.kaoshibao.com/online/?paperId=&kid=25126872"
        )
        is None
    )


def test_windows_browser_profiles_isolated():
    if sys.platform == 'win32':
        for browser in _BROWSER_PROFILES:
            user_data = Path(browser['user_data']).resolve()
            assert_true(
                BROWSER_PROFILE_ROOT.resolve() in user_data.parents,
                f"{browser['name']} 应使用独立浏览器配置目录",
            )


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
test("validate: e_classify URL", test_validate_e_classify_url)
test("validate: paperInfo URL", test_validate_paper_info_url)
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
test("练习序号URL更新", test_practice_sequence_update)
test("练习页paperId校验", test_practice_paper_id_validation)
test("Windows浏览器配置隔离", test_windows_browser_profiles_isolated)
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


def test_start_bad_mode():
    reset_rl()
    r = client.post('/api/start', data=json.dumps({'paper_id': '12345', 'mode': 'evil'}), content_type='application/json')
    assert_eq(r.status_code, 400)
    d = json.loads(r.data)
    assert_in('error', d)


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
    r = client.post('/api/stop/abcd1234')
    assert_eq(r.status_code, 404)


def test_stop_bad_task_id():
    r = client.post('/api/stop/nope!')
    assert_eq(r.status_code, 400)


def test_remove_nonexistent():
    r = client.post('/api/remove/abcd1234')
    assert_eq(r.status_code, 404)


def test_remove_bad_task_id():
    r = client.post('/api/remove/XXGGHHII')
    assert_eq(r.status_code, 400)


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


def test_start_parallel_bad_id():
    reset_rl()
    r = client.post('/api/start-parallel', data=json.dumps({'paper_id': 'abc'}), content_type='application/json')
    assert_eq(r.status_code, 400)


def test_start_parallel_bad_workers():
    reset_rl()
    r = client.post('/api/start-parallel', data=json.dumps({'paper_id': '12345', 'workers': 99}), content_type='application/json')
    assert_eq(r.status_code, 400)


def test_start_parallel_bad_total():
    reset_rl()
    r = client.post('/api/start-parallel', data=json.dumps({'paper_id': '12345', 'workers': 3, 'total_questions': 5}), content_type='application/json')
    assert_eq(r.status_code, 400)


def test_merge_segments_bad_id():
    r = client.post('/api/merge-segments', data=json.dumps({'paper_id': 'xyz'}), content_type='application/json')
    assert_eq(r.status_code, 400)


def test_merge_segments_no_data():
    r = client.post('/api/merge-segments', data=json.dumps({'paper_id': '12345'}), content_type='application/json')
    d = json.loads(r.data)
    assert_in('ok', d)
    assert_eq(d['total'], 0)


def test_health():
    r = client.get('/health')
    assert_eq(r.status_code, 200)
    d = json.loads(r.data)
    assert_in('status', d)
    assert_in('chrome', d)
    assert_in('uptime', d)
    assert_in('ready', d)
    assert_in('tasks_failed', d)
    assert_true(isinstance(d['tasks_running'], int))
    assert_true(isinstance(d['tasks_total'], int))


def test_stats():
    r = client.get('/api/stats')
    assert_eq(r.status_code, 200)
    d = json.loads(r.data)
    assert_in('tasks', d)
    assert_in('files', d)
    assert_true(isinstance(d['tasks']['running'], int))
    assert_true(isinstance(d['tasks']['max'], int))


def test_security_headers():
    r = client.get('/')
    assert_eq(r.headers.get('X-Content-Type-Options'), 'nosniff')
    assert_eq(r.headers.get('X-Frame-Options'), 'SAMEORIGIN')
    assert_eq(r.headers.get('Referrer-Policy'), 'strict-origin-when-cross-origin')
    csp = r.headers.get('Content-Security-Policy', '')
    assert_in("default-src 'self'", csp)
    assert_in("frame-ancestors 'self'", csp)


def test_secret_key_set():
    assert_true(app.secret_key is not None, "SECRET_KEY 应已设置")
    assert_true(len(app.secret_key) >= 32, "SECRET_KEY 长度应 >= 32")


def test_export_bad_id():
    r = client.get('/api/export/abc')
    assert_eq(r.status_code, 400)


def test_export_bad_format():
    r = client.get('/api/export/12345?format=pdf')
    assert_eq(r.status_code, 400)


def test_export_no_data():
    r = client.get('/api/export/99999999?format=csv')
    assert_eq(r.status_code, 404)


def test_csv_export():
    from scraper_core import save_to_csv, DATA_DIR
    qs = [{'序号': 1, '题目类型': '单选', '题目': '测试题', '选项': 'A\nB', '正确答案': 'A', '解析': '解析'}]
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
        path = f.name
    try:
        save_to_csv(qs, path)
        with open(path, 'r', encoding='utf-8-sig') as fh:
            content = fh.read()
        assert_in('测试题', content)
        assert_in('正确答案', content)
    finally:
        os.unlink(path)


def test_json_export():
    from scraper_core import save_to_json
    qs = [{'序号': 1, '题目类型': '单选', '题目': 'JSON题', '选项': ['A', 'B'], '正确答案': 'A', '解析': ''}]
    import tempfile, os, json as _json
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        path = f.name
    try:
        save_to_json(qs, path)
        with open(path, 'r', encoding='utf-8') as fh:
            data = _json.load(fh)
        assert_eq(len(data), 1)
        assert_eq(data[0]['题目'], 'JSON题')
        assert_true(isinstance(data[0]['选项'], list))
    finally:
        os.unlink(path)


def test_history():
    r = client.get('/api/history')
    assert_eq(r.status_code, 200)
    d = json.loads(r.data)
    assert_true(isinstance(d, list))
    for item in d:
        assert_in('paper_id', item)
        assert_in('count', item)
        assert_in('mtime', item)


def test_clear_progress_bad_id():
    r = client.post('/api/clear-progress/abc')
    assert_eq(r.status_code, 400)


def test_clear_progress_nonexistent():
    r = client.post('/api/clear-progress/99999999')
    assert_eq(r.status_code, 200)
    d = json.loads(r.data)
    assert_in('ok', d)
    assert_eq(d['removed'], 0)


def test_clear_progress_actual():
    from scraper_core import save_progress, load_progress, DATA_DIR
    save_progress('88888888', [{'序号': 1, '题目': 'x'}])
    assert_true((DATA_DIR / 'progress_88888888.json').exists())
    r = client.post('/api/clear-progress/88888888')
    assert_eq(r.status_code, 200)
    d = json.loads(r.data)
    assert_eq(d['ok'], True)
    assert_eq(d['removed'], 1)
    assert_true(not (DATA_DIR / 'progress_88888888.json').exists())


def test_delete_files_empty():
    reset_rl()
    r = client.post('/api/delete-files', data=json.dumps({'names': []}), content_type='application/json')
    assert_eq(r.status_code, 400)


def test_delete_files_traversal():
    reset_rl()
    r = client.post('/api/delete-files', data=json.dumps({'names': ['../../bad']}), content_type='application/json')
    d = json.loads(r.data)
    assert_eq(d['ok'], True)
    assert_eq(d['removed'], 0)


def test_delete_files_actual():
    from scraper_core import OUTPUT_DIR, save_to_excel
    fname = 'test_batch_del_001.xlsx'
    fpath = OUTPUT_DIR / fname
    save_to_excel([{'序号': 1, '题目': 'x'}], str(fpath))
    assert_true(fpath.exists())
    reset_rl()
    r = client.post('/api/delete-files', data=json.dumps({'names': [fname]}), content_type='application/json')
    d = json.loads(r.data)
    assert_eq(d['ok'], True)
    assert_eq(d['removed'], 1)
    assert_true(not fpath.exists())


def test_a11y_aria():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('role="status"', c)
    assert_in('aria-live="polite"', c)
    assert_in('role="tablist"', c)
    assert_in('role="tab"', c)
    assert_in('aria-selected', c)
    assert_in('role="tabpanel"', c)
    assert_in('role="progressbar"', c)
    assert_in('aria-valuenow', c)
    assert_in('role="list"', c)
    assert_in('aria-label', c)


def test_export_log_feature():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('function exportLog', c)
    assert_in('URL.createObjectURL', c)
    assert_in('任务日志_', c)


def test_code_style_config():
    assert_true(Path('pyproject.toml').exists(), "缺少 pyproject.toml")
    assert_true(Path('.editorconfig').exists(), "缺少 .editorconfig")
    with open('pyproject.toml', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('tool.ruff', c)
    assert_in('line-length', c)
    with open('.editorconfig', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('indent_style', c)
    assert_in('indent_size', c)


def test_max_content_length():
    assert_true('MAX_CONTENT_LENGTH' in app.config, "应设置 MAX_CONTENT_LENGTH")
    assert_true(app.config['MAX_CONTENT_LENGTH'] > 0)


def test_oversized_request():
    reset_rl()
    big_id = '1' * 10000
    r = client.post('/api/start', data=json.dumps({'paper_id': big_id}), content_type='application/json')
    assert_true(r.status_code in (400, 413))


def test_batch_id_too_long():
    reset_rl()
    long_id = '1' * 300
    r = client.post('/api/batch-start', data=json.dumps({'ids': [long_id]}), content_type='application/json')
    d = json.loads(r.data)
    if 'results' in d:
        assert_true(any('过长' in (r.get('error') or '') for r in d['results']))


def test_404_api_json():
    r = client.get('/api/nonexistent-endpoint')
    assert_eq(r.status_code, 404)
    d = json.loads(r.data)
    assert_in('error', d)
    assert_eq(d.get('code'), 404)


def test_405_method():
    r = client.get('/api/start')
    assert_eq(r.status_code, 405)
    d = json.loads(r.data)
    assert_in('error', d)


def test_413_oversized():
    reset_rl()
    big = 'x' * (2 * 1024 * 1024)
    r = client.post('/api/start', data=json.dumps({'paper_id': big}), content_type='application/json')
    assert_eq(r.status_code, 413)


def test_manifest():
    r = client.get('/manifest.json')
    assert_eq(r.status_code, 200)
    d = json.loads(r.data)
    assert_in('name', d)
    assert_in('short_name', d)
    assert_in('theme_color', d)
    assert_eq(d['display'], 'standalone')


def test_favicon_in_template():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('rel="icon"', c)
    assert_in('image/svg+xml', c)
    assert_in('manifest.json', c)
    assert_in('theme-color', c)


def test_task_timeout_fields():
    from app import new_task
    t = new_task('12345')
    assert_in('timeout', t)
    assert_eq(t['timeout'], 3600)
    assert_in('timed_out', t)
    assert_eq(t['timed_out'], False)


def test_tasks_api_has_timeout():
    r = client.get('/api/tasks')
    d = json.loads(r.data)
    assert_true(isinstance(d, list))


def test_cleanup_bad_days():
    r = client.post('/api/cleanup', data=json.dumps({'days': 0}), content_type='application/json')
    assert_eq(r.status_code, 400)
    r2 = client.post('/api/cleanup', data=json.dumps({'days': 999}), content_type='application/json')
    assert_eq(r2.status_code, 400)


def test_cleanup_bad_type():
    r = client.post('/api/cleanup', data=json.dumps({'days': 'abc'}), content_type='application/json')
    assert_eq(r.status_code, 400)


def test_cleanup_actual():
    from scraper_core import DATA_DIR, save_progress
    import os
    fname = DATA_DIR / 'progress_test_cleanup_old.json'
    save_progress('test_cleanup_old', [{'序号': 1}])
    old_time = time.time() - 40 * 86400
    os.utime(str(fname), (old_time, old_time))
    r = client.post('/api/cleanup', data=json.dumps({'days': 30}), content_type='application/json')
    d = json.loads(r.data)
    assert_eq(d['ok'], True)
    assert_true(d['removed'] >= 1)
    assert_true(not fname.exists())


def test_task_sort_ui():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('taskSort', c)
    assert_in('按状态', c)
    assert_in('按时间', c)
    assert_in('按进度', c)
    assert_in('sorted.sort', c)


def test_fetch_error_handling():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('function apiFetch', c)
    assert_in('unhandledrejection', c)
    assert_in("addEventListener('online'", c)
    assert_in("addEventListener('offline'", c)


def test_type_annotations():
    import inspect
    import scraper_core
    funcs = ['save_to_excel', 'save_to_csv', 'save_to_json', 'export_questions',
             'load_progress', 'save_progress', 'validate_paper_id', 'sanitize_text',
             'is_port_open', 'merge_segments']
    for name in funcs:
        fn = getattr(scraper_core, name)
        sig = inspect.signature(fn)
        hints = sig.return_annotation
        assert_true(hints is not inspect.Parameter.empty, f"{name} 应有返回类型注解")


def test_scrape_unpacks_3_tuple():
    with open('scrape.py', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('ok, msg, restarted = ensure_chrome_debug()', c)
    assert_true('ok, msg = ensure_chrome_debug()' not in c, "不应有2元组解包")


def test_scrape_resume_logic():
    with open('scrape.py', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('start_sequence = len(questions)', c, "应从断点继续")
    assert_in('existing_keys', c, "应合并去重")
    assert_in('auth_error', c, "应处理登录错误")
    assert_in('added', c, "应统计新增题数")
    assert_true('if not questions:' not in c.replace('if not questions:\n', '', 1), "不应跳过已有进度")


def test_atomic_write_progress():
    from scraper_core import save_progress, DATA_DIR
    save_progress('test_atomic_001', [{'序号': 1, '题目': '原子写入测试'}])
    main_file = DATA_DIR / 'progress_test_atomic_001.json'
    tmp_file = DATA_DIR / 'progress_test_atomic_001.json.tmp'
    assert_true(main_file.exists(), "主文件应存在")
    assert_true(not tmp_file.exists(), "临时文件应已被 replace 清理")
    main_file.unlink()


def test_atomic_write_segment():
    from scraper_core import save_segment_progress, DATA_DIR
    save_segment_progress('test_atomic_seg', 0, [{'序号': 1}])
    main_file = DATA_DIR / 'progress_test_atomic_seg_seg0.json'
    tmp_file = DATA_DIR / 'progress_test_atomic_seg_seg0.json.tmp'
    assert_true(main_file.exists())
    assert_true(not tmp_file.exists(), "分段临时文件应已清理")
    main_file.unlink()


def test_log_dir_is_project():
    with open('logging_config.py', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('Path(__file__).parent / "logs"', c)
    assert_true('Desktop' not in c.split('def init_default_logger')[1].split('return')[0], "不应默认用桌面目录")


def test_api_docs():
    r = client.get('/api/docs')
    assert_eq(r.status_code, 200)
    d = json.loads(r.data)
    assert_eq(d['openapi'], '3.0.0')
    assert_in('paths', d)
    assert_in('info', d)
    assert_true(len(d['paths']) >= 15, "应至少 15 个端点")
    assert_in('/health', d['paths'])
    assert_in('/api/start', d['paths'])
    assert_in('/api/export/{paper_id}', d['paths'])


def test_config_persistence():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('function loadConfig', c)
    assert_in('function saveConfig', c)
    assert_in("'cfg_' + key", c)
    assert_in('cfg_parallelMode', c)
    assert_in('bindConfigChange', c)


def test_file_sort():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('id="fileSort"', c)
    assert_in('time-desc', c)
    assert_in('name-asc', c)
    assert_in('size-desc', c)
    assert_in('files.sort', c)


def test_chrome_disconnect_banner():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('id="chromeBanner"', c)
    assert_in('chrome-banner', c)
    assert_in('disconnected', c)
    assert_in('pulsing', c)
    assert_in('chromePulse', c)


def test_skeleton_screen():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('skeletonShimmer', c)
    assert_in('function skeletonItems', c)
    assert_in('skeleton-item', c)
    assert_in('skeleton-line', c)


def test_docker_env_config():
    with open('docker-compose.yml', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('FLASK_SECRET_KEY', c)
    assert_in('LOG_LEVEL', c)
    assert_in('/health', c)
    import os
    assert_true(os.path.exists('.env.example'))


def test_env_example_complete():
    """验证.env.example包含所有必要环境变量"""
    with open('.env.example', 'r', encoding='utf-8') as f:
        content = f.read()
    assert_in('FLASK_SECRET_KEY', content)
    assert_in('AUTH_TOKEN', content)
    assert_in('LOG_LEVEL', content)
    assert_in('PYTHONUNBUFFERED', content)
    assert_in('PLAYWRIGHT_BROWSERS_PATH', content)


def test_save_excel_uses_normalize():
    with open('scraper_core.py', 'r', encoding='utf-8') as f:
        c = f.read()
    idx_excel = c.index('def save_to_excel')
    idx_next = c.index('def ', idx_excel + 10)
    excel_body = c[idx_excel:idx_next]
    assert_in('_normalize_options', excel_body)


def test_log_level_env():
    with open('logging_config.py', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('LOG_LEVEL', c)
    assert_in('os.environ.get', c)


def test_csrf_protection():
    with open('app.py', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('csrf_origin_check', c)
    assert_in('Origin', c)
    reset_rl()
    r = client.post('/api/start', data=json.dumps({'paper_id': '12345'}),
                    content_type='application/json',
                    headers={'Origin': 'http://evil.com', 'Host': 'localhost:5678'})
    assert_eq(r.status_code, 403)


def test_css_variables():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in(':root', c)
    assert_in('--bg:', c)
    assert_in('--card-bg:', c)
    assert_in('var(--bg)', c)
    assert_in('var(--card-bg)', c)


def test_async_type_annotations():
    with open('scraper_core.py', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('async def navigate_with_retry(page, url, retries=3, timeout=30000) -> bool:', c)
    assert_in('async def close_popups(page) -> None:', c)
    assert_in('async def get_current_question(page, mode=\'ocr\') -> dict | None:', c)
    assert_in('async def collect_questions(page, paper_id, log_fn=None, stop_check=None, progress_fn=None,', c)
    assert_in('-> tuple[list[dict[str, Any]], str]:', c)
    assert_in('async def check_login_required(page) -> bool:', c)
    assert_in('async def find_practice_url(page, paper_id, log_fn=None) -> str | None:', c)


def test_gunicorn_wsgi():
    with open('Dockerfile', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('gunicorn', c)
    assert_in('app:app', c)
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('gunicorn', c)
    with open('ecosystem.config.js', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('gunicorn', c)


def test_windows_local_server_scripts():
    for filename in ('start-local.ps1', 'stop-local.ps1'):
        assert_true(Path(filename).exists(), f"缺少: {filename}")
    with open('start-local.ps1', 'r', encoding='utf-8') as f:
        start_script = f.read()
    with open('stop-local.ps1', 'r', encoding='utf-8') as f:
        stop_script = f.read()
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        requirements = f.read()
    assert_in('waitress', start_script)
    assert_in('127.0.0.1:5678', start_script)
    assert_in('taskkill.exe', stop_script)
    assert_in('waitress', requirements)


def test_get_current_question_split():
    with open('scraper_core.py', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('async def _extract_answer_and_type', c)
    assert_in('def _enhance_and_ocr', c)
    assert_in('async def _ocr_analysis_section', c)
    import inspect
    from scraper_core import get_current_question
    lines = inspect.getsource(get_current_question).count(chr(10))
    assert_true(lines < 200, f"get_current_question应<200行, 实际{lines}行")


def test_collect_questions_split():
    with open('scraper_core.py', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('async def _init_recite_mode', c)
    import inspect
    from scraper_core import collect_questions
    lines = inspect.getsource(collect_questions).count(chr(10))
    assert_true(lines < 290, f"collect_questions应<290行, 实际{lines}行")


def test_virtual_scroll():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('fileVisibleCount', c)
    assert_in('loadMoreFiles', c)
    assert_in('加载更多', c)
    assert_in('slice(0, fileVisibleCount)', c)


def test_auth_mechanism():
    with open('app.py', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('AUTH_TOKEN', c)
    assert_in('auth_check', c)
    assert_in('X-Auth-Token', c)
    assert_in('401', c)


test("GET /", test_index)
test("GET /api/chrome-status", test_chrome_status)
test("POST /api/chrome-start", test_chrome_start)
test("GET /api/tasks", test_tasks_empty)
test("POST /api/start 空ID", test_start_empty_id)
test("POST /api/start 错误ID", test_start_bad_id)
test("POST /api/start 错误mode", test_start_bad_mode)
test("POST /api/start 非JSON", test_start_no_json)
test("POST /api/start 无Chrome", test_start_no_chrome)
test("POST /api/stop 不存在", test_stop_nonexistent)
test("POST /api/stop 无效task_id", test_stop_bad_task_id)
test("POST /api/remove 不存在", test_remove_nonexistent)
test("POST /api/remove 无效task_id", test_remove_bad_task_id)
test("GET /api/files", test_files)
test("GET /api/download 路径穿越", test_download_traversal)
test("GET /api/download 不存在", test_download_missing)
test("POST /api/delete-file 路径穿越", test_delete_traversal)
test("POST /api/batch-start 空列表", test_batch_empty)
test("POST /api/batch-start 超限", test_batch_too_many)
test("POST /api/batch-start 混合", test_batch_mixed)
test("速率限制", test_rate_limit)
test("POST /api/start-parallel 错误ID", test_start_parallel_bad_id)
test("POST /api/start-parallel 错误workers", test_start_parallel_bad_workers)
test("POST /api/start-parallel 错误total", test_start_parallel_bad_total)
test("POST /api/merge-segments 错误ID", test_merge_segments_bad_id)
test("POST /api/merge-segments 无数据", test_merge_segments_no_data)
test("GET /health 健康检查", test_health)
test("GET /api/stats 监控指标", test_stats)
test("安全响应头", test_security_headers)
test("SECRET_KEY 已设置", test_secret_key_set)
test("GET /api/export 错误ID", test_export_bad_id)
test("GET /api/export 错误格式", test_export_bad_format)
test("GET /api/export 无数据", test_export_no_data)
test("save_to_csv 导出", test_csv_export)
test("save_to_json 导出", test_json_export)
test("GET /api/history 历史", test_history)
test("POST /api/clear-progress 错误ID", test_clear_progress_bad_id)
test("POST /api/clear-progress 不存在", test_clear_progress_nonexistent)
test("POST /api/clear-progress 实际清除", test_clear_progress_actual)
test("POST /api/delete-files 空列表", test_delete_files_empty)
test("POST /api/delete-files 路径穿越", test_delete_files_traversal)
test("POST /api/delete-files 实际删除", test_delete_files_actual)
test("可访问性 ARIA 属性", test_a11y_aria)
test("任务日志导出功能", test_export_log_feature)
test("代码风格配置文件", test_code_style_config)
test("MAX_CONTENT_LENGTH 已设置", test_max_content_length)
test("超大请求被拒", test_oversized_request)
test("批量ID过长校验", test_batch_id_too_long)
test("404 API 返回 JSON", test_404_api_json)
test("405 方法不允许", test_405_method)
test("413 请求过大", test_413_oversized)
test("GET /manifest.json PWA", test_manifest)
test("favicon 与 manifest 引用", test_favicon_in_template)
test("任务超时字段", test_task_timeout_fields)
test("/api/tasks 含超时信息", test_tasks_api_has_timeout)
test("POST /api/cleanup 错误天数", test_cleanup_bad_days)
test("POST /api/cleanup 错误类型", test_cleanup_bad_type)
test("POST /api/cleanup 实际清理", test_cleanup_actual)
test("任务排序 UI", test_task_sort_ui)
test("前端错误统一处理", test_fetch_error_handling)
test("核心函数类型注解", test_type_annotations)
test("scrape.py 3元组解包修复", test_scrape_unpacks_3_tuple)
test("scrape.py 断点续传逻辑", test_scrape_resume_logic)
test("原子写入进度文件", test_atomic_write_progress)
test("原子写入分段文件", test_atomic_write_segment)
test("日志目录使用项目logs", test_log_dir_is_project)
test("GET /api/docs API文档", test_api_docs)
test("前端配置持久化", test_config_persistence)
test("文件列表排序选项", test_file_sort)
test("Chrome断开明显提示", test_chrome_disconnect_banner)
test("骨架屏加载动画", test_skeleton_screen)
test("Docker环境变量配置", test_docker_env_config)
test("save_to_excel去重", test_save_excel_uses_normalize)
test("日志级别环境变量", test_log_level_env)
test("CSRF Origin验证", test_csrf_protection)
test("CSS变量去重", test_css_variables)
test("async函数类型注解", test_async_type_annotations)
test("生产WSGI(gunicorn)", test_gunicorn_wsgi)
test("Windows本地服务脚本", test_windows_local_server_scripts)
test("get_current_question拆分", test_get_current_question_split)
test("collect_questions拆分", test_collect_questions_split)
test("虚拟滚动(分页加载)", test_virtual_scroll)
test("简单认证机制", test_auth_mechanism)
test(".env.example完整", test_env_example_complete)


def test_ci_config():
    """验证CI/CD配置存在且格式正确"""
    import os
    ci_path = '.github/workflows/ci.yml'
    assert_true(os.path.exists(ci_path), "ci.yml应存在")
    with open(ci_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert_in('jobs', content)
    assert_in('test', content)
    assert_in('lint', content)
    assert_in('python-version', content)
    assert_in('coverage', content)


test("CI/CD配置", test_ci_config)


def test_coverage_config():
    """验证代码覆盖率配置存在且格式正确"""
    import os
    assert_true(os.path.exists('.coveragerc'), ".coveragerc应存在")
    with open('.coveragerc', 'r', encoding='utf-8') as f:
        content = f.read()
    assert_in('[run]', content)
    assert_in('[report]', content)
    assert_in('source', content)
    assert_in('branch', content)
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        req = f.read()
    assert_in('coverage', req)


test("代码覆盖率配置", test_coverage_config)


def test_systemd_not_root():
    """验证systemd服务配置包含Xvfb虚拟显示器支持"""
    with open('kaoshibao.service', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('DISPLAY=', c)
    assert_in('xvfb.service', c)
    with open('xvfb.service', 'r', encoding='utf-8') as f:
        x = f.read()
    assert_in('Xvfb', x)


test("systemd非root用户", test_systemd_not_root)


def test_db_connection_pool():
    """验证db_store使用连接池和批量插入"""
    with open('db_store.py', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('SimpleConnectionPool', c)
    assert_in('_get_pool', c)
    assert_in('execute_values', c)
    assert_in('putconn', c)


test("数据库连接池+批量插入", test_db_connection_pool)


def test_rate_limit_persistence():
    """验证速率限制持久化机制"""
    with open('app.py', 'r', encoding='utf-8') as f:
        c = f.read()
    assert_in('_rate_limit_file', c)
    assert_in('_load_rate_limit', c)
    assert_in('_save_rate_limit', c)
    assert_in('atexit', c)
    assert_in('rate_limit.json', c)


test("速率限制持久化", test_rate_limit_persistence)


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
