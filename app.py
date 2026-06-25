"""考试宝题库爬取 - Web服务端（Chrome CDP模式）"""

import asyncio
import json
import sys
import io
import threading
import time
import uuid
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file

from scraper_core import (
    OUTPUT_DIR, collect_questions,
    save_to_excel, load_progress, save_progress,
    validate_paper_id, ensure_chrome_debug, get_chrome_status, open_cdp_page,
    reopen_kaoshibao, load_segment_progress, save_segment_progress, merge_segments
)

if not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

app = Flask(__name__, template_folder=str(Path(__file__).parent / 'templates'))

MAX_TASKS = 5

tasks = {}
tasks_lock = threading.Lock()

# 速率限制
_rate_limit = {}
_rate_limit_lock = threading.Lock()


def new_task(paper_id, segment_id=-1, start_sequence=0, max_questions=0, mode='ocr'):
    return {
        'task_id': '',
        'paper_id': paper_id,
        'segment_id': segment_id,
        'start_sequence': start_sequence,
        'max_questions': max_questions,
        'mode': mode,
        'running': True,
        'phase': 'init',
        'progress': 0,
        'total': 0,
        'has_answer': 0,
        'message': '启动中...',
        'log': [],
        'stop_requested': False,
        'created_at': time.time(),
        'output_file': '',
        'started_at': 0,
    }


def task_log(task, msg):
    timestamp = time.strftime('%H:%M:%S')
    entry = f"[{timestamp}] {msg}"
    task['log'].append(entry)
    if len(task['log']) > 200:
        task['log'] = task['log'][-200:]
    try:
        print(f"[{task['task_id'][:8]}] {msg}")
    except UnicodeEncodeError:
        print(f"[{task['task_id'][:8]}] (含特殊字符，已跳过输出)")


def check_rate_limit(ip, min_interval=1.0):
    now = time.time()
    with _rate_limit_lock:
        if len(_rate_limit) > 1000:
            cutoff = now - 3600
            expired = [k for k, v in _rate_limit.items() if v < cutoff]
            for k in expired:
                del _rate_limit[k]
        last = _rate_limit.get(ip, 0)
        if now - last < min_interval:
            return False
        _rate_limit[ip] = now
    return True


def get_request_json():
    if not request.is_json:
        return None, '请求格式错误，请使用JSON'
    data = request.json
    if data is None:
        return None, '无效的JSON数据'
    return data, None


def run_task(task_id):
    task = tasks[task_id]
    paper_id = task['paper_id']
    segment_id = task.get('segment_id', -1)
    start_sequence = task.get('start_sequence', 0)
    max_questions = task.get('max_questions', 0)
    mode = task.get('mode', 'ocr')
    is_segment = segment_id >= 0

    mode_suffix = f"_{mode}" if mode and mode != 'ocr' else ''
    output_file = OUTPUT_DIR / f"考试宝题库_{paper_id}{mode_suffix}.xlsx"
    task['output_file'] = str(output_file)

    questions = []
    if not is_segment:
        questions = load_progress(paper_id, suffix=mode_suffix)
        if questions:
            task_log(task, f"已有进度: {len(questions)} 道题目，从第{len(questions)+1}题继续")
            task['has_answer'] = sum(1 for q in questions if q.get('正确答案'))
            task['total'] = len(questions)
            task['progress'] = len(questions)
            # 从上次停止的位置继续
            start_sequence = len(questions)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        from playwright.async_api import async_playwright

        async def do_scrape():
            nonlocal questions

            label = f"分段{segment_id}" if is_segment else ""
            task_log(task, f"连接Chrome{'('+label+')' if is_segment else ''}...")
            async with async_playwright() as p:
                browser, page = await open_cdp_page(p)
                if not browser:
                    task_log(task, "无法连接Chrome，请确保Chrome已启动并登录考试宝")
                    task['phase'] = 'error'
                    task['message'] = '无法连接Chrome'
                    return questions

                try:
                    task_log(task, "已连接Chrome，打开新标签页")
                    task['phase'] = 'collect'
                    task['started_at'] = time.time()

                    def on_progress(collected, with_answer):
                        task['total'] = collected
                        task['progress'] = collected
                        task['has_answer'] = with_answer

                    result, status = await collect_questions(
                        page, paper_id,
                        log_fn=lambda msg: task_log(task, msg),
                        stop_check=lambda: task.get('stop_requested'),
                        progress_fn=on_progress,
                        start_sequence=start_sequence,
                        max_questions=max_questions,
                        mode=mode
                    )

                    if status == 'auth_error':
                        task['phase'] = 'error'
                        task['message'] = '登录超时或已取消，请在Chrome中登录考试宝后重试'
                        return questions

                    if result:
                        # 合并新旧题目
                        existing_keys = {q.get('题目', '')[:80] for q in questions}
                        added = 0
                        for q in result:
                            key = q.get('题目', '')[:80]
                            if key and key not in existing_keys:
                                q['序号'] = len(questions) + 1
                                questions.append(q)
                                existing_keys.add(key)
                                added += 1
                        task_log(task, f"新增 {added} 题，总计 {len(questions)} 题")
                    else:
                        task_log(task, "未收集到新题目，保留已有数据")
                    return questions

                except Exception as e:
                    task_log(task, f"爬取出错: {e}")
                    return questions
                finally:
                    try:
                        await page.close()
                    except Exception:
                        pass

        loop.run_until_complete(do_scrape())

        if is_segment:
            save_segment_progress(paper_id, segment_id, questions)
        elif questions:
            save_progress(paper_id, questions, suffix=mode_suffix)
            save_to_excel(questions, output_file)

        task['phase'] = 'done'
        task['has_answer'] = sum(1 for q in questions if q.get('正确答案'))
        task['total'] = len(questions)
        task['progress'] = len(questions)
        task_log(task, f"完成! 总 {len(questions)} 道, 有答案 {task['has_answer']} 道")
        task['message'] = f"完成! {len(questions)}题, {task['has_answer']}道有答案"

    except Exception as e:
        task_log(task, f"错误: {e}")
        task['phase'] = 'error'
        task['message'] = f"错误: {e}"
    finally:
        task['running'] = False
        loop.close()


