import asyncio
import threading
import flet as ft
import requests
import database as db

SERVER_URL = "http://127.0.0.1:8000"
db.init_db()

def main(page: ft.Page):
    page.title = "SmartTask AI"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 460
    page.window.height = 820
    page.padding = 20

    current_user = None  # Хранит данные вошедшего пользователя

    def show_popup(dialog):
        if dialog not in page.overlay:
            page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def close_popup(dialog):
        dialog.open = False
        page.update()

    # ==========================================
    # 🔐 ЭКРАН АВТОРИЗАЦИИ И РЕГИСТРАЦИИ
    # ==========================================
    def render_auth_view():
        page.clean()
        
        is_signup = False  # Переключатель: Вход / Регистрация

        title_text = ft.Text("Welcome Back", size=26, weight=ft.FontWeight.BOLD)
        subtitle_text = ft.Text("Sign in to sync your AI tasks", size=13, color=ft.Colors.GREY_400)
        
        username_input = ft.TextField(
            label="Username",
            prefix_icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
            border_radius=12,
            filled=True,
            bgcolor=ft.Colors.GREY_900
        )
        password_input = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
            border_radius=12,
            filled=True,
            bgcolor=ft.Colors.GREY_900
        )
        
        error_banner = ft.Text("", color=ft.Colors.RED_400, size=12, weight=ft.FontWeight.W_500)
        action_btn = ft.Button("Sign In", bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, width=400, height=45)
        toggle_link = ft.TextButton("Don't have an account? Sign Up")

        def toggle_mode(e):
            nonlocal is_signup
            is_signup = not is_signup
            error_banner.value = ""
            if is_signup:
                title_text.value = "Create Account"
                subtitle_text.value = "Get 5 free AI Credits instantly"
                action_btn.text = "Sign Up"
                action_btn.bgcolor = ft.Colors.GREEN_600
                toggle_link.text = "Already have an account? Sign In"
            else:
                title_text.value = "Welcome Back"
                subtitle_text.value = "Sign in to sync your AI tasks"
                action_btn.text = "Sign In"
                action_btn.bgcolor = ft.Colors.BLUE_600
                toggle_link.text = "Don't have an account? Sign Up"
            page.update()

        def handle_auth(e):
            nonlocal current_user
            u = username_input.value.strip()
            p = password_input.value.strip()

            if not u or not p:
                error_banner.value = "Please fill in all fields!"
                page.update()
                return

            if is_signup:
                success, res = db.register_user(u, p)
                if success:
                    current_user = {"id": res, "username": u, "credits": 5, "is_pro": False}
                    render_dashboard()
                else:
                    error_banner.value = res
                    page.update()
            else:
                user = db.login_user(u, p)
                if user:
                    current_user = user
                    render_dashboard()
                else:
                    error_banner.value = "Invalid username or password!"
                    page.update()

        action_btn.on_click = handle_auth
        toggle_link.on_click = toggle_mode
        password_input.on_submit = handle_auth

        auth_card = ft.Container(
            content=ft.Column([
                ft.Row([ft.Text("⚡ SmartTask AI", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400)], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=10),
                title_text,
                subtitle_text,
                ft.Container(height=10),
                username_input,
                password_input,
                error_banner,
                ft.Container(height=10),
                action_btn,
                ft.Row([toggle_link], alignment=ft.MainAxisAlignment.CENTER)
            ], tight=True),
            padding=24,
            border_radius=16,
            bgcolor=ft.Colors.GREY_950,
            border=ft.Border.all(1, ft.Colors.GREY_800)
        )

        page.add(
            ft.Container(
                content=auth_card,
                alignment=ft.Alignment(0, 0),
                expand=True
            )
        )
        page.update()

    # ==========================================
    # 📱 ГЛАВНЫЙ ЭКРАН ПРИЛОЖЕНИЯ (DASHBOARD)
    # ==========================================
    def render_dashboard():
        page.clean()
        
        current_filter = "all"
        selected_energy = "medium"
        user_id = current_user["id"]

        # --- ШАПКА ---
        streak_badge = ft.Container(
            content=ft.Row([
                ft.Text("🔥", size=14),
                ft.Text("3 Days", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_400)
            ], tight=True),
            bgcolor=ft.Colors.GREY_900,
            padding=6,
            border_radius=8
        )

        prof = db.get_user_profile(user_id)
        credits_badge = ft.Container(
            content=ft.Text(
                "👑 PRO" if prof["is_pro"] else f"⚡ AI: {prof['credits']}/5",
                color=ft.Colors.GREEN_400 if prof["is_pro"] else ft.Colors.AMBER_400,
                weight=ft.FontWeight.BOLD,
                size=12
            ),
            bgcolor=ft.Colors.GREY_900,
            padding=6,
            border_radius=8
        )

        def logout(e):
            nonlocal current_user
            current_user = None
            render_auth_view()

        progress_text = ft.Text("0%", size=12, color=ft.Colors.GREY_400)
        progress_bar = ft.ProgressBar(value=0, color=ft.Colors.GREEN_ACCENT_400, bgcolor=ft.Colors.GREY_800, height=6)

        def update_progress():
            all_tasks = db.get_tasks(user_id, "all")
            if not all_tasks:
                progress_bar.value = 0
                progress_text.value = "No tasks today"
            else:
                done_count = sum(1 for t in all_tasks if t["is_done"])
                progress_bar.value = done_count / len(all_tasks)
                progress_text.value = f"{done_count}/{len(all_tasks)} ({int(progress_bar.value * 100)}%)"
            page.update()

        # --- ПОМОДОРО ТАЙМЕР ---
        def open_pomodoro(task_title):
            seconds_left = 25 * 60
            timer_running = False
            timer_text = ft.Text("25:00", size=44, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300)
            start_btn = ft.Button("Start", bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE)

            async def run_timer():
                nonlocal seconds_left, timer_running
                while timer_running and seconds_left > 0:
                    await asyncio.sleep(1)
                    if not timer_running:
                        break
                    seconds_left -= 1
                    mins, secs = divmod(seconds_left, 60)
                    timer_text.value = f"{mins:02d}:{secs:02d}"
                    page.update()
                if seconds_left == 0:
                    timer_text.value = "🎉 Done!"
                    timer_text.color = ft.Colors.GREEN_400
                    page.update()

            def toggle_timer(e):
                nonlocal timer_running
                timer_running = not timer_running
                if timer_running:
                    start_btn.text = "Pause"
                    start_btn.bgcolor = ft.Colors.ORANGE_600
                    page.run_task(run_timer)
                else:
                    start_btn.text = "Resume"
                    start_btn.bgcolor = ft.Colors.GREEN_600
                page.update()

            def reset_timer(e):
                nonlocal timer_running, seconds_left
                timer_running = False
                seconds_left = 25 * 60
                timer_text.value = "25:00"
                start_btn.text = "Start"
                start_btn.bgcolor = ft.Colors.GREEN_600
                page.update()

            def close_pomo(e):
                nonlocal timer_running
                timer_running = False
                close_popup(pomo_dialog)

            start_btn.on_click = toggle_timer

            pomo_dialog = ft.AlertDialog(
                title=ft.Text(f"⏱️ Focus: {task_title}", size=15, weight=ft.FontWeight.BOLD),
                content=ft.Column([
                    ft.Container(content=timer_text, alignment=ft.Alignment(0, 0), padding=10),
                    ft.Row([start_btn, ft.Button("Reset", on_click=reset_timer)], alignment=ft.MainAxisAlignment.CENTER)
                ], tight=True),
                actions=[ft.Button("Close", on_click=close_pomo)]
            )
            show_popup(pomo_dialog)

        # --- AI ПЛАН ДНЯ ---
        def open_ai_day_plan():
            p = db.get_user_profile(user_id)
            if not p["is_pro"] and p["credits"] <= 0:
                show_paywall()
                return

            tasks = db.get_tasks(user_id, "all")
            pending = [t["title"] for t in tasks if not t["is_done"]]
            
            plan_text = ft.Text(size=13, selectable=True)
            loading_spinner = ft.Row([
                ft.ProgressRing(width=20, height=20, stroke_width=2),
                ft.Text(" Gemini is structuring your day...", size=12, color=ft.Colors.AMBER_300)
            ])

            plan_dialog = ft.AlertDialog(
                title=ft.Text("🤖 AI Daily Schedule", weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=ft.Column([loading_spinner, plan_text], scroll=ft.ScrollMode.AUTO),
                    height=350,
                    width=380
                ),
                actions=[ft.Button("Got It!", on_click=lambda e: close_popup(plan_dialog))]
            )
            show_popup(plan_dialog)

            if not pending:
                loading_spinner.visible = False
                plan_text.value = "No active tasks! Add some tasks first."
                page.update()
                return

            if not p["is_pro"]:
                db.deduct_credit(user_id)
                credits_badge.content.value = f"⚡ AI: {p['credits'] - 1}/5"

            def fetch_plan():
                try:
                    res = requests.post(f"{SERVER_URL}/api/plan-day", json={"tasks": pending}, timeout=30)
                    if res.status_code == 200:
                        plan_text.value = res.json().get("plan", "Plan is empty")
                    else:
                        plan_text.value = f"Server error: {res.status_code}"
                except Exception as ex:
                    plan_text.value = f"Network error: {ex}"
                finally:
                    loading_spinner.visible = False
                    page.update()

            threading.Thread(target=fetch_plan, daemon=True).start()

        # --- СПИСОК ЗАДАЧ ---
        tasks_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        task_input = ft.TextField(hint_text="Add new task...", expand=True, border_radius=12, filled=True, bgcolor=ft.Colors.GREY_900)

        def set_task_energy(val):
            nonlocal selected_energy
            selected_energy = val
            for b in energy_chips.controls:
                b.bgcolor = ft.Colors.BLUE_600 if b.data == val else ft.Colors.GREY_900
            page.update()

        energy_chips = ft.Row([
            ft.Button("⚡ High Energy", data="high", bgcolor=ft.Colors.GREY_900, on_click=lambda e: set_task_energy("high")),
            ft.Button("☕ Medium", data="medium", bgcolor=ft.Colors.BLUE_600, on_click=lambda e: set_task_energy("medium")),
            ft.Button("🪫 Zombie Mode", data="zombie", bgcolor=ft.Colors.GREY_900, on_click=lambda e: set_task_energy("zombie")),
        ], spacing=6)

        def request_ai_decompose(task_id, title, subtasks_box, ai_btn):
            p = db.get_user_profile(user_id)
            if not p["is_pro"] and p["credits"] <= 0:
                show_paywall()
                return

            if not p["is_pro"]:
                db.deduct_credit(user_id)
                credits_badge.content.value = f"⚡ AI: {p['credits'] - 1}/5"

            ai_btn.disabled = True
            subtasks_box.controls.clear()
            subtasks_box.controls.append(ft.Row([ft.ProgressRing(width=16, height=16, stroke_width=2), ft.Text(" AI is breaking it down...", size=12, color=ft.Colors.AMBER_200)]))
            page.update()

            def fetch_decompose():
                subtasks = []
                try:
                    res = requests.post(f"{SERVER_URL}/api/decompose", json={"task_title": title}, timeout=20)
                    if res.status_code == 200:
                        subtasks = res.json().get("subtasks", [])
                    else:
                        subtasks = [f"Error: {res.status_code}"]
                except Exception as e:
                    subtasks = [f"Network Error: {e}"]

                db.save_subtasks(task_id, subtasks)
                render_subtasks(subtasks_box, subtasks)
                page.update()

            threading.Thread(target=fetch_decompose, daemon=True).start()

        def render_subtasks(container, subtasks):
            container.controls.clear()
            if subtasks:
                container.controls.append(ft.Divider(color=ft.Colors.GREY_800))
                container.controls.append(ft.Text("✨ AI Steps (15 min each):", size=12, color=ft.Colors.AMBER_300, weight=ft.FontWeight.BOLD))
                for st in subtasks:
                    container.controls.append(ft.Row([ft.Checkbox(scale=0.8), ft.Text(st, size=13, color=ft.Colors.GREY_300, expand=True)]))

        def create_task_card(task):
            subtasks_box = ft.Column(tight=True)
            render_subtasks(subtasks_box, task["subtasks"])

            energy_icons = {"high": "⚡", "medium": "☕", "zombie": "🪫"}
            energy_icon = energy_icons.get(task.get("energy", "medium"), "☕")

            ai_btn = ft.IconButton(icon=ft.Icons.AUTO_AWESOME_ROUNDED, icon_color=ft.Colors.AMBER_400, tooltip="AI: Break down task", disabled=bool(task["subtasks"]))
            ai_btn.on_click = lambda e, tid=task["id"], t=task["title"], sb=subtasks_box, b=ai_btn: request_ai_decompose(tid, t, sb, b)

            pomo_btn = ft.IconButton(icon=ft.Icons.TIMER_OUTLINED, icon_color=ft.Colors.ORANGE_300, tooltip="Focus Timer (25m)", on_click=lambda e, t=task["title"]: open_pomodoro(t))

            def on_check(e, tid=task["id"]):
                db.toggle_task(tid, e.control.value)
                update_progress()

            checkbox = ft.Checkbox(value=task["is_done"], on_change=on_check)
            del_btn = ft.IconButton(icon=ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=ft.Colors.GREY_600, icon_size=18, on_click=lambda e, tid=task["id"]: remove_task(tid))

            return ft.Container(
                content=ft.Column([
                    ft.Row([
                        checkbox,
                        ft.Text(f"{energy_icon} {task['title']}", size=15, weight=ft.FontWeight.W_500, expand=True, style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH if task["is_done"] else None)),
                        pomo_btn,
                        ai_btn,
                        del_btn
                    ]),
                    subtasks_box
                ], tight=True),
                bgcolor=ft.Colors.GREY_900,
                border_radius=12,
                padding=8,
                border=ft.Border.all(1, ft.Colors.GREY_800)
            )

        def load_all_tasks():
            tasks_column.controls.clear()
            for t in db.get_tasks(user_id, current_filter):
                tasks_column.controls.append(create_task_card(t))
            update_progress()

        def filter_click(val):
            nonlocal current_filter
            current_filter = val
            for b in filter_tabs.controls:
                b.style = ft.ButtonStyle(color=ft.Colors.AMBER_400 if b.data == val else ft.Colors.GREY_400)
            load_all_tasks()

        filter_tabs = ft.Row([
            ft.Button("All", data="all", on_click=lambda e: filter_click("all")),
            ft.Button("⚡ High", data="high", on_click=lambda e: filter_click("high")),
            ft.Button("🪫 Zombie", data="zombie", on_click=lambda e: filter_click("zombie")),
        ], spacing=4)

        def add_task_click(e):
            if not task_input.value.strip():
                return
            db.add_task(user_id, task_input.value.strip(), selected_energy)
            task_input.value = ""
            filter_click("all")
            page.overlay.append(ft.SnackBar(ft.Text("✅ Task added!"), open=True))
            page.update()

        def remove_task(task_id):
            db.delete_task(task_id)
            load_all_tasks()

        task_input.on_submit = add_task_click

        def show_paywall():
            def buy_pro_click(e):
                db.set_pro(user_id)
                close_popup(paywall)
                credits_badge.content.value = "👑 PRO"
                credits_badge.content.color = ft.Colors.GREEN_400
                page.update()

            paywall = ft.AlertDialog(
                title=ft.Text("👑 SmartTask PRO", weight=ft.FontWeight.BOLD),
                content=ft.Column([
                    ft.Text("You have used all free AI credits."),
                    ft.Divider(),
                    ft.Text("✨ Unlimited AI task breakdown"),
                    ft.Text("🤖 Unlimited AI Daily Schedule"),
                    ft.Container(height=10),
                    ft.Button("Upgrade to PRO — $3.99/mo", bgcolor=ft.Colors.AMBER_500, color=ft.Colors.BLACK, on_click=buy_pro_click)
                ], tight=True),
                actions=[ft.Button("Later", on_click=lambda e: close_popup(paywall))]
            )
            show_popup(paywall)

        # --- СБОРКА ИНТЕРФЕЙСА ---
        header = ft.Row([
            ft.Text(f"Hi, {current_user['username']} 👋", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.IconButton(icon=ft.Icons.AUTO_MODE_ROUNDED, icon_color=ft.Colors.AMBER_400, tooltip="AI Daily Schedule", on_click=lambda e: open_ai_day_plan()),
                streak_badge, 
                credits_badge,
                ft.IconButton(icon=ft.Icons.LOGOUT_ROUNDED, icon_color=ft.Colors.GREY_400, tooltip="Logout", on_click=logout)
            ], spacing=2)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        progress_section = ft.Column([
            ft.Row([ft.Text("Today's Progress", weight=ft.FontWeight.BOLD, size=13), progress_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            progress_bar
        ], spacing=4)

        page.add(
            header,
            ft.Container(height=2),
            progress_section,
            ft.Divider(color=ft.Colors.GREY_800, height=15),
            ft.Row([
                task_input,
                ft.IconButton(icon=ft.Icons.ADD_ROUNDED, bgcolor=ft.Colors.BLUE_600, icon_color=ft.Colors.WHITE, on_click=add_task_click)
            ]),
            ft.Text("Task Energy Level:", size=11, color=ft.Colors.GREY_400),
            energy_chips,
            ft.Container(height=5),
            filter_tabs,
            tasks_column
        )

        load_all_tasks()

    # Стартуем с экрана авторизации
    render_auth_view()

ft.run(main)