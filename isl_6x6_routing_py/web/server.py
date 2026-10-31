# 웹 시뮬레이터 서버 - 화면(static 폴더)과 파이썬 시뮬레이터를 이어 줌. 설치할 것 없음 (파이썬 기본 기능만 사용)
#
# 실행 (isl_6x6_routing_py 폴더에서):
#   python web/server.py            -> 브라우저에서 http://localhost:8000
#   python web/server.py 8080       -> 포트 바꾸기
#
# 주소
#   /                    화면 (web/static)
#   GET  /api/settings   변수 설정 칸 목록 (기본값, 지금 값)
#   POST /api/settings   바꾼 값 저장 -> web/user_settings.json (설정 파일 원본은 안 바꿈)
#   POST /api/control    start, pause, step, stop, reset, speed
#   GET  /api/state      지금 상태, 에피소드 기록, 이벤트
#   GET  /api/stream     실시간 상태 (Server-Sent Events, 약 0.1초마다)
#   GET  /api/results    저장된 학습 기록(train_log.csv)과 평가 결과(summary.csv) 중 가장 최근 것
import csv
import glob
import json
import os
import queue
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))   # isl_6x6_routing_py

from web.live import LiveRunner
from web.schema import build_config, describe

STATIC = os.path.join(BASE, 'static')
SAVED = os.path.join(BASE, 'user_settings.json')
runner = LiveRunner()


def load_saved():
    try:
        with open(SAVED, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def latest_csv(pattern):
    files = sorted(glob.glob(pattern), key=os.path.getmtime)
    if not files:
        return None, []
    with open(files[-1], encoding='utf-8-sig') as f:
        return files[-1], list(csv.DictReader(f))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=STATIC, **k)

    def log_message(self, fmt, *args):   # 요청마다 찍히는 기록은 생략
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get('Content-Length', 0) or 0)
        return json.loads(self.rfile.read(n) or b'{}')

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/api/settings':
            saved = load_saved()
            return self._json(dict(fields=describe(saved), saved=saved))
        if path == '/api/state':
            return self._json(runner.info())
        if path == '/api/results':
            home = os.path.expanduser('~')
            tf, train = latest_csv(os.path.join(home, 'rl_models', 'routeC_*', 'train_log.csv'))
            ef, ev = latest_csv(os.path.join(home, 'isl_saved_runs', 'eval_*', 'summary.csv'))
            return self._json(dict(trainFile=tf, train=train, evalFile=ef, eval=ev))
        if path == '/api/stream':
            return self._stream()
        return super().do_GET()

    def do_POST(self):
        path = self.path.split('?')[0]
        if path == '/api/settings':
            overrides = self._body().get('overrides', {})
            try:
                build_config(overrides)        # 잘못된 값이면 저장하지 않음
            except Exception as e:
                return self._json(dict(ok=False, error=f'{type(e).__name__}: {e}'), 400)
            with open(SAVED, 'w', encoding='utf-8') as f:
                json.dump(overrides, f, ensure_ascii=False, indent=1)
            return self._json(dict(ok=True))
        if path == '/api/control':
            opts = self._body()
            opts.setdefault('overrides', load_saved())
            return self._json(dict(result=runner.control(opts.get('action', ''), opts)))
        self.send_error(404)

    def _stream(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        q = runner.subscribe()
        try:
            self.wfile.write(f'data: {json.dumps(dict(type="hello", **runner.info()), ensure_ascii=False)}\n\n'.encode('utf-8'))
            self.wfile.flush()
            while True:
                try:
                    msg = q.get(timeout=15)
                    data = json.dumps(msg, ensure_ascii=False)
                except queue.Empty:
                    data = '{"type":"ping"}'
                self.wfile.write(f'data: {data}\n\n'.encode('utf-8'))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            runner.unsubscribe(q)


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    srv = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    srv.daemon_threads = True
    print(f'ISL RL Simulator: http://localhost:{port}   (끄려면 Ctrl+C)')
    srv.serve_forever()
