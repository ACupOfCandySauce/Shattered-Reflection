import os
import sys
import threading
import tempfile
import zipfile
import requests
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import numpy as np
import json, shutil
from pathlib import Path
import urllib3
import re
import time
import io
import queue
import concurrent.futures
import subprocess
import gc
import traceback
import random

import torch
import torch.nn.functional as F

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RES = 256

LICENSE_CONTENT = """Copyright © 2026 糖果

“碎隙流光/Shattered Reflection” 由 糖果 创作，采用 CC BY-NC-SA 4.0 国际许可协议授权。

https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.zh-hans
"""

COLOR_MAP = {
    "无颜色": "", "黑色": "&0", "深蓝色": "&1", "深绿色": "&2", "深青色": "&3", 
    "深红色": "&4", "紫色": "&5", "金色": "&6", "灰色": "&7", 
    "深灰色": "&8", "蓝色": "&9", "绿色": "&a", "天蓝色": "&b", 
    "红色": "&c", "粉红色": "&d", "黄色": "&e", "白色": "&f"
}
COLOR_OPTIONS = list(COLOR_MAP.keys())

TK_COLOR_MAP = {
    "无颜色": "white", "黑色": "black", "深蓝色": "darkblue", "深绿色": "darkgreen", 
    "深青色": "darkcyan", "深红色": "darkred", "紫色": "purple", "金色": "gold", 
    "灰色": "gray", "深灰色": "darkgray", "蓝色": "blue", "绿色": "green", 
    "天蓝色": "deepskyblue", "红色": "red", "粉红色": "hotpink", "黄色": "yellow", "白色": "white"
}

MC_JSON_COLOR_MAP = {
    "无颜色": None, "黑色": "black", "深蓝色": "dark_blue", "深绿色": "dark_green", 
    "深青色": "dark_aqua", "深红色": "dark_red", "紫色": "dark_purple", "金色": "gold", 
    "灰色": "gray", "深灰色": "dark_gray", "蓝色": "blue", "绿色": "green", 
    "天蓝色": "aqua", "红色": "red", "粉红色": "light_purple", "黄色": "yellow", "白色": "white"
}


# ============ 版本格式兼容 ============
_PACK_FORMAT_MAP = {
    "26.3": 97, "26.2": 88, "26.1": 84,
    "1.21.11": 75, "1.21.10": 69, "1.21.9": 69,
    "1.21.8": 64, "1.21.7": 64, "1.21.6": 63, "1.21.5": 55,
    "1.21.4": 46, "1.21.3": 42, "1.21.2": 42,
    "1.21.1": 34, "1.21": 34,
    "1.20.6": 32, "1.20.5": 32, "1.20.4": 22, "1.20.3": 22,
    "1.20.2": 18, "1.20.1": 15, "1.20": 15,
    "1.19.4": 13, "1.19.3": 12,
    "1.19.2": 9, "1.19.1": 9, "1.19": 9,
    "1.18.2": 9, "1.18.1": 8, "1.18": 8,
    "1.17.1": 7, "1.17": 7,
    "1.16.5": 6, "1.16.4": 6, "1.16.3": 6, "1.16.2": 6, "1.16.1": 6, "1.16": 6,
}


def _normalize_format(rv):
    if isinstance(rv, (list, tuple)):
        major = int(rv[0])
        minor = int(rv[1]) if len(rv) > 1 else 0
        return [major, minor]
    try:
        return int(rv)
    except (TypeError, ValueError):
        return 34


def _split_format(fmt):
    if isinstance(fmt, (list, tuple)):
        return int(fmt[0]), (int(fmt[1]) if len(fmt) > 1 else 0)
    return int(fmt), 0


def parse_pack_format(ver_data, ver_id):
    pv = ver_data.get("pack_version") if isinstance(ver_data, dict) else None
    if pv is not None:
        if isinstance(pv, dict):
            rv = pv.get("resource", pv.get("data"))
            if rv is not None:
                return _normalize_format(rv)
        else:
            return _normalize_format(pv)
    if ver_id in _PACK_FORMAT_MAP:
        return _PACK_FORMAT_MAP[ver_id]
    return 34


def build_pack_mcmeta(description, pack_format):
    major, minor = _split_format(pack_format)
    pack_data = {"description": description}
    if major < 65:
        pack_data["pack_format"] = major
    else:
        pack_data["pack_format"] = major
        pack_data["min_format"] = [major, minor]
        pack_data["max_format"] = [major, minor]
    return {"pack": pack_data}
# ==========================================


class MirrorMosaicApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MC 镜面马赛克材质生成器 (赛博半金属版)")
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = min(1300, screen_width - 100)
        window_height = min(920, screen_height - 100)
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2)) - 20
        self.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.version_list_data = []
        self.version_vars = {}
        self.res_vars = {}
        self.desc_rows = [] 
        self.icon_path = None
        self.is_syncing_main = False 
        self.update_preview_timer = None
        self.active_temp_dir = None
        self.progress_prefix = ""
        
        self.setup_ui()
        self.fetch_versions_thread()

    def on_closing(self):
        if self.active_temp_dir and Path(self.active_temp_dir).exists():
            try: shutil.rmtree(self.active_temp_dir)
            except: pass
        self.destroy()

    def setup_ui(self):
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", pady=8)
        
        self.progress_text = tk.StringVar(value="准备就绪")
        ctk.CTkLabel(bottom_frame, textvariable=self.progress_text, font=("Microsoft YaHei", 14, "bold"), text_color="#00BFFF").pack(pady=(0, 3))
        
        self.progress = ctk.CTkProgressBar(bottom_frame, width=600, height=15)
        self.progress.pack(pady=3)
        self.progress.set(0)

        self.btn_start = ctk.CTkButton(bottom_frame, text="🚀 生成镜面世界", command=self.start_generation, height=40, font=("Arial", 16, "bold"), fg_color="#28a745", hover_color="#218838")
        self.btn_start.pack(pady=6)

        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.pack(fill="both", expand=True, padx=0, pady=0)

        container = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=8, pady=8)
        container.grid_columnconfigure(0, weight=1, uniform="col")
        container.grid_columnconfigure(1, weight=1, uniform="col")

        left_col = ctk.CTkFrame(container, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        right_col = ctk.CTkFrame(container, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # ============ 左栏 ============
        desc_frame = ctk.CTkFrame(left_col)
        desc_frame.pack(fill="x", pady=(0, 5))
        info_text = (
            "这是一款全自动的镜面马赛克材质包生成器。\n\n"
            "▶ 核心特性与底层优化：\n"
            "1. 赛博半金属：超高金属反射率搭配极低粗糙度，阳光扫过极度耀眼。\n"
            "2. 斜面POM：无任何黑线遮盖，纯粹依靠法线高度差呈现物理凹陷。\n"
            "3. 完美透光：精准拦截纯动画(.mcmeta)，玻璃树叶完美支持。\n"
            "4. Iris变体：自动生成 properties 配置文件，光影下完美随机变体。"
        )
        info_box = ctk.CTkTextbox(desc_frame, height=100, font=("Microsoft YaHei", 13), wrap="word")
        info_box.pack(fill="x", padx=10, pady=10)
        info_box.insert("1.0", info_text)
        info_box.configure(state="disabled")

        net_frame = ctk.CTkFrame(left_col)
        net_frame.pack(fill="x", pady=5)
        self.source_var = tk.StringVar(value="mirror")
        ctk.CTkRadioButton(net_frame, text="镜像源 (推荐)", variable=self.source_var, value="mirror").pack(side="left", padx=10, pady=10)
        ctk.CTkRadioButton(net_frame, text="官方源 (Mojang)", variable=self.source_var, value="official").pack(side="left", padx=10, pady=10)
        ctk.CTkLabel(net_frame, text="搜索版本:").pack(side="left", padx=(15, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_versions)
        ctk.CTkEntry(net_frame, textvariable=self.search_var, width=120, height=28).pack(side="left", padx=(0, 8))

        ver_frame = ctk.CTkFrame(left_col)
        ver_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(ver_frame, text="选择版本（可多选）:").pack(anchor="w", padx=10, pady=(8, 0))
        self.version_scroll = ctk.CTkScrollableFrame(ver_frame, height=220)
        self.version_scroll.pack(fill="x", padx=10, pady=(0, 8))

        res_frame = ctk.CTkFrame(left_col)
        res_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(res_frame, text="选择分辨率（可多选）:").pack(side="left", padx=10)
        for r in ["64X", "128X", "256X"]:
            var = tk.BooleanVar(value=(r == "256X"))
            self.res_vars[r] = var
            ctk.CTkCheckBox(res_frame, text=r, variable=var).pack(side="left", padx=12)

        # ============ 右栏 ============
        info_frame = ctk.CTkFrame(right_col)
        info_frame.pack(fill="x", pady=(0, 5))

        frame_name = ctk.CTkFrame(info_frame, fg_color="transparent")
        frame_name.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(frame_name, text="包名:", width=40, anchor="w").pack(side="left")
        self.name_entry = ctk.CTkEntry(frame_name, width=300, height=28)
        self.name_entry.pack(side="left", padx=5)
        self.name_entry.insert(0, "碎隙流光")

        frame_desc = ctk.CTkFrame(info_frame, fg_color="transparent")
        frame_desc.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(frame_desc, text="描述:", width=40, anchor="w").pack(side="left")
        self.desc_main = ctk.CTkEntry(frame_desc, height=28)
        self.desc_main.pack(side="left", padx=5, fill="x", expand=True)
        self.desc_main.insert(0, "喵~")
        self.desc_main.bind("<Return>", self.on_main_entry_change)
        self.desc_main.bind("<FocusOut>", self.on_main_entry_change)

        self.desc_canvas = ctk.CTkCanvas(info_frame, height=150, highlightthickness=0, bg="#2b2b2b")
        self.desc_scroll = ctk.CTkScrollbar(info_frame, orientation="vertical", command=self.desc_canvas.yview)
        self.desc_list_frame = ctk.CTkFrame(self.desc_canvas, fg_color="#2b2b2b")
        
        self.canvas_window = self.desc_canvas.create_window((0, 0), window=self.desc_list_frame, anchor="nw")
        self.desc_canvas.configure(yscrollcommand=self.desc_scroll.set)
        self.desc_canvas.bind("<Configure>", self._on_canvas_configure)
        
        self.desc_canvas.pack(fill="x", padx=10, pady=5)
        self.desc_scroll.place(relx=1.0, rely=0.0, relheight=1.0, anchor="ne")
        self.desc_list_frame.bind("<Configure>", lambda e: self.desc_canvas.configure(scrollregion=self.desc_canvas.bbox("all")))

        merge_frame = ctk.CTkFrame(info_frame)
        merge_frame.pack(fill="x", padx=10, pady=(5,10))
        
        self.merge_var = tk.StringVar(value="newline")
        ctk.CTkLabel(merge_frame, text="拼接方式:").pack(side="left", padx=5)
        ctk.CTkRadioButton(merge_frame, text="换行", variable=self.merge_var, value="newline", command=self.update_preview).pack(side="left", padx=5)
        ctk.CTkRadioButton(merge_frame, text="空格", variable=self.merge_var, value="space", command=self.update_preview).pack(side="left", padx=5)
        ctk.CTkRadioButton(merge_frame, text="无缝", variable=self.merge_var, value="none", command=self.update_preview).pack(side="left", padx=5)

        ctk.CTkLabel(merge_frame, text=" | 碎片数:").pack(side="left", padx=5)
        self.variant_var = tk.StringVar(value="80")
        ctk.CTkEntry(merge_frame, textvariable=self.variant_var, width=40, height=28).pack(side="left")
        
        ctk.CTkLabel(merge_frame, text=" | 变体数:").pack(side="left", padx=5)
        self.v_count_var = tk.StringVar(value="4")
        ctk.CTkEntry(merge_frame, textvariable=self.v_count_var, width=40, height=28).pack(side="left")
        ctk.CTkLabel(merge_frame, text="(物品固定1)", text_color="gray", font=("Microsoft YaHei", 11)).pack(side="left", padx=5)

        preview_frame = ctk.CTkFrame(info_frame)
        preview_frame.pack(fill="x", padx=10, pady=(5,10))
        ctk.CTkLabel(preview_frame, text="游戏内实时预览:").pack(anchor="w", padx=5)
        self.preview_text = ctk.CTkTextbox(preview_frame, height=60, font=("Microsoft YaHei", 14), wrap="word")
        self.preview_text.pack(fill="x", padx=5, pady=5)

        path7z_frame = ctk.CTkFrame(right_col)
        path7z_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(path7z_frame, text="压缩模式:").pack(side="left", padx=(10, 5))
        self.compress_var = tk.StringVar(value="极速不压缩")
        ctk.CTkComboBox(path7z_frame, variable=self.compress_var, values=["极速不压缩", "内置多核压缩", "7z极速压缩"], width=110, height=28, state="readonly").pack(side="left", padx=5)
        
        ctk.CTkLabel(path7z_frame, text="| 7z 路径:").pack(side="left", padx=5)
        default_7z = "C:\\Program Files\\7-Zip\\7z.exe"
        if not os.path.exists(default_7z): default_7z = "C:\\Program Files (x86)\\7-Zip\\7z.exe"
        if not os.path.exists(default_7z): default_7z = "D:\\7-Zip\\7z.exe"
        if not os.path.exists(default_7z): default_7z = "C:\\7-Zip\\7z.exe"
        if not os.path.exists(default_7z): default_7z = "7z"
        self.path7z_var = tk.StringVar(value=default_7z)
        ctk.CTkEntry(path7z_frame, textvariable=self.path7z_var, width=220, height=28).pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(path7z_frame, text="浏览", width=60, height=28, command=self.select_7z).pack(side="left", padx=5)

        path_frame = ctk.CTkFrame(right_col)
        path_frame.pack(fill="x", pady=5)
        
        ctk.CTkButton(path_frame, text="选择封面图", command=self.select_icon, width=100, height=28).grid(row=0, column=0, padx=10, pady=10)
        self.icon_preview = ctk.CTkLabel(path_frame, text="无封面", fg_color="gray", width=64, height=64, corner_radius=8)
        self.icon_preview.grid(row=0, column=1, padx=10)
        
        ctk.CTkLabel(path_frame, text="导出路径:").grid(row=1, column=0, padx=10, pady=(0,10))
        self.path_var = tk.StringVar(value=str(Path.home() / "Desktop"))
        ctk.CTkEntry(path_frame, textvariable=self.path_var, width=300, height=28).grid(row=1, column=1, sticky="ew", padx=5, pady=(0,10))
        ctk.CTkButton(path_frame, text="浏览...", command=self.select_path, width=80, height=28).grid(row=1, column=2, padx=10, pady=(0,10))
        path_frame.grid_columnconfigure(1, weight=1)

        self.on_main_entry_change(None)
        if self.desc_rows:
            self.desc_rows[0]["italic"].set(True)
            self.sync_from_list()

    def _on_canvas_configure(self, event):
        self.desc_canvas.itemconfig(self.canvas_window, width=event.width - 20)

    def select_7z(self):
        file_path = filedialog.askopenfilename(filetypes=[("可执行文件", "*.exe")])
        if file_path:
            self.path7z_var.set(file_path)

    def on_main_entry_change(self, event=None):
        if self.is_syncing_main: return
        self.parse_description()

    def sync_from_list(self):
        if self.update_preview_timer:
            self.after_cancel(self.update_preview_timer)
        self.update_preview_timer = self.after(200, self._do_sync)

    def _do_sync(self):
        parts = [row["text"].get().strip() for row in self.desc_rows]
        new_main_text = "|".join(parts)
        
        self.is_syncing_main = True
        self.desc_main.delete(0, tk.END)
        self.desc_main.insert(0, new_main_text)
        self.is_syncing_main = False
        self.update_preview()

    def parse_description(self, event=None):
        current_state = []
        for row in self.desc_rows:
            current_state.append({
                "text": row["text"].get(), "color": row["color"].get(),
                "italic": row["italic"].get(), "bold": row["bold"].get(),
                "under": row["under"].get(), "custom_hex": row["custom_hex"].get()
            })
        
        for widget in self.desc_list_frame.winfo_children():
            widget.destroy()
        self.desc_rows.clear()
        
        raw_desc = self.desc_main.get() or ""
        parts = raw_desc.split("|")
        
        for i, part in enumerate(parts):
            state_to_use = None
            if i < len(current_state) and current_state[i]["text"] == part.strip():
                state_to_use = current_state[i]
            self.create_row(i, part.strip(), state_to_use)
            
        self.update_preview()

    def create_row(self, index, text_val, state=None):
        row_frame = ctk.CTkFrame(self.desc_list_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)
        row_dict = {"frame": row_frame}
        
        def delete_this_row():
            row_frame.destroy()
            self.desc_rows.remove(row_dict)
            parts = [r["text"].get().strip() for r in self.desc_rows]
            self.is_syncing_main = True
            self.desc_main.delete(0, tk.END)
            self.desc_main.insert(0, "|".join(parts))
            self.is_syncing_main = False
            self.parse_description()
            
        def add_row_after():
            parts = [r["text"].get().strip() for r in self.desc_rows]
            parts.insert(index + 1, "")
            self.is_syncing_main = True
            self.desc_main.delete(0, tk.END)
            self.desc_main.insert(0, "|".join(parts))
            self.is_syncing_main = False
            self.parse_description()
            
        ctk.CTkButton(row_frame, text="+", width=40, height=28, font=("Arial", 18, "bold"), fg_color="#28a745", hover_color="#1e7e34", command=add_row_after).grid(row=0, column=8, padx=5, pady=4, sticky="e")
        ctk.CTkButton(row_frame, text="-", width=40, height=28, font=("Arial", 18, "bold"), fg_color="#dc3545", hover_color="#a71d2a", command=delete_this_row).grid(row=0, column=0, padx=2, pady=4)
        
        ctk.CTkLabel(row_frame, text=f"段 {index+1}:", width=45).grid(row=0, column=1, padx=5, pady=4)
        
        entry = ctk.CTkEntry(row_frame, width=150, height=28)
        entry.grid(row=0, column=2, padx=5, pady=4, sticky="ew")
        entry.insert(0, text_val)
            
        color_val = "天蓝色"
        custom_hex_val = "#FFFFFF"
        italic_val = False
        bold_val = False
        under_val = False
        
        if state:
            color_val = state["color"]
            custom_hex_val = state["custom_hex"]
            italic_val = state["italic"]
            bold_val = state["bold"]
            under_val = state["under"]
            
        color_var = tk.StringVar(value=color_val)
        color_combo = ctk.CTkComboBox(row_frame, variable=color_var, values=COLOR_OPTIONS + ["自定义颜色"], width=90, height=28, state="readonly")
        color_combo.grid(row=0, column=3, padx=5, pady=4)
        
        custom_hex_var = tk.StringVar(value=custom_hex_val)
        def pick_color():
            from tkinter import colorchooser
            color_code = colorchooser.askcolor(title="选择颜色", color=custom_hex_var.get())
            if color_code and color_code[1]:
                custom_hex_var.set(color_code[1])
                color_var.set("自定义颜色")
                self.sync_from_list()
                
        ctk.CTkButton(row_frame, text="颜色", width=45, height=28, font=("Microsoft YaHei", 12, "bold"), fg_color="#1f538d", hover_color="#14375e", command=pick_color).grid(row=0, column=4, padx=5, pady=4)
        
        italic_var = tk.BooleanVar(value=italic_val)
        bold_var = tk.BooleanVar(value=bold_val)
        under_var = tk.BooleanVar(value=under_val)
        
        ctk.CTkCheckBox(row_frame, text="斜体", variable=italic_var, width=50, height=28, command=self.sync_from_list).grid(row=0, column=5, padx=2, pady=4)
        ctk.CTkCheckBox(row_frame, text="粗体", variable=bold_var, width=50, height=28, command=self.sync_from_list).grid(row=0, column=6, padx=2, pady=4)
        ctk.CTkCheckBox(row_frame, text="下划线", variable=under_var, width=60, height=28, command=self.sync_from_list).grid(row=0, column=7, padx=2, pady=4)
        
        row_frame.grid_columnconfigure(2, weight=1)
        
        entry.bind("<KeyRelease>", lambda e: self.sync_from_list())
        color_combo.bind("<<ComboboxSelected>>", lambda e: self.sync_from_list())
        
        row_dict.update({
            "text": entry, "color": color_var, "italic": italic_var,
            "bold": bold_var, "under": under_var, "custom_hex": custom_hex_var
        })
        self.desc_rows.append(row_dict)

    def update_preview(self):
        txt = self.preview_text._textbox
        txt.configure(state="normal")
        txt.delete("1.0", tk.END)
        
        merge_method = self.merge_var.get()
        valid_parts = 0
        
        for row in self.desc_rows:
            text = row["text"].get().strip()
            if not text: continue
            valid_parts += 1
            
            color_name = row["color"].get()
            if color_name == "自定义颜色":
                fg_color = row["custom_hex"].get()
            else:
                fg_color = TK_COLOR_MAP.get(color_name, "white")
            
            font_family = "Microsoft YaHei"
            size = 14
            weight = "bold" if row["bold"].get() else "normal"
            slant = "italic" if row["italic"].get() else "roman"
            underline = row["under"].get()
            
            tag_name = f"tag_{valid_parts}"
            font_obj = tkfont.Font(family=font_family, size=size, weight=weight, slant=slant, underline=underline)
            
            txt.tag_configure(tag_name, foreground=fg_color, font=font_obj)
            txt.insert(tk.END, text, tag_name)
            
            if merge_method == "newline":
                txt.insert(tk.END, "\n")
            elif merge_method == "space":
                txt.insert(tk.END, " ")
                
        txt.configure(state="disabled")

    def select_icon(self):
        file_path = filedialog.askopenfilename(filetypes=[("图片文件", "*.png;*.jpg;*.jpeg")])
        if file_path:
            self.icon_path = file_path
            try:
                img = Image.open(file_path)
                img.thumbnail((64, 64))
                self.icon_preview_img = ctk.CTkImage(light_image=img, dark_image=img, size=(64, 64))
                self.icon_preview.configure(image=self.icon_preview_img, text="")
            except Exception as e:
                messagebox.showerror("错误", f"无法加载图片: {e}")

    def select_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)

    def fetch_versions_thread(self):
        threading.Thread(target=self.fetch_versions, daemon=True).start()

    def fetch_versions(self):
        url = "https://bmclapi2.bangbang93.com/mc/game/version_manifest_v2.json" if self.source_var.get() == "mirror" else "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            self.version_list_data = [v["id"] for v in data["versions"] if v["type"] == "release"]
            self.after(0, self.filter_versions)
        except Exception:
            self.after(0, lambda: messagebox.showerror("网络错误", "无法拉取版本列表，请检查网络或镜像状态！"))

    def filter_versions(self, *args):
        search = self.search_var.get().lower()
        filtered = [v for v in self.version_list_data if search in v.lower()]
        MAX_DISPLAY = 120
        display_list = filtered[:MAX_DISPLAY]

        def rebuild():
            for w in self.version_scroll.winfo_children():
                w.destroy()
            if not display_list:
                ctk.CTkLabel(self.version_scroll, text="无匹配版本", text_color="gray").pack(anchor="w", padx=5, pady=2)
                return
            for v in display_list:
                var = self.version_vars.get(v)
                if var is None:
                    var = tk.BooleanVar(value=False)
                    self.version_vars[v] = var
                ctk.CTkCheckBox(self.version_scroll, text=v, variable=var).pack(anchor="w", padx=5, pady=1)
            if len(filtered) > MAX_DISPLAY:
                ctk.CTkLabel(self.version_scroll, text=f"...共 {len(filtered)} 个，请用搜索缩小范围", text_color="gray").pack(anchor="w", padx=5, pady=2)

        self.after(0, rebuild)

    def update_ui(self, text, percent, reset=False):
        prefix = self.progress_prefix
        display = f"{prefix} {text}" if prefix else text
        self.after(0, lambda: self.progress_text.set(display))
        self.after(0, lambda: self.progress.set(percent))
        if reset: self.after(0, lambda: self.progress.set(0))

    @torch.no_grad()
    def process_batch_gpu(self, batch_arrays, num_points, res):
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        np_batch = np.stack(batch_arrays) 
        tensor = torch.from_numpy(np_batch).permute(0, 3, 1, 2).float().to(device)
        
        rgb = tensor[:, :3, :, :]
        alpha = tensor[:, 3:4, :, :]
        B = rgb.shape[0]
        
        x = torch.arange(res, device=device).float()
        y = torch.arange(res, device=device).float()
        grid_y, grid_x = torch.meshgrid(y, x, indexing='ij')
        grid_pts = torch.stack([grid_x.flatten(), grid_y.flatten()], dim=1).unsqueeze(0)
        
        pts = torch.rand(B, num_points, 2, device=device) * res
        
        shifts = torch.tensor([
            [-res, 0], [res, 0], [0, -res], [0, res],
            [-res, -res], [res, res], [res, -res], [-res, res]
        ], device=device).float()
        
        pts_ext = pts.unsqueeze(2) + shifts.unsqueeze(0).unsqueeze(0)
        pts_ext = pts_ext.reshape(B, num_points * 8, 2)
        pts_ext = torch.cat([pts, pts_ext], dim=1)
        
        dists = torch.cdist(grid_pts, pts_ext) 
        min1_val, min1_idx = torch.min(dists, dim=2)
        
        indices = min1_idx.reshape(B, res, res)
        
        del dists, grid_pts, pts_ext
        if torch.cuda.is_available(): torch.cuda.empty_cache()
        
        edge_mask = torch.zeros((B, res, res), dtype=torch.bool, device=device)
        edge_mask[:, :, :-1] |= (indices[:, :, :-1] != indices[:, :, 1:])
        edge_mask[:, :-1, :] |= (indices[:, :-1, :] != indices[:, 1:, :])
        
        seam_mask = F.max_pool2d(edge_mask.float().unsqueeze(1), kernel_size=3, stride=1, padding=1).squeeze(1) > 0.5
        
        # === 1. 颜色图 ===
        color_out = rgb.to(torch.uint8)
        color_rgba = torch.cat([color_out, alpha.to(torch.uint8)], dim=1)
        
        # === 2. 高光图（块级随机，提升无损压缩率） ===
        spec = torch.zeros((B, 4, res, res), device=device)
        
        metal_table = 200 + torch.rand(B, num_points * 9, device=device) * 20
        rough_table = 30 + torch.rand(B, num_points * 9, device=device) * 30
        
        metal = torch.gather(metal_table, 1, indices.reshape(B, -1)).reshape(B, res, res)
        rough = torch.gather(rough_table, 1, indices.reshape(B, -1)).reshape(B, res, res)
        
        spec[:, 0] = metal
        spec[:, 1] = rough
        spec[:, 0] = torch.where(seam_mask, torch.tensor(0.0, device=device, dtype=spec.dtype), spec[:, 0])
        spec[:, 1] = torch.where(seam_mask, torch.tensor(255.0, device=device, dtype=spec.dtype), spec[:, 1])
        spec[:, 3, :, :] = alpha.squeeze(1)
        
        # === 3. 法线图与 POM 高度 ===
        angle_x_table = (torch.rand(B, num_points * 9, device=device) * 0.35 - 0.175).unsqueeze(2).unsqueeze(3) 
        angle_y_table = (torch.rand(B, num_points * 9, device=device) * 0.35 - 0.175).unsqueeze(2).unsqueeze(3)
        
        nx = torch.gather(angle_x_table.expand(-1, -1, res, res), 1, indices.unsqueeze(1)).squeeze(1)
        ny = torch.gather(angle_y_table.expand(-1, -1, res, res), 1, indices.unsqueeze(1)).squeeze(1)
        nz = torch.ones_like(nx)
        
        length = torch.sqrt(nx**2 + ny**2 + nz**2)
        nx, ny, nz = nx/length, ny/length, nz/length
        
        alpha_mask = (alpha.squeeze(1) < 0.5)
        transparent_count = alpha_mask.sum(dim=(1,2))
        is_transparent = transparent_count > 1000 
        
        depth_val = torch.where(is_transparent, 110.0, 105.0).float().view(B, 1, 1)
        
        hn = torch.ones_like(nx) * 128.0
        hn = torch.where(seam_mask, depth_val, hn)
        
        normal_rgba = torch.stack([
            (nx*0.5+0.5)*255, 
            (-ny*0.5+0.5)*255, 
            (nz*0.5+0.5)*255, 
            hn
        ], dim=1).to(torch.uint8)
        
        return (color_rgba.permute(0, 2, 3, 1).cpu().numpy(),
                normal_rgba.permute(0, 2, 3, 1).cpu().numpy(),
                spec.to(torch.uint8).permute(0, 2, 3, 1).cpu().numpy())

    def prepare_version(self, ver_id, is_mirror, headers, temp_dir):
        manifest_url = "https://bmclapi2.bangbang93.com/mc/game/version_manifest_v2.json" if is_mirror else "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
        
        manifest = None
        for _ in range(3):
            try:
                manifest = requests.get(manifest_url, headers=headers, timeout=10).json()
                break
            except Exception:
                time.sleep(1)
        
        if not manifest:
            raise RuntimeError("无法连接到版本服务器，请检查网络或切换源！")

        target_ver = next((v for v in manifest["versions"] if v["id"] == ver_id), None)
        if not target_ver:
            raise RuntimeError(f"找不到版本 {ver_id} 的配置信息！")

        ver_json_url = target_ver["url"]
        if is_mirror:
            ver_json_url = ver_json_url.replace("piston-meta.mojang.com", "bmclapi2.bangbang93.com")
        
        ver_data = None
        for _ in range(3):
            try:
                ver_data = requests.get(ver_json_url, headers=headers, timeout=10).json()
                break
            except Exception:
                time.sleep(1)
        
        if not ver_data:
            raise RuntimeError("获取详细版本信息失败！")

        pack_format = parse_pack_format(ver_data, ver_id)
        print(f"[DEBUG] {ver_id} -> pack_format = {pack_format}")

        client_url = ver_data["downloads"]["client"]["url"]
        if is_mirror:
            client_url = client_url.replace("piston-meta.mojang.com", "bmclapi2.bangbang93.com").replace("piston-data.mojang.com", "bmclapi2.bangbang93.com")

        jar_path = temp_dir / f"client_{ver_id}.jar"
        self.update_ui(f"正在下载 {ver_id} 客户端...", 0, reset=True)
        download_success = False
        try:
            with requests.get(client_url, headers=headers, stream=True, timeout=15) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                last_update = time.time()
                with open(jar_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            now = time.time()
                            if now - last_update > 0.1 and total_size > 0:
                                last_update = now
                                self.update_ui(f"下载中: {downloaded/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB", downloaded / total_size)
            download_success = True
            self.update_ui("下载完成", 1.0)
        except Exception as e:
            print(f"[DEBUG] 镜像下载失败: {e}，尝试使用官方源...")
        
        if not download_success:
            client_url_official = client_url.replace("bmclapi2.bangbang93.com", "piston-data.mojang.com")
            try:
                with requests.get(client_url_official, headers=headers, stream=True, timeout=15) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get('content-length', 0))
                    downloaded = 0
                    last_update = time.time()
                    with open(jar_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                now = time.time()
                                if now - last_update > 0.1 and total_size > 0:
                                    last_update = now
                                    self.update_ui(f"官方源下载中: {downloaded/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB", downloaded / total_size)
                self.update_ui("下载完成", 1.0)
            except Exception as e:
                raise RuntimeError(f"镜像和官方源均下载失败: {e}")

        return jar_path, pack_format

    def process_one_pack(self, jar_path, pack_format, res, display_name, final_zip_path,
                         final_desc_json, mosaic_points, variant_count, compress_mode, path_7z, work_dir):
        use_folder = (compress_mode == "7z极速压缩")
        pack_dir = work_dir / "pack"

        block_files = []
        other_files = []

        print(f"[DEBUG] 正在扫描 jar 包文件 ({display_name})...")
        with zipfile.ZipFile(jar_path, 'r') as z:
            names_list = z.namelist()
            names_set = set(names_list)
            for name in names_list:
                if not name.endswith(".png"): continue
                
                if "/textures/particle/" in name:
                    continue
                    
                if "/textures/entity/" in name:
                    if "trident" not in name.lower():
                        continue

                has_mcmeta = (name + ".mcmeta") in names_set
                mc_bytes = None
                if has_mcmeta:
                    with z.open(name + ".mcmeta") as mf: mc_bytes = mf.read()
                        
                if "/textures/block/" in name:
                    block_files.append((name, has_mcmeta, mc_bytes))
                elif "/textures/item/" in name:
                    other_files.append((name, has_mcmeta, mc_bytes))
                elif "/textures/entity/trident" in name.lower():
                    other_files.append((name, has_mcmeta, mc_bytes))

        total_tasks = len(other_files)
        for _, has_mc, _ in block_files:
            if has_mc:
                total_tasks += 1
            else:
                total_tasks += variant_count

        print(f"[DEBUG] 扫描完成！总需处理 {total_tasks} 张贴图。")
        if not block_files and not other_files:
            raise RuntimeError("未找到任何贴图！可能是版本不匹配或文件损坏。")

        processed_count = [0] 

        read_queue = queue.Queue(maxsize=2000) 
        write_queue = queue.Queue(maxsize=2000)  
        
        def is_true_animation(mc_bytes):
            if not mc_bytes: return False
            try:
                mc_json = json.loads(mc_bytes.decode('utf-8'))
                return "animation" in mc_json
            except Exception:
                return False

        def convert_task(img_name, img_bytes, is_block, has_mcmeta, mc_bytes):
            try:
                if has_mcmeta and is_true_animation(mc_bytes):
                    if use_folder:
                        write_queue.put(("RAW_FILE", img_name, img_bytes, mc_bytes))
                    else:
                        write_queue.put(("RAW", img_name, img_bytes, mc_bytes))
                    return
                    
                src = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
                w, h = src.size
                if w != h:
                    max_dim = max(w, h)
                    new_img = Image.new("RGBA", (max_dim, max_dim), (0, 0, 0, 0))
                    new_img.paste(src, ((max_dim - w) // 2, (max_dim - h) // 2))
                    src = new_img

                v_limit = variant_count if is_block else 1
                base_img = src.resize((res, res), Image.NEAREST)
                base_arr = np.array(base_img)
                
                for v in range(v_limit):
                    var_name = img_name if v == 0 else img_name.replace(".png", f"_{v}.png")
                    v_mc_bytes = mc_bytes if v == 0 else None
                    read_queue.put(("ARRAY", var_name, base_arr, v_mc_bytes))
            except Exception as e:
                print(f"[ERROR] 处理 {img_name} 失败: {e}")

        def read_loop():
            try:
                with zipfile.ZipFile(jar_path, 'r') as z_read:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
                        futures = []
                        for img_name, has_mc, mc_bytes in block_files:
                            with z_read.open(img_name) as f: img_bytes = f.read()
                            futures.append(executor.submit(convert_task, img_name, img_bytes, True, has_mc, mc_bytes))
                        for img_name, has_mc, mc_bytes in other_files:
                            with z_read.open(img_name) as f: img_bytes = f.read()
                            futures.append(executor.submit(convert_task, img_name, img_bytes, False, has_mc, mc_bytes))
                        
                        for future in concurrent.futures.as_completed(futures):
                            pass
            except Exception as e:
                print(f"[ERROR] 读取线程失败: {e}")
            finally:
                read_queue.put(None)

        zip_lock = threading.Lock()
        out_zip = None
        if not use_folder:
            final_zip_path.parent.mkdir(parents=True, exist_ok=True)
            out_zip = zipfile.ZipFile(final_zip_path, 'w', zipfile.ZIP_STORED)

        def write_task(item, out_zip=None):
            if not use_folder:
                if item[0] == "RAW":
                    _, name, img_bytes, mc_bytes = item
                    rel_path = name.replace("\\", "/")
                    with zip_lock:
                        out_zip.writestr(rel_path, img_bytes)
                        if mc_bytes: out_zip.writestr(rel_path + ".mcmeta", mc_bytes)
                    processed_count[0] += 1
                elif item[0] == "ARRAY":
                    _, name, res_img, res_norm, res_spec, mc_bytes = item
                    rel_path = name.replace("\\", "/")
                    
                    bio_img = io.BytesIO(); Image.fromarray(res_img, "RGBA").save(bio_img, format="PNG", compress_level=0)
                    bio_norm = io.BytesIO(); Image.fromarray(res_norm, "RGBA").save(bio_norm, format="PNG", compress_level=0)
                    bio_spec = io.BytesIO(); Image.fromarray(res_spec, "RGBA").save(bio_spec, format="PNG", compress_level=0)
                    
                    with zip_lock:
                        out_zip.writestr(rel_path, bio_img.getvalue())
                        out_zip.writestr(rel_path.replace(".png", "_n.png"), bio_norm.getvalue())
                        out_zip.writestr(rel_path.replace(".png", "_s.png"), bio_spec.getvalue())
                        if mc_bytes: out_zip.writestr(rel_path + ".mcmeta", mc_bytes)
                    processed_count[0] += 1
                
            if processed_count[0] % 20 == 0 or processed_count[0] == total_tasks:
                percent = processed_count[0] / total_tasks if total_tasks else 1.0
                self.update_ui(f"正在极速转换: {processed_count[0]} / {total_tasks} 张", percent)

        writers = []
        for _ in range(16):
            def writer_loop():
                while True:
                    item = write_queue.get()
                    if item is None: break
                    
                    try:
                        if item[0] == "RAW_FILE":
                            _, name, img_bytes, mc_bytes = item
                            out_path = pack_dir / name
                            out_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(out_path, 'wb') as f: f.write(img_bytes)
                            if mc_bytes:
                                with open(str(out_path) + ".mcmeta", 'wb') as f: f.write(mc_bytes)
                            processed_count[0] += 1
                        elif item[0] == "ARRAY_FILE":
                            _, name, res_img, res_norm, res_spec, mc_bytes = item
                            out_path = pack_dir / name
                            out_path.parent.mkdir(parents=True, exist_ok=True)
                            Image.fromarray(res_img, "RGBA").save(out_path, format="PNG", compress_level=0)
                            Image.fromarray(res_norm, "RGBA").save(out_path.with_name(f"{out_path.stem}_n.png"), format="PNG", compress_level=0)
                            Image.fromarray(res_spec, "RGBA").save(out_path.with_name(f"{out_path.stem}_s.png"), format="PNG", compress_level=0)
                            if mc_bytes:
                                with open(str(out_path) + ".mcmeta", 'wb') as f: f.write(mc_bytes)
                            processed_count[0] += 1
                        else:
                            write_task(item, out_zip)
                            
                        if processed_count[0] % 20 == 0 or processed_count[0] == total_tasks:
                            percent = processed_count[0] / total_tasks if total_tasks else 1.0
                            self.update_ui(f"正在极速转换: {processed_count[0]} / {total_tasks} 张", percent)
                    except Exception as e:
                        print(f"[ERROR] 写入线程出错: {e}")
                        
            w = threading.Thread(target=writer_loop)
            w.start(); writers.append(w)

        threading.Thread(target=read_loop, daemon=True).start()

        batch_arrays, batch_names, batch_mcmetas = [], [], []
        batch_size = 64
        
        while True:
            item = read_queue.get()
            if item is None: break
                
            _, name, arr, mc_bytes = item
            batch_names.append(name)
            batch_arrays.append(arr)
            batch_mcmetas.append(mc_bytes)
            
            if len(batch_arrays) >= batch_size:
                try:
                    r_img, r_norm, r_spec = self.process_batch_gpu(batch_arrays, mosaic_points, res)
                except torch.OutOfMemoryError:
                    print("[WARN] 显存不足，自动降低 batch_size 处理...")
                    if torch.cuda.is_available(): torch.cuda.empty_cache()
                    r_img, r_norm, r_spec = [], [], []
                    for arr in batch_arrays:
                        a_img, a_norm, a_spec = self.process_batch_gpu([arr], mosaic_points, res)
                        r_img.extend(a_img); r_norm.extend(a_norm); r_spec.extend(a_spec)
                        
                for i in range(len(batch_arrays)): 
                    if use_folder:
                        write_queue.put(("ARRAY_FILE", batch_names[i], r_img[i], r_norm[i], r_spec[i], batch_mcmetas[i]))
                    else:
                        write_queue.put(("ARRAY", batch_names[i], r_img[i], r_norm[i], r_spec[i], batch_mcmetas[i]))
                batch_arrays.clear(); batch_names.clear(); batch_mcmetas.clear()

        if batch_arrays:
            try:
                r_img, r_norm, r_spec = self.process_batch_gpu(batch_arrays, mosaic_points, res)
            except torch.OutOfMemoryError:
                if torch.cuda.is_available(): torch.cuda.empty_cache()
                r_img, r_norm, r_spec = [], [], []
                for arr in batch_arrays:
                    a_img, a_norm, a_spec = self.process_batch_gpu([arr], mosaic_points, res)
                    r_img.extend(a_img); r_norm.extend(a_norm); r_spec.extend(a_spec)

            for i in range(len(batch_arrays)): 
                if use_folder:
                    write_queue.put(("ARRAY_FILE", batch_names[i], r_img[i], r_norm[i], r_spec[i], batch_mcmetas[i]))
                else:
                    write_queue.put(("ARRAY", batch_names[i], r_img[i], r_norm[i], r_spec[i], batch_mcmetas[i]))

        for _ in range(16): write_queue.put(None)
        for w in writers: w.join()

        print("[DEBUG] 贴图转换完毕，正在写入配置文件和变体配置...")
        self.update_ui("正在写入配置文件...", 1.0)
        pack_mcmeta = build_pack_mcmeta(final_desc_json, pack_format)
        
        if use_folder:
            with open(pack_dir / "pack.mcmeta", 'w', encoding='utf-8') as f: f.write(json.dumps(pack_mcmeta, indent=2, ensure_ascii=False))
            with open(pack_dir / "texture.properties", 'w', encoding='utf-8') as f: f.write("labPBR=1.3\n")
            with open(pack_dir / "LICENSE.md", 'w', encoding='utf-8') as f: f.write(LICENSE_CONTENT)
            if self.icon_path and Path(self.icon_path).exists():
                try:
                    Image.open(self.icon_path).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS).save(pack_dir / "pack.png", format="PNG")
                except: pass
        else:
            out_zip.writestr("pack.mcmeta", json.dumps(pack_mcmeta, indent=2, ensure_ascii=False))
            out_zip.writestr("texture.properties", "labPBR=1.3\n")
            out_zip.writestr("LICENSE.md", LICENSE_CONTENT)
            if self.icon_path and Path(self.icon_path).exists():
                try:
                    icon_img = Image.open(self.icon_path).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
                    icon_bio = io.BytesIO(); icon_img.save(icon_bio, format="PNG")
                    out_zip.writestr("pack.png", icon_bio.getvalue())
                except: pass

        if variant_count > 1:
            print("[DEBUG] 正在生成 Iris/OptiFine 变体配置文件...")
            tex_indices = " ".join([str(i) for i in range(variant_count)])
            props_content = f"textures={tex_indices}\n"
            
            for img_name, has_mc, mc_bytes in block_files:
                if has_mc and is_true_animation(mc_bytes): continue
                
                rel_path = img_name.replace("textures/", "optifine/random/").replace(".png", ".properties")
                if use_folder:
                    prop_path = pack_dir / rel_path
                    prop_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(prop_path, 'w', encoding='utf-8') as f:
                        f.write(props_content)
                else:
                    with zip_lock:
                        out_zip.writestr(rel_path, props_content)

        if not use_folder:
            out_zip.close()

        if use_folder:
            self.update_ui("正在调用 7z 引擎进行多核压缩...", 0, reset=True)
            if not Path(path_7z).exists():
                self.after(0, lambda: messagebox.showwarning("警告", f"未找到 7z.exe: {path_7z}\n请点击界面上的“浏览”按钮手动选择。"))
                raise Exception("7z 未找到")
            else:
                try:
                    cmd = [path_7z, "a", "-tzip", "-mx=5", "-mmt=on", "-bsp1", str(final_zip_path), ".\\*"]
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                    process = subprocess.Popen(
                        cmd, cwd=str(pack_dir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                        text=True, encoding='gbk', errors='ignore', startupinfo=startupinfo
                    )
                    
                    for line in iter(process.stdout.readline, ''):
                        match = re.search(r'(\d+)%', line)
                        if match:
                            percent = int(match.group(1)) / 100.0
                            self.update_ui(f"正在进行 7z 压缩: {match.group(1)}%", percent)
                            
                    process.wait()
                    if process.returncode != 0:
                        raise Exception("7z 返回了错误代码。")
                except Exception as e:
                    self.after(0, lambda err=str(e): messagebox.showwarning("警告", f"7z 压缩失败: {err}"))
                    raise e

        self.update_ui("生成成功！", 1.0)

    def generate_all(self, selected_versions, selected_res, pack_name, final_desc_json, out_dir,
                     mosaic_points, variant_count, compress_mode, path_7z, total_packs,
                     single_zip_path, multi_root):
        temp_dir = Path(tempfile.mkdtemp(prefix="mc_mosaic_"))
        self.active_temp_dir = temp_dir
        is_mirror = self.source_var.get() == "mirror"
        headers = {"User-Agent": "Mozilla/5.0"}

        jar_cache = {}
        pack_index = 0
        success_packs = 0
        failed = []

        try:
            for ver in selected_versions:
                if ver not in jar_cache:
                    self.progress_prefix = f"[{ver}]"
                    jar_cache[ver] = self.prepare_version(ver, is_mirror, headers, temp_dir)
                jar_path, pack_format = jar_cache[ver]

                for res_str in selected_res:
                    pack_index += 1
                    res = int(res_str.replace("X", ""))
                    display_name = f"{pack_name} [{ver}] [{res_str}]"
                    self.progress_prefix = f"[{pack_index}/{total_packs}]"

                    if total_packs == 1:
                        final_zip_path = single_zip_path
                    else:
                        ver_dir = multi_root / ver
                        ver_dir.mkdir(parents=True, exist_ok=True)
                        final_zip_path = ver_dir / f"{display_name}.zip"

                    work_dir = temp_dir / f"work_{ver}_{res_str}"
                    work_dir.mkdir(parents=True, exist_ok=True)

                    try:
                        self.update_ui(f"开始处理 {display_name}", 0, reset=True)
                        self.process_one_pack(
                            jar_path, pack_format, res, display_name, final_zip_path,
                            final_desc_json, mosaic_points, variant_count, compress_mode, path_7z, work_dir
                        )
                        success_packs += 1
                        print(f"[DEBUG] 完成: {final_zip_path}")
                    except Exception as e:
                        traceback.print_exc()
                        failed.append(f"{display_name}: {e}")
                        print(f"[ERROR] {display_name} 生成失败: {e}")
                    finally:
                        shutil.rmtree(work_dir, ignore_errors=True)

            self.progress_prefix = ""
            if failed:
                self.update_ui("部分完成", 1.0)
                msg = f"成功生成 {success_packs} / {total_packs} 个材质包。\n\n失败项：\n" + "\n".join(failed)
                self.after(0, lambda: messagebox.showwarning("部分完成", msg))
            else:
                self.update_ui("全部生成成功！", 1.0)
                target = str(single_zip_path) if total_packs == 1 else str(multi_root)
                self.after(0, lambda: messagebox.showinfo("完成", f"共生成 {total_packs} 个材质包。\n保存至: {target}"))

        except Exception as e:
            traceback.print_exc()
            self.progress_prefix = ""
            self.after(0, lambda err=str(e): messagebox.showerror("生成失败", f"发生错误:\n{err}\n\n详细堆栈已打印到控制台(CMD)。"))
            self.update_ui("生成失败", 0)
        finally:
            self.active_temp_dir = None
            shutil.rmtree(temp_dir, ignore_errors=True)
            self.progress_prefix = ""
            self.after(0, lambda: self.btn_start.configure(state="normal", text="🚀 生成镜面世界"))

    def start_generation(self):
        selected_versions = [v for v, var in self.version_vars.items() if var.get()]
        selected_res = [r for r, var in self.res_vars.items() if var.get()]

        if not selected_versions:
            messagebox.showwarning("警告", "请至少勾选一个版本！")
            return
        if not selected_res:
            messagebox.showwarning("警告", "请至少勾选一个分辨率！")
            return

        pack_name = self.name_entry.get().strip()
        if not pack_name:
            messagebox.showwarning("警告", "包名不能为空！")
            return

        out_dir = Path(self.path_var.get())

        json_desc_list = []
        merge_method = self.merge_var.get()
        for i, row in enumerate(self.desc_rows):
            text = row["text"].get()
            if not text.strip(): continue
            part = {"text": text}
            color_name = row["color"].get()
            if color_name == "自定义颜色": part["color"] = row["custom_hex"].get()
            elif color_name in MC_JSON_COLOR_MAP and MC_JSON_COLOR_MAP[color_name]: part["color"] = MC_JSON_COLOR_MAP[color_name]
            if row["italic"].get(): part["italic"] = True
            if row["bold"].get(): part["bold"] = True
            if row["under"].get(): part["underlined"] = True
            
            if i < len(self.desc_rows) - 1:
                if merge_method == "newline": part["text"] += "\n"
                elif merge_method == "space": part["text"] += " "
            json_desc_list.append(part)

        if not json_desc_list: final_desc_json = {"text": ""}
        elif len(json_desc_list) == 1: final_desc_json = json_desc_list[0]
        else: final_desc_json = {"text": "", "extra": json_desc_list}

        try: mosaic_points = max(1, int(self.variant_var.get().strip()))
        except: mosaic_points = 80
        try: variant_count = max(1, int(self.v_count_var.get().strip()))
        except: variant_count = 4

        compress_mode = self.compress_var.get()
        path_7z = self.path7z_var.get()

        total = len(selected_versions) * len(selected_res)

        single_zip_path = None
        multi_root = None
        if total == 1:
            ver = selected_versions[0]
            res_str = selected_res[0]
            single_zip_path = out_dir / f"{pack_name} [{ver}] [{res_str}].zip"
            if single_zip_path.exists() and not messagebox.askyesno("覆盖", f"{single_zip_path.name} 已存在，是否覆盖？"):
                return
        else:
            timestamp = time.strftime("%Y-%m-%d_%H%M%S")
            multi_root = out_dir / f"{pack_name}_{timestamp}"
            if multi_root.exists():
                multi_root = out_dir / f"{pack_name}_{timestamp}_{random.randint(1000, 9999)}"
            multi_root.mkdir(parents=True, exist_ok=True)

        self.btn_start.configure(state="disabled", text="正在生成...")
        threading.Thread(target=self.generate_all, args=(
            selected_versions, selected_res, pack_name, final_desc_json, out_dir,
            mosaic_points, variant_count, compress_mode, path_7z, total, single_zip_path, multi_root
        ), daemon=True).start()


if __name__ == "__main__":
    app = MirrorMosaicApp()
    app.mainloop()