/* English UI for ZBrush Plugin Manager.
 *
 * The interface is written in Chinese. When the language is English, every
 * text node and title / placeholder attribute that the page renders is looked
 * up here and replaced: first by exact text (EXACT), then by a pattern for
 * text that contains numbers or paths (RULES). Text with no entry stays as it
 * is, so a missing translation shows Chinese instead of breaking anything.
 * Switching back to Chinese reloads the page.
 */
const I18N = (() => {
  const EXACT = {
    // window / sidebar / drop overlay
    'ZBrush 插件管理器': 'ZBrush Plugin Manager',
    'ZBrush 版本': 'ZBrush versions',
    '把': 'Drop',
    'ZBrush 文件夹': 'a ZBrush folder',
    '、': ', ',
    '或': 'or a ',
    '桌面快捷方式': 'desktop shortcut',
    '拖到窗口任意位置': ' anywhere in the window',
    '浏览添加': 'Browse…',
    '自动搜索': 'Auto search',
    '切换深色 / 浅色': 'Dark / light theme',
    '快捷键': 'Keyboard shortcuts',
    '切换语言 / Language': 'Language / 切换语言',
    '松开鼠标': 'Release to drop',
    '程序会自动识别你拖进来的是 ZBrush 还是插件': 'ZBrush installs and plugins are recognized automatically',
    '添加 ZBrush': 'Add ZBrush',
    '文件夹 · ZBrush.exe · 快捷方式': 'Folder · ZBrush.exe · shortcut',
    '安装插件': 'Install plugins',
    '.zsc · .py · .zip · 插件文件夹': '.zsc · .py · .zip · plugin folder',
    '管理员': 'Administrator',
    '普通权限': 'Standard user',
    '还没有添加 ZBrush。': 'No ZBrush added yet.',
    '拖入 ZBrush 文件夹或快捷方式，或点击下方「自动搜索」。': 'Drop a ZBrush folder or shortcut here, or click "Auto search" below.',
    '从列表移除（不会删除任何文件）': 'Remove from list (no files are deleted)',
    '目录不存在': 'Folder missing',
    '搜索中…': 'Searching…',
    // empty state
    '先告诉我 ZBrush 在哪里': 'First, show me where ZBrush is',
    'ZBrush 安装文件夹': 'your ZBrush install folder',
    '或者': 'or',
    '桌面上的 ZBrush 快捷方式': ' a ZBrush desktop shortcut',
    '直接拖进这个窗口，程序会自动找到它的插件库。任何版本都可以，也可以一次拖入一个包含多个 ZBrush 的上级文件夹。':
      ' into this window and its plugin library is found automatically. Any version works, and you can also drop a parent folder that contains several ZBrush installs.',
    '选择 ZBrush 文件夹': 'Choose ZBrush folder',
    '自动搜索本机': 'Search this PC',
    // header / toolbar
    '在资源管理器中打开': 'Open in Explorer',
    '复制路径': 'Copy path',
    '刷新 (F5)': 'Refresh (F5)',
    '刷新': 'Refresh',
    '打开插件目录': 'Open plugin folder',
    '插件目录': 'Plugin folder',
    '启动 ZBrush': 'Launch ZBrush',
    'ZBrush 正在运行': 'ZBrush is running',
    '— 启用、禁用、安装的改动要在重启 ZBrush 后才生效；运行中删除插件可能失败。':
      '— enabling, disabling and installing take effect after ZBrush restarts; deleting a plugin while it runs may fail.',
    '插件总数': 'Plugins',
    '已启用': 'Enabled',
    'ZBrush 启动时加载': 'Loaded when ZBrush starts',
    '已禁用': 'Disabled',
    '可随时恢复': 'Can be restored any time',
    '第三方': 'Third-party',
    '版本不匹配': 'Version mismatch',
    '占用空间': 'Disk usage',
    '插件 + 数据文件夹': 'Plugins + data folders',
    '不存在': 'Missing',
    '搜索插件 (Ctrl+F)': 'Search plugins (Ctrl+F)',
    '全部': 'All',
    '全部来源': 'All sources',
    '官方': 'Official',
    '显示 / 隐藏详情面板': 'Show / hide details panel',
    // list
    '插件': 'Plugin',
    '来源 / 类型': 'Source / type',
    '数据文件夹': 'Data folder',
    '大小': 'Size',
    '更新时间': 'Modified',
    '状态': 'Status',
    '正在扫描插件…': 'Scanning plugins…',
    '没有符合条件的插件': 'No matching plugins',
    '换个关键词或筛选条件试试。': 'Try another keyword or filter.',
    '清除筛选': 'Clear filters',
    '这个 ZBrush 还没有插件': 'This ZBrush has no plugins yet',
    '把 .zsc / .py / .zip 插件拖进窗口即可安装。': 'Drop .zsc / .py / .zip plugins into the window to install them.',
    '点击禁用': 'Click to disable',
    '点击启用': 'Click to enable',
    '启用': 'Enable',
    '禁用': 'Disable',
    '删除': 'Delete',
    '取消选择': 'Clear selection',
    // details panel
    '使用指南': 'Quick guide',
    '点击左边列表里的插件，这里会显示它的文件、数据文件夹和说明。': 'Click a plugin in the list to see its files, data folder and notes here.',
    '启用 / 禁用': 'Enable / disable',
    '点开关、双击某一行或按空格。禁用只是把文件移到备用目录，': 'Click the switch, double-click a row or press Space. Disabling only moves the files to a backup folder; it ',
    '不会删除': 'does not delete',
    '，随时可以恢复。': ' them, and they can be restored at any time.',
    '把 .zsc、.py、.zip 或插件文件夹拖进窗口。压缩包里的 ZPlugs64 结构会被自动识别。': 'Drop .zsc, .py, .zip files or plugin folders into the window. A ZPlugs64 layout inside a zip is recognized automatically.',
    '多个 ZBrush': 'Several ZBrush versions',
    '左侧可以添加任意多个版本，点一下就能切换。': 'Add as many versions as you like on the left and switch with one click.',
    '记得重启': 'Remember to restart',
    '所有改动都在重启 ZBrush 后生效。': 'All changes take effect after ZBrush restarts.',
    '删除的文件会进入回收站，删错了可以还原。': 'Deleted files go to the Recycle Bin, so mistakes can be undone.',
    '关闭': 'Close',
    'ZBrush 官方插件': 'Official ZBrush plugin',
    '第三方插件': 'Third-party plugin',
    'ZBrush 启动时会加载这个插件': 'ZBrush loads this plugin at startup',
    '文件在备用目录中，ZBrush 不会加载': 'Files are in the backup folder; ZBrush will not load them',
    '基本信息': 'Details',
    '插件大小': 'Plugin size',
    '数据大小': 'Data size',
    '无数据文件夹': 'No data folder',
    '所在目录': 'Location',
    '文件': 'Files',
    '在资源管理器中显示': 'Show in Explorer',
    '打开': 'Open',
    '说明': 'Notes',
    '打开位置': 'Open location',
    '删除插件（移入回收站）': 'Delete plugin (to Recycle Bin)',
    // actions / toasts / dialogs
    '已刷新': 'Refreshed',
    'ZBrush 已在运行': 'ZBrush is already running',
    '仍然要再启动一个 ZBrush 吗？': 'Start another ZBrush anyway?',
    '再启动一个': 'Start another',
    '正在启动 ZBrush…': 'Starting ZBrush…',
    '已复制到剪贴板': 'Copied to clipboard',
    '文件会移入': 'Files will be moved to the ',
    '回收站': 'Recycle Bin',
    '，删错了可以从回收站还原。': '. If you delete the wrong one, restore it from there.',
    '同时删除数据文件夹（插件的配置和资源）': "Also delete the data folders (the plugins' settings and resources)",
    '知道了': 'OK',
    '以管理员身份重启': 'Restart as administrator',
    '有操作没有完成': 'Some actions did not finish',
    '检测到 ZBrush 正在运行': 'ZBrush is running',
    '，文件可能被占用，请关闭 ZBrush 后再试。': ', so files may be locked. Close ZBrush and try again.',
    'ZBrush 装在受保护的目录（例如 C:\\Program Files）时，需要以管理员身份运行本程序。':
      'When ZBrush is installed in a protected folder (such as C:\\Program Files), run this program as administrator.',
    '无法安装': 'Cannot install',
    '安装': 'Install',
    '将复制到：': 'Will be copied to:',
    '数据': 'Data',
    '覆盖': 'Replace',
    '新增': 'New',
    '取消': 'Cancel',
    '移除': 'Remove',
    '从列表移除？': 'Remove from list?',
    '只会把它从左侧列表里去掉，': 'This only removes it from the list on the left. It ',
    '任何文件。': ' any files.',
    '这个目录里没有找到 ZBrush（需要包含 ZBrush.exe 和 ZStartup）': 'No ZBrush found in this folder (it needs ZBrush.exe and ZStartup)',
    '请先添加一个 ZBrush，再拖入插件': 'Add a ZBrush first, then drop plugins',
    '确定': 'OK',
    // keyboard shortcuts dialog
    '空格': 'Space',
    '启用 / 禁用 选中的插件': 'Enable / disable selected plugins',
    '双击': 'Double-click',
    '单击': 'Click',
    '多选': 'Multi-select',
    '连续选择': 'Select a range',
    '全选当前列表': 'Select all in list',
    '删除（进回收站）': 'Delete (to Recycle Bin)',
    '搜索': 'Search',
    '上下切换插件': 'Previous / next plugin',
    '取消选择 / 关闭弹窗': 'Clear selection / close dialog',
    // text coming from the Python side
    '安装目录': 'Install folder',
    '安装目录 (32位 ZPlugs)': 'Install folder (32-bit ZPlugs)',
    '公共文档': 'Public Documents',
    'ZBrush 未知版本': 'ZBrush (unknown version)',
    '请先添加并选择一个 ZBrush': 'Add and select a ZBrush first',
    '没有在这些文件里找到插件（.zsc / .py）': 'No plugins (.zsc / .py) found in these files',
    '安装任务已失效，请重新拖入': 'This install task has expired. Please drop the files again.',
  };

  const RULES = [
    [/^v(.+) · 支持所有 ZBrush 版本$/, 'v$1 · Works with all ZBrush versions'],
    [/^(\d+) 启用$/, '$1 enabled'],
    [/^(\d+) 禁用$/, '$1 disabled'],
    [/^(\d+) 第三方$/, '$1 third-party'],
    [/^(\d+) 个$/, '$1'],
    [/^找到 (\d+) 个 ZBrush，已全部添加$/, 'Found $1 ZBrush installs and added them all'],
    [/^已添加 ZBrush：([\s\S]*)$/, 'Added ZBrush: $1'],
    [/^自动搜索完成：发现 (\d+) 个 ZBrush，新增 (\d+) 个$/, 'Search finished: found $1 ZBrush installs, $2 new'],
    [/^占用 (.+)$/, 'Uses $1'],
    [/^插件标注的版本不是 (.*)$/, 'Labeled for a version other than $1'],
    [/^点击打开：([\s\S]*)$/, 'Click to open: $1'],
    [/^该目录不存在：([\s\S]*)$/, 'Folder does not exist: $1'],
    [/^文件名标注 (\S+)，当前 ZBrush 是 (\S+)$/, 'File name says $1; this ZBrush is $2'],
    [/^插件 (.+) \+ 数据 (.+)$/, 'Plugin $1 + data $2'],
    [/^(\d+) 分钟前$/, '$1 min ago'],
    [/^(\d+) 小时前$/, '$1 h ago'],
    [/^(\d+) 天前$/, '$1 days ago'],
    [/^(\d+) 个月前$/, '$1 months ago'],
    [/^([\d.]+) 年前$/, '$1 years ago'],
    [/^已选择 (\d+) 个$/, '$1 selected'],
    [/^(\d+) 个启用中 · (\d+) 个已禁用$/, '$1 enabled · $2 disabled'],
    [/^为 (\S+) 版制作$/, 'Made for $1'],
    [/^\((\d+) 个文件\)$/, '($1 files)'],
    [/^(.+) · (\d+) 个文件$/, '$1 · $2 files'],
    [/^文件名标注适用于 ZBrush (\S+)，而当前是 (\S+)。如果 ZBrush 启动时报错，可以先禁用它。$/,
      'The file name says it is for ZBrush $1, but this is $2. If ZBrush shows errors at startup, disable it first.'],
    [/^已启用 (\d+) 个插件 · 重启 ZBrush 后生效$/, 'Enabled $1 plugin(s) · takes effect after ZBrush restarts'],
    [/^已禁用 (\d+) 个插件 · 重启 ZBrush 后生效$/, 'Disabled $1 plugin(s) · takes effect after ZBrush restarts'],
    [/^删除 (\d+) 个插件？$/, 'Delete $1 plugin(s)?'],
    [/^其中 (\d+) 个是 ZBrush 自带插件，一般建议用「禁用」代替删除。$/, '$1 of them ship with ZBrush. Disabling is usually better than deleting.'],
    [/^已将 (\d+) 个插件移入回收站$/, 'Moved $1 plugin(s) to the Recycle Bin'],
    [/^另外还有 (\d+) 项失败。$/, '$1 more item(s) also failed.'],
    [/^安装 (\d+) 个插件$/, 'Install $1 plugin(s)'],
    [/^有 (\d+) 项已存在，旧文件会先移入回收站。$/, '$1 item(s) already exist; the old files will be moved to the Recycle Bin first.'],
    [/^无法读取：([\s\S]*)$/, 'Could not read: $1'],
    [/^安装完成（(\d+) 项）· 重启 ZBrush 后生效$/, 'Installed $1 item(s) · takes effect after ZBrush restarts'],
    [/^无法识别：([\s\S]*)$/, 'Not recognized: $1'],
    [/^移入回收站失败 \(代码 (\d+)\): ([\s\S]*)$/, 'Could not move to Recycle Bin (code $1): $2'],
  ];

  const HAS_CJK = /[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]/;
  let lang = 'zh';
  let observer = null;

  function tr(s) {
    if (!s || !HAS_CJK.test(s)) return s;
    const m = s.match(/^(\s*)([\s\S]*?)(\s*)$/);
    const lead = m[1], core = m[2], tail = m[3];
    if (Object.prototype.hasOwnProperty.call(EXACT, core)) return lead + EXACT[core] + tail;
    for (const [re, out] of RULES) if (re.test(core)) return lead + core.replace(re, out).replace(/，/g, ', ') + tail;
    if (core.startsWith('· ')) { const r = tr(core.slice(2)); if (r !== core.slice(2)) return lead + '· ' + r + tail; }
    return s;
  }

  function translate(node) {
    if (node.nodeType === 3) {
      const v = tr(node.nodeValue);
      if (v !== node.nodeValue) node.nodeValue = v;
      return;
    }
    if (node.nodeType !== 1) return;
    for (const a of ['title', 'placeholder']) {
      const v = node.getAttribute(a);
      if (v) { const t = tr(v); if (t !== v) node.setAttribute(a, t); }
    }
    if (node.tagName === 'SCRIPT' || node.tagName === 'STYLE') return;
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
      acceptNode: n => (n.nodeType === 1 && (n.tagName === 'SCRIPT' || n.tagName === 'STYLE'))
        ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
    });
    let n = walker.nextNode();
    while (n) {
      if (n.nodeType === 3) {
        const v = tr(n.nodeValue);
        if (v !== n.nodeValue) n.nodeValue = v;
      } else {
        for (const a of ['title', 'placeholder']) {
          const v = n.getAttribute(a);
          if (v) { const t = tr(v); if (t !== v) n.setAttribute(a, t); }
        }
      }
      n = walker.nextNode();
    }
  }

  function set(next) {
    lang = next === 'en' ? 'en' : 'zh';
    document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN';
    if (lang !== 'en') { if (observer) { observer.disconnect(); observer = null; } return; }
    document.title = tr(document.title);
    translate(document.body);
    if (!observer) {
      observer = new MutationObserver(list => {
        for (const m of list) m.addedNodes.forEach(translate);
      });
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }

  return { set, tr, get lang() { return lang; } };
})();