# ---- Flask 路由 ----

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/chrome-status')
def chrome_status():
    ok = get_chrome_status()
    return jsonify({'online': ok})


@app.route('/api/chrome-start', methods=['POST'])
def chrome_start():
    if not check_rate_limit(request.remote_addr, 5.0):
        return jsonify({'error': '操作太频繁'}), 429
    ok, msg, restarted = ensure_chrome_debug()

    login_status = None
    if ok and restarted:
        # Chrome重启后，自动打开本工具页面 + 考试宝并检查登录态
        try:
            from playwright.async_api import async_playwright
            async def reopen_pages():
                async with async_playwright() as p:
                    browser = await p.chromium.connect_over_cdp(CDP_URL)
                    if not browser.contexts:
                        return None
                    context = browser.contexts[0]
                    # 先打开本工具页面（用户能立刻看到界面）
                    tool_page = await context.new_page()
                    await tool_page.goto('http://localhost:5678')
                    # 再打开考试宝检查登录态
                    ks_page, logged_in = await reopen_kaoshibao(p)
                    if ks_page:
                        try:
                            await ks_page.close()
                        except Exception:
                            pass
                    return logged_in
            loop = asyncio.new_event_loop()
            login_status = loop.run_until_complete(reopen_pages())
            loop.close()
        except Exception as e:
            print(f"Chrome重启后打开页面失败: {e}")

    return jsonify({'ok': ok, 'message': msg, 'restarted': restarted, 'logged_in': login_status})


@app.route('/api/tasks')
def list_tasks():
    with tasks_lock:
        result = []
        for tid, t in tasks.items():
            elapsed = 0
            if t.get('started_at') and (t['running'] or t['phase'] == 'done'):
                elapsed = int(time.time() - t['started_at'])
            result.append({
                'task_id': t['task_id'],
                'paper_id': t['paper_id'],
                'segment_id': t.get('segment_id', -1),
                'mode': t.get('mode', 'ocr'),
                'running': t['running'],
                'phase': t['phase'],
                'progress': t['progress'],
                'total': t['total'],
                'has_answer': t['has_answer'],
                'message': t['message'],
                'log': t['log'],
                'output_file': t['output_file'],
                'created_at': t['created_at'],
                'elapsed': elapsed,
            })
    return jsonify(result)


