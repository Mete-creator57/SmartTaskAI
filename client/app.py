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
    page.window.height = 800
    page.padding = 16

    profile = db.get_profile()
    current_filter = "all"
    selected_energy = "medium"

    # Универсальная функция показа любого модального окна через overlay
    def show_popup(dialog):
        if dialog not in page.overlay:
            page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def close_popup(dialog):
        dialog.open = False
        page.update()

    # --- ШАПКА ---
    streak_badge = ft.Container(
        content=ft.Row([
            ft.Text("🔥", size=15),
            ft.Text("3 дня", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_400)
        ], tight=True),
        bgcolor=ft.Colors.GREY_900,
        padding=6,
        border_radius=8
    )

    credits_badge = ft.Container(
        content=ft.Text(
            "👑 PRO" if profile["is_pro"] else f"⚡ AI: {profile['credits']}/5",
            color=ft.Colors.GREEN_400 if profile["is_pro"] else ft.Colors.AMBER_400,
            weight=ft.FontWeight.BOLD,
            size=12
        ),
        bgcolor=ft.Colors.GREY_900,
        padding=6,
        border_radius=8
    )

    # Прогресс
    progress_text = ft.Text("0%", size=12, color=ft.Colors.GREY_400)
    progress_bar = ft.ProgressBar(value=0, color=ft.Colors.GREEN_ACCENT_400, bgcolor=ft.Colors.GREY_800, height=6)

    def update_progress():
        all_tasks = db.get_tasks("all")
        if not all_tasks:
            progress_bar.value = 0
            progress_text.value = "0%"
        else:
            done_count = sum(1 for t in all_tasks if t["is_done"])
            progress_bar.value = done_count / len(all_tasks)
            progress_text.value = f"{done_count}/{len(all_tasks)} ({int(progress_bar.value * 100)}%)"
        page.update()

    # --- МОДАЛКА 1: ПОМОДОРО ТАЙМЕР ---
    def open_pomodoro(task_title):
        seconds_left = 25 * 60
        timer_running = False
        timer_text = ft.Text("25:00", size=44, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300)
        start_btn = ft.Button("Старт", bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE)

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
                timer_text.value = "🎉 Готово!"
                timer_text.color = ft.Colors.GREEN_400
                page.update()

        def toggle_timer(e):
            nonlocal timer_running
            timer_running = not timer_running
            if timer_running:
                start_btn.text = "Пауза"
                start_btn.bgcolor = ft.Colors.ORANGE_600
                page.run_task(run_timer)
            else:
                start_btn.text = "Продолжить"
                start_btn.bgcolor = ft.Colors.GREEN_600
            page.update()

        def reset_timer(e):
            nonlocal timer_running, seconds_left
            timer_running = False
            seconds_left = 25 * 60
            timer_text.value = "25:00"
            start_btn.text = "Старт"
            start_btn.bgcolor = ft.Colors.GREEN_600
            page.update()

        start_btn.on_click = toggle_timer

        pomo_dialog = ft.AlertDialog(
            title=ft.Text(f"⏱️ Фокус: {task_title}", size=15, weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Container(content=timer_text, alignment=ft.Alignment(0, 0), padding=10),
                ft.Row([
                    start_btn,
                    ft.Button("Сброс", on_click=reset_timer)
                ], alignment=ft.MainAxisAlignment.CENTER)
            ], tight=True),
            actions=[
                ft.Button("Закрыть", on_click=lambda e: close_popup(pomo_dialog))
            ]
        )
        show_popup(pomo_dialog)

    # --- МОДАЛКА 2: AI ПЛАН ДНЯ ---
    def open_ai_day_plan():
        curr_prof = db.get_profile()
        if not curr_prof["is_pro"] and curr_prof["credits"] <= 0:
            show_paywall()
            return

        tasks = db.get_tasks("all")
        pending = [t["title"] for t in tasks if not t["is_done"]]
        
        plan_text = ft.Text(size=13, selectable=True)
        loading_spinner = ft.Row([
            ft.ProgressRing(width=20, height=20, stroke_width=2),
            ft.Text(" Gemini составляет расписание дня...", size=12, color=ft.Colors.AMBER_300)
        ])

        plan_dialog = ft.AlertDialog(
            title=ft.Text("🤖 AI План дня", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([loading_spinner, plan_text], scroll=ft.ScrollMode.AUTO),
                height=350,
                width=380
            ),
            actions=[
                ft.Button("Закрыть", on_click=lambda e: close_popup(plan_dialog))
            ]
        )

        show_popup(plan_dialog)

        if not pending:
            loading_spinner.visible = False
            plan_text.value = "У вас нет невыполненных задач! Добавьте дела в список."
            page.update()
            return

        if not curr_prof["is_pro"]:
            db.deduct_credit()
            credits_badge.content.value = f"⚡ AI: {curr_prof['credits'] - 1}/5"

        def fetch_plan():
            try:
                res = requests.post(f"{SERVER_URL}/api/plan-day", json={"tasks": pending}, timeout=30)
                if res.status_code == 200:
                    plan_text.value = res.json().get("plan", "План пуст")
                else:
                    plan_text.value = f"Ошибка сервера: {res.status_code}"
            except Exception as ex:
                plan_text.value = f"Ошибка связи с сервером: {ex}"
            finally:
                loading_spinner.visible = False
                page.update()

        threading.Thread(target=fetch_plan, daemon=True).start()

    # --- СПИСОК ЗАДАЧ ---
    tasks_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    task_input = ft.TextField(hint_text="Новая задача...", expand=True, border_radius=12, filled=True, bgcolor=ft.Colors.GREY_900)

    def set_task_energy(energy_val):
        nonlocal selected_energy
        selected_energy = energy_val
        for btn in energy_chips.controls:
            btn.bgcolor = ft.Colors.BLUE_600 if btn.data == energy_val else ft.Colors.GREY_900
        page.update()

    energy_chips = ft.Row([
        ft.Button("⚡ Сил много", data="high", bgcolor=ft.Colors.GREY_900, on_click=lambda e: set_task_energy("high")),
        ft.Button("☕ Норм", data="medium", bgcolor=ft.Colors.BLUE_600, on_click=lambda e: set_task_energy("medium")),
        ft.Button("🪫 Зомби", data="zombie", bgcolor=ft.Colors.GREY_900, on_click=lambda e: set_task_energy("zombie")),
    ], spacing=6)

    def request_ai_decompose(task_id, title, subtasks_box, ai_btn):
        curr_prof = db.get_profile()
        if not curr_prof["is_pro"] and curr_prof["credits"] <= 0:
            show_paywall()
            return

        if not curr_prof["is_pro"]:
            db.deduct_credit()
            credits_badge.content.value = f"⚡ AI: {curr_prof['credits'] - 1}/5"

        ai_btn.disabled = True
        subtasks_box.controls.clear()
        subtasks_box.controls.append(ft.Row([ft.ProgressRing(width=16, height=16, stroke_width=2), ft.Text(" ИИ думает...", size=12, color=ft.Colors.AMBER_200)]))
        page.update()

        def fetch_decompose():
            subtasks = []
            try:
                res = requests.post(f"{SERVER_URL}/api/decompose", json={"task_title": title}, timeout=20)
                if res.status_code == 200:
                    subtasks = res.json().get("subtasks", [])
                else:
                    subtasks = [f"Ошибка: {res.status_code}"]
            except Exception as e:
                subtasks = [f"Ошибка сети: {e}"]

            db.save_subtasks(task_id, subtasks)
            render_subtasks(subtasks_box, subtasks)
            page.update()

        threading.Thread(target=fetch_decompose, daemon=True).start()

    def render_subtasks(container, subtasks):
        container.controls.clear()
        if subtasks:
            container.controls.append(ft.Divider(color=ft.Colors.GREY_800))
            container.controls.append(ft.Text("✨ AI Шаги (по 15 мин):", size=12, color=ft.Colors.AMBER_300, weight=ft.FontWeight.BOLD))
            for st in subtasks:
                container.controls.append(ft.Row([ft.Checkbox(scale=0.8), ft.Text(st, size=13, color=ft.Colors.GREY_300, expand=True)]))

    def create_task_card(task):
        subtasks_box = ft.Column(tight=True)
        render_subtasks(subtasks_box, task["subtasks"])

        energy_icons = {"high": "⚡", "medium": "☕", "zombie": "🪫"}
        energy_icon = energy_icons.get(task.get("energy", "medium"), "☕")

        ai_btn = ft.IconButton(
            icon=ft.Icons.AUTO_AWESOME_ROUNDED,
            icon_color=ft.Colors.AMBER_400,
            tooltip="AI: Разбить задачу",
            disabled=bool(task["subtasks"])
        )
        ai_btn.on_click = lambda e, tid=task["id"], t=task["title"], sb=subtasks_box, b=ai_btn: request_ai_decompose(tid, t, sb, b)

        pomo_btn = ft.IconButton(
            icon=ft.Icons.TIMER_OUTLINED,
            icon_color=ft.Colors.ORANGE_300,
            tooltip="Запустить Помодоро (25 мин)",
            on_click=lambda e, t=task["title"]: open_pomodoro(t)
        )

        def add_task_click(e):
            if not task_input.value.strip():
                return
            # Сохраняем задачу в базу (БЕСПЛАТНО, без лимитов)
            db.add_task(task_input.value.strip(), selected_energy)
            task_input.value = ""
            
            # Автоматически сбрасываем фильтр на "Все", чтобы задача сразу появилась на экране
            filter_click("all")
            
            # Всплывающее уведомление
            page.overlay.append(ft.SnackBar(ft.Text("✅ Задача добавлена!"), open=True))
            page.update()

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
        for t in db.get_tasks(current_filter):
            tasks_column.controls.append(create_task_card(t))
        update_progress()

    def filter_click(filter_val):
        nonlocal current_filter
        current_filter = filter_val
        for btn in filter_tabs.controls:
            btn.style = ft.ButtonStyle(color=ft.Colors.AMBER_400 if btn.data == filter_val else ft.Colors.GREY_400)
        load_all_tasks()

    filter_tabs = ft.Row([
        ft.Button("Все", data="all", on_click=lambda e: filter_click("all")),
        ft.Button("⚡ Сил много", data="high", on_click=lambda e: filter_click("high")),
        ft.Button("🪫 Зомби", data="zombie", on_click=lambda e: filter_click("zombie")),
    ], spacing=4)

    def add_task_click(e):
        if not task_input.value.strip():
            return
        db.add_task(task_input.value.strip(), selected_energy)
        task_input.value = ""
        load_all_tasks()

    def remove_task(task_id):
        db.delete_task(task_id)
        load_all_tasks()

    task_input.on_submit = add_task_click

    def show_paywall():
        paywall = ft.AlertDialog(
            title=ft.Text("👑 SmartTask PRO", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text("Бесплатные AI-кредиты закончились."),
                ft.Divider(),
                ft.Text("✨ Безлимитная декомпозиция задач"),
                ft.Text("🤖 Безлимитный AI План дня"),
                ft.Container(height=10),
                ft.Button("Оформить PRO за $3.99/мес", bgcolor=ft.Colors.AMBER_500, color=ft.Colors.BLACK, on_click=lambda e: buy_pro_click(paywall))
            ], tight=True),
            actions=[
                ft.Button("Позже", on_click=lambda e: close_popup(paywall))
            ]
        )
        show_popup(paywall)

    def buy_pro_click(dialog):
        db.set_pro()
        close_popup(dialog)
        credits_badge.content.value = "👑 PRO"
        credits_badge.content.color = ft.Colors.GREEN_400
        page.update()

    # --- ГЛАВНЫЙ ЭКРАН ---
    header = ft.Row([
        ft.Text("SmartTask", size=22, weight=ft.FontWeight.BOLD),
        ft.Row([
            ft.IconButton(icon=ft.Icons.AUTO_MODE_ROUNDED, icon_color=ft.Colors.AMBER_400, tooltip="AI: Составить план дня", on_click=lambda e: open_ai_day_plan()),
            streak_badge, 
            credits_badge
        ], spacing=4)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    progress_section = ft.Column([
        ft.Row([ft.Text("Сегодня", weight=ft.FontWeight.BOLD, size=14), progress_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
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
        ft.Text("Энергия задачи:", size=11, color=ft.Colors.GREY_400),
        energy_chips,
        ft.Container(height=5),
        filter_tabs,
        tasks_column
    )

    load_all_tasks()

ft.run(main)