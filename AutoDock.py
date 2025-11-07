import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import re
import platform

class WindowArranger:
    def __init__(self):
        self.system = platform.system()
        self.windows = []
        self.monitors = self.get_monitors()
        
    def get_monitors(self):
        """获取所有显示器的信息"""
        monitors = []
        
        if self.system == "Darwin":  # macOS
            try:
                script = '''
                tell application "Finder"
                    set screenCount to count of windows
                end tell
                return screenCount
                '''
                # macOS显示器信息获取
                import subprocess
                result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], 
                                      capture_output=True, text=True)
                # 简化处理，使用screeninfo库会更准确
                try:
                    from screeninfo import get_monitors as get_screen_info
                    for m in get_screen_info():
                        monitors.append({
                            'id': len(monitors),
                            'x': m.x,
                            'y': m.y,
                            'width': m.width,
                            'height': m.height,
                            'name': m.name,
                            'is_primary': m.is_primary
                        })
                except ImportError:
                    # 如果没有screeninfo，使用默认主屏幕
                    monitors.append({
                        'id': 0,
                        'x': 0,
                        'y': 0,
                        'width': 1920,
                        'height': 1080,
                        'name': '主屏幕',
                        'is_primary': True
                    })
            except Exception as e:
                print(f"获取显示器信息失败: {e}")
                
        elif self.system == "Linux":
            try:
                result = subprocess.run(['xrandr', '--query'], 
                                      capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if ' connected' in line:
                        parts = line.split()
                        name = parts[0]
                        # 解析分辨率和位置
                        for part in parts:
                            if 'x' in part and '+' in part:
                                # 格式: 1920x1080+0+0
                                match = re.match(r'(\d+)x(\d+)\+(\d+)\+(\d+)', part)
                                if match:
                                    width, height, x, y = map(int, match.groups())
                                    monitors.append({
                                        'id': len(monitors),
                                        'x': x,
                                        'y': y,
                                        'width': width,
                                        'height': height,
                                        'name': name,
                                        'is_primary': 'primary' in line
                                    })
                                    break
            except Exception as e:
                print(f"获取显示器信息失败: {e}")
                
        elif self.system == "Windows":
            try:
                import win32api
                import win32con
                from win32api import EnumDisplayMonitors, GetMonitorInfo
                
                # 获取所有显示器
                monitor_list = EnumDisplayMonitors()
                
                for idx, monitor in enumerate(monitor_list):
                    monitor_info = GetMonitorInfo(monitor[0])
                    rect = monitor_info['Monitor']
                    work_rect = monitor_info['Work']  # 工作区域（排除任务栏）
                    
                    monitors.append({
                        'id': idx,
                        'x': rect[0],
                        'y': rect[1],
                        'width': rect[2] - rect[0],
                        'height': rect[3] - rect[1],
                        'name': f"显示器 {idx + 1}",
                        'is_primary': monitor_info['Flags'] == win32con.MONITORINFOF_PRIMARY
                    })
            except ImportError:
                print("Windows系统需要安装: pip install pywin32")
            except Exception as e:
                print(f"获取Windows显示器信息失败: {e}")
        
        # 如果没有检测到显示器，添加默认值
        if not monitors:
            monitors.append({
                'id': 0,
                'x': 0,
                'y': 0,
                'width': 1920,
                'height': 1080,
                'name': '主屏幕',
                'is_primary': True
            })
        
        return monitors
    
    def get_chrome_windows(self):
        """获取所有Chrome窗口"""
        windows = []
        
        if self.system == "Darwin":  # macOS
            script = '''
            tell application "System Events"
                set chromeWindows to every window of (processes whose name is "Google Chrome")
                set windowList to {}
                repeat with proc in chromeWindows
                    repeat with win in proc
                        set windowInfo to {name of win, id of win}
                        set end of windowList to windowInfo
                    end repeat
                end repeat
                return windowList
            end tell
            '''
            try:
                result = subprocess.run(['osascript', '-e', script], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and result.stdout:
                    # 解析返回的窗口信息
                    output = result.stdout.strip()
                    # 简单解析，实际可能需要更复杂的处理
                    windows = self._parse_mac_windows(output)
            except Exception as e:
                print(f"获取窗口失败: {e}")
                
        elif self.system == "Linux":
            try:
                result = subprocess.run(['wmctrl', '-l'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Google Chrome' in line or 'Chromium' in line:
                            parts = line.split(None, 3)
                            if len(parts) >= 4:
                                windows.append({
                                    'id': parts[0],
                                    'title': parts[3]
                                })
            except FileNotFoundError:
                messagebox.showerror("错误", "请先安装wmctrl: sudo apt-get install wmctrl")
                
        elif self.system == "Windows":
            try:
                import win32gui
                import win32process
                import psutil
                
                def callback(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        try:
                            proc = psutil.Process(pid)
                            if 'chrome.exe' in proc.name().lower():
                                title = win32gui.GetWindowText(hwnd)
                                if title:
                                    windows.append({
                                        'id': hwnd,
                                        'title': title
                                    })
                        except:
                            pass
                    return True
                
                win32gui.EnumWindows(callback, windows)
            except ImportError:
                messagebox.showerror("错误", 
                    "Windows系统需要安装: pip install pywin32 psutil")
        
        return windows
    
    def _parse_mac_windows(self, output):
        """解析macOS的AppleScript输出"""
        windows = []
        # 这是简化版本，实际输出格式可能需要调整
        items = output.split(',')
        for i in range(0, len(items), 2):
            if i + 1 < len(items):
                windows.append({
                    'title': items[i].strip(),
                    'id': items[i + 1].strip()
                })
        return windows
    
    def arrange_windows(self, selected_windows, rows, cols, monitor_id=0):
        """排列选中的窗口"""
        if not selected_windows:
            messagebox.showwarning("警告", "请至少选择一个窗口")
            return
        
        # 获取指定显示器的信息
        if monitor_id >= len(self.monitors):
            monitor_id = 0
        
        monitor = self.monitors[monitor_id]
        screen_x = monitor['x']
        screen_y = monitor['y']
        screen_width = monitor['width']
        screen_height = monitor['height']
        
        # 计算每个窗口的大小和位置
        window_width = screen_width // cols
        window_height = screen_height // rows
        
        # 排列窗口
        for idx, window in enumerate(selected_windows):
            if idx >= rows * cols:
                break
                
            row = idx // cols
            col = idx % cols
            
            x = screen_x + (col * window_width)
            y = screen_y + (row * window_height)
            
            self._move_resize_window(window['id'], x, y, window_width, window_height)
    
    def _move_resize_window(self, window_id, x, y, width, height):
        """移动和调整窗口大小"""
        if self.system == "Darwin":  # macOS
            script = f'''
            tell application "System Events"
                tell process "Google Chrome"
                    set position of window id {window_id} to {{{x}, {y}}}
                    set size of window id {window_id} to {{{width}, {height}}}
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script])
            
        elif self.system == "Linux":
            subprocess.run(['wmctrl', '-i', '-r', window_id, '-e', 
                          f'0,{x},{y},{width},{height}'])
            
        elif self.system == "Windows":
            import win32gui
            win32gui.MoveWindow(window_id, x, y, width, height, True)


class ArrangerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chrome窗口排列工具")
        self.root.geometry("600x500")
        
        self.arranger = WindowArranger()
        self.windows = []
        self.setup_monitor_info()
        
        self.create_widgets()
    
    def setup_monitor_info(self):
        """设置显示器信息"""
        self.monitors = self.arranger.monitors
        if not self.monitors:
            self.monitors = [{
                'id': 0,
                'name': '主屏幕',
                'width': 1920,
                'height': 1080,
                'is_primary': True
            }]
        
    def create_widgets(self):
        # 顶部按钮
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Button(top_frame, text="刷新窗口列表", 
                  command=self.refresh_windows).pack(side=tk.LEFT, padx=5)
        
        # 窗口列表
        list_frame = ttk.LabelFrame(self.root, text="Chrome窗口列表", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.window_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE,
                                         yscrollcommand=scrollbar.set)
        self.window_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.window_listbox.yview)
        
        # 布局设置
        layout_frame = ttk.LabelFrame(self.root, text="布局设置", padding="10")
        layout_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 显示器选择
        monitor_frame = ttk.Frame(layout_frame)
        monitor_frame.pack(fill=tk.X, pady=5)
        ttk.Label(monitor_frame, text="目标屏幕:").pack(side=tk.LEFT, padx=5)
        
        self.monitor_var = tk.StringVar()
        monitor_options = []
        for m in self.monitors:
            label = f"{m['name']} ({m['width']}x{m['height']})"
            if m['is_primary']:
                label += " [主屏幕]"
            monitor_options.append(label)
        
        if monitor_options:
            self.monitor_var.set(monitor_options[0])
        
        monitor_combo = ttk.Combobox(monitor_frame, textvariable=self.monitor_var,
                                     values=monitor_options, state='readonly', width=30)
        monitor_combo.pack(side=tk.LEFT, padx=5)
        
        # 行数
        row_frame = ttk.Frame(layout_frame)
        row_frame.pack(fill=tk.X, pady=2)
        ttk.Label(row_frame, text="行数:").pack(side=tk.LEFT, padx=5)
        self.rows_var = tk.IntVar(value=2)
        ttk.Spinbox(row_frame, from_=1, to=5, textvariable=self.rows_var,
                   width=10).pack(side=tk.LEFT)
        
        # 列数
        col_frame = ttk.Frame(layout_frame)
        col_frame.pack(fill=tk.X, pady=2)
        ttk.Label(col_frame, text="列数:").pack(side=tk.LEFT, padx=5)
        self.cols_var = tk.IntVar(value=3)
        ttk.Spinbox(col_frame, from_=1, to=5, textvariable=self.cols_var,
                   width=10).pack(side=tk.LEFT)
        
        # 预设布局按钮
        preset_frame = ttk.Frame(layout_frame)
        preset_frame.pack(fill=tk.X, pady=5)
        ttk.Label(preset_frame, text="快速预设:").pack(side=tk.LEFT, padx=5)
        ttk.Button(preset_frame, text="2x2", 
                  command=lambda: self.set_layout(2, 2)).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="2x3", 
                  command=lambda: self.set_layout(2, 3)).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="3x3", 
                  command=lambda: self.set_layout(3, 3)).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="1x2", 
                  command=lambda: self.set_layout(1, 2)).pack(side=tk.LEFT, padx=2)
        
        # 执行按钮
        bottom_frame = ttk.Frame(self.root, padding="10")
        bottom_frame.pack(fill=tk.X)
        
        ttk.Button(bottom_frame, text="排列选中窗口", 
                  command=self.arrange_windows,
                  style="Accent.TButton").pack(expand=True)
        
        # 初始加载窗口列表
        self.refresh_windows()
    
    def set_layout(self, rows, cols):
        """设置预设布局"""
        self.rows_var.set(rows)
        self.cols_var.set(cols)
    
    def refresh_windows(self):
        """刷新窗口列表"""
        self.windows = self.arranger.get_chrome_windows()
        self.window_listbox.delete(0, tk.END)
        
        if not self.windows:
            self.window_listbox.insert(tk.END, "未找到Chrome窗口")
            return
        
        for window in self.windows:
            self.window_listbox.insert(tk.END, window['title'])
    
    def arrange_windows(self):
        """排列选中的窗口"""
        selected_indices = self.window_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("警告", "请选择至少一个窗口")
            return
        
        selected_windows = [self.windows[i] for i in selected_indices]
        rows = self.rows_var.get()
        cols = self.cols_var.get()
        
        # 获取选中的显示器ID
        monitor_index = 0
        current_monitor = self.monitor_var.get()
        for idx, m in enumerate(self.monitors):
            label = f"{m['name']} ({m['width']}x{m['height']})"
            if m['is_primary']:
                label += " [主屏幕]"
            if label == current_monitor:
                monitor_index = idx
                break
        
        self.arranger.arrange_windows(selected_windows, rows, cols, monitor_index)
        
        monitor_name = self.monitors[monitor_index]['name']
        messagebox.showinfo("完成", 
            f"已在 {monitor_name} 上按 {rows}x{cols} 布局排列 {len(selected_windows)} 个窗口")
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ArrangerGUI()
    app.run()