@app.route('/api/start', methods=['POST'])
def start_task():
    if not check_rate_limit(request.remote_addr, 2.0):
        return jsonify({'error': '操作太频繁，请稍后再试'}), 429

    data, err = get_request_json()
    if err:
        return jsonify({'error': err}), 400

    raw_id = data.get('paper_id', '')
    paper_id, err = validate_paper_id(raw_id)
    if err:
        return jsonify({'error': err}), 400

    mode = data.get('mode', 'ocr')

    # 检查Chrome是否可用
    if not get_chrome_status():
        return jsonify({'error': 'Chrome未启动，请先点击"启动Chrome"'}), 400

    # 竞速模式：同时启动OCR和DOM两个任务
    if mode == 'race':
        with tasks_lock:
            running_count = sum(1 for t in tasks.values() if t['running'])
            if running_count + 2 > MAX_TASKS * 2:
                return jsonify({'error': '当前运行任务过多'}), 400

            task_ids = []
            for m in ['hybrid', 'ocr', 'dom']:
                task_id = str(uuid.uuid4())[:8]
                task = new_task(paper_id, mode=m)
                task['task_id'] = task_id
                task['message'] = f'竞速模式({m.upper()})'
                tasks[task_id] = task
                task_ids.append(task_id)

        for tid in task_ids:
            thread = threading.Thread(target=run_task, args=(tid,), daemon=True)
            thread.start()
        return jsonify({'ok': True, 'task_ids': task_ids, 'mode': 'race'})

    with tasks_lock:
        running_count = sum(1 for t in tasks.values() if t['running'])
        if running_count >= MAX_TASKS:
            return jsonify({'error': f'最多同时运行{MAX_TASKS}个任务'}), 400

        for t in tasks.values():
            if t['paper_id'] == paper_id and t['running']:
                return jsonify({'error': f'题库 {paper_id} 正在爬取中'}), 400

        task_id = str(uuid.uuid4())[:8]
        task = new_task(paper_id, mode=mode)
        task['task_id'] = task_id
        tasks[task_id] = task

    thread = threading.Thread(target=run_task, args=(task_id,), daemon=True)
    thread.start()
    return jsonify({'ok': True, 'task_id': task_id})


@app.route('/api/stop/<task_id>', methods=['POST'])
def stop_task(task_id):
    with tasks_lock:
        task = tasks.get(task_id)
        if not task:
            return jsonify({'error': '任务不存在'}), 404
        if not task['running']:
            return jsonify({'error': '任务已停止'}), 400
        task['stop_requested'] = True
        task_log(task, "正在停止...")
    return jsonify({'ok': True})


@app.route('/api/remove/<task_id>', methods=['POST'])
def remove_task(task_id):
    with tasks_lock:
        task = tasks.get(task_id)
        if not task:
            return jsonify({'error': '任务不存在'}), 404
        if task['running']:
            return jsonify({'error': '请先停止任务'}), 400
        del tasks[task_id]
    return jsonify({'ok': True})


@app.route('/api/files')
def list_files():
    files = []
    for f in OUTPUT_DIR.glob('*.xlsx'):
        files.append({
            'name': f.name,
            'size': f.stat().st_size,
            'time': f.stat().st_mtime
        })
    files.sort(key=lambda x: x['time'], reverse=True)
    return jsonify(files)


@app.route('/api/download/<filename>')
def download_file(filename):
    if not filename or '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': '无效文件名'}), 400
    import re
    if not re.match(r'^[\w\-\.一-鿿]+$', filename):
        return jsonify({'error': '无效文件名'}), 400
    filepath = OUTPUT_DIR / filename
    if not filepath.exists() or filepath.suffix != '.xlsx':
        return jsonify({'error': '文件不存在'}), 404
    return send_file(filepath, as_attachment=True, download_name=filename)


@app.route('/api/delete-file', methods=['POST'])
def delete_file():
    data, err = get_request_json()
    if err:
        return jsonify({'error': err}), 400
    name = data.get('name', '')
    if not name or '..' in name or '/' in name or '\\' in name:
        return jsonify({'error': '无效文件名'}), 400
    filepath = OUTPUT_DIR / name
    if filepath.exists() and filepath.suffix == '.xlsx':
        filepath.unlink()
        return jsonify({'ok': True})
    return jsonify({'error': '文件不存在'}), 404


