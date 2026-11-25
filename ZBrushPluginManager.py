# -*- coding: utf-8 -*-
"""
ZBrush 插件管理器 v2 —— pywebview (Edge WebView2) 界面
后端逻辑见 zbpm_core.py，界面见 ui/index.html
"""
import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from ctypes import wintypes

# 必须在创建任何窗口之前设置：按显示器感知 DPI，保证坐标都是物理像素
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# 独立的任务栏身份：任务栏不再显示成 Python，并使用本程序图标
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ZBrushPluginManager.App")
except Exception:
    pass

import webview
from webview.dom import DOMEventHandler

import zbpm_core as core

APP_VER = "2.0"
TITLE = f"ZBrush 插件管理器"


def res_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


# ================================================================ 显示器 / 窗口位置
user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT), ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD), ("szDevice", wintypes.WCHAR * 32)]


class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [("length", wintypes.UINT), ("flags", wintypes.UINT), ("showCmd", wintypes.UINT),
                ("ptMinPosition", wintypes.POINT), ("ptMaxPosition", wintypes.POINT),
                ("rcNormalPosition", RECT)]


user32.MonitorFromPoint.restype = ctypes.c_void_p
user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
user32.MonitorFromWindow.restype = ctypes.c_void_p
user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(RECT), wintypes.LPARAM)


def _mon_info(hmon):
    mi = MONITORINFOEXW()
    mi.cbSize = ctypes.sizeof(MONITORINFOEXW)
    user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
    dpi = 96
    try:
        x, y = wintypes.UINT(), wintypes.UINT()
        ctypes.windll.shcore.GetDpiForMonitor(ctypes.c_void_p(hmon), 0, ctypes.byref(x), ctypes.byref(y))
        dpi = x.value or 96
    except Exception:
        pass
    m, w = mi.rcMonitor, mi.rcWork
    return {"device": mi.szDevice, "mon": [m.l, m.t, m.r, m.b], "work": [w.l, w.t, w.r, w.b],
            "primary": bool(mi.dwFlags & 1), "dpi": dpi}


def monitors():
    res = []

    def cb(h, hdc, rc, lp):
        res.append(_mon_info(h))
        return True
    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    return res


def monitor_under_cursor():
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return _mon_info(user32.MonitorFromPoint(pt, 2))


