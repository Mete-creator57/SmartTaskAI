import asyncio
import threading
import random
import flet as ft
import requests
import database as db

SERVER_URL = "http://127.0.0.1:8000"
db.init_db()

# 🎨 ОФИЦИАЛЬНАЯ ПАЛИТРА GITHUB DARK
GH_BG = "#0d1117"         # Canvas Default
GH_SURFACE = "#161b22"    # Canvas Subtle
GH_BUTTON_SEC = "#21262d" # Secondary Button
GH_BORDER = "#30363d"     # Borders & Dividers
GH_GREEN = "#238636"      # Success Action
GH_MATRIX_GREEN = "#3fb950" # Matrix Green
GH_BLUE = "#58a6ff"       # Focus & Links
GH_TEXT = "#f0f6fc"       # Primary Text
GH_MUTED = "#8b949e"      # Muted Text

def main(page: ft.Page):
    page.title = "SmartTask AI"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = GH_BG
    page.window.width = 1220
    page.window.height = 820
    page.padding = 0

    # 🔤 ПОДКЛЮЧЕНИЕ INTER
    page.fonts = {
        "Inter": "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf"
    }
    page.theme = ft.Theme(font_family="Inter")

    current_user = None
    active_tab = "tasks"
    auth_matrix_running = False

    def show_popup(dialog):
        if dialog not in page.overlay:
            page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def close_popup(dialog):
        dialog.open = False
        page.update()

    # ==========================================
    # 🔐 AUTH VIEW (ONLY GOOGLE + DENSE MATRIX)
    # ==========================================
    def render_auth_view():
        nonlocal auth_matrix_running
        auth_matrix_running = True
        page.clean()
        is_signup = False

        title_text = ft.Text("Log in", size=28, weight=ft.FontWeight.BOLD, color=GH_TEXT)
        username_input = ft.TextField(hint_text="Username", border_radius=6, bgcolor=GH_SURFACE, border_color=GH_BORDER, filled=True, height=42, content_padding=12, color=GH_TEXT, cursor_color=GH_BLUE)
        password_input = ft.TextField(hint_text="Password", password=True, can_reveal_password=True, border_radius=6, bgcolor=GH_SURFACE, border_color=GH_BORDER, filled=True, height=42, content_padding=12, color=GH_TEXT, cursor_color=GH_BLUE)
        error_banner = ft.Text("", color=ft.Colors.RED_400, size=12, weight=ft.FontWeight.W_500)
        action_btn = ft.Button("Continue", bgcolor=GH_GREEN, color=ft.Colors.WHITE, width=380, height=44)
        
        toggle_link = ft.Text("Create an account", color=GH_BLUE, weight=ft.FontWeight.BOLD)
        toggle_row = ft.Row([
            ft.Text("Don't have an account?", size=13, color=GH_MUTED),
            ft.Container(content=toggle_link, on_click=lambda e: toggle_mode())
        ], spacing=4)

        def toggle_mode():
            nonlocal is_signup
            is_signup = not is_signup
            error_banner.value = ""
            if is_signup:
                title_text.value = "Create an account"
                action_btn.text = "Create Account"
                toggle_link.value = "Log in to existing"
            else:
                title_text.value = "Log in"
                action_btn.text = "Continue"
                toggle_link.value = "Create an account"
            page.update()

        def handle_auth(e):
            nonlocal current_user, auth_matrix_running
            u = username_input.value.strip()
            p = password_input.value.strip()
            if not u or not p:
                error_banner.value = "Please fill in all fields!"
                page.update()
                return

            if is_signup:
                success, res = db.register_user(u, p)
                if success:
                    auth_matrix_running = False
                    current_user = {"id": res, "username": u, "credits": 5, "is_pro": False, "focus_seconds": 0}
                    render_dashboard()
                else:
                    error_banner.value = res
                    page.update()
            else:
                user = db.login_user(u, p)
                if user:
                    auth_matrix_running = False
                    current_user = user
                    render_dashboard()
                else:
                    error_banner.value = "Invalid username or password!"
                    page.update()

        action_btn.on_click = handle_auth
        password_input.on_submit = handle_auth

        google_btn = ft.Container(
            content=ft.Text("Continue with Google", size=13, weight=ft.FontWeight.W_500, color=GH_TEXT, text_align=ft.TextAlign.CENTER),
            alignment=ft.Alignment(0, 0),
            width=380,
            height=42,
            border_radius=6,
            border=ft.Border.all(1, GH_BORDER),
            bgcolor=GH_BUTTON_SEC,
            on_click=lambda e: None
        )

        left_auth_pane = ft.Container(
            content=ft.Column([
                ft.Text("SmartTask", size=20, weight=ft.FontWeight.BOLD, color=GH_BLUE),
                ft.Container(height=8),
                title_text,
                ft.Container(height=12),
                google_btn,
                ft.Container(height=4),
                ft.Row([
                    ft.Divider(color=GH_BORDER, expand=True),
                    ft.Text("OR", size=11, color=GH_MUTED, weight=ft.FontWeight.BOLD),
                    ft.Divider(color=GH_BORDER, expand=True),
                ], width=380, spacing=10),
                ft.Container(height=4),
                ft.Text("Username", size=12, weight=ft.FontWeight.W_500, color=GH_MUTED),
                username_input,
                ft.Text("Password", size=12, weight=ft.FontWeight.W_500, color=GH_MUTED),
                password_input,
                error_banner,
                ft.Container(height=4),
                action_btn,
                ft.Container(height=4),
                toggle_row,
                ft.Container(height=12),
                ft.Text("256-bit encrypted local SQLite session", size=11, color=GH_MUTED)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.START, tight=True),
            width=480,
            padding=ft.Padding(50, 40, 50, 40),
            bgcolor=GH_BG,
            alignment=ft.Alignment(0, 0)
        )

        # 🟢 ПЛОТНЫЙ МАТРИЧНЫЙ ДОЖДЬ
        NUM_COLS = 42
        NUM_ROWS = 50
        matrix_columns = [
            ft.Text("", size=10, font_family="monospace", color="#1c4824", no_wrap=True)
            for _ in range(NUM_COLS)
        ]
        
        matrix_stream_row = ft.Row(
            controls=matrix_columns,
            spacing=4,
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            expand=True
        )

        async def run_matrix_rain():
            chars = ["0", "1", "0", "1", "1", "0", "x", "y", "z", "{", "}", ";", "<", ">", "/", "_", "$"]
            column_texts = [[" " for _ in range(NUM_ROWS)] for _ in range(NUM_COLS)]
            
            while auth_matrix_running:
                await asyncio.sleep(0.06)
                for col_idx in range(NUM_COLS):
                    column_texts[col_idx].pop(0)
                    column_texts[col_idx].append(random.choice(chars))
                    col_str = "\n".join(column_texts[col_idx])
                    matrix_columns[col_idx].value = col_str
                    matrix_columns[col_idx].color = random.choice([GH_MATRIX_GREEN, "#238636", "#164520", "#2ea043", "#0e2913", "#3fb950"])
                try:
                    page.update()
                except Exception:
                    break

        right_hero_pane = ft.Container(
            content=ft.Stack([
                ft.Container(content=matrix_stream_row, opacity=0.40, alignment=ft.Alignment(0, 0), padding=0, expand=True),
                ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=ft.Row([
                                ft.Text("Ask SmartTask AI to optimize your study & dev flow.", size=14, color=GH_TEXT, expand=True),
                                ft.Container(
                                    content=ft.Text("→", color=ft.Colors.WHITE, size=16, weight=ft.FontWeight.BOLD),
                                    bgcolor=GH_GREEN,
                                    border_radius=20,
                                    padding=ft.Padding(8, 4, 8, 4)
                                )
                            ], spacing=12),
                            bgcolor=GH_SURFACE,
                            border=ft.Border.all(1, GH_BORDER),
                            border_radius=10,
                            padding=ft.Padding(18, 12, 14, 12),
                            width=460,
                            shadow=ft.BoxShadow(spread_radius=2, blur_radius=30, color="#010409", offset=ft.Offset(0, 10))
                        )
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.Alignment(0, 0)
                )
            ]),
            expand=True,
            bgcolor="#05080a"
        )

        page.add(ft.Row([left_auth_pane, right_hero_pane], expand=True, spacing=0))
        page.update()
        page.run_task(run_matrix_rain)

    # ==========================================
    # 🖥️ DESKTOP DASHBOARD
    # ==========================================
    def render_dashboard():
        page.clean()
        user_id = current_user["id"]
        active_note_id = None
        selected_image_path = None

        # --- ПОМОДОРО ПЕРЕМЕННЫЕ ---
        pomo_seconds_left = 25 * 60
        pomo_running = False
        pomo_big_timer_text = ft.Text("25:00", size=84, weight=ft.FontWeight.BOLD, color=GH_TEXT)
        pomo_start_btn = ft.Button("Start Focus", bgcolor=GH_GREEN, color=ft.Colors.WHITE, height=50, width=220)

        main_content_slot = ft.Container(expand=True, padding=0)

        # 4 карточки статистики
        stat_estimated = ft.Text("0m", size=22, weight=ft.FontWeight.BOLD, color=GH_BLUE)
        stat_pending = ft.Text("0", size=22, weight=ft.FontWeight.BOLD, color="#f78166")
        stat_elapsed = ft.Text("0m", size=22, weight=ft.FontWeight.BOLD, color=GH_GREEN)
        stat_completed = ft.Text("0", size=22, weight=ft.FontWeight.BOLD, color=GH_BLUE)

        def build_stat_card(val_widget, label_text):
            return ft.Container(
                content=ft.Column([
                    val_widget,
                    ft.Text(label_text, size=11, color=GH_MUTED)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                expand=True,
                bgcolor=GH_SURFACE,
                padding=12,
                border_radius=6,
                border=ft.Border.all(1, GH_BORDER)
            )

        top_stats_banner = ft.Container(
            content=ft.Row([
                build_stat_card(stat_estimated, "Estimated Time"),
                build_stat_card(stat_pending, "Tasks to Complete"),
                build_stat_card(stat_elapsed, "Elapsed Focus"),
                build_stat_card(stat_completed, "Completed Tasks"),
            ], spacing=10),
            padding=ft.Padding.symmetric(vertical=8, horizontal=0)
        )

        def update_stats():
            tasks = db.get_tasks(user_id, "all")
            prof = db.get_user_profile(user_id)
            done = [t for t in tasks if t["is_done"]]
            pending = [t for t in tasks if not t["is_done"]]

            stat_pending.value = str(len(pending))
            stat_completed.value = str(len(done))
            stat_estimated.value = f"{len(pending) * 25}m"
            
            mins = prof["focus_seconds"] // 60
            hrs = mins // 60
            stat_elapsed.value = f"{hrs}h {mins % 60}m" if hrs > 0 else f"{mins}m"
            page.update()

        # VIEW 1: TASKS
        tasks_column = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
        task_input = ft.TextField(hint_text="Add a task, press [Enter] to save...", expand=True, border_radius=6, filled=True, bgcolor=GH_SURFACE, border_color=GH_BORDER, color=GH_TEXT, cursor_color=GH_BLUE)

        def request_ai_decompose(task_id, title, subtasks_box, ai_btn):
            p = db.get_user_profile(user_id)
            if not p["is_pro"] and p["credits"] <= 0:
                show_paywall()
                return
            if not p["is_pro"]:
                db.deduct_credit(user_id)
                credits_label.value = f"AI Credits: {p['credits'] - 1}/5"

            ai_btn.disabled = True
            subtasks_box.controls.clear()
            subtasks_box.controls.append(ft.Text("Decomposing task with Gemini...", size=12, color=GH_MUTED))
            page.update()

            def fetch():
                subtasks = []
                try:
                    res = requests.post(f"{SERVER_URL}/api/decompose", json={"task_title": title}, timeout=20)
                    if res.status_code == 200:
                        subtasks = res.json().get("subtasks", [])
                    else:
                        subtasks = [f"Error: {res.status_code}"]
                except Exception as ex:
                    subtasks = [f"Network Error: {ex}"]

                db.save_subtasks(task_id, subtasks)
                render_subtasks(subtasks_box, subtasks)
                page.update()

            threading.Thread(target=fetch, daemon=True).start()

        def render_subtasks(container, subtasks):
            container.controls.clear()
            if subtasks:
                container.controls.append(ft.Divider(color=GH_BORDER))
                container.controls.append(ft.Text("AI Steps (15m each):", size=11, color=GH_BLUE, weight=ft.FontWeight.BOLD))
                for st in subtasks:
                    container.controls.append(ft.Row([ft.Checkbox(scale=0.8, active_color=GH_GREEN), ft.Text(st, size=13, color=GH_TEXT, expand=True)]))

        def create_task_card(task):
            subtasks_box = ft.Column(tight=True)
            render_subtasks(subtasks_box, task["subtasks"])

            ai_btn = ft.Button("AI Steps", bgcolor=GH_BUTTON_SEC, color=GH_BLUE, height=28, disabled=bool(task["subtasks"]))
            ai_btn.on_click = lambda e, tid=task["id"], t=task["title"], sb=subtasks_box, b=ai_btn: request_ai_decompose(tid, t, sb, b)

            def on_check(e, tid=task["id"]):
                db.toggle_task(tid, e.control.value)
                update_stats()
                load_tasks_view()

            checkbox = ft.Checkbox(value=task["is_done"], on_change=on_check, active_color=GH_GREEN)
            del_btn = ft.Button("Delete", bgcolor=GH_BUTTON_SEC, color=GH_MUTED, height=28, on_click=lambda e, tid=task["id"]: delete_task_click(tid))

            return ft.Container(
                content=ft.Column([
                    ft.Row([
                        checkbox,
                        ft.Text(task["title"], size=14, weight=ft.FontWeight.W_500, color=GH_TEXT, expand=True, style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH if task["is_done"] else None)),
                        ai_btn,
                        del_btn
                    ]),
                    subtasks_box
                ], tight=True),
                bgcolor=GH_SURFACE,
                border_radius=6,
                padding=8,
                border=ft.Border.all(1, GH_BORDER)
            )

        def load_tasks_view():
            tasks_column.controls.clear()
            tasks = db.get_tasks(user_id, "all" if active_tab == "tasks" else "completed")
            for t in tasks:
                tasks_column.controls.append(create_task_card(t))
            update_stats()
            page.update()

        def add_task_click(e):
            if not task_input.value.strip(): return
            db.add_task(user_id, task_input.value.strip(), "medium")
            task_input.value = ""
            load_tasks_view()

        def delete_task_click(tid):
            db.delete_task(tid)
            load_tasks_view()

        task_input.on_submit = add_task_click

        tasks_view_content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Tasks", size=22, weight=ft.FontWeight.BOLD, color=GH_TEXT),
                    ft.Button("AI Daily Plan", bgcolor=GH_GREEN, color=ft.Colors.WHITE, on_click=lambda e: open_ai_day_plan())
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                top_stats_banner,
                ft.Row([
                    task_input,
                    ft.Button("Add Task", bgcolor=GH_GREEN, color=ft.Colors.WHITE, height=42, on_click=add_task_click)
                ]),
                ft.Container(height=4),
                tasks_column
            ], expand=True),
            padding=24
        )

        def open_ai_day_plan():
            p = db.get_user_profile(user_id)
            if not p["is_pro"] and p["credits"] <= 0:
                show_paywall()
                return
            tasks = db.get_tasks(user_id, "all")
            pending = [t["title"] for t in tasks if not t["is_done"]]
            
            plan_text = ft.Text(size=13, selectable=True, color=GH_TEXT)
            spinner_text = ft.Text("Gemini is structuring your day...", size=12, color=GH_MUTED)

            dlg = ft.AlertDialog(
                title=ft.Text("AI Daily Schedule", weight=ft.FontWeight.BOLD, color=GH_TEXT),
                content=ft.Container(content=ft.Column([spinner_text, plan_text], scroll=ft.ScrollMode.AUTO), height=380, width=440),
                actions=[ft.Button("Done", on_click=lambda e: close_popup(dlg))]
            )
            show_popup(dlg)

            if not pending:
                spinner_text.value = "No active tasks! Add some tasks first."
                page.update()
                return

            if not p["is_pro"]:
                db.deduct_credit(user_id)
                credits_label.value = f"AI Credits: {p['credits'] - 1}/5"

            def fetch():
                try:
                    res = requests.post(f"{SERVER_URL}/api/plan-day", json={"tasks": pending}, timeout=30)
                    plan_text.value = res.json().get("plan", "No plan") if res.status_code == 200 else f"Error: {res.status_code}"
                except Exception as ex:
                    plan_text.value = f"Network Error: {ex}"
                finally:
                    spinner_text.visible = False
                    page.update()

            threading.Thread(target=fetch, daemon=True).start()

        # ==========================================
        # VIEW 2: BIG POMODORO (WITH PAUSE & RESUME)
        # ==========================================
        async def run_big_pomodoro():
            nonlocal pomo_seconds_left, pomo_running
            while pomo_running and pomo_seconds_left > 0:
                await asyncio.sleep(1)
                if not pomo_running: break
                pomo_seconds_left -= 1
                db.add_focus_time(user_id, 1)
                m, s = divmod(pomo_seconds_left, 60)
                pomo_big_timer_text.value = f"{m:02d}:{s:02d}"
                page.update()
            if pomo_seconds_left == 0:
                pomo_big_timer_text.value = "Done!"
                pomo_big_timer_text.color = GH_GREEN
                pomo_start_btn.text = "Start Focus"
                pomo_start_btn.bgcolor = GH_GREEN
                page.update()

        # Умный тумблер: Старт ↔ Пауза ↔ Продолжить
        def toggle_big_pomodoro(e):
            nonlocal pomo_running
            pomo_running = not pomo_running
            if pomo_running:
                pomo_start_btn.text = "Pause Focus"
                pomo_start_btn.bgcolor = GH_BUTTON_SEC
                page.run_task(run_big_pomodoro)
            else:
                pomo_start_btn.text = "Resume Focus"
                pomo_start_btn.bgcolor = GH_GREEN
            page.update()

        pomo_start_btn.on_click = toggle_big_pomodoro

        def reset_big_pomodoro(e=None):
            nonlocal pomo_running, pomo_seconds_left
            pomo_running = False
            pomo_seconds_left = 25 * 60
            pomo_big_timer_text.value = "25:00"
            pomo_start_btn.text = "Start Focus"
            pomo_start_btn.bgcolor = GH_GREEN
            page.update()

        pomodoro_view_content = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Container(height=20),
                        ft.Container(
                            content=ft.Column([
                                pomo_big_timer_text,
                                ft.Text("25-minute Focus Session", size=13, color=GH_MUTED)
                            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            width=320,
                            height=320,
                            border_radius=160,
                            bgcolor=GH_SURFACE,
                            border=ft.Border.all(2, GH_BORDER),
                            alignment=ft.Alignment(0, 0)
                        ),
                        ft.Container(height=20),
                        pomo_start_btn,
                        ft.Button("Reset to 25:00", bgcolor=GH_BUTTON_SEC, color=GH_MUTED, on_click=reset_big_pomodoro)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    expand=2
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Today's Focus Summary", size=16, weight=ft.FontWeight.BOLD, color=GH_TEXT),
                        ft.Divider(color=GH_BORDER),
                        top_stats_banner,
                        ft.Text("Deep Focus:\n25 minutes of undistracted work enhances retention and output.", size=13, color=GH_MUTED)
                    ], tight=True),
                    expand=1,
                    bgcolor=GH_SURFACE,
                    padding=20,
                    border_radius=6,
                    border=ft.Border.all(1, GH_BORDER)
                )
            ], expand=True),
            padding=24
        )

        # ==========================================
        # 📊 VIEW 3: NATIVE GITHUB-STYLE ANALYTICS
        # ==========================================
        def build_bar(day_name, height_val, minutes_str):
            return ft.Column([
                ft.Text(minutes_str, size=10, color=GH_MUTED),
                ft.Container(
                    width=32,
                    height=height_val,
                    bgcolor=GH_GREEN,
                    border_radius=4,
                    tooltip=f"{day_name}: {minutes_str}"
                ),
                ft.Text(day_name, size=11, color=GH_TEXT, weight=ft.FontWeight.W_500)
            ], alignment=ft.MainAxisAlignment.END, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6)

        weekly_bars = ft.Row([
            build_bar("Mon", 45, "45m"),
            build_bar("Tue", 90, "90m"),
            build_bar("Wed", 30, "30m"),
            build_bar("Thu", 110, "1h 50m"),
            build_bar("Fri", 140, "2h 20m"),
            build_bar("Sat", 60, "1h"),
            build_bar("Sun", 80, "1h 20m"),
        ], alignment=ft.MainAxisAlignment.SPACE_EVENLY, expand=True)

        activity_boxes = []
        heat_colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
        for _ in range(60):
            activity_boxes.append(
                ft.Container(width=14, height=14, bgcolor=random.choice(heat_colors), border_radius=2)
            )

        activity_grid = ft.Row(activity_boxes[:20], spacing=4)
        activity_grid_2 = ft.Row(activity_boxes[20:40], spacing=4)
        activity_grid_3 = ft.Row(activity_boxes[40:60], spacing=4)

        analytics_view_content = ft.Container(
            content=ft.Column([
                ft.Text("Productivity & Focus Analytics", size=22, weight=ft.FontWeight.BOLD, color=GH_TEXT),
                ft.Container(height=4),
                top_stats_banner,
                ft.Container(height=12),
                ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Weekly Focus Distribution", size=14, weight=ft.FontWeight.BOLD, color=GH_TEXT),
                            ft.Divider(color=GH_BORDER),
                            ft.Container(content=weekly_bars, height=180, padding=10),
                        ]),
                        bgcolor=GH_SURFACE,
                        padding=18,
                        border_radius=8,
                        border=ft.Border.all(1, GH_BORDER),
                        expand=2
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Activity Streak & Heatmap", size=14, weight=ft.FontWeight.BOLD, color=GH_TEXT),
                            ft.Divider(color=GH_BORDER),
                            ft.Text("Consistent daily work blocks create compounding results.", size=12, color=GH_MUTED),
                            ft.Container(height=8),
                            activity_grid,
                            activity_grid_2,
                            activity_grid_3,
                            ft.Container(height=8),
                            ft.Row([
                                ft.Text("Less", size=10, color=GH_MUTED),
                                ft.Container(width=10, height=10, bgcolor="#161b22", border_radius=2),
                                ft.Container(width=10, height=10, bgcolor="#0e4429", border_radius=2),
                                ft.Container(width=10, height=10, bgcolor="#26a641", border_radius=2),
                                ft.Container(width=10, height=10, bgcolor="#39d353", border_radius=2),
                                ft.Text("More", size=10, color=GH_MUTED),
                            ], spacing=4)
                        ]),
                        bgcolor=GH_SURFACE,
                        padding=18,
                        border_radius=8,
                        border=ft.Border.all(1, GH_BORDER),
                        expand=1
                    )
                ], expand=True)
            ], expand=True),
            padding=24
        )

        # VIEW 4: OBSIDIAN NOTES
        notes_list_column = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        breadcrumb_title = ft.Text("Notes", size=12, color=GH_MUTED)

        editor_title = ft.TextField(
            hint_text="Untitled Note",
            text_size=26,
            text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, size=26),
            border_color=ft.Colors.TRANSPARENT,
            bgcolor=ft.Colors.TRANSPARENT,
            color=GH_TEXT,
            content_padding=0
        )

        status_bar_text = ft.Text("0 words  •  0 characters", size=11, color=GH_MUTED)

        def update_word_count(e=None):
            text = editor_content.value or ""
            chars = len(text)
            words = len([w for w in text.split() if w.strip()])
            status_bar_text.value = f"{words} words  •  {chars} characters"
            breadcrumb_title.value = f"Notes / {editor_title.value or 'Untitled'}"
            page.update()

        editor_content = ft.TextField(
            hint_text="Start writing your thoughts, code snippets, or study notes here...",
            multiline=True,
            min_lines=18,
            max_lines=32,
            text_size=15,
            border_color=ft.Colors.TRANSPARENT,
            bgcolor=ft.Colors.TRANSPARENT,
            color=GH_TEXT,
            content_padding=0,
            expand=True,
            on_change=update_word_count
        )
        editor_title.on_change = update_word_count
        editor_image_preview = ft.Container(visible=False)

        async def pick_note_image(e):
            nonlocal selected_image_path
            try:
                files = await ft.FilePicker().pick_files(allow_multiple=False)
                if files and len(files) > 0:
                    selected_image_path = files[0].path
                    editor_image_preview.content = ft.Image(src=selected_image_path, height=180, fit="cover", border_radius=6)
                    editor_image_preview.visible = True
                    attach_btn.text = f"Photo: {files[0].name[:15]}..."
                    page.update()
            except Exception as ex:
                print("Pick image error:", ex)

        attach_btn = ft.Button("Attach Image", bgcolor=GH_BUTTON_SEC, color=GH_TEXT, on_click=pick_note_image)

        def save_current_note(e):
            nonlocal active_note_id, selected_image_path
            t = editor_title.value.strip() or "Untitled Note"
            c = editor_content.value
            if active_note_id is None:
                active_note_id = db.add_note(user_id, t, c, selected_image_path)
            else:
                db.update_note(active_note_id, t, c, selected_image_path)
            
            page.overlay.append(ft.SnackBar(ft.Text("Note saved"), open=True))
            load_obsidian_notes_list()
            page.update()

        def create_new_note(e):
            nonlocal active_note_id, selected_image_path
            active_note_id = None
            selected_image_path = None
            editor_title.value = ""
            editor_content.value = ""
            editor_image_preview.visible = False
            attach_btn.text = "Attach Image"
            update_word_count()
            load_obsidian_notes_list()
            page.update()

        def open_note(note):
            nonlocal active_note_id, selected_image_path
            active_note_id = note["id"]
            selected_image_path = note["image_path"]
            editor_title.value = note["title"]
            editor_content.value = note["content"]
            
            if selected_image_path:
                editor_image_preview.content = ft.Image(src=selected_image_path, height=180, fit="cover", border_radius=6)
                editor_image_preview.visible = True
                attach_btn.text = "Change Image"
            else:
                editor_image_preview.visible = False
                attach_btn.text = "Attach Image"
            
            update_word_count()
            load_obsidian_notes_list()
            page.update()

        def delete_current_note(e):
            nonlocal active_note_id
            if active_note_id:
                db.delete_note(active_note_id)
                create_new_note(None)

        def load_obsidian_notes_list():
            notes_list_column.controls.clear()
            notes = db.get_notes(user_id)
            if not notes:
                notes_list_column.controls.append(ft.Text("No notes. Click '+ New' to create.", size=12, color=GH_MUTED))
            for n in notes:
                is_selected = (n["id"] == active_note_id)
                item = ft.Container(
                    content=ft.Text(n["title"], size=13, weight=ft.FontWeight.W_500 if is_selected else ft.FontWeight.NORMAL, color=GH_BLUE if is_selected else GH_TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    padding=ft.Padding(8, 6, 8, 6),
                    border_radius=4,
                    bgcolor=GH_SURFACE if is_selected else ft.Colors.TRANSPARENT,
                    border=ft.Border.all(1, GH_BLUE if is_selected else ft.Colors.TRANSPARENT),
                    on_click=lambda e, note=n: open_note(note)
                )
                notes_list_column.controls.append(item)

        notes_sidebar = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Files", size=13, weight=ft.FontWeight.BOLD, color=GH_TEXT),
                    ft.Button("+ New", bgcolor=GH_BUTTON_SEC, color=GH_BLUE, height=26, on_click=create_new_note)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(color=GH_BORDER, height=8),
                notes_list_column
            ]),
            width=200,
            bgcolor=GH_SURFACE,
            padding=12,
            border=ft.Border(right=ft.BorderSide(1, GH_BORDER))
        )

        notes_canvas = ft.Container(
            content=ft.Column([
                ft.Row([
                    breadcrumb_title,
                    ft.Row([
                        attach_btn,
                        ft.Button("Save", bgcolor=GH_GREEN, color=ft.Colors.WHITE, on_click=save_current_note),
                        ft.Button("Delete", bgcolor=GH_BUTTON_SEC, color=GH_MUTED, on_click=delete_current_note)
                    ], spacing=6)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(color=GH_BORDER, height=8),
                editor_title,
                editor_image_preview,
                editor_content,
                ft.Row([
                    ft.Text("Markdown Canvas", size=11, color=GH_MUTED),
                    status_bar_text
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], expand=True, spacing=8),
            expand=True,
            padding=ft.Padding(24, 16, 24, 12)
        )

        obsidian_notes_view = ft.Row([
            notes_sidebar,
            notes_canvas
        ], expand=True, spacing=0)

        # ==========================================
        # 📑 TABS SWITCHING
        # ==========================================
        def switch_view(tab_name):
            nonlocal active_tab
            active_tab = tab_name
            for item in nav_items:
                is_active = (item.data == tab_name)
                item.bgcolor = GH_BUTTON_SEC if is_active else ft.Colors.TRANSPARENT
                item.border = ft.Border.all(1, GH_BLUE if is_active else ft.Colors.TRANSPARENT)
            
            if tab_name == "tasks" or tab_name == "completed":
                main_content_slot.content = tasks_view_content
                load_tasks_view()
            elif tab_name == "pomodoro":
                main_content_slot.content = pomodoro_view_content
                update_stats()
            elif tab_name == "analytics":
                main_content_slot.content = analytics_view_content
                update_stats()
            elif tab_name == "notes":
                main_content_slot.content = obsidian_notes_view
                load_obsidian_notes_list()
                if not active_note_id:
                    all_n = db.get_notes(user_id)
                    if all_n: open_note(all_n[0])
            page.update()

        # ==========================================
        # 🚪 SIDEBAR
        # ==========================================
        prof = db.get_user_profile(user_id)
        credits_label = ft.Text(f"Credits: {prof['credits']}/5", color=GH_BLUE, size=11)

        def make_nav_item(title, tab_name, is_default=False):
            return ft.Container(
                content=ft.Text(title, size=13, weight=ft.FontWeight.W_500, color=GH_TEXT),
                data=tab_name,
                padding=ft.Padding(12, 8, 12, 8),
                border_radius=6,
                bgcolor=GH_BUTTON_SEC if is_default else ft.Colors.TRANSPARENT,
                border=ft.Border.all(1, GH_BLUE if is_default else ft.Colors.TRANSPARENT),
                on_click=lambda e, t=tab_name: switch_view(t)
            )

        nav_items = [
            make_nav_item("All Tasks", "tasks", is_default=True),
            make_nav_item("Focus Pomodoro", "pomodoro"),
            make_nav_item("Analytics & Charts", "analytics"),
            make_nav_item("Notes & Summaries", "notes"),
            make_nav_item("Completed", "completed"),
        ]

        sidebar = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(current_user["username"], weight=ft.FontWeight.BOLD, size=14, color=GH_TEXT),
                            credits_label
                        ], spacing=1, expand=True),
                        ft.Button("Logout", bgcolor=GH_BUTTON_SEC, color=GH_MUTED, height=26, on_click=lambda e: render_auth_view())
                    ]),
                    padding=ft.Padding(0, 0, 0, 8)
                ),
                ft.Divider(color=GH_BORDER),
                ft.Container(height=2),
                ft.Column(nav_items, spacing=4),
                ft.Container(expand=True),
                ft.Button("Upgrade PRO", bgcolor=GH_GREEN, color=ft.Colors.WHITE, height=36, on_click=lambda e: show_paywall())
            ]),
            width=220,
            bgcolor=GH_SURFACE,
            padding=16,
            border=ft.Border(right=ft.BorderSide(1, GH_BORDER))
        )

        def show_paywall():
            def buy(e):
                db.set_pro(user_id)
                close_popup(paywall)
                credits_label.value = "PRO Plan"
                page.update()

            paywall = ft.AlertDialog(
                title=ft.Text("Upgrade to SmartTask PRO", weight=ft.FontWeight.BOLD, color=GH_TEXT),
                content=ft.Column([
                    ft.Text("Unlock full productivity power:"),
                    ft.Text("• Unlimited AI task breakdowns"),
                    ft.Text("• Unlimited AI Day Planning"),
                    ft.Text("• Unlimited Note Attachments"),
                    ft.Button("Get PRO for $3.99/mo", bgcolor=GH_GREEN, color=ft.Colors.WHITE, on_click=buy)
                ], tight=True),
                actions=[ft.Button("Later", on_click=lambda e: close_popup(paywall))]
            )
            show_popup(paywall)

        main_content_slot.content = tasks_view_content
        page.add(ft.Row([sidebar, main_content_slot], expand=True, spacing=0))
        load_tasks_view()

    render_auth_view()

ft.run(main)