@app.route('/api/batch-start', methods=['POST'])
def batch_start():
    if not check_rate_limit(request.remote_addr, 3.0):
        return jsonify({'error': '操作太频繁'}), 429

    data, err = get_request_json()
    if err:
        return jsonify({'error': err}), 400

    ids_raw = data.get('ids', [])
    if not ids_raw or not isinstance(ids_raw, list):
        return jsonify({'error': '请输入题库ID列表'}), 400
    if len(ids_raw) > 10:
        return jsonify({'error': '单次最多10个'}), 400

    if not get_chrome_status():
        return jsonify({'error': 'Chrome未启动，请先启动Chrome'}), 400

    results = []
    for raw_id in ids_raw:
        paper_id, err = validate_paper_id(str(raw_id))
        if err:
            results.append({'id': str(raw_id), 'error': err})
            continue

        with tasks_lock:
            running_count = sum(1 for t in tasks.values() if t['running'])
            if running_count >= MAX_TASKS:
                results.append({'id': paper_id, 'error': f'已达最大并发数{MAX_TASKS}'})
                continue

            duplicate = any(t['paper_id'] == paper_id and t['running'] for t in tasks.values())
            if duplicate:
                results.append({'id': paper_id, 'error': '已在运行中'})
                continue

            task_id = str(uuid.uuid4())[:8]
            task = new_task(paper_id)
            task['task_id'] = task_id
            tasks[task_id] = task

        thread = threading.Thread(target=run_task, args=(task_id,), daemon=True)
        thread.start()
        results.append({'id': paper_id, 'ok': True, 'task_id': task_id})

    return jsonify({'results': results})


@app.route('/api/start-parallel', methods=['POST'])
def start_parallel():
    """分段并行爬取：把一个题库拆成多段同时爬"""
    if not check_rate_limit(request.remote_addr, 5.0):
        return jsonify({'error': '操作太频繁'}), 429

    data, err = get_request_json()
    if err:
        return jsonify({'error': err}), 400

    raw_id = data.get('paper_id', '')
    paper_id, err = validate_paper_id(raw_id)
    if err:
        return jsonify({'error': err}), 400

    workers = data.get('workers', 4)
    if not isinstance(workers, int) or workers < 2 or workers > 5:
        return jsonify({'error': '并行数需在2-5之间'}), 400

    total_questions = data.get('total_questions', 702)
    if not isinstance(total_questions, int) or total_questions < 10:
        return jsonify({'error': '总题数需>=10'}), 400

    if not get_chrome_status():
        return jsonify({'error': 'Chrome未启动，请先启动Chrome'}), 400

    # 计算每段的题数和起始位置
    seg_size = total_questions // workers
    segments = []
    for i in range(workers):
        start = i * seg_size
        count = seg_size if i < workers - 1 else total_questions - start
        segments.append({'segment_id': i, 'start_sequence': start, 'max_questions': count})

    with tasks_lock:
        running_count = sum(1 for t in tasks.values() if t['running'])
        if running_count + workers > MAX_TASKS * 2:
            return jsonify({'error': f'当前运行任务过多，请稍后再试'}), 400

        task_ids = []
        for seg in segments:
            task_id = str(uuid.uuid4())[:8]
            task = new_task(
                paper_id,
                segment_id=seg['segment_id'],
                start_sequence=seg['start_sequence'],
                max_questions=seg['max_questions']
            )
            task['task_id'] = task_id
            task['message'] = f"分段{seg['segment_id']+1}/{workers}: 第{seg['start_sequence']+1}-{seg['start_sequence']+seg['max_questions']}题"
            tasks[task_id] = task
            task_ids.append(task_id)

    # 启动所有分段任务
    for tid in task_ids:
        thread = threading.Thread(target=run_task, args=(tid,), daemon=True)
        thread.start()

    return jsonify({
        'ok': True,
        'task_ids': task_ids,
        'paper_id': paper_id,
        'workers': workers,
        'segments': segments
    })


@app.route('/api/merge-segments', methods=['POST'])
def merge_segments_api():
    """合并分段结果"""
    data, err = get_request_json()
    if err:
        return jsonify({'error': err}), 400

    raw_id = data.get('paper_id', '')
    paper_id, err = validate_paper_id(raw_id)
    if err:
        return jsonify({'error': err}), 400

    workers = data.get('workers', 4)

    # 检查所有分段是否完成
    with tasks_lock:
        for t in tasks.values():
            if t['paper_id'] == paper_id and t.get('segment_id', -1) >= 0 and t['running']:
                return jsonify({'error': '还有分段任务在运行中'}), 400

    result = merge_segments(paper_id, workers)
    has_ans = sum(1 for q in result if q.get('正确答案'))
    return jsonify({
        'ok': True,
        'total': len(result),
        'has_answer': has_ans
    })


if __name__ == '__main__':
    print("正在检查Chrome...")
    ok, msg, restarted = ensure_chrome_debug()
    print(msg)

    import webbrowser
    # Chrome就绪后再打开页面（如果Chrome重启了，新窗口里打开）
    if ok:
        time.sleep(1)  # 等Chrome完全就绪
        webbrowser.open('http://localhost:5678')
    else:
        print("Chrome未就绪，请手动打开 http://localhost:5678")

    app.run(host='0.0.0.0', port=5678, debug=False)