def default_geometry(mon):
    l, t, r, b = mon["work"]
    W, H = r - l, b - t
    s = mon["dpi"] / 96
    # 约占工作区 3/4，但保证至少能放下完整布局（1280x800 逻辑像素），且不超过 95%
    w = int(min(max(W * 0.8, 1280 * s), W * 0.95))
    h = int(min(max(H * 0.84, 800 * s), H * 0.95))
    return [l + (W - w) // 2, t + (H - h) // 2, w, h]


def restore_geometry(saved):
    """返回 (x, y, w, h, maximized)。保存的显示器仍在且分辨率相同则还原原位置，否则在当前显示器上按分辨率计算。"""
    mons = monitors()
    if saved:
        for m in mons:
            if m["device"] == saved.get("device") and m["mon"] == saved.get("mon"):
                x, y, w, h = saved["rect"]
                l, t, r, b = m["work"]
                # 窗口至少要有一大块在工作区里，并且不超过工作区
                w, h = min(w, r - l), min(h, b - t)
                x = max(l, min(x, r - w))
                y = max(t, min(y, b - h))
                return x, y, w, h, bool(saved.get("maximized"))
    target = None
    if saved:
        target = next((m for m in mons if m["device"] == saved.get("device")), None)
    target = target or monitor_under_cursor()
    return (*default_geometry(target), False)


# ================================================================ 后端 API（JS 调用）
def stem_year(stem):
    m = re.search(r"(?:^|[_\- ])v?(20\d\d)(?:\.\d+)*$", stem)
    return int(m.group(1)) if m else None


def read_notes(p):
    """读取伴随 .txt 或 .py 开头的说明"""
    for f in p.files:
        fp = os.path.join(p.folder, f)
        try:
            if f.lower().endswith(".txt"):
                with open(fp, "rb") as fh:
                    raw = fh.read(4000)
                for enc in ("utf-8", "gbk", "latin-1"):
                    try:
                        return raw.decode(enc).strip()
                    except UnicodeDecodeError:
                        continue
            if f.lower().endswith(".py"):
                with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                    head = fh.read(4000)
                m = re.search(r'^\s*(?:#.*\n)*\s*("""|\'\'\')(.*?)\1', head, re.S)
                if m:
                    return m.group(2).strip()
                lines = [l[1:].strip() for l in head.splitlines()[:15] if l.startswith("#")]
                if lines:
                    return "\n".join(lines)
        except OSError:
            pass
    return ""


class Api:
    def __init__(self):
        self._window = None
        self._cfg_lock = threading.Lock()
        self._cfg = self._load_cfg()
        self._installs = {}
        for r in self._cfg.get("installs", []):
            if core.is_zbrush_root(r):
                self._add(r)
        self._current = self._cfg.get("last") if self._cfg.get("last") in self._installs else next(iter(self._installs), None)
        self._plugins = {}
        self._pending = {}
        self._size_cache = {}

    # ---------- 配置
    def _load_cfg(self):
        try:
            with open(core.CONFIG_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_cfg(self):
        with self._cfg_lock:
            self._cfg["installs"] = list(self._installs.keys())
            self._cfg["last"] = self._current
            try:
                os.makedirs(core.CONFIG_DIR, exist_ok=True)
                with open(core.CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._cfg, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def _add(self, root):
        root = os.path.normpath(root)
        for k in self._installs:
            if k.lower() == root.lower():
                return k
        self._installs[root] = core.Install(root)
        return root

    # ---------- 安装列表
    def _install_summary(self, inst, quick=True):
        en = dis = third = 0
        for loc in inst.locations:
            g, _ = core.group_files(loc.enabled_dir)
            en += len(g)
            third += sum(1 for k, (s, fs) in g.items()
                         if core.norm_stem([f for f in fs if f.lower().endswith(core.PLUGIN_EXTS)][0]) not in core.OFFICIAL)
            d, _ = core.group_files(loc.disabled_dir)
            dis += len([k for k in d if k not in g])
        return {"root": inst.root, "version": inst.version, "year": inst.year,
                "name": os.path.basename(inst.root), "enabled": en, "disabled": dis, "third": third,
                "exists": core.is_zbrush_root(inst.root)}

    def get_state(self):
        items = sorted(self._installs.values(), key=lambda i: (-(i.year or 0), i.root.lower()))
        return {"installs": [self._install_summary(i) for i in items], "current": self._current,
                "admin": core.is_admin(), "version": APP_VER, "config": core.CONFIG_FILE,
                "ui": self._cfg.get("ui", {})}

    def save_ui(self, ui):
        self._cfg["ui"] = ui
        self._save_cfg()
        return True

    def select_install(self, root):
        if root in self._installs:
            self._current = root
            self._save_cfg()
        return self.scan()

    def remove_install(self, root):
        self._installs.pop(root, None)
        if self._current == root:
            self._current = next(iter(self._installs), None)
        self._save_cfg()
        return self.get_state()

    def add_path(self, path):
        roots = core.find_roots(path or "")
        added = [self._add(r) for r in roots]
        if added:
            self._current = added[0]
            self._save_cfg()
        return {"added": added}

    def browse_install(self):
        r = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if not r:
            return {"added": [], "cancel": True}
        return self.add_path(r[0] if isinstance(r, (list, tuple)) else r)

    def discover(self):
        roots = core.auto_discover()
        before = set(k.lower() for k in self._installs)
        added = [self._add(r) for r in roots]
        new = [a for a in added if a.lower() not in before]
        if self._current is None and added:
            self._current = added[0]
        self._save_cfg()
        return {"found": len(roots), "new": new}

    # ---------- 插件扫描
    def _dsize(self, path):
        try:
            mt = os.path.getmtime(path)
        except OSError:
            return 0, 0
        c = self._size_cache.get(path)
        if c and c[0] == mt:
            return c[1], c[2]
        total = n = 0
        for dp, _, fs in os.walk(path):
            for f in fs:
                n += 1
                try:
                    total += os.path.getsize(os.path.join(dp, f))
                except OSError:
                    pass
        self._size_cache[path] = (mt, total, n)
        return total, n

    def _pid(self, p):
        return f"{p.loc.enabled_dir}|{p.stem}".lower()

    def scan(self):
        if not self._current or self._current not in self._installs:
            return {"install": None}
        inst = self._installs[self._current]
        plist = inst.scan()
        self._plugins = {}
        out = []
        for p in plist:
            pid = self._pid(p)
            self._plugins[pid] = p
            data_size = data_files = 0
            if p.data_dir:
                data_size, data_files = self._dsize(os.path.join(p.loc.enabled_dir, p.data_dir))
            y = stem_year(p.stem)
            out.append({
                "id": pid, "name": p.stem, "display": re.sub(r"[_\- ]?v?20\d\d(\.\d+)*$", "", p.stem) or p.stem,
                "enabled": p.enabled, "official": p.official, "kind": p.kind, "loc": p.loc.label,
                "files": p.files, "main": p.main, "data": p.data_dir or "", "size": p.size(),
                "data_size": data_size, "data_files": data_files, "mtime": p.mtime(),
                "year": y, "mismatch": bool(y and inst.year and y != inst.year),
            })
        locs = []
        for l in inst.locations:
            locs.append({"label": l.label, "path": l.enabled_dir, "exists": os.path.isdir(l.enabled_dir),
                         "disabled_path": l.disabled_dir,
                         "count": sum(1 for p in plist if p.loc is l)})
        return {"install": {"root": inst.root, "version": inst.version, "year": inst.year,
                            "exe": os.path.join(inst.root, "ZBrush.exe"),
                            "user_base": inst.user_base},
                "locations": locs, "plugins": out}

    def plugin_detail(self, pid):
        p = self._plugins.get(pid)
        if not p:
            return None
        files = []
        for f in p.files:
            fp = os.path.join(p.folder, f)
            try:
                st = os.stat(fp)
                files.append({"name": f, "path": fp, "size": st.st_size, "mtime": st.st_mtime})
            except OSError:
                files.append({"name": f, "path": fp, "size": 0, "mtime": 0})
        data = None
        if p.data_dir:
            dp = os.path.join(p.loc.enabled_dir, p.data_dir)
            size, n = self._dsize(dp)
            try:
                entries = sorted(os.listdir(dp), key=str.lower)
            except OSError:
                entries = []
            data = {"name": p.data_dir, "path": dp, "size": size, "files": n, "entries": entries[:40],
                    "more": max(0, len(entries) - 40)}
        return {"id": pid, "folder": p.folder, "files": files, "data": data, "notes": read_notes(p)[:3000]}

    # ---------- 操作
    def _err(self, ex):
        need_admin = isinstance(ex, PermissionError) or getattr(ex, "winerror", None) in (5, 32)
        return {"msg": str(ex), "need_admin": need_admin and not core.is_admin(),
                "running": core.zbrush_running() if need_admin else False}

    def set_enabled(self, ids, enable):
        done, errors = 0, []
        for pid in ids:
            p = self._plugins.get(pid)
            if not p or p.enabled == enable:
                continue
            try:
                core.move_plugin(p, enable)
                done += 1
            except Exception as ex:
                errors.append(self._err(ex))
        return {"done": done, "errors": errors}

    def delete(self, ids, with_data):
        done, errors = 0, []
        for pid in ids:
            p = self._plugins.get(pid)
            if not p:
                continue
            try:
                core.delete_plugin(p, with_data)
                done += 1
            except Exception as ex:
                errors.append(self._err(ex))
        return {"done": done, "errors": errors}

    def pick_plugin_files(self):
        r = self._window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=True,
                                           file_types=("ZBrush 插件 / plugins (*.zsc;*.py;*.zip)", "所有文件 / All files (*.*)"))
        return list(r) if r else []

    def preview_install(self, paths):
        if not self._current:
            return {"error": "请先添加并选择一个 ZBrush"}
        inst = self._installs[self._current]
        target = inst.locations[0].enabled_dir
        tmp = tempfile.mkdtemp(prefix="zbpm_")
        items, bad = [], []
        for p in paths:
            try:
                items += core.collect_install_items(p, tmp)
            except zipfile.BadZipFile:
                bad.append(os.path.basename(p))
            except Exception as ex:
                bad.append(f"{os.path.basename(p)}：{ex}")
        if not any(n.lower().endswith(core.PLUGIN_EXTS) for _, n in items):
            shutil.rmtree(tmp, ignore_errors=True)
            return {"error": "没有在这些文件里找到插件（.zsc / .py）", "bad": bad}
        token = uuid.uuid4().hex
        self._pending[token] = (tmp, items, target, inst.locations[0].disabled_dir)
        return {"token": token, "target": target, "bad": bad,
                "items": [{"name": n, "dir": os.path.isdir(s), "exists": os.path.exists(os.path.join(target, n)),
                           "plugin": n.lower().endswith(core.PLUGIN_EXTS)} for s, n in items]}

    def do_install(self, token):
        tmp, items, target, disabled = self._pending.pop(token, (None, None, None, None))
        if not items:
            return {"done": 0, "errors": [{"msg": "安装任务已失效，请重新拖入"}]}
        try:
            os.makedirs(target, exist_ok=True)
            for src, name in items:
                dst = os.path.join(target, name)
                if os.path.exists(dst):
                    core.recycle(dst)
                dis = os.path.join(disabled, name)
                if os.path.isfile(dis):
                    os.remove(dis)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            return {"done": len(items), "errors": []}
        except Exception as ex:
            return {"done": 0, "errors": [self._err(ex)]}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def cancel_install(self, token):
        tmp = self._pending.pop(token, (None,))[0]
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
        return True

    def handle_drop(self, paths):
        """拖入：ZBrush 目录 / exe / lnk → 添加；插件文件 → 安装预览"""
        added, plugins, unknown = [], [], []
        for f in paths:
            low = f.lower()
            if low.endswith((".zsc", ".py", ".zip")):
                plugins.append(f)
                continue
            roots = core.find_roots(f)
            if roots:
                added += [self._add(r) for r in roots]
            elif os.path.isdir(f):
                plugins.append(f)
            else:
                unknown.append(os.path.basename(f))
        if added:
            self._current = added[0]
            self._save_cfg()
        preview = self.preview_install(plugins) if plugins and self._current else None
        return {"added": added, "preview": preview, "unknown": unknown,
                "need_install": bool(plugins and not self._current)}

    def open_path(self, path, select=False):
        if select and os.path.exists(path):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        elif os.path.isdir(path):
            os.startfile(path)
        else:
            return False
        return True

    def launch_zbrush(self):
        if self._current:
            os.startfile(os.path.join(self._current, "ZBrush.exe"))
            return True
        return False

    def zbrush_running(self):
        return core.zbrush_running()

    def relaunch_admin(self):
        exe = sys.executable
        if getattr(sys, "frozen", False):
            args = ""
        else:
            if exe.lower().endswith("python.exe") and os.path.exists(exe[:-10] + "pythonw.exe"):
                exe = exe[:-10] + "pythonw.exe"
            args = f'"{os.path.abspath(__file__)}"'
        r = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, args, None, 1)
        if r > 32:
            threading.Timer(0.2, lambda: self._window.destroy()).start()
            return True
        return False

    def copy_text(self, text):
        try:
            subprocess.run(["clip"], input=text.encode("utf-16-le"), creationflags=core.CREATE_NO_WINDOW)
            return True
        except Exception:
            return False


# ================================================================ 启动
def main():
    api = Api()
    x, y, w, h, maxed = restore_geometry(api._cfg.get("window"))
    window = webview.create_window(
        TITLE, url=res_path(os.path.join("ui", "index.html")), js_api=api,
        x=x, y=y, width=w, height=h, min_size=(1000, 640),
        background_color="#111318", text_select=False)
    api._window = window
    state = {"hwnd": None}

    def hwnd_of():
        """通过进程 ID + 标题找到本程序的顶层窗口（不访问 WinForms 对象，避免跨线程卡死）"""
        if state["hwnd"] and user32.IsWindow(state["hwnd"]):
            return state["hwnd"]
        pid, found = os.getpid(), []

        def cb(h, lp):
            p = wintypes.DWORD()
            user32.GetWindowThreadProcessId(h, ctypes.byref(p))
            if p.value == pid:
                buf = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(h, buf, 256)
                if buf.value == TITLE:
                    found.append(h)
            return True
        user32.EnumWindows(ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(cb), 0)
        if found:
            state["hwnd"] = found[0]
        return state["hwnd"]

    def apply_geometry():
        h_ = hwnd_of()
        if h_:
            user32.SetWindowPos(h_, None, x, y, w, h, 0x0004 | 0x0010)  # NOZORDER | NOACTIVATE


    def set_icon(h_):
        ico = res_path("icon.ico")
        if not os.path.exists(ico):
            return
        user32.LoadImageW.restype = ctypes.c_void_p
        user32.LoadImageW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, ctypes.c_void_p]
        for kind, metric in ((1, 11), (0, 49)):   # ICON_BIG/SM_CXICON, ICON_SMALL/SM_CXSMICON
            sz = user32.GetSystemMetrics(metric) * (2 if kind == 1 else 1)
            hicon = user32.LoadImageW(None, ico, 1, sz, sz, 0x10)
            if hicon:
                user32.SendMessageW(h_, 0x80, kind, hicon)

    def on_shown():
        h_ = hwnd_of()
        if h_:
            set_icon(h_)
        # 被父进程以“最小化/隐藏”方式启动时，强制恢复为正常窗口
        if h_ and user32.IsIconic(h_):
            user32.ShowWindow(h_, 9)   # SW_RESTORE
        apply_geometry()
        if h_:
            if maxed:
                user32.ShowWindow(h_, 3)
            user32.SetForegroundWindow(h_)


    def on_closing():
        h_ = hwnd_of()
        if not h_:
            return
        wp = WINDOWPLACEMENT()
        wp.length = ctypes.sizeof(WINDOWPLACEMENT)
        user32.GetWindowPlacement(h_, ctypes.byref(wp))
        zoomed = bool(user32.IsZoomed(h_))
        if zoomed:
            rc = wp.rcNormalPosition
            mon = _mon_info(user32.MonitorFromWindow(h_, 2))
            # rcNormalPosition 是工作区坐标，换算成屏幕坐标
            ox, oy = mon["work"][0] - mon["mon"][0], mon["work"][1] - mon["mon"][1]
            rect = [rc.l + ox, rc.t + oy, rc.r - rc.l, rc.b - rc.t]
        else:
            r = RECT()
            user32.GetWindowRect(h_, ctypes.byref(r))
            rect = [r.l, r.t, r.r - r.l, r.b - r.t]
        if user32.IsIconic(h_):
            return   # 最小化时不覆盖上次的位置
        mon = _mon_info(user32.MonitorFromWindow(h_, 2))
        api._cfg["window"] = {"device": mon["device"], "mon": mon["mon"], "rect": rect, "maximized": zoomed}
        api._save_cfg()

    def on_loaded():
        def on_drop(e):
            files = (e.get("dataTransfer") or {}).get("files") or []
            paths = [f.get("pywebviewFullPath") for f in files if f.get("pywebviewFullPath")]
            if paths:
                window.evaluate_js(f"window.onNativeDrop && window.onNativeDrop({json.dumps(paths)})")
        try:
            doc = window.dom.document
            doc.events.dragover += DOMEventHandler(lambda e: None, True, True)
            doc.events.drop += DOMEventHandler(on_drop, True, True)
        except Exception as ex:
            print("drop init failed:", ex)

    window.events.before_show += apply_geometry
    window.events.shown += on_shown
    window.events.closing += on_closing
    window.events.loaded += on_loaded

    startup = [a for a in sys.argv[1:] if not a.startswith("-")]
    if startup:
        def first():
            window.events.loaded.wait(15)
            time.sleep(0.6)
            window.evaluate_js(f"window.onNativeDrop && window.onNativeDrop({json.dumps(startup)})")
        threading.Thread(target=first, daemon=True).start()

    webview.start(debug="--debug" in sys.argv, private_mode=False,
                  storage_path=os.path.join(core.CONFIG_DIR, "webview"))


if __name__ == "__main__":
    main()
