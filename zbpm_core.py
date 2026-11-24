# -*- coding: utf-8 -*-
r"""
ZBrush 插件管理器 —— 核心逻辑（与界面无关，仅依赖 Python 标准库）
- 从目录 / ZBrush.exe / 快捷方式(.lnk) 定位 ZBrush 根目录，读取版本
- 扫描 ZStartup\ZPlugs64、ZPlugs 和公共文档 ZBrushDataXXXX\ZStartup\ZPlugs64
- 启用 / 禁用（移动到 _PluginManager_Disabled）、安装（.zsc/.py/.zip/文件夹）、删除（回收站）
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
import zipfile
from ctypes import wintypes

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ZBrushPluginManager")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DISABLED_DIRNAME = "_PluginManager_Disabled"   # 放在 ZStartup 的同级目录，ZBrush 不会扫描
PLUGIN_EXTS = (".zsc", ".py")
COMPANION_EXTS = (".zsc", ".txt", ".py", ".zscm")
CREATE_NO_WINDOW = 0x08000000

# ZBrush 自带插件（去掉版本后缀、小写后比较）
OFFICIAL = {
    "3dprinthub", "ambientocclusion", "axisrotate", "bevelproplugin", "blendshapesexport",
    "curveshelper", "decimationmaster", "exportscaleutility", "fbx-exportimport", "fragclean",
    "help", "imageplane", "intersectionmasker", "launchhomepage", "localquadretopo",
    "multimapexporter", "paintstop", "polygroupit", "projection_master", "projectionmaster",
    "scalemaster", "snapangle", "subtoolanalysis", "subtoolmaster", "text3d", "transposemaster",
    "usd_format", "uvmaster", "zapplink", "zbenchmark", "zbridge", "zbrushtophotoshop",
    "zcameras", "zcolor", "zmeshmend", "zhomepage", "goz", "ztree", "maskbyfeature",
    "spotlightprojection", "zplugin_help", "nanomesh", "zmodeler",
}


# ---------------------------------------------------------------- 工具函数
def norm_stem(name):
    s = os.path.splitext(name)[0].lower()
    s = re.sub(r"[_\- ]?(v)?20\d\d(\.\d+)*$", "", s)
    s = re.sub(r"[_\- ]?v?\d+(\.\d+)+$", "", s)
    return s


def alnum(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def human_size(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def dir_size(path):
    total = 0
    for dp, _, fs in os.walk(path):
        for f in fs:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return total


def resolve_lnk(paths):
    """批量解析 .lnk 快捷方式，返回 {lnk: target}"""
    if not paths:
        return {}
    env = dict(os.environ)
    env["ZBPM_LNKS"] = "\n".join(paths)
    cmd = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8;$s=New-Object -ComObject WScript.Shell;"
           "$env:ZBPM_LNKS -split \"`n\" | % { try { $s.CreateShortcut($_).TargetPath } catch { '' } }")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                             capture_output=True, env=env, creationflags=CREATE_NO_WINDOW,
                             timeout=30)
        lines = out.stdout.decode("utf-8", "replace").lstrip("﻿").splitlines()
    except Exception:
        return {}
    res = {}
    for i, p in enumerate(paths):
        res[p] = lines[i].strip() if i < len(lines) else ""
    return res


def exe_version(path):
    try:
        ver = ctypes.windll.version
        size = ver.GetFileVersionInfoSizeW(path, None)
        if not size:
            return None
        buf = ctypes.create_string_buffer(size)
        if not ver.GetFileVersionInfoW(path, 0, size, buf):
            return None
        p = ctypes.c_void_p()
        n = wintypes.UINT()
        if not ver.VerQueryValueW(buf, "\\", ctypes.byref(p), ctypes.byref(n)):
            return None
        info = ctypes.cast(p, ctypes.POINTER(wintypes.DWORD * 13)).contents
        ms, ls = info[2], info[3]
        return (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)
    except Exception:
        return None


def is_zbrush_root(d):
    return os.path.isfile(os.path.join(d, "ZBrush.exe")) and os.path.isdir(os.path.join(d, "ZStartup"))


def find_roots(path):
    """从任意输入（目录 / exe / lnk / 子目录）找出 ZBrush 根目录列表"""
    path = path.strip().strip('"')
    if not path:
        return []
    if path.lower().endswith(".lnk"):
        path = resolve_lnk([path]).get(path, "") or path
    if os.path.isfile(path):
        path = os.path.dirname(path)
    if not os.path.isdir(path):
        return []
    # 向上找
    cur = os.path.abspath(path)
    for _ in range(5):
        if is_zbrush_root(cur):
            return [cur]
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    # 向下找（最多 2 层）
    found = []
    try:
        for a in os.scandir(path):
            if not a.is_dir():
                continue
            if is_zbrush_root(a.path):
                found.append(a.path)
                continue
            try:
                for b in os.scandir(a.path):
                    if b.is_dir() and is_zbrush_root(b.path):
                        found.append(b.path)
            except OSError:
                pass
    except OSError:
        pass
    return found


def version_of(root):
    v = exe_version(os.path.join(root, "ZBrush.exe"))
    year = None
    label = ""
    if v and v[0] >= 2018:
        year = v[0]
        label = ".".join(str(x) for x in v[:3])
    else:
        m = re.search(r"(20\d\d)(\.\d+)*", os.path.basename(root))
        if m:
            year = int(m.group(1))
            label = m.group(0)
        elif v:
            label = ".".join(str(x) for x in v[:3])
    if year is None:
        for f in os.listdir(os.path.join(root, "ZStartup")) if os.path.isdir(os.path.join(root, "ZStartup")) else []:
            m = re.search(r"(20\d\d)", f)
            if m:
                year = int(m.group(1))
                break
    return year, label or "未知版本"


def auto_discover():
    """从注册表、开始菜单、桌面快捷方式自动发现 ZBrush"""
    cands = []
    try:
        import winreg
        for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                          (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")):
            try:
                k = winreg.OpenKey(hive, key)
            except OSError:
                continue
            for i in range(winreg.QueryInfoKey(k)[0]):
                try:
                    sk = winreg.OpenKey(k, winreg.EnumKey(k, i))
                    name = winreg.QueryValueEx(sk, "DisplayName")[0]
                    if "zbrush" in str(name).lower():
                        try:
                            cands.append(winreg.QueryValueEx(sk, "InstallLocation")[0])
                        except OSError:
                            pass
                except OSError:
                    pass
    except Exception:
        pass
    lnks = []
    for base in (os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
                 os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop"),
                 os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
                 os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), r"Microsoft\Windows\Start Menu\Programs")):
        if not os.path.isdir(base):
            continue
        for dp, _, fs in os.walk(base):
            for f in fs:
                if f.lower().endswith(".lnk") and "zbrush" in f.lower():
                    lnks.append(os.path.join(dp, f))
    cands += [t for t in resolve_lnk(lnks).values() if t]
    for pf in (os.environ.get("ProgramFiles", r"C:\Program Files"),):
        for sub in ("Maxon", "Pixologic", ""):
            d = os.path.join(pf, sub) if sub else pf
            if os.path.isdir(d):
                try:
                    for e in os.scandir(d):
                        if e.is_dir() and "zbrush" in e.name.lower():
                            cands.append(e.path)
                except OSError:
                    pass
    roots = []
    for c in cands:
        for r in find_roots(c):
            r = os.path.normpath(r)
            if r.lower() not in [x.lower() for x in roots]:
                roots.append(r)
    return roots


def recycle(path):
    """移动到回收站"""
    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT),
                    ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
                    ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]
    op = SHFILEOPSTRUCTW()
    op.wFunc = 3  # FO_DELETE
    op.pFrom = os.path.abspath(path) + "\0"
    op.fFlags = 0x40 | 0x10 | 0x400 | 0x4  # ALLOWUNDO | NOCONFIRMATION | NOERRORUI | SILENT
    r = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if r != 0:
        raise OSError(f"移入回收站失败 (代码 {r}): {path}")


def zbrush_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ZBrush.exe", "/NH"],
                             capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=10)
        return b"zbrush.exe" in out.stdout.lower()
    except Exception:
        return False


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ---------------------------------------------------------------- 数据模型
class Location:
    def __init__(self, label, base, sub):
        self.label = label             # 显示名
        self.base = base               # ZStartup 的父目录
        self.sub = sub                 # ZPlugs64 / ZPlugs
        self.enabled_dir = os.path.join(base, "ZStartup", sub)
        self.disabled_dir = os.path.join(base, DISABLED_DIRNAME, sub)


class Plugin:
    def __init__(self, loc, stem, files, enabled):
        self.loc = loc
        self.stem = stem
        self.files = files             # 插件主文件 + 同名伴随文件（文件名）
        self.enabled = enabled
        self.data_dir = None
        main = [f for f in files if f.lower().endswith(PLUGIN_EXTS)]
        self.main = main[0] if main else files[0]
        self.kind = "Python" if self.main.lower().endswith(".py") else "ZScript"
        self.official = norm_stem(self.main) in OFFICIAL

    @property
    def folder(self):
        return self.loc.enabled_dir if self.enabled else self.loc.disabled_dir

    @property
    def key(self):
        return (self.loc.enabled_dir.lower(), self.stem.lower())

    def size(self):
        s = 0
        for f in self.files:
            try:
                s += os.path.getsize(os.path.join(self.folder, f))
            except OSError:
                pass
        return s

    def mtime(self):
        try:
            return os.path.getmtime(os.path.join(self.folder, self.main))
        except OSError:
            return 0


def group_files(folder):
    """把目录中插件文件按文件名分组"""
    groups = {}
    if not os.path.isdir(folder):
        return groups, []
    dirs = []
    for e in os.scandir(folder):
        if e.is_dir():
            dirs.append(e.name)
        elif e.name.lower().endswith(COMPANION_EXTS):
            stem = os.path.splitext(e.name)[0]
            groups.setdefault(stem.lower(), [stem, []])[1].append(e.name)
    # 只保留含 .zsc/.py 的组
    result = {k: v for k, v in groups.items() if any(f.lower().endswith(PLUGIN_EXTS) for f in v[1])}
    return result, dirs


def match_data_dir(plugin_name, dirs):
    p = alnum(norm_stem(plugin_name))
    best, best_len = None, 0
    for d in dirs:
        dn = alnum(re.sub(r"data$", "", d, flags=re.I)) or alnum(d)
        if len(dn) < 3:
            continue
        if dn == p or alnum(d) == p:
            return d
        if (p.startswith(dn) or dn.startswith(p)) and min(len(dn), len(p)) >= 4 and len(dn) > best_len:
            best, best_len = d, len(dn)
    return best


class Install:
    def __init__(self, root):
        self.root = os.path.normpath(root)
        self.year, self.version = version_of(self.root)
        self.locations = []
        for sub in ("ZPlugs64", "ZPlugs"):
            if os.path.isdir(os.path.join(self.root, "ZStartup", sub)) or sub == "ZPlugs64":
                self.locations.append(Location("安装目录" + ("" if sub == "ZPlugs64" else " (32位 ZPlugs)"),
                                               self.root, sub))
        self.user_base = None
        if self.year:
            ub = os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Documents", f"ZBrushData{self.year}")
            if os.path.isdir(ub):
                self.user_base = ub
                self.locations.append(Location("公共文档", ub, "ZPlugs64"))

    @property
    def title(self):
        return f"ZBrush {self.version}  —  {self.root}"

    def scan(self):
        plugins = []
        for loc in self.locations:
            en, en_dirs = group_files(loc.enabled_dir)
            dis, _ = group_files(loc.disabled_dir)
            for k, (stem, files) in en.items():
                plugins.append(Plugin(loc, stem, sorted(files), True))
            for k, (stem, files) in dis.items():
                if k in en:   # 已同时存在于启用目录，忽略禁用副本
                    continue
                plugins.append(Plugin(loc, stem, sorted(files), False))
            for p in plugins:
                if p.loc is loc:
                    p.data_dir = match_data_dir(p.main, en_dirs)
        return plugins


# ---------------------------------------------------------------- 文件操作
def move_plugin(p, enable):
    src_dir = p.folder
    dst_dir = p.loc.enabled_dir if enable else p.loc.disabled_dir
    os.makedirs(dst_dir, exist_ok=True)
    for f in p.files:
        src = os.path.join(src_dir, f)
        dst = os.path.join(dst_dir, f)
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(src, dst)
    p.enabled = enable


def delete_plugin(p, with_data):
    for f in p.files:
        recycle(os.path.join(p.folder, f))
    if with_data and p.data_dir:
        d = os.path.join(p.loc.enabled_dir, p.data_dir)
        if os.path.isdir(d):
            recycle(d)


def collect_install_items(path, tmpdir):
    """返回 [(源路径, 目标相对名)]。支持 .zsc/.py 文件、文件夹、.zip"""
    items = []
    if os.path.isfile(path) and path.lower().endswith(".zip"):
        ex = os.path.join(tmpdir, os.path.splitext(os.path.basename(path))[0])
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                # 修正中文文件名编码
                name = info.filename
                if not info.flag_bits & 0x800:
                    try:
                        name = name.encode("cp437").decode("gbk")
                    except Exception:
                        pass
                target = os.path.normpath(os.path.join(ex, name))
                if not target.startswith(os.path.normpath(ex)):
                    continue
                if name.endswith("/"):
                    os.makedirs(target, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with z.open(info) as s, open(target, "wb") as d:
                        shutil.copyfileobj(s, d)
        path = ex
    if os.path.isfile(path):
        stem = os.path.splitext(os.path.basename(path))[0].lower()
        folder = os.path.dirname(path)
        for e in os.scandir(folder):
            if e.is_file() and os.path.splitext(e.name)[0].lower() == stem and e.name.lower().endswith(COMPANION_EXTS):
                items.append((e.path, e.name))
        return items
    if os.path.isdir(path):
        # 优先找名为 ZPlugs64 的目录
        zp = None
        for dp, dns, fns in os.walk(path):
            if os.path.basename(dp).lower() == "zplugs64":
                zp = dp
                break
        if zp is None:
            # 找包含插件文件的最浅目录
            for dp, dns, fns in os.walk(path):
                if any(f.lower().endswith(PLUGIN_EXTS) for f in fns):
                    zp = dp
                    break
        if zp:
            for e in os.scandir(zp):
                items.append((e.path, e.name))
    return items


