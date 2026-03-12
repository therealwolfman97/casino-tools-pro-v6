import requests
import certifi
import sys
import hashlib
import hmac
import random
import json
import os
import math
import statistics
import threading
import time
from functools import wraps

from decimal import Decimal, getcontext
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.widget import Widget
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.graphics import Color, Line, Rectangle
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.clock import Clock

# Theme Configuration
STAKE_DARK = '#000000'
STAKE_INPUT = '#0b0b0b'
STAKE_GREEN = '#00e701'
STAKE_RED = '#ff4e4e'
STAKE_TEXT = '#b1bad3'

SOFT_RED = '#7a0c0c'
DIVIDER_COLOR = '#111111'
SUBTITLE_TEXT = '#9a9a9a'

DICE_COLOR = '#1abc9c'
LIMBO_COLOR = '#3498db'
KENO_COLOR = '#9b59b6'
MINES_COLOR = '#e67e22'
SPORTS_COLOR = '#e74c3c'
UTILITY_COLOR = '#2c3e50'
LIBRARY_COLOR = STAKE_GREEN

Window.clearcolor = get_color_from_hex(STAKE_DARK)
getcontext().prec = 40


def safe_float(text, default=0.0):
    try:
        return float(str(text).strip())
    except Exception:
        return default


def safe_int(text, default=0):
    try:
        return int(float(str(text).strip()))
    except Exception:
        return default


def _ui_call(fn, *args, **kwargs):
    Clock.schedule_once(lambda dt: fn(*args, **kwargs), 0)



def get_app_data_dir():
    try:
        if sys.platform == "android":
            from android.storage import app_storage_path
            data_dir = app_storage_path()
        else:
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_data")
    except Exception:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_data")

    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_strategy_file():
    return os.path.join(get_app_data_dir(), "strategies_master.json")


def get_tracker_file():
    return os.path.join(get_app_data_dir(), "tracker_state.json")


class BankrollManager:
    def __init__(self):
        self.session_profit = 0.0
        self.start_time_epoch = time.time()
        self.total_sessions = 0
        self.strategies = []
        self.load_tracker_state()
        self.load_strategies()

    def get_duration(self):
        elapsed = max(0, int(time.time() - self.start_time_epoch))
        mins, secs = divmod(elapsed, 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def save_tracker_state(self):
        payload = {
            "session_profit": self.session_profit,
            "start_time_epoch": self.start_time_epoch,
            "total_sessions": self.total_sessions,
        }
        try:
            with open(get_tracker_file(), 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"save_tracker_state error: {e}")

    def load_tracker_state(self):
        try:
            with open(get_tracker_file(), 'r', encoding='utf-8') as f:
                raw = json.load(f)
            self.session_profit = float(raw.get("session_profit", 0.0))
            self.start_time_epoch = float(raw.get("start_time_epoch", time.time()))
            self.total_sessions = int(raw.get("total_sessions", 0))
        except Exception:
            self.session_profit = 0.0
            self.start_time_epoch = time.time()
            self.total_sessions = 0

    def reset_tracker_state(self):
        self.session_profit = 0.0
        self.start_time_epoch = time.time()
        self.total_sessions = 0
        self.save_tracker_state()

    def save_strategies(self):
        cleaned = [normalize_strategy(s) for s in self.strategies]
        try:
            with open(get_strategy_file(), 'w', encoding='utf-8') as f:
                json.dump(cleaned, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"save_strategies error: {e}")

    def load_strategies(self):
        try:
            with open(get_strategy_file(), 'r', encoding='utf-8') as f:
                raw = json.load(f)
                if isinstance(raw, list):
                    self.strategies = [normalize_strategy(s) for s in raw]
                else:
                    self.strategies = []
        except Exception:
            self.strategies = []

def normalize_strategy(raw):
    if not isinstance(raw, dict):
        raw = {}

    return {
        "name": str(raw.get("name", "Untitled Strategy")),
        "category": str(raw.get("category", "Manual Custom")),
        "game": str(raw.get("game", "general")),
        "source": str(raw.get("source", "manual")),
        "bank": str(raw.get("bank", "")),
        "base": str(raw.get("base", "")),
        "multi": str(raw.get("multi", "")),
        "win_action": str(raw.get("win_action", "Reset")),
        "loss_action": str(raw.get("loss_action", "")),
        "max_bets": str(raw.get("max_bets", "")),
        "created_at": str(raw.get("created_at", "")),
        "notes": str(raw.get("notes", "")),
    }


GLOBAL_BANK = BankrollManager()

DEMO = "demo"
PRO = "pro"
PRO_PLUS = "pro_plus"
LICENSE_SECRET = "ctp6_sh_2026_v1"

FEATURE_TIERS = {
    "strats": PRO,
    "dice_sim": PRO,
    "dice": PRO,
    "mc": PRO,
    "dice_opt": PRO_PLUS,
    "dice_gen": PRO,
    "forge": PRO_PLUS,
    "dice_evo": PRO_PLUS,
    "limbo_evo": PRO_PLUS,
    "keno_evo": PRO_PLUS,
    "mines_evo": PRO_PLUS,
    "stress_lab": PRO,
    "survival_lab": PRO_PLUS,
    "keno_mc": PRO_PLUS,
    "mines": PRO,
    "bj": PRO,
    "sports_lab": PRO,
    "sports_kelly": PRO,
    "sports_parlay": PRO,
    "sports_value": PRO,
    "sports_arb": PRO,
    "compound": PRO,
    "pattern": PRO,
    "converter": DEMO,
}

TOOL_TITLES = {
    "strats": "Strategies Library",
    "dice_sim": "Dice Simulator",
    "dice": "Dice / Limbo Calculator",
    "mc": "Monte Carlo Simulator",
    "dice_opt": "Dice Optimizer",
    "dice_gen": "Dice Auto Generator",
    "forge": "Strategy Forge",
    "dice_evo": "Dice Evolution Engine",
    "limbo_evo": "Limbo Evolution Engine",
    "keno_evo": "Keno Evolution Engine",
    "mines_evo": "Mines Evolution Engine",
    "stress_lab": "Strategy Stress Test",
    "survival_lab": "Bankroll Survival Lab",
    "keno_mc": "Keno Monte Carlo",
    "mines": "Mines Analytics",
    "bj": "Blackjack Strategy Hub",
    "sports_lab": "Sports Betting Lab",
    "sports_kelly": "Kelly Bet Calculator",
    "sports_parlay": "Parlay Analyzer",
    "sports_value": "Value Bet Calculator",
    "sports_arb": "Arbitrage Calculator",
    "compound": "Compound Growth Pro",
    "pattern": "Pattern Sequence Master",
    "converter": "Live Crypto Converter",
}

DEMO_LIMITS = {
    "strats_save": 2,
    "dice_sim_rolls": 50,
    "dice": 10,
    "mc": 10,
    "stress_lab": 3,
    "mines": 10,
    "bj": 15,
    "sports_kelly": 10,
    "sports_parlay": 5,
    "sports_value": 10,
    "sports_arb": 10,
    "compound": 10,
    "pattern": 10,
}

def get_license_file():
    return os.path.join(get_app_data_dir(), "license_state.json")

def get_demo_usage_file():
    return os.path.join(get_app_data_dir(), "demo_usage.json")

def get_device_file():
    return os.path.join(get_app_data_dir(), "device_identity.json")

def _load_json_file(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def _save_json_file(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"save json error: {e}")

def get_device_code():
    stored = _load_json_file(get_device_file(), {})
    code = str(stored.get("device_code", "")).strip()
    if code:
        return code
    raw = ""
    try:
        if sys.platform == "android":
            from jnius import autoclass
            Secure = autoclass('android.provider.Settings$Secure')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            raw = Secure.getString(activity.getContentResolver(), Secure.ANDROID_ID) or ""
    except Exception:
        raw = ""
    if not raw:
        raw = f"fallback-{random.random()}-{time.time()}-{os.getpid()}"
    digest = hashlib.sha256((raw + "|casino_tools_pro_v6").encode()).hexdigest()[:8].upper()
    code = f"CTP6-DEV-{digest}"
    _save_json_file(get_device_file(), {"device_code": code})
    return code

def build_expected_license(tier, device_code=None):
    if device_code is None:
        device_code = get_device_code()
    tier = str(tier).strip().lower()
    if tier not in (PRO, PRO_PLUS):
        return ""
    device_suffix = device_code.split('-')[-1]
    tier_tag = "PRO" if tier == PRO else "PPLUS"
    payload = f"{tier}|{device_suffix}|casino_tools_pro"
    sig = hmac.new(LICENSE_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:12].upper()
    return f"CTP6-{tier_tag}-{device_suffix}-{sig}"

def verify_license_key(key, device_code=None):
    if device_code is None:
        device_code = get_device_code()
    cleaned = str(key).strip().upper().replace(" ", "")
    if cleaned == build_expected_license(PRO, device_code).upper():
        return True, PRO
    if cleaned == build_expected_license(PRO_PLUS, device_code).upper():
        return True, PRO_PLUS
    return False, DEMO

class LicenseState:
    def __init__(self):
        self.tier = DEMO
        self.license_key = ""
        self.load()

    def load(self):
        raw = _load_json_file(get_license_file(), {})
        self.tier = str(raw.get("tier", DEMO)).strip().lower()
        if self.tier not in (DEMO, PRO, PRO_PLUS):
            self.tier = DEMO
        self.license_key = str(raw.get("license_key", "")).strip()

    def save(self):
        _save_json_file(get_license_file(), {"tier": self.tier, "license_key": self.license_key})

    def activate(self, key):
        ok, tier = verify_license_key(key)
        if ok:
            self.tier = tier
            self.license_key = str(key).strip()
            self.save()
            return True, tier
        return False, DEMO

class DemoUsageManager:
    def __init__(self):
        self.usage = {}
        self.load()

    def load(self):
        raw = _load_json_file(get_demo_usage_file(), {})
        self.usage = {str(k): int(v) for k, v in raw.items() if str(k) in DEMO_LIMITS}

    def save(self):
        _save_json_file(get_demo_usage_file(), self.usage)
        app = App.get_running_app()
        if app and hasattr(app, 'refresh_status_labels'):
            Clock.schedule_once(lambda dt: app.refresh_status_labels(), 0)

    def get_used(self, key):
        return int(self.usage.get(key, 0))

    def remaining(self, key):
        limit = DEMO_LIMITS.get(key, 0)
        return max(0, limit - self.get_used(key))

    def can_use(self, key, amount=1):
        if key not in DEMO_LIMITS:
            return True
        return self.get_used(key) + amount <= DEMO_LIMITS[key]

    def consume(self, key, amount=1):
        if key not in DEMO_LIMITS:
            return True
        if not self.can_use(key, amount):
            return False
        self.usage[key] = self.get_used(key) + amount
        self.save()
        return True

LICENSE_STATE = LicenseState()
DEMO_USAGE = DemoUsageManager()

def show_upgrade_popup(title, required_tier=PRO, reason="Preview mode only."):
    content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
    msg = Label(text=f"{title}\n\n{reason}\n\nUpgrade to {'Pro+' if required_tier == PRO_PLUS else 'Pro'} to use this tool.",
                color=get_color_from_hex(STAKE_TEXT), halign='center', valign='middle')
    msg.bind(size=lambda instance, value: setattr(instance, 'text_size', value))
    row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
    close_btn = StyledButton(text='CLOSE', bg_color=UTILITY_COLOR)
    close_btn.color = (1,1,1,1)
    license_btn = StyledButton(text='LICENSE', bg_color=STAKE_GREEN)
    row.add_widget(close_btn)
    row.add_widget(license_btn)
    content.add_widget(msg)
    content.add_widget(row)
    popup = Popup(title='Upgrade Required', content=content, size_hint=(0.86, 0.42))
    close_btn.bind(on_release=lambda *a: popup.dismiss())
    license_btn.bind(on_release=lambda *a: (popup.dismiss(), App.get_running_app().show_license_popup()))
    popup.open()

# --- Shared UI Components ---
class StyledInput(TextInput):
    def __init__(self, **kwargs):
        kwargs.setdefault('multiline', False)
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(38)
        self.background_color = get_color_from_hex(STAKE_INPUT)
        self.foreground_color = (1, 1, 1, 1)
        self.padding = [dp(10), dp(8)]
        self.cursor_color = get_color_from_hex(STAKE_GREEN)
        self.font_size = '13sp'


class StyledButton(Button):
    def __init__(self, **kwargs):
        color_hex = kwargs.pop('bg_color', STAKE_GREEN)
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(42)
        self.background_normal = ''
        self.background_color = get_color_from_hex(color_hex)
        self.bold = True
        self.color = (0, 0, 0, 1) if color_hex == STAKE_GREEN else (1, 1, 1, 1)


class SimpleNav(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(50)
        self.padding = [0, dp(5)]
        btn = StyledButton(text="BACK TO HOME", bg_color=STAKE_INPUT)
        btn.color = get_color_from_hex(STAKE_GREEN)
        btn.bind(on_release=lambda x: setattr(App.get_running_app().root, 'current', 'menu'))
        self.add_widget(btn)

def analyze_strategy_rating(strategy):
    s = normalize_strategy(strategy)
    notes = str(s.get("notes", "") or "")

    avg_profit = 0.0
    bust_rate = 0.0

    try:
        if "Avg " in notes:
            avg_part = notes.split("Avg ", 1)[1].split(" |", 1)[0].strip()
            avg_profit = float(avg_part)
    except Exception:
        avg_profit = 0.0

    try:
        if "Bust " in notes:
            bust_part = notes.split("Bust ", 1)[1].split("%", 1)[0].strip()
            bust_rate = float(bust_part)
    except Exception:
        bust_rate = 0.0

    rating = max(0.0, min(10.0, (avg_profit * 1.2) - (bust_rate * 0.15) + 5.0))

    if bust_rate <= 0.10:
        risk = "Safe"
        color = STAKE_GREEN
    elif bust_rate <= 1.00:
        risk = "Balanced"
        color = "#f1c40f"
    elif bust_rate <= 3.00:
        risk = "Aggressive"
        color = "#e67e22"
    else:
        risk = "Extreme"
        color = STAKE_RED

    return {
        "avg_profit": avg_profit,
        "bust_rate": bust_rate,
        "rating": round(rating, 2),
        "risk": risk,
        "color": color,
    }

# --- Strategy Library Screen ---
class StrategyLibraryScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        self.selected_category = "All"

        self.layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

        self.layout.add_widget(Label(
            text="STRATEGY LIBRARY",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(40)
        ))

        filter_row = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(42))
        filter_row.add_widget(Label(
            text="Category",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='12sp'
        ))

        self.category_spinner = Spinner(
            text='All',
            values=(
                'All',
                'Dice Optimizer',
                'Dice Auto Generator',
                'Keno',
                'Mines',
                'Manual Custom',
                'Experimental',
                'Imported'
            ),
            size_hint_y=None,
            height=dp(38),
            background_normal='',
            background_color=get_color_from_hex(STAKE_INPUT),
            color=(1, 1, 1, 1)
        )
        self.category_spinner.bind(text=self.on_category_change)
        filter_row.add_widget(self.category_spinner)
        self.layout.add_widget(filter_row)

        self.scroll = ScrollView()
        self.strat_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(12))
        self.strat_list.bind(minimum_height=self.strat_list.setter('height'))
        self.scroll.add_widget(self.strat_list)
        self.layout.add_widget(self.scroll)

        btn_box = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))

        add_btn = StyledButton(text="NEW STRAT", bg_color=STAKE_GREEN, size_hint_x=0.5)
        add_btn.bind(on_release=self.show_add_popup)

        export_btn = StyledButton(text="EXPORT TXT", bg_color=UTILITY_COLOR, size_hint_x=0.5)
        export_btn.color = (1, 1, 1, 1)
        export_btn.bind(on_release=self.export_to_txt)

        btn_box.add_widget(add_btn)
        btn_box.add_widget(export_btn)
        self.layout.add_widget(btn_box)

        self.layout.add_widget(SimpleNav())
        self.add_widget(self.layout)

    def get_game_color(self, game):
        game = str(game).lower().strip()
        if game == 'dice':
            return DICE_COLOR
        if game == 'limbo':
            return LIMBO_COLOR
        if game == 'keno':
            return KENO_COLOR
        if game == 'mines':
            return MINES_COLOR
        if game == 'sports':
            return SPORTS_COLOR
        return UTILITY_COLOR

    def on_pre_enter(self, *args):
        self.refresh_list()

    def on_category_change(self, instance, value):
        self.selected_category = value
        self.refresh_list()

    def get_filtered_strategies(self):
        normalized = [normalize_strategy(s) for s in GLOBAL_BANK.strategies]
        if self.selected_category == "All":
            return normalized
        return [s for s in normalized if s.get("category", "Manual Custom") == self.selected_category]

    def refresh_list(self, *args):
        self.strat_list.clear_widgets()
        filtered = self.get_filtered_strategies()

        if not filtered:
            self.strat_list.add_widget(Label(
                text="No strategies in this category",
                color=get_color_from_hex(STAKE_TEXT),
                size_hint_y=None,
                height=dp(40)
            ))
            return

        for index, s in enumerate(GLOBAL_BANK.strategies):
            s = normalize_strategy(s)
            if self.selected_category != "All" and s["category"] != self.selected_category:
                continue

            game_name = s.get('game', 'other')
            stripe_color = self.get_game_color(game_name)
            analysis = analyze_strategy_rating(s)

            card = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(305),
                padding=dp(10),
                spacing=dp(5)
            )

            def update_card_rect(instance, value):
                if hasattr(instance, '_bg_rect'):
                    instance._bg_rect.pos = instance.pos
                    instance._bg_rect.size = instance.size
                if hasattr(instance, '_stripe_rect'):
                    instance._stripe_rect.pos = instance.pos
                    instance._stripe_rect.size = (dp(5), instance.height)

            with card.canvas.before:
                Color(rgba=get_color_from_hex(STAKE_INPUT))
                card._bg_rect = Rectangle(pos=card.pos, size=card.size)
                Color(rgba=get_color_from_hex(stripe_color))
                card._stripe_rect = Rectangle(pos=card.pos, size=(dp(5), card.height))

            card.bind(pos=update_card_rect, size=update_card_rect)

            title_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(6))

            badge = Label(
                text=game_name.upper(),
                size_hint_x=None,
                width=dp(68),
                bold=True,
                color=(0, 0, 0, 1) if stripe_color != UTILITY_COLOR else (1, 1, 1, 1)
            )
            with badge.canvas.before:
                Color(rgba=get_color_from_hex(stripe_color))
                badge._bg_rect = Rectangle(pos=badge.pos, size=badge.size)

            def _update_badge(instance, value):
                if hasattr(instance, '_bg_rect'):
                    instance._bg_rect.pos = instance.pos
                    instance._bg_rect.size = instance.size

            badge.bind(pos=_update_badge, size=_update_badge)

            name_lbl = Label(
                text=s['name'].upper(),
                bold=True,
                color=get_color_from_hex(analysis['color']),
                halign='left'
            )

            rename_btn = Button(
                text='RENAME',
                size_hint_x=None,
                width=dp(72),
                background_color=get_color_from_hex(UTILITY_COLOR),
                background_normal='',
                font_size='10sp',
                bold=True
            )
            rename_btn.bind(on_release=lambda x, i=index: self.show_rename_popup(i))

            del_btn = Button(
                text='X',
                size_hint_x=None,
                width=dp(30),
                background_color=get_color_from_hex(SOFT_RED),
                background_normal=''
            )
            del_btn.bind(on_release=lambda x, i=index: self.delete_strat(i))

            title_row.add_widget(badge)
            title_row.add_widget(name_lbl)
            title_row.add_widget(rename_btn)
            title_row.add_widget(del_btn)
            card.add_widget(title_row)

            meta_row = GridLayout(cols=2, spacing=dp(2), size_hint_y=None, height=dp(66))
            for txt, col in [
                (f"Category: {s['category']}", STAKE_TEXT),
                (f"Game: {s['game']}", STAKE_TEXT),
                (f"Source: {s['source']}", STAKE_TEXT),
                (f"Max Bets: {s['max_bets'] or '--'}", STAKE_TEXT),
                (f"Rating: {analysis['rating']}/10", STAKE_GREEN),
                (f"Risk: {analysis['risk']}", analysis['color'])
            ]:
                meta_row.add_widget(Label(text=txt, font_size='11sp', color=get_color_from_hex(col)))
            card.add_widget(meta_row)

            grid = GridLayout(cols=2, spacing=dp(2), size_hint_y=None, height=dp(52))
            details = [
                f"Bank: {s['bank']}",
                f"Multi: {s['multi']}x",
                f"Base: {s['base']}",
                f"Win: {s['win_action']}",
                f"Loss: {s['loss_action']}"
            ]
            for d in details:
                grid.add_widget(Label(text=d, font_size='11sp', color=get_color_from_hex(STAKE_TEXT)))
            card.add_widget(grid)

            notes_lbl = Label(
                text=f"Note: {s.get('notes', '')}",
                font_size='10sp',
                italic=True,
                color=get_color_from_hex(SUBTITLE_TEXT),
                size_hint_y=None,
                height=dp(34),
                text_size=(Window.width - dp(40), None),
                halign='left'
            )
            card.add_widget(notes_lbl)

            actions = BoxLayout(size_hint_y=None, height=dp(70), spacing=dp(5), orientation='vertical')
            row_a = BoxLayout(spacing=dp(5))
            run_sim = Button(text='RUN SIM', background_color=get_color_from_hex('#2980b9'), background_normal='', font_size='11sp', bold=True)
            run_sim.bind(on_release=lambda x, data=s: self.run_in_sim(data))
            run_calc = Button(text='RUN CALC', background_color=get_color_from_hex('#8e44ad'), background_normal='', font_size='11sp', bold=True)
            run_calc.bind(on_release=lambda x, data=s: self.run_in_calc(data))
            row_a.add_widget(run_sim)
            row_a.add_widget(run_calc)

            stress_btn = Button(text='STRESS TEST', background_color=get_color_from_hex(UTILITY_COLOR), background_normal='', font_size='11sp', bold=True)
            stress_btn.bind(on_release=lambda x, data=s: self.run_in_stress(data))
            actions.add_widget(row_a)
            actions.add_widget(stress_btn)
            card.add_widget(actions)

            self.strat_list.add_widget(card)



    def show_rename_popup(self, index):
        if not (0 <= index < len(GLOBAL_BANK.strategies)):
            return
        current = normalize_strategy(GLOBAL_BANK.strategies[index])
        content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
        content.add_widget(Label(
            text='Rename strategy',
            color=get_color_from_hex(STAKE_TEXT),
            size_hint_y=None,
            height=dp(24)
        ))
        name_input = StyledInput(text=current.get('name', ''))
        content.add_widget(name_input)

        btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        save_btn = StyledButton(text='SAVE', bg_color=STAKE_GREEN)
        cancel_btn = StyledButton(text='CANCEL', bg_color=UTILITY_COLOR)
        cancel_btn.color = (1, 1, 1, 1)
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)

        popup = Popup(title='Rename Strategy', content=content, size_hint=(0.86, 0.34))

        def do_save(*args):
            new_name = str(name_input.text).strip()
            if new_name:
                strategy = normalize_strategy(GLOBAL_BANK.strategies[index])
                strategy['name'] = new_name
                GLOBAL_BANK.strategies[index] = strategy
                GLOBAL_BANK.save_strategies()
                self.refresh_list()
            popup.dismiss()

        save_btn.bind(on_release=do_save)
        cancel_btn.bind(on_release=lambda *a: popup.dismiss())
        popup.open()

    def run_in_stress(self, data):
        data = normalize_strategy(data)
        stress_screen = App.get_running_app().root.get_screen('stress_lab')
        stress_screen.load_strategy(data)
        App.get_running_app().root.current = 'stress_lab'

    def delete_strat(self, index):
        if 0 <= index < len(GLOBAL_BANK.strategies):
            GLOBAL_BANK.strategies.pop(index)
            GLOBAL_BANK.save_strategies()
            self.refresh_list()

    def export_to_txt(self, *args):
        try:
            filename = "exported_strategies.txt"
            with open(filename, "w") as f:
                f.write("=== STAKE PRO STRATEGY EXPORT ===\n\n")
                for raw in GLOBAL_BANK.strategies:
                    s = normalize_strategy(raw)
                    f.write(f"NAME: {s['name']}\n")
                    f.write(f"Category: {s['category']} | Game: {s['game']} | Source: {s['source']}\n")
                    f.write(f"Bankroll: {s['bank']} | Multiplier: {s['multi']}x | Base Bet: {s['base']} | Max Bets: {s['max_bets']}\n")
                    f.write(f"Win Action: {s['win_action']} | Loss Action: {s['loss_action']}\n")
                    f.write(f"Notes: {s.get('notes', '')}\n")
                    f.write("-" * 40 + "\n")
            Popup(title='Success', content=Label(text=f"Saved to {filename}"), size_hint=(0.6, 0.2)).open()
        except Exception as e:
            Popup(title='Error', content=Label(text=str(e)), size_hint=(0.6, 0.2)).open()

    def run_in_sim(self, data):
        data = normalize_strategy(data)
        sim_screen = App.get_running_app().root.get_screen('dice_sim')
        sim_screen.balance_input.text = str(data['bank'] or '1000')
        sim_screen.change_balance()
        sim_screen.bet_input.text = str(data['base'] or '1')
        try:
            sim_screen.multi_input.text = str(data['multi'] or '2.0')
            sim_screen.on_manual_multi_change()
        except Exception:
            pass
        try:
            val = str(data['loss_action']).split(' ')[1].replace('%', '')
            if hasattr(sim_screen, 'auto_inputs') and 'Loss+%' in sim_screen.auto_inputs:
                sim_screen.auto_inputs['Loss+%'].text = val
        except Exception:
            pass
        App.get_running_app().root.current = 'dice_sim'

    def run_in_calc(self, data):
        data = normalize_strategy(data)
        calc_screen = App.get_running_app().root.get_screen('dice')
        calc_screen.inputs['Balance'].text = str(data['bank'] or '1')
        calc_screen.inputs['Base Bet'].text = str(data['base'] or '0.00015')
        calc_screen.inputs['Multiplier'].text = str(data['multi'] or '2.0')
        try:
            val = str(data['loss_action']).split(' ')[1].replace('%', '')
            calc_screen.inputs['Increase on Loss %'].text = val
        except Exception:
            calc_screen.inputs['Increase on Loss %'].text = '0'
        calc_screen.calculate()
        App.get_running_app().root.current = 'dice'

    def show_add_popup(self, *args):
        app = App.get_running_app()
        if app and app.get_tier() == DEMO and DEMO_USAGE.remaining('strats_save') <= 0:
            show_upgrade_popup('Strategies Library', PRO, 'Demo save limit reached.')
            return
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(5))
        inputs = {}
        fields = [
            ('Name', 'Manual Strategy'), ('Category', 'Manual Custom'), ('Game', 'general'), ('Source', 'manual'),
            ('Bankroll', '1000'), ('Base Bet', '1'), ('Multiplier', '2.0'), ('On Win', 'Reset'),
            ('On Loss', 'Increase 100%'), ('Max Bets', ''), ('Notes', '')
        ]
        for f, d in fields:
            content.add_widget(Label(text=f, font_size='11sp', size_hint_y=None, height=dp(15)))
            ti = StyledInput(text=d)
            inputs[f] = ti
            content.add_widget(ti)
        save_btn = StyledButton(text='SAVE STRATEGY')
        content.add_widget(save_btn)
        popup = Popup(title='New Strategy', content=content, size_hint=(0.9, 0.95))

        def save_strat(*a):
            app = App.get_running_app()
            if app and app.get_tier() == DEMO:
                if not DEMO_USAGE.consume('strats_save', 1):
                    show_upgrade_popup('Strategies Library', PRO, 'Demo save limit reached.')
                    popup.dismiss()
                    return
            new_s = normalize_strategy({
                'name': inputs['Name'].text, 'category': inputs['Category'].text or 'Manual Custom',
                'game': inputs['Game'].text or 'general', 'source': inputs['Source'].text or 'manual',
                'bank': inputs['Bankroll'].text, 'base': inputs['Base Bet'].text, 'multi': inputs['Multiplier'].text,
                'win_action': inputs['On Win'].text, 'loss_action': inputs['On Loss'].text,
                'max_bets': inputs['Max Bets'].text, 'notes': inputs['Notes'].text
            })
            GLOBAL_BANK.strategies.append(new_s)
            GLOBAL_BANK.save_strategies()
            self.refresh_list()
            popup.dismiss()

        save_btn.bind(on_release=save_strat)
        popup.open()

class ProfitGraph(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history = [0]
        self.bind(pos=self.redraw, size=self.redraw)

    def add_point(self, profit):
        self.history.append(profit)
        if len(self.history) > 60:
            self.history.pop(0)
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        if len(self.history) < 2:
            return

        with self.canvas:
            Color(0.1, 0.12, 0.15, 1)
            Rectangle(pos=self.pos, size=self.size)

            Color(0, 0.7, 1, 1)
            points = []
            x_step = self.width / max(1, (len(self.history) - 1))
            min_h = min(self.history)
            max_h = max(self.history)
            h_range = max(1.0, max_h - min_h)

            for i, val in enumerate(self.history):
                px = self.x + (i * x_step)
                py = self.y + ((val - min_h) / h_range) * self.height
                points.extend([px, py])

            Line(points=points, width=dp(1.5))

class DiceSimScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        # Core state
        self.balance = 1000.0
        self.base_bet = 1.0
        self.total_wagered = 0.0
        self.session_profit = 0.0
        self.wins = 0
        self.losses = 0
        self.is_auto_running = False
        self.roll_history = []

        # Dice config
        self.target_value = 50.5
        self.roll_mode = "OVER"  # OVER / UNDER
        self.client_seed = "stake_pro_seed"
        self.server_seed = hashlib.sha256(f"{random.random()}-{Clock.get_time()}".encode()).hexdigest()
        self.nonce = 0

        outer = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6))

        title = Label(
            text="DICE SIMULATOR V2",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(30)
        )
        outer.add_widget(title)

        tabs = TabbedPanel(do_default_tab=False, tab_height=dp(38), tab_width=dp(140))

        # ---------------- MANUAL TAB ----------------
        manual_tab = TabbedPanelItem(text="MANUAL")
        manual_scroll = ScrollView()
        manual_col = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8), padding=[0, 0, 0, dp(6)])
        manual_col.bind(minimum_height=manual_col.setter('height'))

        # Header card
        header_card = self.make_card(height=dp(90))
        header_grid = GridLayout(cols=2, spacing=dp(6), padding=dp(8))

        self.balance_lbl = Label(text="Balance: $1000.00", color=get_color_from_hex(STAKE_GREEN), bold=True)
        self.profit_lbl = Label(text="Session P/L: $0.00", color=get_color_from_hex(STAKE_TEXT), bold=True)
        self.wager_lbl = Label(text="Wagered: $0.00", color=get_color_from_hex(STAKE_TEXT))
        self.wl_lbl = Label(text="W / L: 0 / 0", color=get_color_from_hex(STAKE_TEXT))

        header_grid.add_widget(self.balance_lbl)
        header_grid.add_widget(self.profit_lbl)
        header_grid.add_widget(self.wager_lbl)
        header_grid.add_widget(self.wl_lbl)
        header_card.add_widget(header_grid)
        manual_col.add_widget(header_card)

        # Result card
        result_card = self.make_card(height=dp(120))
        result_col = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(4))

        top_row = BoxLayout(size_hint_y=None, height=dp(24))
        self.mode_lbl = Label(text="Mode: OVER", color=get_color_from_hex(STAKE_TEXT), font_size='12sp')
        self.stats_lbl = Label(text="Chance: 49.50% | Multi: 2.00x", color=get_color_from_hex(STAKE_TEXT), font_size='12sp')
        top_row.add_widget(self.mode_lbl)
        top_row.add_widget(self.stats_lbl)

        self.roll_lbl = Label(
            text="0.00",
            font_size='44sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN)
        )

        result_col.add_widget(top_row)
        result_col.add_widget(self.roll_lbl)
        result_card.add_widget(result_col)
        manual_col.add_widget(result_card)

        # Graph card
        graph_card = self.make_card(height=dp(170))
        graph_col = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6))

        graph_top = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(6))
        hist_btn = StyledButton(text="HISTORY", bg_color="#2c3e50", height=dp(30))
        hist_btn.color = (1, 1, 1, 1)
        hist_btn.bind(on_release=self.show_history)

        reset_btn = StyledButton(text="RESET STATS", bg_color=SOFT_RED, height=dp(30))
        reset_btn.color = (1, 1, 1, 1)
        reset_btn.bind(on_release=self.reset_stats)

        graph_top.add_widget(hist_btn)
        graph_top.add_widget(reset_btn)

        self.graph = ProfitGraph()

        graph_col.add_widget(graph_top)
        graph_col.add_widget(self.graph)
        graph_card.add_widget(graph_col)
        manual_col.add_widget(graph_card)

        # Balance / bet card
        bank_card = self.make_card(height=dp(115))
        bank_col = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6))

        row1 = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        self.balance_input = StyledInput(text="1000")
        set_bal_btn = StyledButton(text="SET BAL", bg_color="#2c3e50", height=dp(38), size_hint_x=0.35)
        set_bal_btn.color = (1, 1, 1, 1)
        set_bal_btn.bind(on_release=self.change_balance)
        row1.add_widget(self.balance_input)
        row1.add_widget(set_bal_btn)

        row2 = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        self.bet_input = StyledInput(text="1.0")
        max_btn = StyledButton(text="MAX", bg_color="#2c3e50", height=dp(38), size_hint_x=0.35)
        max_btn.color = (1, 1, 1, 1)
        max_btn.bind(on_release=lambda x: setattr(self.bet_input, 'text', str(round(self.balance, 8))))
        row2.add_widget(self.bet_input)
        row2.add_widget(max_btn)

        bank_col.add_widget(row1)
        bank_col.add_widget(row2)
        bank_card.add_widget(bank_col)
        manual_col.add_widget(bank_card)

        # Control card
        control_card = self.make_card(height=dp(205))
        control_col = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6))

        mode_row = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(6))
        self.over_btn = StyledButton(text="ROLL OVER", bg_color=STAKE_GREEN)
        self.under_btn = StyledButton(text="ROLL UNDER", bg_color=STAKE_INPUT)
        self.under_btn.color = (1, 1, 1, 1)

        self.over_btn.bind(on_release=lambda x: self.set_roll_mode("OVER"))
        self.under_btn.bind(on_release=lambda x: self.set_roll_mode("UNDER"))

        mode_row.add_widget(self.over_btn)
        mode_row.add_widget(self.under_btn)

        calc_grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(82))

        chance_box = BoxLayout(orientation='vertical', spacing=0)
        chance_box.add_widget(Label(text="CHANCE %", font_size='10sp', color=get_color_from_hex(STAKE_TEXT), size_hint_y=None, height=dp(16)))
        self.chance_input = StyledInput(text="49.50", height=dp(34))
        self.chance_input.bind(text=self.on_manual_chance_change)
        chance_box.add_widget(self.chance_input)

        multi_box = BoxLayout(orientation='vertical', spacing=0)
        multi_box.add_widget(Label(text="MULTI", font_size='10sp', color=get_color_from_hex(STAKE_TEXT), size_hint_y=None, height=dp(16)))
        self.multi_input = StyledInput(text="2.00", height=dp(34))
        self.multi_input.bind(text=self.on_manual_multi_change)
        multi_box.add_widget(self.multi_input)

        calc_grid.add_widget(chance_box)
        calc_grid.add_widget(multi_box)

        self.slider = Slider(min=0.01, max=98.99, value=50.5, size_hint_y=None, height=dp(32))
        self.slider.bind(value=self.on_slider_change)

        roll_btn = StyledButton(text="ROLL NOW", bg_color=STAKE_GREEN, height=dp(34))
        roll_btn.bind(on_release=self.play_manual)

        control_col.add_widget(mode_row)
        control_col.add_widget(calc_grid)
        control_col.add_widget(self.slider)
        control_col.add_widget(roll_btn)

        control_card.add_widget(control_col)
        manual_col.add_widget(control_card)

        manual_scroll.add_widget(manual_col)
        manual_tab.add_widget(manual_scroll)
        manual_tab.background_normal = ''
        manual_tab.background_color = get_color_from_hex(DICE_COLOR)
        manual_tab.color = (0, 0, 0, 1)
        tabs.add_widget(manual_tab)

        # ---------------- AUTO TAB ----------------
        auto_tab = TabbedPanelItem(text="AUTO / SEEDS")
        auto_scroll = ScrollView()
        auto_col = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8), padding=[0, 0, 0, dp(6)])
        auto_col.bind(minimum_height=auto_col.setter('height'))

        # Auto card
        auto_card = self.make_card(height=dp(220))
        auto_inner = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6))

        auto_inner.add_widget(Label(
            text="AUTO BET CONTROLS",
            color=get_color_from_hex(STAKE_GREEN),
            bold=True,
            size_hint_y=None,
            height=dp(20)
        ))

        self.auto_inputs = {}
        auto_grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(110))

        for lbl, default in [
            ("Win+%", "0"),
            ("Loss+%", "100"),
            ("Stop Profit", "0"),
            ("Stop Loss", "0"),
        ]:
            box = BoxLayout(orientation='vertical', spacing=0)
            box.add_widget(Label(
                text=lbl,
                font_size='10sp',
                color=get_color_from_hex(STAKE_TEXT),
                size_hint_y=None,
                height=dp(16)
            ))
            ti = StyledInput(text=default, height=dp(34))
            self.auto_inputs[lbl] = ti
            box.add_widget(ti)
            auto_grid.add_widget(box)

        speed_box = BoxLayout(orientation='vertical', spacing=0, size_hint_y=None, height=dp(52))
        speed_box.add_widget(Label(
            text="SPEED",
            font_size='10sp',
            color=get_color_from_hex(STAKE_TEXT),
            size_hint_y=None,
            height=dp(16)
        ))
        self.speed_slider = Slider(min=0.05, max=1.0, value=0.5)
        speed_box.add_widget(self.speed_slider)

        self.auto_btn = StyledButton(text="START AUTO", bg_color=SOFT_RED, height=dp(34))
        self.auto_btn.bind(on_release=self.toggle_auto)

        auto_inner.add_widget(auto_grid)
        auto_inner.add_widget(speed_box)
        auto_inner.add_widget(self.auto_btn)

        auto_card.add_widget(auto_inner)
        auto_col.add_widget(auto_card)

        # Seed card
        seed_card = self.make_card(height=dp(145))
        seed_col = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6))

        seed_col.add_widget(Label(
            text="SEED / TECHNICAL",
            color=get_color_from_hex(STAKE_GREEN),
            bold=True,
            size_hint_y=None,
            height=dp(20)
        ))

        self.seed_info_lbl = Label(
            text=f"Client: {self.client_seed} | Nonce: {self.nonce}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        seed_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        self.seed_input = StyledInput(text="stake_pro_seed")
        set_seed_btn = StyledButton(text="SET SEED", bg_color="#2c3e50", size_hint_x=0.3)
        set_seed_btn.color = (1, 1, 1, 1)
        set_seed_btn.bind(on_release=self.set_client_seed)
        seed_row.add_widget(self.seed_input)
        seed_row.add_widget(set_seed_btn)

        reset_seed_btn = StyledButton(text="RESET SERVER SEED", bg_color=SOFT_RED, height=dp(34))
        reset_seed_btn.color = (1, 1, 1, 1)
        reset_seed_btn.bind(on_release=self.reset_server_seed)

        seed_col.add_widget(self.seed_info_lbl)
        seed_col.add_widget(seed_row)
        seed_col.add_widget(reset_seed_btn)
        seed_card.add_widget(seed_col)
        auto_col.add_widget(seed_card)

        # Auto actions card
        action_card = self.make_card(height=dp(95))
        action_row = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6))

        hist_btn2 = StyledButton(text="HISTORY", bg_color="#2c3e50", height=dp(34))
        hist_btn2.color = (1, 1, 1, 1)
        hist_btn2.bind(on_release=self.show_history)

        reset_btn2 = StyledButton(text="RESET STATS", bg_color=SOFT_RED, height=dp(34))
        reset_btn2.color = (1, 1, 1, 1)
        reset_btn2.bind(on_release=self.reset_stats)

        action_row.add_widget(hist_btn2)
        action_row.add_widget(reset_btn2)
        action_card.add_widget(action_row)
        auto_col.add_widget(action_card)

        auto_scroll.add_widget(auto_col)
        auto_tab.add_widget(auto_scroll)
        auto_tab.background_normal = ''
        auto_tab.background_color = get_color_from_hex(STAKE_INPUT)
        auto_tab.color = (1, 1, 1, 1)
        tabs.add_widget(auto_tab)

        def refresh_tab_colors(*args):
            current = tabs.current_tab
            if current == manual_tab:
                manual_tab.background_color = get_color_from_hex(DICE_COLOR)
                manual_tab.color = (0, 0, 0, 1)
                auto_tab.background_color = get_color_from_hex(STAKE_INPUT)
                auto_tab.color = (1, 1, 1, 1)
            else:
                auto_tab.background_color = get_color_from_hex(DICE_COLOR)
                auto_tab.color = (0, 0, 0, 1)
                manual_tab.background_color = get_color_from_hex(STAKE_INPUT)
                manual_tab.color = (1, 1, 1, 1)

        tabs.bind(current_tab=lambda *a: refresh_tab_colors())
        refresh_tab_colors()

        outer.add_widget(tabs)
        outer.add_widget(SimpleNav())
        self.add_widget(outer)

        self.refresh_ui()

    # ---------- UI helpers ----------
    def make_card(self, height):
        card = BoxLayout(size_hint_y=None, height=height)

        def update_rect(instance, value):
            if hasattr(instance, "_bg_rect"):
                instance._bg_rect.pos = instance.pos
                instance._bg_rect.size = instance.size

        with card.canvas.before:
            Color(rgba=get_color_from_hex(STAKE_INPUT))
            card._bg_rect = Rectangle(pos=card.pos, size=card.size)

        card.bind(pos=update_rect, size=update_rect)
        return card

    def refresh_ui(self):
        self.balance_lbl.text = f"Balance: ${self.balance:.2f}"
        profit_color = STAKE_GREEN if self.session_profit >= 0 else STAKE_RED
        self.profit_lbl.text = f"Session P/L: ${self.session_profit:.2f}"
        self.profit_lbl.color = get_color_from_hex(profit_color)
        self.wager_lbl.text = f"Wagered: ${self.total_wagered:.2f}"
        self.wl_lbl.text = f"W / L: {self.wins} / {self.losses}"
        self.mode_lbl.text = f"Mode: {self.roll_mode}"
        self.stats_lbl.text = f"Chance: {self.get_current_win_chance():.2f}% | Multi: {self.get_current_multiplier():.2f}x"
        self.seed_info_lbl.text = f"Client: {self.client_seed} | Nonce: {self.nonce}"

    # ---------- Dice math ----------
    def set_roll_mode(self, mode):
        self.roll_mode = mode
        if mode == "OVER":
            self.over_btn.background_color = get_color_from_hex(STAKE_GREEN)
            self.over_btn.color = (0, 0, 0, 1)
            self.under_btn.background_color = get_color_from_hex(STAKE_INPUT)
            self.under_btn.color = (1, 1, 1, 1)
        else:
            self.under_btn.background_color = get_color_from_hex(STAKE_GREEN)
            self.under_btn.color = (0, 0, 0, 1)
            self.over_btn.background_color = get_color_from_hex(STAKE_INPUT)
            self.over_btn.color = (1, 1, 1, 1)

        self.on_manual_chance_change()
        self.refresh_ui()

    def on_slider_change(self, instance, value):
        self.target_value = round(value, 2)
        win_chance = self.target_value if self.roll_mode == "UNDER" else (100 - self.target_value)
        win_chance = max(0.01, min(99.99, win_chance))
        self.chance_input.text = f"{win_chance:.2f}"
        self.multi_input.text = f"{(99 / win_chance):.2f}"
        self.refresh_ui()

    def on_manual_chance_change(self, *args):
        try:
            wc = float(self.chance_input.text)
            wc = max(0.01, min(99.99, wc))
            self.multi_input.text = f"{(99 / wc):.2f}"
            if self.roll_mode == "UNDER":
                self.target_value = wc
                self.slider.value = wc
            else:
                self.target_value = 100 - wc
                self.slider.value = 100 - wc
        except Exception:
            pass
        self.refresh_ui()

    def on_manual_multi_change(self, *args):
        try:
            multi = float(self.multi_input.text)
            if multi >= 1.01:
                wc = max(0.01, min(99.99, 99 / multi))
                self.chance_input.text = f"{wc:.2f}"
                if self.roll_mode == "UNDER":
                    self.target_value = wc
                    self.slider.value = wc
                else:
                    self.target_value = 100 - wc
                    self.slider.value = 100 - wc
        except Exception:
            pass
        self.refresh_ui()

    def get_current_win_chance(self):
        try:
            return max(0.01, min(99.99, float(self.chance_input.text)))
        except Exception:
            return 49.5

    def get_current_multiplier(self):
        try:
            return max(1.01, float(self.multi_input.text))
        except Exception:
            return 2.0

    def is_win(self, roll_value):
        if self.roll_mode == "UNDER":
            return roll_value < self.target_value
        return roll_value > self.target_value

    def generate_roll(self):
        combined = f"{self.client_seed}:{self.nonce}".encode()
        digest = hmac.new(self.server_seed.encode(), combined, hashlib.sha512).hexdigest()
        value = int(digest[:8], 16) % 10000
        self.nonce += 1
        return value / 100.0

    # ---------- Actions ----------
    def change_balance(self, *args):
        value = safe_float(self.balance_input.text, self.balance)
        if value > 0:
            self.balance = value
            self.refresh_ui()

    def set_client_seed(self, *args):
        seed = str(self.seed_input.text).strip()
        if seed:
            self.client_seed = seed
            self.nonce = 0
            self.refresh_ui()

    def reset_server_seed(self, *args):
        self.server_seed = hashlib.sha256(f"{random.random()}-{Clock.get_time()}".encode()).hexdigest()
        self.nonce = 0
        self.refresh_ui()

    def execute_roll(self):
        bet = safe_float(self.bet_input.text, 0.0)
        if bet <= 0 or bet > self.balance:
            return "stop"

        self.balance -= bet
        self.total_wagered += bet

        roll_value = self.generate_roll()
        self.roll_lbl.text = f"{roll_value:.2f}"

        won = self.is_win(roll_value)
        multiplier = self.get_current_multiplier()

        if won:
            payout = bet * multiplier
            profit = payout - bet
            self.balance += payout
            self.session_profit += profit
            self.wins += 1
            self.roll_lbl.color = get_color_from_hex(STAKE_GREEN)
            self.roll_history.insert(0, f"{roll_value:05.2f} | WIN | +{profit:.4f}")
            change_pct = safe_float(self.auto_inputs["Win+%"].text, 0.0)
        else:
            self.session_profit -= bet
            self.losses += 1
            self.roll_lbl.color = get_color_from_hex(STAKE_RED)
            self.roll_history.insert(0, f"{roll_value:05.2f} | LOSE | -{bet:.4f}")
            change_pct = safe_float(self.auto_inputs["Loss+%"].text, 0.0)

        self.roll_history = self.roll_history[:120]
        self.graph.add_point(self.session_profit)

        if self.is_auto_running:
            if change_pct == 0:
                self.bet_input.text = str(self.base_bet)
            else:
                new_bet = bet * (1 + change_pct / 100.0)
                self.bet_input.text = str(round(max(0.00000001, new_bet), 8))

        self.refresh_ui()

        stop_profit = safe_float(self.auto_inputs["Stop Profit"].text, 0.0)
        stop_loss = safe_float(self.auto_inputs["Stop Loss"].text, 0.0)

        if stop_profit > 0 and self.session_profit >= stop_profit:
            return "stop"
        if stop_loss > 0 and self.session_profit <= -stop_loss:
            return "stop"

        return "continue"

    def play_manual(self, *args):
        if not self.is_auto_running:
            self.execute_roll()

    def toggle_auto(self, *args):
        if self.is_auto_running:
            self.is_auto_running = False
            self.auto_btn.text = "START AUTO"
        else:
            self.base_bet = safe_float(self.bet_input.text, 0.0)
            if self.base_bet <= 0:
                return
            self.is_auto_running = True
            self.auto_btn.text = "STOP AUTO"
            self.auto_loop()

    def auto_loop(self, *args):
        if not self.is_auto_running:
            return

        status = self.execute_roll()
        if status == "stop":
            self.is_auto_running = False
            self.auto_btn.text = "START AUTO"
            return

        interval = max(0.01, 1.05 - self.speed_slider.value)
        Clock.schedule_once(self.auto_loop, interval)

    def reset_stats(self, *args):
        self.session_profit = 0.0
        self.total_wagered = 0.0
        self.wins = 0
        self.losses = 0
        self.roll_history = []
        self.graph.history = [0]
        self.graph.redraw()
        self.roll_lbl.text = "0.00"
        self.roll_lbl.color = get_color_from_hex(STAKE_GREEN)
        self.refresh_ui()

    def show_history(self, *args):
        content = ScrollView()
        hist_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        hist_list.bind(minimum_height=hist_list.setter('height'))

        if not self.roll_history:
            hist_list.add_widget(Label(
                text="No rolls yet",
                size_hint_y=None,
                height=dp(24),
                color=get_color_from_hex(STAKE_TEXT)
            ))
        else:
            for entry in self.roll_history[:80]:
                color = (0, 1, 0, 1) if "| WIN |" in entry else (1, 0, 0, 1)
                hist_list.add_widget(Label(
                    text=entry,
                    size_hint_y=None,
                    height=dp(20),
                    color=color,
                    font_size='11sp'
                ))

        content.add_widget(hist_list)
        Popup(title="ROLL HISTORY", content=content, size_hint=(0.86, 0.7)).open()

class DiceScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(5))
        self.inputs = {}

        fields = [
            ('Balance', '1.0'),
            ('Base Bet', '0.00015'),
            ('Multiplier', '2.0'),
            ('Win Chance %', '49.5'),
            ('Increase on Loss %', '100.0')
        ]

        grid = GridLayout(cols=2, spacing=dp(5), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for label, default in fields:
            grid.add_widget(Label(text=label, color=get_color_from_hex(STAKE_TEXT), font_size='12sp'))
            self.inputs[label] = StyledInput(text=default)
            if label == 'Multiplier':
                self.inputs[label].bind(text=self.update_win_chance)
            grid.add_widget(self.inputs[label])

        layout.add_widget(grid)

        self.stats_lbl = Label(
            text="Streak Analysis: --",
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(30)
        )
        layout.add_widget(self.stats_lbl)

        btn_box = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(5))
        calc_btn = StyledButton(text="Calculate")
        calc_btn.bind(on_release=self.calculate)
        btn_box.add_widget(calc_btn)
        layout.add_widget(btn_box)

        self.res_grid = GridLayout(cols=3, spacing=2, size_hint_y=None)
        self.res_grid.bind(minimum_height=self.res_grid.setter('height'))
        scroll = ScrollView()
        scroll.add_widget(self.res_grid)
        layout.add_widget(scroll)

        layout.add_widget(SimpleNav())
        self.add_widget(layout)

    def update_win_chance(self, instance, value):
        try:
            m = float(value)
            if m > 1:
                self.inputs['Win Chance %'].text = f"{(99 / m):.2f}"
        except Exception:
            pass

    def calculate(self, *args):
        self.res_grid.clear_widgets()

        try:
            bal = float(self.inputs['Balance'].text)
            base = float(self.inputs['Base Bet'].text)
            inc_raw = float(self.inputs['Increase on Loss %'].text)
            inc = inc_raw / 100
            m_val = float(self.inputs['Multiplier'].text)

            min_inc_needed = (100 / (m_val - 1)) if m_val > 1 else 0
            t_bet = 0
            c_bet = base
            s = 0

            while (t_bet + c_bet) <= bal:
                s += 1
                t_bet += c_bet
                for v in [str(s), f"{c_bet:.8f}", f"{t_bet:.8f}"]:
                    self.res_grid.add_widget(
                        Label(text=v, height=dp(25), size_hint_y=None, font_size='11sp')
                    )
                c_bet += (c_bet * inc)

            prob_streak = ((1 - (99 / (m_val * 100))) ** s) * 100

            self.stats_lbl.color = (
                get_color_from_hex(STAKE_GREEN)
                if inc_raw >= min_inc_needed
                else get_color_from_hex(STAKE_RED)
            )

            self.stats_lbl.text = (
                f"Max Loss: {s} | Min Recov: {min_inc_needed:.2f}% | Prob: {prob_streak:.6f}%"
            )
        except Exception:
            pass


# --- Monte Carlo Engine + Screen ---
class MonteCarloEngine:
    @staticmethod
    def run_sessions(
        bankroll,
        base_bet,
        multiplier,
        win_chance,
        inc_on_win,
        inc_on_loss,
        stop_profit,
        stop_loss,
        max_bets,
        sessions,
    ):
        results = []
        busts = 0
        winning_sessions = 0
        total_bets_all = 0
        longest_loss_streak_seen = 0

        bankroll = max(0.00000001, bankroll)
        base_bet = max(0.00000001, base_bet)
        multiplier = max(1.01, multiplier)
        win_chance = min(99.99, max(0.01, win_chance))
        inc_on_win = max(-100.0, inc_on_win)
        inc_on_loss = max(-100.0, inc_on_loss)
        stop_profit = max(0.0, stop_profit)
        stop_loss = max(0.0, stop_loss)
        max_bets = max(1, max_bets)
        sessions = max(1, sessions)

        for _ in range(sessions):
            balance = bankroll
            current_bet = base_bet
            session_profit = 0.0
            bets_used = 0
            loss_streak = 0
            busted = False

            for _roll in range(max_bets):
                if current_bet <= 0 or current_bet > balance:
                    busted = True
                    busts += 1
                    break

                bets_used += 1
                balance -= current_bet

                roll = random.uniform(0, 100)
                is_win = roll < win_chance

                if is_win:
                    payout = current_bet * multiplier
                    net_profit = payout - current_bet
                    balance += payout
                    session_profit += net_profit
                    loss_streak = 0
                    current_bet = current_bet * (1 + inc_on_win / 100.0) if inc_on_win != 0 else base_bet
                else:
                    session_profit -= current_bet
                    loss_streak += 1
                    longest_loss_streak_seen = max(longest_loss_streak_seen, loss_streak)
                    current_bet = current_bet * (1 + inc_on_loss / 100.0) if inc_on_loss != 0 else base_bet

                if stop_profit > 0 and session_profit >= stop_profit:
                    break
                if stop_loss > 0 and session_profit <= -stop_loss:
                    break

            total_bets_all += bets_used
            results.append(session_profit)

            if session_profit > 0:
                winning_sessions += 1

            if busted:
                pass

        avg_profit = statistics.mean(results) if results else 0.0
        median_profit = statistics.median(results) if results else 0.0
        best_session = max(results) if results else 0.0
        worst_session = min(results) if results else 0.0
        win_rate = (winning_sessions / sessions) * 100 if sessions else 0.0
        bust_rate = (busts / sessions) * 100 if sessions else 0.0
        avg_bets = total_bets_all / sessions if sessions else 0.0

        return {
            "sessions": sessions,
            "average_profit": avg_profit,
            "median_profit": median_profit,
            "best_session": best_session,
            "worst_session": worst_session,
            "win_rate": win_rate,
            "bust_rate": bust_rate,
            "avg_bets": avg_bets,
            "longest_loss_streak": longest_loss_streak_seen,
        }


class MonteCarloScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        outer = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))

        title = Label(
            text="MONTE CARLO SIMULATOR",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(36)
        )
        outer.add_widget(title)

        scroll = ScrollView()
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        inner.bind(minimum_height=inner.setter('height'))

        self.mc_inputs = {}

        fields = [
            ("Bankroll", "20"),
            ("Base Bet", "0.1"),
            ("Multiplier", "3.5"),
            ("Win Chance %", "28.29"),
            ("Increase on Win %", "0"),
            ("Increase on Loss %", "50"),
            ("Stop Profit", "0"),
            ("Stop Loss", "0"),
            ("Max Bets / Session", "11"),
            ("Number of Sessions", "5000"),
        ]

        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for label_text, default in fields:
            lbl = Label(
                text=label_text,
                color=get_color_from_hex(STAKE_TEXT),
                font_size='12sp',
                size_hint_y=None,
                height=dp(36)
            )
            ti = StyledInput(text=default)
            self.mc_inputs[label_text] = ti
            grid.add_widget(lbl)
            grid.add_widget(ti)

        inner.add_widget(grid)

        btn_row = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(6))
        self.run_btn = StyledButton(text="RUN MONTE CARLO")
        self.run_btn.bind(on_release=self.run_monte_carlo)

        fill_btn = StyledButton(text="LOAD FROM DICE CALC", bg_color="#2c3e50")
        fill_btn.color = (1, 1, 1, 1)
        fill_btn.bind(on_release=self.load_from_dice_calc)

        btn_row.add_widget(self.run_btn)
        btn_row.add_widget(fill_btn)
        inner.add_widget(btn_row)

        self.status_lbl = Label(text="Status: Idle", color=get_color_from_hex(STAKE_TEXT), font_size='11sp', size_hint_y=None, height=dp(22))
        inner.add_widget(self.status_lbl)
        self.progress_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(10))
        inner.add_widget(self.progress_bar)

        self.summary = Label(
            text="Results will appear here",
            color=get_color_from_hex(STAKE_GREEN),
            font_size='14sp',
            size_hint_y=None,
            height=dp(80)
        )
        inner.add_widget(self.summary)

        self.results_grid = GridLayout(cols=2, spacing=dp(4), size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        inner.add_widget(self.results_grid)

        scroll.add_widget(inner)
        outer.add_widget(scroll)
        outer.add_widget(SimpleNav())
        self.add_widget(outer)

    def load_from_dice_calc(self, *args):
        try:
            dice_screen = App.get_running_app().root.get_screen('dice')
            self.mc_inputs["Bankroll"].text = dice_screen.inputs["Balance"].text
            self.mc_inputs["Base Bet"].text = dice_screen.inputs["Base Bet"].text
            self.mc_inputs["Multiplier"].text = dice_screen.inputs["Multiplier"].text
            self.mc_inputs["Win Chance %"].text = dice_screen.inputs["Win Chance %"].text
            self.mc_inputs["Increase on Loss %"].text = dice_screen.inputs["Increase on Loss %"].text
            self.summary.text = "Loaded values from Dice / Limbo Calculator"
        except Exception as e:
            self.summary.text = f"Load failed: {e}"

    def add_result_row(self, label, value, good=None):
        color = get_color_from_hex(STAKE_TEXT)
        if good is True:
            color = get_color_from_hex(STAKE_GREEN)
        elif good is False:
            color = get_color_from_hex(STAKE_RED)

        self.results_grid.add_widget(
            Label(
                text=label,
                color=get_color_from_hex(STAKE_TEXT),
                size_hint_y=None,
                height=dp(28),
                font_size='12sp'
            )
        )
        self.results_grid.add_widget(
            Label(
                text=value,
                color=color,
                size_hint_y=None,
                height=dp(28),
                font_size='12sp'
            )
        )

    def _set_progress(self, value, text):
        self.progress_bar.value = value
        self.status_lbl.text = text

    def _finish_monte_carlo(self, result):
        self.run_btn.disabled = False
        self.progress_bar.value = self.progress_bar.max
        self.status_lbl.text = "Status: Complete"
        self.summary.text = f"Completed {result['sessions']:,} sessions"
        self.results_grid.clear_widgets()
        self.add_result_row("Average Profit", f"{result['average_profit']:.4f}", result['average_profit'] >= 0)
        self.add_result_row("Median Profit", f"{result['median_profit']:.4f}", result['median_profit'] >= 0)
        self.add_result_row("Best Session", f"{result['best_session']:.4f}", True)
        self.add_result_row("Worst Session", f"{result['worst_session']:.4f}", False)
        self.add_result_row("Win Rate", f"{result['win_rate']:.2f}%")
        self.add_result_row("Bust Rate", f"{result['bust_rate']:.2f}%", False if result['bust_rate'] > 50 else None)
        self.add_result_row("Avg Bets / Session", f"{result['avg_bets']:.2f}")
        self.add_result_row("Longest Loss Streak", str(result['longest_loss_streak']))

    def run_monte_carlo(self, *args):
        self.results_grid.clear_widgets()
        bankroll = safe_float(self.mc_inputs["Bankroll"].text, 20)
        base_bet = safe_float(self.mc_inputs["Base Bet"].text, 0.1)
        multiplier = safe_float(self.mc_inputs["Multiplier"].text, 2.0)
        win_chance = safe_float(self.mc_inputs["Win Chance %"].text, 49.5)
        inc_on_win = safe_float(self.mc_inputs["Increase on Win %"].text, 0)
        inc_on_loss = safe_float(self.mc_inputs["Increase on Loss %"].text, 100)
        stop_profit = safe_float(self.mc_inputs["Stop Profit"].text, 0)
        stop_loss = safe_float(self.mc_inputs["Stop Loss"].text, 0)
        max_bets = safe_int(self.mc_inputs["Max Bets / Session"].text, 20)
        sessions = safe_int(self.mc_inputs["Number of Sessions"].text, 5000)
        if bankroll <= 0 or base_bet <= 0:
            self.summary.text = "Bankroll and Base Bet must be greater than 0"
            return
        if base_bet > bankroll:
            self.summary.text = "Base Bet cannot be greater than Bankroll"
            return
        self.run_btn.disabled = True
        self.progress_bar.max = max(1, sessions)
        self.progress_bar.value = 0
        self.status_lbl.text = "Status: Running Monte Carlo..."
        def worker():
            batch = max(10, sessions // 100)
            all_results=[]; busts=0; wins=0; total_bets=0; longest=0
            done=0
            while done < sessions:
                cur=min(batch, sessions-done)
                result = MonteCarloEngine.run_sessions(bankroll, base_bet, multiplier, win_chance, inc_on_win, inc_on_loss, stop_profit, stop_loss, max_bets, cur)
                # approximate aggregation by expanding session metrics
                all_results.extend([result['average_profit']]*cur)
                busts += result['bust_rate'] * cur / 100.0
                wins += result['win_rate'] * cur / 100.0
                total_bets += result['avg_bets'] * cur
                longest = max(longest, result['longest_loss_streak'])
                done += cur
                _ui_call(self._set_progress, done, f"Status: Running {done}/{sessions} sessions")
            final = {
                'sessions': sessions,
                'average_profit': statistics.mean(all_results) if all_results else 0.0,
                'median_profit': statistics.median(all_results) if all_results else 0.0,
                'best_session': max(all_results) if all_results else 0.0,
                'worst_session': min(all_results) if all_results else 0.0,
                'win_rate': (wins / sessions) * 100 if sessions else 0.0,
                'bust_rate': (busts / sessions) * 100 if sessions else 0.0,
                'avg_bets': total_bets / sessions if sessions else 0.0,
                'longest_loss_streak': longest,
            }
            _ui_call(self._finish_monte_carlo, final)
        threading.Thread(target=worker, daemon=True).start()


class KenoMonteCarloScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        outer = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))

        title = Label(
            text="KENO MONTE CARLO",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(36)
        )
        outer.add_widget(title)

        scroll = ScrollView()
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        inner.bind(minimum_height=inner.setter('height'))

        self.inputs = {}

        fields = [
            ("Bankroll", "20"),
            ("Base Bet", "0.1"),
            ("Picks", "10"),
            ("Hit Chance %", "28.0"),
            ("Small Multiplier", "3.5"),
            ("Medium Multiplier", "8"),
            ("Big Multiplier", "13"),
            ("Jackpot Multiplier", "63"),
            ("Increase on Loss %", "50"),
            ("Max Bets / Session", "11"),
            ("Number of Sessions", "5000"),
        ]

        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for label_text, default in fields:
            lbl = Label(
                text=label_text,
                color=get_color_from_hex(STAKE_TEXT),
                font_size='12sp',
                size_hint_y=None,
                height=dp(36)
            )
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(lbl)
            grid.add_widget(ti)

        inner.add_widget(grid)

        info = Label(
            text="Model: miss / small / medium / big / jackpot weighted outcome model",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(30)
        )
        inner.add_widget(info)

        self.run_btn = StyledButton(text="RUN KENO MONTE CARLO")
        self.run_btn.bind(on_release=self.run_keno_mc)
        inner.add_widget(self.run_btn)

        self.status_lbl = Label(text="Status: Idle", color=get_color_from_hex(STAKE_TEXT), font_size='11sp', size_hint_y=None, height=dp(22))
        inner.add_widget(self.status_lbl)
        self.progress_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(10))
        inner.add_widget(self.progress_bar)

        self.summary = Label(
            text="Results will appear here",
            color=get_color_from_hex(STAKE_GREEN),
            font_size='14sp',
            size_hint_y=None,
            height=dp(80)
        )
        inner.add_widget(self.summary)

        self.results_grid = GridLayout(cols=2, spacing=dp(4), size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        inner.add_widget(self.results_grid)

        scroll.add_widget(inner)
        outer.add_widget(scroll)
        outer.add_widget(SimpleNav())
        self.add_widget(outer)

    def add_result_row(self, label, value, good=None):
        color = get_color_from_hex(STAKE_TEXT)
        if good is True:
            color = get_color_from_hex(STAKE_GREEN)
        elif good is False:
            color = get_color_from_hex(STAKE_RED)

        self.results_grid.add_widget(Label(
            text=label,
            color=get_color_from_hex(STAKE_TEXT),
            size_hint_y=None,
            height=dp(28),
            font_size='12sp'
        ))
        self.results_grid.add_widget(Label(
            text=value,
            color=color,
            size_hint_y=None,
            height=dp(28),
            font_size='12sp'
        ))

    def weighted_keno_outcome(self, hit_chance):
        # hit_chance = total chance of "any paying hit"
        # split paying hits into 4 buckets to mimic your style:
        # small, medium, big, jackpot
        # You can tune these later if needed.

        hit_chance = max(0.0, min(100.0, hit_chance))
        pay_prob = hit_chance / 100.0
        miss_prob = 1.0 - pay_prob

        # Among paying hits:
        # 70% small, 20% medium, 8% big, 2% jackpot
        r = random.random()

        if r < miss_prob:
            return "miss"

        pay_roll = random.random()
        if pay_roll < 0.70:
            return "small"
        elif pay_roll < 0.90:
            return "medium"
        elif pay_roll < 0.98:
            return "big"
        else:
            return "jackpot"

    def _set_progress(self, value, text):
        self.progress_bar.value = value
        self.status_lbl.text = text

    def _finish_keno_mc(self, payload):
        self.run_btn.disabled = False
        self.progress_bar.value = self.progress_bar.max
        self.status_lbl.text = "Status: Complete"
        self.summary.text = f"Completed {payload['sessions']:,} Keno sessions"
        self.results_grid.clear_widgets()
        self.add_result_row("Picks", str(payload['picks']))
        self.add_result_row("Average Profit", f"{payload['avg_profit']:.4f}", payload['avg_profit'] >= 0)
        self.add_result_row("Median Profit", f"{payload['median_profit']:.4f}", payload['median_profit'] >= 0)
        self.add_result_row("Best Session", f"{payload['best_session']:.4f}", True)
        self.add_result_row("Worst Session", f"{payload['worst_session']:.4f}", False)
        self.add_result_row("Bust Rate", f"{payload['bust_rate']:.2f}%", False if payload['bust_rate'] > 50 else None)
        self.add_result_row("Profitable Sessions", f"{payload['profitable_rate']:.2f}%", True if payload['profitable_rate'] >= 50 else None)
        self.add_result_row("Avg Bets / Session", f"{payload['avg_bets']:.2f}")
        self.add_result_row("Longest Loss Streak", str(payload['longest_loss_streak_seen']))
        self.add_result_row("Total Paying Hits", str(payload['total_hits']))
        self.add_result_row("Small Hits", str(payload['small_hits']))
        self.add_result_row("Medium Hits", str(payload['medium_hits']))
        self.add_result_row("Big Hits", str(payload['big_hits']))
        self.add_result_row("Jackpot Hits", str(payload['jackpot_hits']))

    def run_keno_mc(self, *args):
        self.results_grid.clear_widgets()
        bankroll = safe_float(self.inputs["Bankroll"].text, 20)
        base_bet = safe_float(self.inputs["Base Bet"].text, 0.1)
        picks = safe_int(self.inputs["Picks"].text, 10)
        hit_chance = safe_float(self.inputs["Hit Chance %"].text, 28.0)
        small_mult = safe_float(self.inputs["Small Multiplier"].text, 3.5)
        medium_mult = safe_float(self.inputs["Medium Multiplier"].text, 8)
        big_mult = safe_float(self.inputs["Big Multiplier"].text, 13)
        jackpot_mult = safe_float(self.inputs["Jackpot Multiplier"].text, 63)
        inc_loss = safe_float(self.inputs["Increase on Loss %"].text, 50)
        max_bets = safe_int(self.inputs["Max Bets / Session"].text, 11)
        sessions = safe_int(self.inputs["Number of Sessions"].text, 5000)
        if bankroll <= 0 or base_bet <= 0:
            self.summary.text = "Bankroll and Base Bet must be greater than 0"; return
        if base_bet > bankroll:
            self.summary.text = "Base Bet cannot be greater than Bankroll"; return
        self.run_btn.disabled = True
        self.progress_bar.max = max(1, sessions)
        self.progress_bar.value = 0
        self.status_lbl.text = "Status: Running Keno Monte Carlo..."
        def worker():
            session_results=[]; busts=small_hits=medium_hits=big_hits=jackpot_hits=profitable_sessions=0; longest=0; total_bets=0
            for i in range(max(1, sessions)):
                balance=bankroll; bet=base_bet; session_profit=0.0; loss_streak=0; bets_used=0
                for _roll in range(max(1, max_bets)):
                    if bet <= 0 or bet > balance:
                        busts += 1; break
                    balance -= bet; bets_used += 1
                    outcome = self.weighted_keno_outcome(hit_chance)
                    if outcome == 'miss':
                        session_profit -= bet; loss_streak += 1; longest = max(longest, loss_streak); bet = bet * (1 + inc_loss / 100.0)
                    else:
                        loss_streak = 0
                        if outcome == 'small': payout = bet * small_mult; small_hits += 1
                        elif outcome == 'medium': payout = bet * medium_mult; medium_hits += 1
                        elif outcome == 'big': payout = bet * big_mult; big_hits += 1
                        else: payout = bet * jackpot_mult; jackpot_hits += 1
                        profit = payout - bet; balance += payout; session_profit += profit; break
                total_bets += bets_used; session_results.append(session_profit)
                if session_profit > 0: profitable_sessions += 1
                if (i+1) % max(1, sessions//100) == 0 or i == sessions-1:
                    _ui_call(self._set_progress, i+1, f"Status: Running {i+1}/{sessions} sessions")
            payload={
                'sessions': sessions, 'picks': picks,
                'avg_profit': statistics.mean(session_results) if session_results else 0.0,
                'median_profit': statistics.median(session_results) if session_results else 0.0,
                'best_session': max(session_results) if session_results else 0.0,
                'worst_session': min(session_results) if session_results else 0.0,
                'bust_rate': (busts/sessions)*100 if sessions else 0.0,
                'profitable_rate': (profitable_sessions/sessions)*100 if sessions else 0.0,
                'avg_bets': total_bets/sessions if sessions else 0.0,
                'longest_loss_streak_seen': longest,
                'total_hits': small_hits+medium_hits+big_hits+jackpot_hits,
                'small_hits': small_hits, 'medium_hits': medium_hits, 'big_hits': big_hits, 'jackpot_hits': jackpot_hits,
            }
            _ui_call(self._finish_keno_mc, payload)
        threading.Thread(target=worker, daemon=True).start()



class DiceOptimizerScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        outer = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))

        title = Label(
            text="DICE STRATEGY OPTIMIZER",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(36)
        )
        outer.add_widget(title)

        scroll = ScrollView()
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        inner.bind(minimum_height=inner.setter('height'))

        self.inputs = {}

        fields = [
            ("Bankroll", "20"),
            ("Win Chance %", "49.5"),
            ("Base Bet Start", "0.05"),
            ("Base Bet End", "0.20"),
            ("Base Bet Step", "0.05"),
            ("Multiplier Start", "2.0"),
            ("Multiplier End", "3.5"),
            ("Multiplier Step", "0.5"),
            ("Loss % Start", "20"),
            ("Loss % End", "60"),
            ("Loss % Step", "10"),
            ("Max Bets / Session", "12"),
            ("Sessions / Test", "1000"),
            ("Top Results", "10"),
        ]

        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for label_text, default in fields:
            lbl = Label(
                text=label_text,
                color=get_color_from_hex(STAKE_TEXT),
                font_size='12sp',
                size_hint_y=None,
                height=dp(36)
            )
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(lbl)
            grid.add_widget(ti)

        inner.add_widget(grid)

        # Simulation Quality
        quality_row = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(40))
        quality_row.add_widget(Label(
            text="Simulation Quality",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='12sp'
        ))
        self.quality_spinner = Spinner(
            text='Balanced',
            values=('Fast', 'Balanced', 'Accurate', 'Extreme'),
            size_hint_y=None,
            height=dp(38),
            background_normal='',
            background_color=get_color_from_hex(STAKE_INPUT),
            color=(1, 1, 1, 1)
        )
        quality_row.add_widget(self.quality_spinner)
        inner.add_widget(quality_row)

        # Optimize For
        goal_row = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(40))
        goal_row.add_widget(Label(
            text="Optimize For",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='12sp'
        ))
        self.goal_spinner = Spinner(
            text='Profit/Risk',
            values=('Profit', 'Safety', 'Profit/Risk'),
            size_hint_y=None,
            height=dp(38),
            background_normal='',
            background_color=get_color_from_hex(STAKE_INPUT),
            color=(1, 1, 1, 1)
        )
        goal_row.add_widget(self.goal_spinner)
        inner.add_widget(goal_row)

        info = Label(
            text="Tests multiple Dice progression combinations and ranks the best results",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(30)
        )
        inner.add_widget(info)

        self.run_btn = StyledButton(text="RUN OPTIMIZER")
        self.run_btn.bind(on_release=self.run_optimizer)
        inner.add_widget(self.run_btn)

        self.status_lbl = Label(text="Status: Idle", color=get_color_from_hex(STAKE_TEXT), font_size='11sp', size_hint_y=None, height=dp(22))
        inner.add_widget(self.status_lbl)
        self.progress_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(10))
        inner.add_widget(self.progress_bar)

        self.summary = Label(
            text="Optimizer results will appear here",
            color=get_color_from_hex(STAKE_GREEN),
            font_size='14sp',
            size_hint_y=None,
            height=dp(80)
        )
        inner.add_widget(self.summary)

        self.results_grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        inner.add_widget(self.results_grid)

        scroll.add_widget(inner)
        outer.add_widget(scroll)
        outer.add_widget(SimpleNav())
        self.add_widget(outer)

    def frange(self, start, end, step):
        vals = []
        if step <= 0:
            return [start]
        x = start
        while x <= end + 1e-9:
            vals.append(round(x, 8))
            x += step
        return vals

    def get_sessions_for_quality(self):
        quality = self.quality_spinner.text
        if quality == "Fast":
            return 1000
        elif quality == "Balanced":
            return 5000
        elif quality == "Accurate":
            return 20000
        else:
            return 50000

    def compute_score(self, avg_profit, bust_rate, win_rate):
        goal = self.goal_spinner.text

        if goal == "Profit":
            return avg_profit

        elif goal == "Safety":
            # reward low bust + decent win rate
            return (win_rate * 0.2) - (bust_rate * 3.0)

        else:  # Profit/Risk
            # reward profit but penalize bust strongly
            return avg_profit - (bust_rate * 0.25)

    def add_result_card(self, rank, item):
        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(118),
            padding=dp(8),
            spacing=dp(3)
        )

        def update_rect(instance, value):
            if hasattr(instance, '_bg_rect'):
                instance._bg_rect.pos = instance.pos
                instance._bg_rect.size = instance.size

        with card.canvas.before:
            Color(rgba=get_color_from_hex(STAKE_INPUT))
            card._bg_rect = Rectangle(pos=card.pos, size=card.size)

        card.bind(pos=update_rect, size=update_rect)

        title = Label(
            text=f"#{rank} | Avg {item['avg_profit']:.4f} | Bust {item['bust_rate']:.2f}%",
            color=get_color_from_hex(STAKE_GREEN),
            bold=True,
            font_size='12sp',
            size_hint_y=None,
            height=dp(24)
        )

        row1 = Label(
            text=f"Base: {item['base_bet']} | Multi: {item['multiplier']} | Loss+: {item['loss_pct']}%",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row2 = Label(
            text=f"Win Rate: {item['win_rate']:.2f}% | Max Bets: {item['max_bets']} | Longest LS: {item['longest_ls']}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row3 = Label(
            text=f"Median: {item['median_profit']:.4f} | Best: {item['best_session']:.4f} | Worst: {item['worst_session']:.4f}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row4 = Label(
            text=f"Score: {item['score']:.4f} | Quality: {self.quality_spinner.text} | Goal: {self.goal_spinner.text}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='10sp',
            size_hint_y=None,
            height=dp(18)
        )

        card.add_widget(title)
        card.add_widget(row1)
        card.add_widget(row2)
        card.add_widget(row3)
        card.add_widget(row4)

        self.results_grid.add_widget(card)

    def _set_progress(self, value, text):
        self.progress_bar.value = value
        self.status_lbl.text = text

    def _finish_optimizer(self, combos, top_results):
        self.run_btn.disabled = False
        self.progress_bar.value = self.progress_bar.max
        self.status_lbl.text = "Status: Complete"
        self.results_grid.clear_widgets()
        combos.sort(key=lambda x: x["score"], reverse=True)
        show_n = max(1, min(top_results, len(combos)))
        self.summary.text = (
            f"Tested {len(combos)} combinations | "
            f"Showing top {show_n} | "
            f"Quality: {self.quality_spinner.text} | "
            f"Goal: {self.goal_spinner.text}"
        )
        for i, item in enumerate(combos[:show_n], start=1):
            self.add_result_card(i, item)

    def run_optimizer(self, *args):
        self.results_grid.clear_widgets()
        bankroll = safe_float(self.inputs["Bankroll"].text, 20)
        win_chance = safe_float(self.inputs["Win Chance %"].text, 49.5)
        base_start = safe_float(self.inputs["Base Bet Start"].text, 0.05)
        base_end = safe_float(self.inputs["Base Bet End"].text, 0.20)
        base_step = safe_float(self.inputs["Base Bet Step"].text, 0.05)
        multi_start = safe_float(self.inputs["Multiplier Start"].text, 2.0)
        multi_end = safe_float(self.inputs["Multiplier End"].text, 3.5)
        multi_step = safe_float(self.inputs["Multiplier Step"].text, 0.5)
        loss_start = safe_float(self.inputs["Loss % Start"].text, 20)
        loss_end = safe_float(self.inputs["Loss % End"].text, 60)
        loss_step = safe_float(self.inputs["Loss % Step"].text, 10)
        max_bets = safe_int(self.inputs["Max Bets / Session"].text, 12)
        manual_sessions = safe_int(self.inputs["Sessions / Test"].text, 1000)
        top_results = safe_int(self.inputs["Top Results"].text, 10)
        if bankroll <= 0:
            self.summary.text = "Bankroll must be greater than 0"
            return
        sessions_per_test = self.get_sessions_for_quality()
        if manual_sessions > 0:
            sessions_per_test = manual_sessions if self.quality_spinner.text == "Fast" else sessions_per_test
        combos_to_test=[]
        for base_bet in self.frange(base_start, base_end, base_step):
            for multiplier in self.frange(multi_start, multi_end, multi_step):
                for loss_pct in self.frange(loss_start, loss_end, loss_step):
                    if base_bet <= bankroll:
                        combos_to_test.append((base_bet, multiplier, loss_pct))
        self.run_btn.disabled = True
        self.progress_bar.max = max(1, len(combos_to_test))
        self.progress_bar.value = 0
        self.status_lbl.text = "Status: Running optimizer..."
        def worker():
            combos=[]
            total=len(combos_to_test)
            for idx,(base_bet,multiplier,loss_pct) in enumerate(combos_to_test, start=1):
                result = MonteCarloEngine.run_sessions(
                    bankroll=bankroll, base_bet=base_bet, multiplier=multiplier, win_chance=win_chance,
                    inc_on_win=0, inc_on_loss=loss_pct, stop_profit=0, stop_loss=0,
                    max_bets=max_bets, sessions=sessions_per_test)
                score = self.compute_score(result['average_profit'], result['bust_rate'], result['win_rate'])
                combos.append({
                    'base_bet': base_bet, 'multiplier': multiplier, 'loss_pct': loss_pct, 'max_bets': max_bets,
                    'avg_profit': result['average_profit'], 'median_profit': result['median_profit'],
                    'best_session': result['best_session'], 'worst_session': result['worst_session'],
                    'win_rate': result['win_rate'], 'bust_rate': result['bust_rate'],
                    'longest_ls': result['longest_loss_streak'], 'score': score,
                })
                if idx % max(1, total//100) == 0 or idx == total:
                    _ui_call(self._set_progress, idx, f"Status: Testing {idx}/{total} combos")
            _ui_call(self._finish_optimizer, combos, top_results)
        threading.Thread(target=worker, daemon=True).start()

class DiceAutoGeneratorScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        outer = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))

        title = Label(
            text="DICE AUTO GENERATOR",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(36)
        )
        outer.add_widget(title)

        scroll = ScrollView()
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        inner.bind(minimum_height=inner.setter('height'))

        self.inputs = {}

        fields = [
            ("Bankroll", "20"),
            ("Win Chance %", "49.5"),
            ("Strategies To Generate", "100"),
            ("Sessions / Strategy", "2000"),
            ("Max Bets / Session", "12"),
            ("Top Results", "10"),
        ]

        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for label_text, default in fields:
            lbl = Label(
                text=label_text,
                color=get_color_from_hex(STAKE_TEXT),
                font_size='12sp',
                size_hint_y=None,
                height=dp(36)
            )
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(lbl)
            grid.add_widget(ti)

        inner.add_widget(grid)

        goal_row = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(40))
        goal_row.add_widget(Label(
            text="Optimize For",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='12sp'
        ))
        self.goal_spinner = Spinner(
            text='Profit/Risk',
            values=('Profit', 'Safety', 'Profit/Risk'),
            size_hint_y=None,
            height=dp(38),
            background_normal='',
            background_color=get_color_from_hex(STAKE_INPUT),
            color=(1, 1, 1, 1)
        )
        goal_row.add_widget(self.goal_spinner)
        inner.add_widget(goal_row)

        info = Label(
            text="Generates random Dice strategies and keeps the strongest results",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(30)
        )
        inner.add_widget(info)

        self.run_btn = StyledButton(text="RUN AUTO GENERATOR")
        self.run_btn.bind(on_release=self.run_generator)
        inner.add_widget(self.run_btn)

        self.status_lbl = Label(text="Status: Idle", color=get_color_from_hex(STAKE_TEXT), font_size='11sp', size_hint_y=None, height=dp(22))
        inner.add_widget(self.status_lbl)
        self.progress_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(10))
        inner.add_widget(self.progress_bar)

        self.summary = Label(
            text="Generated strategy results will appear here",
            color=get_color_from_hex(STAKE_GREEN),
            font_size='14sp',
            size_hint_y=None,
            height=dp(80)
        )
        inner.add_widget(self.summary)

        self.results_grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        inner.add_widget(self.results_grid)

        scroll.add_widget(inner)
        outer.add_widget(scroll)
        outer.add_widget(SimpleNav())
        self.add_widget(outer)

    def compute_score(self, avg_profit, bust_rate, win_rate):
        goal = self.goal_spinner.text

        if goal == "Profit":
            return avg_profit
        elif goal == "Safety":
            return (win_rate * 0.2) - (bust_rate * 3.0)
        else:
            return avg_profit - (bust_rate * 0.25)

    def random_strategy(self, bankroll):
        base_bet = round(random.uniform(0.01, min(0.25, bankroll * 0.02)), 4)
        multiplier = round(random.uniform(1.8, 5.0), 2)
        loss_pct = round(random.uniform(10, 80), 2)
        return {
            "base_bet": base_bet,
            "multiplier": multiplier,
            "loss_pct": loss_pct,
        }

    def save_generated_strategy(self, item, rank):
        strategy = normalize_strategy({
            "name": f"DICE GEN | B{item['base_bet']} M{item['multiplier']} L{item['loss_pct']}",
            "category": "Dice Auto Generator",
            "game": "dice",
            "source": "auto_generator",
            "bank": str(self.inputs["Bankroll"].text),
            "base": str(item["base_bet"]),
            "multi": str(item["multiplier"]),
            "win_action": "Reset",
            "loss_action": f"Increase {item['loss_pct']}%",
            "max_bets": str(item["max_bets"]),
            "notes": (
                f"Saved from Auto Generator | Rank #{rank} | "
                f"Avg {item['avg_profit']:.4f} | "
                f"Bust {item['bust_rate']:.2f}% | "
                f"Score {item['score']:.4f} | "
                f"Goal {self.goal_spinner.text}"
            )
        })

        GLOBAL_BANK.strategies.append(strategy)
        GLOBAL_BANK.save_strategies()

        Popup(
            title="Saved",
            content=Label(text=f"Saved:\n{strategy['name']}"),
            size_hint=(0.75, 0.25)
        ).open()

    def add_result_card(self, rank, item):
        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(156),
            padding=dp(8),
            spacing=dp(3)
        )

        def update_rect(instance, value):
            if hasattr(instance, '_bg_rect'):
                instance._bg_rect.pos = instance.pos
                instance._bg_rect.size = instance.size

        with card.canvas.before:
            Color(rgba=get_color_from_hex(STAKE_INPUT))
            card._bg_rect = Rectangle(pos=card.pos, size=card.size)

        card.bind(pos=update_rect, size=update_rect)

        title = Label(
            text=f"#{rank} | Avg {item['avg_profit']:.4f} | Bust {item['bust_rate']:.2f}%",
            color=get_color_from_hex(STAKE_GREEN),
            bold=True,
            font_size='12sp',
            size_hint_y=None,
            height=dp(24)
        )

        row1 = Label(
            text=f"Base: {item['base_bet']} | Multi: {item['multiplier']} | Loss+: {item['loss_pct']}%",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row2 = Label(
            text=f"Win Rate: {item['win_rate']:.2f}% | Max Bets: {item['max_bets']} | Longest LS: {item['longest_ls']}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row3 = Label(
            text=f"Median: {item['median_profit']:.4f} | Best: {item['best_session']:.4f} | Worst: {item['worst_session']:.4f}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row4 = Label(
            text=f"Score: {item['score']:.4f} | Goal: {self.goal_spinner.text}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='10sp',
            size_hint_y=None,
            height=dp(18)
        )

        save_btn = StyledButton(
            text="SAVE TO LIBRARY",
            bg_color="#2c3e50",
            height=dp(34)
        )
        save_btn.color = (1, 1, 1, 1)
        save_btn.bind(on_release=lambda x: self.save_generated_strategy(item, rank))

        card.add_widget(title)
        card.add_widget(row1)
        card.add_widget(row2)
        card.add_widget(row3)
        card.add_widget(row4)
        card.add_widget(save_btn)

        self.results_grid.add_widget(card)

    def _set_progress(self, value, text):
        self.progress_bar.value = value
        self.status_lbl.text = text

    def _finish_generator(self, results, top_results):
        self.run_btn.disabled = False
        self.progress_bar.value = self.progress_bar.max
        self.status_lbl.text = "Status: Complete"
        results.sort(key=lambda x: x["score"], reverse=True)
        show_n = max(1, min(top_results, len(results)))
        self.summary.text = (
            f"Generated {len(results)} random strategies | "
            f"Showing top {show_n} | "
            f"Goal: {self.goal_spinner.text}"
        )
        self.results_grid.clear_widgets()
        for i, item in enumerate(results[:show_n], start=1):
            self.add_result_card(i, item)

    def run_generator(self, *args):
        self.results_grid.clear_widgets()
        bankroll = safe_float(self.inputs["Bankroll"].text, 20)
        win_chance = safe_float(self.inputs["Win Chance %"].text, 49.5)
        strategies_to_generate = safe_int(self.inputs["Strategies To Generate"].text, 100)
        sessions_per_strategy = safe_int(self.inputs["Sessions / Strategy"].text, 2000)
        max_bets = safe_int(self.inputs["Max Bets / Session"].text, 12)
        top_results = safe_int(self.inputs["Top Results"].text, 10)
        if bankroll <= 0:
            self.summary.text = "Bankroll must be greater than 0"; return
        self.run_btn.disabled = True
        self.progress_bar.max = max(1, strategies_to_generate)
        self.progress_bar.value = 0
        self.status_lbl.text = "Status: Generating strategies..."
        def worker():
            results=[]
            total=max(1, strategies_to_generate)
            for idx in range(total):
                strat=self.random_strategy(bankroll)
                result = MonteCarloEngine.run_sessions(bankroll, strat['base_bet'], strat['multiplier'], win_chance, 0, strat['loss_pct'], 0, 0, max_bets, sessions_per_strategy)
                score=self.compute_score(result['average_profit'], result['bust_rate'], result['win_rate'])
                results.append({
                    'base_bet': strat['base_bet'], 'multiplier': strat['multiplier'], 'loss_pct': strat['loss_pct'], 'max_bets': max_bets,
                    'avg_profit': result['average_profit'], 'median_profit': result['median_profit'], 'best_session': result['best_session'],
                    'worst_session': result['worst_session'], 'win_rate': result['win_rate'], 'bust_rate': result['bust_rate'], 'longest_ls': result['longest_loss_streak'], 'score': score,
                })
                if (idx+1) % max(1, total//100) == 0 or idx+1 == total:
                    _ui_call(self._set_progress, idx+1, f"Status: Generated {idx+1}/{total}")
            _ui_call(self._finish_generator, results, top_results)
        threading.Thread(target=worker, daemon=True).start()

class DiceEvolutionScreen(Screen):                                                                                 
    def __init__(self, **kw):
        super().__init__(**kw)

        outer = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))

        title = Label(
            text="DICE EVOLUTION ENGINE",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(36)
        )
        outer.add_widget(title)

        scroll = ScrollView()
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        inner.bind(minimum_height=inner.setter('height'))

        self.inputs = {}

        fields = [
            ("Bankroll", "20"),
            ("Win Chance %", "49.5"),
            ("Population Size", "40"),
            ("Generations", "5"),
            ("Elite Keep", "8"),
            ("Children Per Generation", "40"),
            ("Sessions / Strategy", "2000"),
            ("Max Bets / Session", "12"),
            ("Top Results", "10"),
        ]

        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for label_text, default in fields:
            lbl = Label(
                text=label_text,
                color=get_color_from_hex(STAKE_TEXT),
                font_size='12sp',
                size_hint_y=None,
                height=dp(36)
            )
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(lbl)
            grid.add_widget(ti)

        inner.add_widget(grid)

        goal_row = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(40))
        goal_row.add_widget(Label(
            text="Optimize For",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='12sp'
        ))
        self.goal_spinner = Spinner(
            text='Profit/Risk',
            values=('Profit', 'Safety', 'Profit/Risk'),
            size_hint_y=None,
            height=dp(38),
            background_normal='',
            background_color=get_color_from_hex(STAKE_INPUT),
            color=(1, 1, 1, 1)
        )
        goal_row.add_widget(self.goal_spinner)
        inner.add_widget(goal_row)

        info = Label(
            text="Evolves Dice strategies across generations using mutation and elite selection",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(30)
        )
        inner.add_widget(info)

        self.run_btn = StyledButton(text="RUN EVOLUTION")
        self.run_btn.bind(on_release=self.run_evolution)
        inner.add_widget(self.run_btn)

        self.status_lbl = Label(text="Status: Idle", color=get_color_from_hex(STAKE_TEXT), font_size='11sp', size_hint_y=None, height=dp(22))
        inner.add_widget(self.status_lbl)
        self.progress_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(10))
        inner.add_widget(self.progress_bar)

        self.summary = Label(
            text="Evolution results will appear here",
            color=get_color_from_hex(STAKE_GREEN),
            font_size='14sp',
            size_hint_y=None,
            height=dp(80)
        )
        inner.add_widget(self.summary)

        self.results_grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        inner.add_widget(self.results_grid)

        scroll.add_widget(inner)
        outer.add_widget(scroll)
        outer.add_widget(SimpleNav())
        self.add_widget(outer)

    def compute_score(self, avg_profit, bust_rate, win_rate):
        goal = self.goal_spinner.text
        if goal == "Profit":
            return avg_profit
        elif goal == "Safety":
            return (win_rate * 0.2) - (bust_rate * 3.0)
        else:
            return avg_profit - (bust_rate * 0.25)

    def random_strategy(self, bankroll):
        base_bet = round(random.uniform(0.01, min(0.25, bankroll * 0.02)), 4)
        multiplier = round(random.uniform(1.8, 5.0), 2)
        loss_pct = round(random.uniform(10, 80), 2)
        return {
            "base_bet": base_bet,
            "multiplier": multiplier,
            "loss_pct": loss_pct,
        }

    def mutate_strategy(self, parent, bankroll):
        new_base = round(parent["base_bet"] * random.uniform(0.85, 1.15), 4)
        new_multi = round(parent["multiplier"] * random.uniform(0.90, 1.10), 2)
        new_loss = round(parent["loss_pct"] * random.uniform(0.85, 1.15), 2)

        new_base = max(0.01, min(new_base, min(0.25, bankroll * 0.02)))
        new_multi = max(1.5, min(new_multi, 6.0))
        new_loss = max(5.0, min(new_loss, 100.0))

        return {
            "base_bet": new_base,
            "multiplier": new_multi,
            "loss_pct": new_loss,
        }

    def evaluate_strategy(self, strat, bankroll, win_chance, max_bets, sessions_per_strategy):
        result = MonteCarloEngine.run_sessions(
            bankroll=bankroll,
            base_bet=strat["base_bet"],
            multiplier=strat["multiplier"],
            win_chance=win_chance,
            inc_on_win=0,
            inc_on_loss=strat["loss_pct"],
            stop_profit=0,
            stop_loss=0,
            max_bets=max_bets,
            sessions=sessions_per_strategy,
        )

        score = self.compute_score(
            avg_profit=result["average_profit"],
            bust_rate=result["bust_rate"],
            win_rate=result["win_rate"]
        )

        return {
            "base_bet": strat["base_bet"],
            "multiplier": strat["multiplier"],
            "loss_pct": strat["loss_pct"],
            "max_bets": max_bets,
            "avg_profit": result["average_profit"],
            "median_profit": result["median_profit"],
            "best_session": result["best_session"],
            "worst_session": result["worst_session"],
            "win_rate": result["win_rate"],
            "bust_rate": result["bust_rate"],
            "longest_ls": result["longest_loss_streak"],
            "score": score,
        }

    def save_evolved_strategy(self, item, rank):
        strategy = normalize_strategy({
            "name": f"DICE EVO | B{item['base_bet']} M{item['multiplier']} L{item['loss_pct']}",
            "category": "Experimental",
            "game": "dice",
            "source": "evolution_engine",
            "bank": str(self.inputs["Bankroll"].text),
            "base": str(item["base_bet"]),
            "multi": str(item["multiplier"]),
            "win_action": "Reset",
            "loss_action": f"Increase {item['loss_pct']}%",
            "max_bets": str(item["max_bets"]),
            "notes": (
                f"Saved from Evolution Engine | Rank #{rank} | "
                f"Avg {item['avg_profit']:.4f} | "
                f"Bust {item['bust_rate']:.2f}% | "
                f"Score {item['score']:.4f} | "
                f"Goal {self.goal_spinner.text}"
            )
        })

        GLOBAL_BANK.strategies.append(strategy)
        GLOBAL_BANK.save_strategies()

        Popup(
            title="Saved",
            content=Label(text=f"Saved:\n{strategy['name']}"),
            size_hint=(0.75, 0.25)
        ).open()

    def add_result_card(self, rank, item):
        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(156),
            padding=dp(8),
            spacing=dp(3)
        )

        def update_rect(instance, value):
            if hasattr(instance, '_bg_rect'):
                instance._bg_rect.pos = instance.pos
                instance._bg_rect.size = instance.size

        with card.canvas.before:
            Color(rgba=get_color_from_hex(STAKE_INPUT))
            card._bg_rect = Rectangle(pos=card.pos, size=card.size)

        card.bind(pos=update_rect, size=update_rect)

        title = Label(
            text=f"#{rank} | Avg {item['avg_profit']:.4f} | Bust {item['bust_rate']:.2f}%",
            color=get_color_from_hex(STAKE_GREEN),
            bold=True,
            font_size='12sp',
            size_hint_y=None,
            height=dp(24)
        )

        row1 = Label(
            text=f"Base: {item['base_bet']} | Multi: {item['multiplier']} | Loss+: {item['loss_pct']}%",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row2 = Label(
            text=f"Win Rate: {item['win_rate']:.2f}% | Max Bets: {item['max_bets']} | Longest LS: {item['longest_ls']}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row3 = Label(
            text=f"Median: {item['median_profit']:.4f} | Best: {item['best_session']:.4f} | Worst: {item['worst_session']:.4f}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row4 = Label(
            text=f"Score: {item['score']:.4f} | Goal: {self.goal_spinner.text}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='10sp',
            size_hint_y=None,
            height=dp(18)
        )

        save_btn = StyledButton(
            text="SAVE TO LIBRARY",
            bg_color="#2c3e50",
            height=dp(34)
        )
        save_btn.color = (1, 1, 1, 1)
        save_btn.bind(on_release=lambda x: self.save_evolved_strategy(item, rank))

        card.add_widget(title)
        card.add_widget(row1)
        card.add_widget(row2)
        card.add_widget(row3)
        card.add_widget(row4)
        card.add_widget(save_btn)

        self.results_grid.add_widget(card)

    def _set_progress(self, value, text):
        self.progress_bar.value = value
        self.status_lbl.text = text

    def _finish_evolution(self, unique_results, generations, top_results):
        self.run_btn.disabled = False
        self.progress_bar.value = self.progress_bar.max
        self.status_lbl.text = "Status: Complete"
        show_n = max(1, min(top_results, len(unique_results)))
        self.summary.text = f"Evolved across {generations} generations | Showing top {show_n} | Goal: {self.goal_spinner.text}"
        self.results_grid.clear_widgets()
        for i, item in enumerate(unique_results[:show_n], start=1):
            self.add_result_card(i, item)

    def run_evolution(self, *args):
        self.results_grid.clear_widgets()
        bankroll = safe_float(self.inputs["Bankroll"].text, 20)
        win_chance = safe_float(self.inputs["Win Chance %"].text, 49.5)
        population_size = safe_int(self.inputs["Population Size"].text, 40)
        generations = safe_int(self.inputs["Generations"].text, 5)
        elite_keep = safe_int(self.inputs["Elite Keep"].text, 8)
        children_per_generation = safe_int(self.inputs["Children Per Generation"].text, 40)
        sessions_per_strategy = safe_int(self.inputs["Sessions / Strategy"].text, 2000)
        max_bets = safe_int(self.inputs["Max Bets / Session"].text, 12)
        top_results = safe_int(self.inputs["Top Results"].text, 10)
        if bankroll <= 0: self.summary.text = "Bankroll must be greater than 0"; return
        self.run_btn.disabled = True
        self.progress_bar.max = max(1, generations * max(2, population_size))
        self.progress_bar.value = 0
        self.status_lbl.text = "Status: Running evolution..."
        def worker():
            population=[self.random_strategy(bankroll) for _ in range(max(2,population_size))]
            best_overall=[]; progress=0
            for gen in range(max(1, generations)):
                evaluated=[]
                for s in population:
                    evaluated.append(self.evaluate_strategy(s, bankroll, win_chance, max_bets, sessions_per_strategy))
                    progress += 1
                    if progress % max(1, self.progress_bar.max//100) == 0 or progress == self.progress_bar.max:
                        _ui_call(self._set_progress, progress, f"Status: Generation {gen+1}/{generations}")
                evaluated.sort(key=lambda x: x['score'], reverse=True)
                elites=evaluated[:max(1, elite_keep)]
                best_overall.extend(elites)
                elite_strats=[{'base_bet':e['base_bet'],'multiplier':e['multiplier'],'loss_pct':e['loss_pct']} for e in elites]
                population=[]
                while len(population) < max(2, children_per_generation):
                    population.append(self.mutate_strategy(random.choice(elite_strats), bankroll))
            best_overall.sort(key=lambda x: x['score'], reverse=True)
            seen=set(); unique_results=[]
            for item in best_overall:
                key=(round(item['base_bet'],4), round(item['multiplier'],2), round(item['loss_pct'],2))
                if key not in seen:
                    seen.add(key); unique_results.append(item)
            _ui_call(self._finish_evolution, unique_results, generations, top_results)
        threading.Thread(target=worker, daemon=True).start()
class LimboEvolutionScreen(Screen):                                                                                              
    def __init__(self, **kw):
        super().__init__(**kw)

        outer = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))

        title = Label(
            text="LIMBO EVOLUTION ENGINE",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(36)
        )
        outer.add_widget(title)

        scroll = ScrollView()
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        inner.bind(minimum_height=inner.setter('height'))

        self.inputs = {}

        fields = [
            ("Bankroll", "20"),
            ("Population Size", "40"),
            ("Generations", "5"),
            ("Elite Keep", "8"),
            ("Children Per Generation", "40"),
            ("Sessions / Strategy", "2000"),
            ("Max Bets / Session", "12"),
            ("Top Results", "10"),
        ]

        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for label_text, default in fields:
            lbl = Label(
                text=label_text,
                color=get_color_from_hex(STAKE_TEXT),
                font_size='12sp',
                size_hint_y=None,
                height=dp(36)
            )
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(lbl)
            grid.add_widget(ti)

        inner.add_widget(grid)

        goal_row = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(40))
        goal_row.add_widget(Label(
            text="Optimize For",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='12sp'
        ))
        self.goal_spinner = Spinner(
            text='Profit/Risk',
            values=('Profit', 'Safety', 'Profit/Risk'),
            size_hint_y=None,
            height=dp(38),
            background_normal='',
            background_color=get_color_from_hex(STAKE_INPUT),
            color=(1, 1, 1, 1)
        )
        goal_row.add_widget(self.goal_spinner)
        inner.add_widget(goal_row)

        info = Label(
            text="Evolves Limbo strategies across generations using mutation and elite selection",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(30)
        )
        inner.add_widget(info)

        self.run_btn = StyledButton(text="RUN LIMBO EVOLUTION")
        self.run_btn.bind(on_release=self.run_evolution)
        inner.add_widget(self.run_btn)

        self.status_lbl = Label(text="Status: Idle", color=get_color_from_hex(STAKE_TEXT), font_size='11sp', size_hint_y=None, height=dp(22))
        inner.add_widget(self.status_lbl)
        self.progress_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(10))
        inner.add_widget(self.progress_bar)

        self.summary = Label(
            text="Limbo evolution results will appear here",
            color=get_color_from_hex(STAKE_GREEN),
            font_size='14sp',
            size_hint_y=None,
            height=dp(80)
        )
        inner.add_widget(self.summary)

        self.results_grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        inner.add_widget(self.results_grid)

        scroll.add_widget(inner)
        outer.add_widget(scroll)
        outer.add_widget(SimpleNav())
        self.add_widget(outer)

    def compute_score(self, avg_profit, bust_rate, win_rate):
        goal = self.goal_spinner.text
        if goal == "Profit":
            return avg_profit
        elif goal == "Safety":
            return (win_rate * 0.2) - (bust_rate * 3.0)
        else:
            return avg_profit - (bust_rate * 0.25)

    def random_strategy(self, bankroll):
        base_bet = round(random.uniform(0.01, min(0.25, bankroll * 0.02)), 4)
        target_multiplier = round(random.uniform(1.5, 15.0), 2)
        loss_pct = round(random.uniform(5, 80), 2)
        return {
            "base_bet": base_bet,
            "target_multiplier": target_multiplier,
            "loss_pct": loss_pct,
        }

    def mutate_strategy(self, parent, bankroll):
        new_base = round(parent["base_bet"] * random.uniform(0.85, 1.15), 4)
        new_multi = round(parent["target_multiplier"] * random.uniform(0.90, 1.10), 2)
        new_loss = round(parent["loss_pct"] * random.uniform(0.85, 1.15), 2)

        new_base = max(0.01, min(new_base, min(0.25, bankroll * 0.02)))
        new_multi = max(1.2, min(new_multi, 25.0))
        new_loss = max(1.0, min(new_loss, 100.0))

        return {
            "base_bet": new_base,
            "target_multiplier": new_multi,
            "loss_pct": new_loss,
        }

    def run_limbo_sessions(self, bankroll, base_bet, target_multiplier, inc_on_loss, max_bets, sessions):
        results = []
        busts = 0
        winning_sessions = 0
        total_bets_all = 0
        longest_loss_streak_seen = 0

        bankroll = max(0.00000001, bankroll)
        base_bet = max(0.00000001, base_bet)
        target_multiplier = max(1.01, target_multiplier)
        inc_on_loss = max(-100.0, inc_on_loss)
        max_bets = max(1, max_bets)
        sessions = max(1, sessions)

        win_chance = min(99.0, max(0.01, 99.0 / target_multiplier))

        for _ in range(sessions):
            balance = bankroll
            current_bet = base_bet
            session_profit = 0.0
            bets_used = 0
            loss_streak = 0
            busted = False

            for _roll in range(max_bets):
                if current_bet <= 0 or current_bet > balance:
                    busted = True
                    busts += 1
                    break

                bets_used += 1
                balance -= current_bet

                roll = random.uniform(0, 100.0)
                is_win = roll < win_chance

                if is_win:
                    payout = current_bet * target_multiplier
                    net_profit = payout - current_bet
                    balance += payout
                    session_profit += net_profit
                    loss_streak = 0
                    current_bet = base_bet
                else:
                    session_profit -= current_bet
                    loss_streak += 1
                    longest_loss_streak_seen = max(longest_loss_streak_seen, loss_streak)
                    current_bet = current_bet * (1 + inc_on_loss / 100.0)

            total_bets_all += bets_used
            results.append(session_profit)

            if session_profit > 0:
                winning_sessions += 1

        avg_profit = statistics.mean(results) if results else 0.0
        median_profit = statistics.median(results) if results else 0.0
        best_session = max(results) if results else 0.0
        worst_session = min(results) if results else 0.0
        win_rate = (winning_sessions / sessions) * 100 if sessions else 0.0
        bust_rate = (busts / sessions) * 100 if sessions else 0.0

        return {
            "average_profit": avg_profit,
            "median_profit": median_profit,
            "best_session": best_session,
            "worst_session": worst_session,
            "win_rate": win_rate,
            "bust_rate": bust_rate,
            "longest_loss_streak": longest_loss_streak_seen,
        }

    def evaluate_strategy(self, strat, bankroll, max_bets, sessions_per_strategy):
        result = self.run_limbo_sessions(
            bankroll=bankroll,
            base_bet=strat["base_bet"],
            target_multiplier=strat["target_multiplier"],
            inc_on_loss=strat["loss_pct"],
            max_bets=max_bets,
            sessions=sessions_per_strategy,
        )

        score = self.compute_score(
            avg_profit=result["average_profit"],
            bust_rate=result["bust_rate"],
            win_rate=result["win_rate"]
        )

        return {
            "base_bet": strat["base_bet"],
            "target_multiplier": strat["target_multiplier"],
            "loss_pct": strat["loss_pct"],
            "max_bets": max_bets,
            "avg_profit": result["average_profit"],
            "median_profit": result["median_profit"],
            "best_session": result["best_session"],
            "worst_session": result["worst_session"],
            "win_rate": result["win_rate"],
            "bust_rate": result["bust_rate"],
            "longest_ls": result["longest_loss_streak"],
            "score": score,
        }

    def save_evolved_strategy(self, item, rank):
        strategy = normalize_strategy({
            "name": f"LIMBO EVO | B{item['base_bet']} M{item['target_multiplier']} L{item['loss_pct']}",
            "category": "Experimental",
            "game": "limbo",
            "source": "evolution_engine",
            "bank": str(self.inputs["Bankroll"].text),
            "base": str(item["base_bet"]),
            "multi": str(item["target_multiplier"]),
            "win_action": "Reset",
            "loss_action": f"Increase {item['loss_pct']}%",
            "max_bets": str(item["max_bets"]),
            "notes": (
                f"Saved from Limbo Evolution Engine | Rank #{rank} | "
                f"Avg {item['avg_profit']:.4f} | "
                f"Bust {item['bust_rate']:.2f}% | "
                f"Score {item['score']:.4f} | "
                f"Goal {self.goal_spinner.text}"
            )
        })

        GLOBAL_BANK.strategies.append(strategy)
        GLOBAL_BANK.save_strategies()

        Popup(
            title="Saved",
            content=Label(text=f"Saved:\n{strategy['name']}"),
            size_hint=(0.75, 0.25)
        ).open()

    def add_result_card(self, rank, item):
        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(156),
            padding=dp(8),
            spacing=dp(3)
        )

        def update_rect(instance, value):
            if hasattr(instance, '_bg_rect'):
                instance._bg_rect.pos = instance.pos
                instance._bg_rect.size = instance.size

        with card.canvas.before:
            Color(rgba=get_color_from_hex(STAKE_INPUT))
            card._bg_rect = Rectangle(pos=card.pos, size=card.size)

        card.bind(pos=update_rect, size=update_rect)

        title = Label(
            text=f"#{rank} | Avg {item['avg_profit']:.4f} | Bust {item['bust_rate']:.2f}%",
            color=get_color_from_hex(STAKE_GREEN),
            bold=True,
            font_size='12sp',
            size_hint_y=None,
            height=dp(24)
        )

        row1 = Label(
            text=f"Base: {item['base_bet']} | Target: {item['target_multiplier']}x | Loss+: {item['loss_pct']}%",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row2 = Label(
            text=f"Win Rate: {item['win_rate']:.2f}% | Max Bets: {item['max_bets']} | Longest LS: {item['longest_ls']}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row3 = Label(
            text=f"Median: {item['median_profit']:.4f} | Best: {item['best_session']:.4f} | Worst: {item['worst_session']:.4f}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row4 = Label(
            text=f"Score: {item['score']:.4f} | Goal: {self.goal_spinner.text}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='10sp',
            size_hint_y=None,
            height=dp(18)
        )

        save_btn = StyledButton(
            text="SAVE TO LIBRARY",
            bg_color="#2c3e50",
            height=dp(34)
        )
        save_btn.color = (1, 1, 1, 1)
        save_btn.bind(on_release=lambda x: self.save_evolved_strategy(item, rank))

        card.add_widget(title)
        card.add_widget(row1)
        card.add_widget(row2)
        card.add_widget(row3)
        card.add_widget(row4)
        card.add_widget(save_btn)

        self.results_grid.add_widget(card)

    def _set_progress(self, value, text):
        self.progress_bar.value = value
        self.status_lbl.text = text

    def _finish_evolution(self, unique_results, generations, top_results):
        self.run_btn.disabled = False
        self.progress_bar.value = self.progress_bar.max
        self.status_lbl.text = "Status: Complete"
        show_n = max(1, min(top_results, len(unique_results)))
        self.summary.text = f"Evolved Limbo across {generations} generations | Showing top {show_n} | Goal: {self.goal_spinner.text}"
        self.results_grid.clear_widgets()
        for i, item in enumerate(unique_results[:show_n], start=1):
            self.add_result_card(i, item)

    def run_evolution(self, *args):
        self.results_grid.clear_widgets()
        bankroll=safe_float(self.inputs['Bankroll'].text,20); population_size=safe_int(self.inputs['Population Size'].text,40); generations=safe_int(self.inputs['Generations'].text,5); elite_keep=safe_int(self.inputs['Elite Keep'].text,8); children_per_generation=safe_int(self.inputs['Children Per Generation'].text,40); sessions_per_strategy=safe_int(self.inputs['Sessions / Strategy'].text,2000); max_bets=safe_int(self.inputs['Max Bets / Session'].text,12); top_results=safe_int(self.inputs['Top Results'].text,10)
        if bankroll<=0: self.summary.text='Bankroll must be greater than 0'; return
        self.run_btn.disabled=True; self.progress_bar.max=max(1, generations*max(2,population_size)); self.progress_bar.value=0; self.status_lbl.text='Status: Running evolution...'
        def worker():
            population=[self.random_strategy(bankroll) for _ in range(max(2,population_size))]; best_overall=[]; progress=0
            for gen in range(max(1,generations)):
                evaluated=[]
                for s in population:
                    evaluated.append(self.evaluate_strategy(s, bankroll, max_bets, sessions_per_strategy)); progress += 1
                    if progress % max(1,self.progress_bar.max//100) == 0 or progress == self.progress_bar.max:
                        _ui_call(self._set_progress, progress, f'Status: Generation {gen+1}/{generations}')
                evaluated.sort(key=lambda x:x['score'], reverse=True); elites=evaluated[:max(1,elite_keep)]; best_overall.extend(elites)
                elite_strats=[{'base_bet':e['base_bet'],'target_multiplier':e['target_multiplier'],'loss_pct':e['loss_pct']} for e in elites]
                population=[]
                while len(population)<max(2,children_per_generation): population.append(self.mutate_strategy(random.choice(elite_strats), bankroll))
            best_overall.sort(key=lambda x:x['score'], reverse=True)
            seen=set(); unique_results=[]
            for item in best_overall:
                key=(round(item['base_bet'],4), round(item['target_multiplier'],2), round(item['loss_pct'],2))
                if key not in seen: seen.add(key); unique_results.append(item)
            _ui_call(self._finish_evolution, unique_results, generations, top_results)
        threading.Thread(target=worker, daemon=True).start()
class KenoEvolutionScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        outer = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))

        title = Label(
            text="KENO EVOLUTION ENGINE",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(36)
        )
        outer.add_widget(title)

        scroll = ScrollView()
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        inner.bind(minimum_height=inner.setter('height'))

        self.inputs = {}

        fields = [
            ("Bankroll", "20"),
            ("Population Size", "40"),
            ("Generations", "5"),
            ("Elite Keep", "8"),
            ("Children Per Generation", "40"),
            ("Sessions / Strategy", "2000"),
            ("Max Bets / Session", "12"),
            ("Top Results", "10"),
        ]

        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for label_text, default in fields:
            lbl = Label(
                text=label_text,
                color=get_color_from_hex(STAKE_TEXT),
                font_size='12sp',
                size_hint_y=None,
                height=dp(36)
            )
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(lbl)
            grid.add_widget(ti)

        inner.add_widget(grid)

        goal_row = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(40))
        goal_row.add_widget(Label(
            text="Optimize For",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='12sp'
        ))
        self.goal_spinner = Spinner(
            text='Profit/Risk',
            values=('Profit', 'Safety', 'Profit/Risk'),
            size_hint_y=None,
            height=dp(38),
            background_normal='',
            background_color=get_color_from_hex(STAKE_INPUT),
            color=(1, 1, 1, 1)
        )
        goal_row.add_widget(self.goal_spinner)
        inner.add_widget(goal_row)

        info = Label(
            text="Evolves advanced Keno strategies using tiles, target hits, progression and elite selection",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(30)
        )
        inner.add_widget(info)

        self.run_btn = StyledButton(text="RUN KENO EVOLUTION")
        self.run_btn.bind(on_release=self.run_evolution)
        inner.add_widget(self.run_btn)

        self.status_lbl = Label(text="Status: Idle", color=get_color_from_hex(STAKE_TEXT), font_size='11sp', size_hint_y=None, height=dp(22))
        inner.add_widget(self.status_lbl)
        self.progress_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(10))
        inner.add_widget(self.progress_bar)

        self.summary = Label(
            text="Keno evolution results will appear here",
            color=get_color_from_hex(STAKE_GREEN),
            font_size='14sp',
            size_hint_y=None,
            height=dp(80)
        )
        inner.add_widget(self.summary)

        self.results_grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        inner.add_widget(self.results_grid)

        scroll.add_widget(inner)
        outer.add_widget(scroll)
        outer.add_widget(SimpleNav())
        self.add_widget(outer)

    def compute_score(self, avg_profit, bust_rate, win_rate):
        goal = self.goal_spinner.text
        if goal == "Profit":
            return avg_profit
        elif goal == "Safety":
            return (win_rate * 0.2) - (bust_rate * 3.0)
        else:
            return avg_profit - (bust_rate * 0.25)

    def comb(self, n, r):
        if r < 0 or r > n:
            return 0
        r = min(r, n - r)
        if r == 0:
            return 1
        numer = 1
        denom = 1
        for i in range(1, r + 1):
            numer *= (n - r + i)
            denom *= i
        return numer // denom

    def hypergeom_prob(self, tiles, hits):
        # 40-number board, 10 numbers drawn
        # Player picks `tiles`, probability of exactly `hits`
        if hits < 0 or hits > tiles or hits > 10:
            return 0.0
        total = self.comb(40, 10)
        ways = self.comb(tiles, hits) * self.comb(40 - tiles, 10 - hits)
        return ways / total if total else 0.0

    def keno_win_prob(self, tiles, target_hits):
        prob = 0.0
        for h in range(target_hits, min(tiles, 10) + 1):
            prob += self.hypergeom_prob(tiles, h)
        return prob

    def keno_payout_multiplier(self, tiles, target_hits):
        # Synthetic payout curve for evolution:
        # rarer events pay more, slight house edge built in
        win_prob = max(0.000001, self.keno_win_prob(tiles, target_hits))
        fair_mult = 1.0 / win_prob
        return fair_mult * 0.94

    def random_strategy(self, bankroll):
        tiles = random.randint(1, 10)
        target_hits = random.randint(1, min(tiles, 6))
        base_bet = round(random.uniform(0.01, min(0.25, bankroll * 0.02)), 4)
        loss_pct = round(random.uniform(5, 80), 2)

        return {
            "tiles": tiles,
            "target_hits": target_hits,
            "base_bet": base_bet,
            "loss_pct": loss_pct,
        }

    def mutate_strategy(self, parent, bankroll):
        tiles = parent["tiles"] + random.choice([-1, 0, 1])
        tiles = max(1, min(10, tiles))

        target_hits = parent["target_hits"] + random.choice([-1, 0, 1])
        target_hits = max(1, min(tiles, target_hits))

        new_base = round(parent["base_bet"] * random.uniform(0.85, 1.15), 4)
        new_loss = round(parent["loss_pct"] * random.uniform(0.85, 1.15), 2)

        new_base = max(0.01, min(new_base, min(0.25, bankroll * 0.02)))
        new_loss = max(1.0, min(new_loss, 100.0))

        return {
            "tiles": tiles,
            "target_hits": target_hits,
            "base_bet": new_base,
            "loss_pct": new_loss,
        }

    def simulate_keno_hits(self, tiles):
        # 40-number board, 10 draws, `tiles` picks
        population = list(range(40))
        picked = set(random.sample(population, tiles))
        drawn = set(random.sample(population, 10))
        return len(picked & drawn)

    def run_keno_sessions(self, bankroll, tiles, target_hits, base_bet, inc_on_loss, max_bets, sessions):
        results = []
        busts = 0
        winning_sessions = 0
        longest_loss_streak_seen = 0

        bankroll = max(0.00000001, bankroll)
        base_bet = max(0.00000001, base_bet)
        inc_on_loss = max(-100.0, inc_on_loss)
        max_bets = max(1, max_bets)
        sessions = max(1, sessions)

        payout_multiplier = self.keno_payout_multiplier(tiles, target_hits)

        for _ in range(sessions):
            balance = bankroll
            current_bet = base_bet
            session_profit = 0.0
            loss_streak = 0

            for _round in range(max_bets):
                if current_bet <= 0 or current_bet > balance:
                    busts += 1
                    break

                balance -= current_bet
                hits = self.simulate_keno_hits(tiles)

                if hits >= target_hits:
                    payout = current_bet * payout_multiplier
                    net_profit = payout - current_bet
                    balance += payout
                    session_profit += net_profit
                    loss_streak = 0
                    current_bet = base_bet
                else:
                    session_profit -= current_bet
                    loss_streak += 1
                    longest_loss_streak_seen = max(longest_loss_streak_seen, loss_streak)
                    current_bet = current_bet * (1 + inc_on_loss / 100.0)

            results.append(session_profit)
            if session_profit > 0:
                winning_sessions += 1

        avg_profit = statistics.mean(results) if results else 0.0
        median_profit = statistics.median(results) if results else 0.0
        best_session = max(results) if results else 0.0
        worst_session = min(results) if results else 0.0
        win_rate = (winning_sessions / sessions) * 100 if sessions else 0.0
        bust_rate = (busts / sessions) * 100 if sessions else 0.0

        return {
            "average_profit": avg_profit,
            "median_profit": median_profit,
            "best_session": best_session,
            "worst_session": worst_session,
            "win_rate": win_rate,
            "bust_rate": bust_rate,
            "longest_loss_streak": longest_loss_streak_seen,
            "payout_multiplier": payout_multiplier,
        }

    def evaluate_strategy(self, strat, bankroll, max_bets, sessions_per_strategy):
        result = self.run_keno_sessions(
            bankroll=bankroll,
            tiles=strat["tiles"],
            target_hits=strat["target_hits"],
            base_bet=strat["base_bet"],
            inc_on_loss=strat["loss_pct"],
            max_bets=max_bets,
            sessions=sessions_per_strategy,
        )

        score = self.compute_score(
            avg_profit=result["average_profit"],
            bust_rate=result["bust_rate"],
            win_rate=result["win_rate"]
        )

        return {
            "tiles": strat["tiles"],
            "target_hits": strat["target_hits"],
            "base_bet": strat["base_bet"],
            "loss_pct": strat["loss_pct"],
            "max_bets": max_bets,
            "avg_profit": result["average_profit"],
            "median_profit": result["median_profit"],
            "best_session": result["best_session"],
            "worst_session": result["worst_session"],
            "win_rate": result["win_rate"],
            "bust_rate": result["bust_rate"],
            "longest_ls": result["longest_loss_streak"],
            "payout_multiplier": result["payout_multiplier"],
            "score": score,
        }

    def save_evolved_strategy(self, item, rank):
        strategy = normalize_strategy({
            "name": f"KENO EVO | {item['tiles']}T {item['target_hits']}H B{item['base_bet']} L{item['loss_pct']}",
            "category": "Experimental",
            "game": "keno",
            "source": "evolution_engine",
            "bank": str(self.inputs["Bankroll"].text),
            "base": str(item["base_bet"]),
            "multi": str(round(item["payout_multiplier"], 2)),
            "win_action": "Reset",
            "loss_action": f"Increase {item['loss_pct']}%",
            "max_bets": str(item["max_bets"]),
            "notes": (
                f"Saved from Keno Evolution Engine | Rank #{rank} | "
                f"Tiles {item['tiles']} | Target {item['target_hits']} | "
                f"Avg {item['avg_profit']:.4f} | "
                f"Bust {item['bust_rate']:.2f}% | "
                f"Score {item['score']:.4f} | "
                f"Goal {self.goal_spinner.text}"
            )
        })

        GLOBAL_BANK.strategies.append(strategy)
        GLOBAL_BANK.save_strategies()

        Popup(
            title="Saved",
            content=Label(text=f"Saved:\n{strategy['name']}"),
            size_hint=(0.75, 0.25)
        ).open()

    def add_result_card(self, rank, item):
        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(174),
            padding=dp(8),
            spacing=dp(3)
        )

        def update_rect(instance, value):
            if hasattr(instance, '_bg_rect'):
                instance._bg_rect.pos = instance.pos
                instance._bg_rect.size = instance.size

        with card.canvas.before:
            Color(rgba=get_color_from_hex(STAKE_INPUT))
            card._bg_rect = Rectangle(pos=card.pos, size=card.size)

        card.bind(pos=update_rect, size=update_rect)

        title = Label(
            text=f"#{rank} | Avg {item['avg_profit']:.4f} | Bust {item['bust_rate']:.2f}%",
            color=get_color_from_hex(STAKE_GREEN),
            bold=True,
            font_size='12sp',
            size_hint_y=None,
            height=dp(24)
        )

        row1 = Label(
            text=f"Tiles: {item['tiles']} | Target: {item['target_hits']} hits | Payout: {item['payout_multiplier']:.2f}x",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row2 = Label(
            text=f"Base: {item['base_bet']} | Loss+: {item['loss_pct']}% | Max Bets: {item['max_bets']}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row3 = Label(
            text=f"Win Rate: {item['win_rate']:.2f}% | Longest LS: {item['longest_ls']}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row4 = Label(
            text=f"Median: {item['median_profit']:.4f} | Best: {item['best_session']:.4f} | Worst: {item['worst_session']:.4f}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row5 = Label(
            text=f"Score: {item['score']:.4f} | Goal: {self.goal_spinner.text}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='10sp',
            size_hint_y=None,
            height=dp(18)
        )

        save_btn = StyledButton(
            text="SAVE TO LIBRARY",
            bg_color="#2c3e50",
            height=dp(34)
        )
        save_btn.color = (1, 1, 1, 1)
        save_btn.bind(on_release=lambda x: self.save_evolved_strategy(item, rank))

        card.add_widget(title)
        card.add_widget(row1)
        card.add_widget(row2)
        card.add_widget(row3)
        card.add_widget(row4)
        card.add_widget(row5)
        card.add_widget(save_btn)

        self.results_grid.add_widget(card)

    def _set_progress(self, value, text):
        self.progress_bar.value = value
        self.status_lbl.text = text

    def _finish_evolution(self, unique_results, generations, top_results):
        self.run_btn.disabled = False
        self.progress_bar.value = self.progress_bar.max
        self.status_lbl.text = "Status: Complete"
        show_n = max(1, min(top_results, len(unique_results)))
        self.summary.text = f"Evolved Keno across {generations} generations | Showing top {show_n} | Goal: {self.goal_spinner.text}"
        self.results_grid.clear_widgets()
        for i, item in enumerate(unique_results[:show_n], start=1):
            self.add_result_card(i, item)

    def run_evolution(self, *args):
        self.results_grid.clear_widgets(); bankroll=safe_float(self.inputs['Bankroll'].text,20); population_size=safe_int(self.inputs['Population Size'].text,40); generations=safe_int(self.inputs['Generations'].text,5); elite_keep=safe_int(self.inputs['Elite Keep'].text,8); children_per_generation=safe_int(self.inputs['Children Per Generation'].text,40); sessions_per_strategy=safe_int(self.inputs['Sessions / Strategy'].text,2000); max_bets=safe_int(self.inputs['Max Bets / Session'].text,12); top_results=safe_int(self.inputs['Top Results'].text,10)
        if bankroll<=0: self.summary.text='Bankroll must be greater than 0'; return
        self.run_btn.disabled=True; self.progress_bar.max=max(1, generations*max(2,population_size)); self.progress_bar.value=0; self.status_lbl.text='Status: Running evolution...'
        def worker():
            population=[self.random_strategy(bankroll) for _ in range(max(2,population_size))]; best_overall=[]; progress=0
            for gen in range(max(1,generations)):
                evaluated=[]
                for s in population:
                    evaluated.append(self.evaluate_strategy(s, bankroll, max_bets, sessions_per_strategy)); progress += 1
                    if progress % max(1,self.progress_bar.max//100) == 0 or progress == self.progress_bar.max:
                        _ui_call(self._set_progress, progress, f'Status: Generation {gen+1}/{generations}')
                evaluated.sort(key=lambda x:x['score'], reverse=True); elites=evaluated[:max(1,elite_keep)]; best_overall.extend(elites)
                elite_strats=[{'tiles':e['tiles'],'target_hits':e['target_hits'],'base_bet':e['base_bet'],'loss_pct':e['loss_pct']} for e in elites]
                population=[]
                while len(population)<max(2,children_per_generation): population.append(self.mutate_strategy(random.choice(elite_strats), bankroll))
            best_overall.sort(key=lambda x:x['score'], reverse=True)
            seen=set(); unique_results=[]
            for item in best_overall:
                key=(item['tiles'], item['target_hits'], round(item['base_bet'],4), round(item['loss_pct'],2))
                if key not in seen: seen.add(key); unique_results.append(item)
            _ui_call(self._finish_evolution, unique_results, generations, top_results)
        threading.Thread(target=worker, daemon=True).start()
class MinesEvolutionScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        outer = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))

        title = Label(
            text="MINES EVOLUTION ENGINE",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(36)
        )
        outer.add_widget(title)

        scroll = ScrollView()
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        inner.bind(minimum_height=inner.setter('height'))

        self.inputs = {}

        fields = [
            ("Bankroll", "20"),
            ("Population Size", "40"),
            ("Generations", "5"),
            ("Elite Keep", "8"),
            ("Children Per Generation", "40"),
            ("Sessions / Strategy", "2000"),
            ("Max Bets / Session", "12"),
            ("Top Results", "10"),
        ]

        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for label_text, default in fields:
            lbl = Label(
                text=label_text,
                color=get_color_from_hex(STAKE_TEXT),
                font_size='12sp',
                size_hint_y=None,
                height=dp(36)
            )
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(lbl)
            grid.add_widget(ti)

        inner.add_widget(grid)

        goal_row = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(40))
        goal_row.add_widget(Label(
            text="Optimize For",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='12sp'
        ))
        self.goal_spinner = Spinner(
            text='Profit/Risk',
            values=('Profit', 'Safety', 'Profit/Risk'),
            size_hint_y=None,
            height=dp(38),
            background_normal='',
            background_color=get_color_from_hex(STAKE_INPUT),
            color=(1, 1, 1, 1)
        )
        goal_row.add_widget(self.goal_spinner)
        inner.add_widget(goal_row)

        info = Label(
            text="Evolves Mines strategies using mines count, safe picks and progression",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(30)
        )
        inner.add_widget(info)

        self.run_btn = StyledButton(text="RUN MINES EVOLUTION")
        self.run_btn.bind(on_release=self.run_evolution)
        inner.add_widget(self.run_btn)

        self.status_lbl = Label(text="Status: Idle", color=get_color_from_hex(STAKE_TEXT), font_size='11sp', size_hint_y=None, height=dp(22))
        inner.add_widget(self.status_lbl)
        self.progress_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(10))
        inner.add_widget(self.progress_bar)

        self.summary = Label(
            text="Mines evolution results will appear here",
            color=get_color_from_hex(STAKE_GREEN),
            font_size='14sp',
            size_hint_y=None,
            height=dp(80)
        )
        inner.add_widget(self.summary)

        self.results_grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        inner.add_widget(self.results_grid)

        scroll.add_widget(inner)
        outer.add_widget(scroll)
        outer.add_widget(SimpleNav())
        self.add_widget(outer)

    def compute_score(self, avg_profit, bust_rate, win_rate):
        goal = self.goal_spinner.text
        if goal == "Profit":
            return avg_profit
        elif goal == "Safety":
            return (win_rate * 0.2) - (bust_rate * 3.0)
        else:
            return avg_profit - (bust_rate * 0.25)

    def comb(self, n, r):
        if r < 0 or r > n:
            return 0
        r = min(r, n - r)
        if r == 0:
            return 1
        numer = 1
        denom = 1
        for i in range(1, r + 1):
            numer *= (n - r + i)
            denom *= i
        return numer // denom

    def mines_win_prob(self, mines_count, safe_picks):
        # Probability of surviving `safe_picks` picks on 25-tile board
        if safe_picks < 0 or mines_count < 1 or mines_count >= 25:
            return 0.0
        safe_tiles = 25 - mines_count
        if safe_picks > safe_tiles:
            return 0.0

        prob = 1.0
        for i in range(safe_picks):
            prob *= (safe_tiles - i) / (25 - i)
        return prob

    def mines_payout_multiplier(self, mines_count, safe_picks):
        win_prob = max(0.000001, self.mines_win_prob(mines_count, safe_picks))
        fair_mult = 1.0 / win_prob
        return fair_mult * 0.94

    def random_strategy(self, bankroll):
        mines_count = random.randint(1, 10)
        max_safe_possible = 24 - mines_count
        safe_picks = random.randint(1, max(1, min(10, max_safe_possible)))
        base_bet = round(random.uniform(0.01, min(0.25, bankroll * 0.02)), 4)
        loss_pct = round(random.uniform(5, 80), 2)

        return {
            "mines_count": mines_count,
            "safe_picks": safe_picks,
            "base_bet": base_bet,
            "loss_pct": loss_pct,
        }

    def mutate_strategy(self, parent, bankroll):
        mines_count = parent["mines_count"] + random.choice([-1, 0, 1])
        mines_count = max(1, min(10, mines_count))

        max_safe_possible = 24 - mines_count
        safe_picks = parent["safe_picks"] + random.choice([-1, 0, 1])
        safe_picks = max(1, min(max_safe_possible, safe_picks))

        new_base = round(parent["base_bet"] * random.uniform(0.85, 1.15), 4)
        new_loss = round(parent["loss_pct"] * random.uniform(0.85, 1.15), 2)

        new_base = max(0.01, min(new_base, min(0.25, bankroll * 0.02)))
        new_loss = max(1.0, min(new_loss, 100.0))

        return {
            "mines_count": mines_count,
            "safe_picks": safe_picks,
            "base_bet": new_base,
            "loss_pct": new_loss,
        }

    def simulate_single_mines_round(self, mines_count, safe_picks):
        tiles = list(range(25))
        mine_set = set(random.sample(tiles, mines_count))
        remaining = tiles[:]

        for _ in range(safe_picks):
            pick = random.choice(remaining)
            remaining.remove(pick)
            if pick in mine_set:
                return False
        return True

    def run_mines_sessions(self, bankroll, mines_count, safe_picks, base_bet, inc_on_loss, max_bets, sessions):
        results = []
        busts = 0
        winning_sessions = 0
        longest_loss_streak_seen = 0

        bankroll = max(0.00000001, bankroll)
        base_bet = max(0.00000001, base_bet)
        inc_on_loss = max(-100.0, inc_on_loss)
        max_bets = max(1, max_bets)
        sessions = max(1, sessions)

        payout_multiplier = self.mines_payout_multiplier(mines_count, safe_picks)

        for _ in range(sessions):
            balance = bankroll
            current_bet = base_bet
            session_profit = 0.0
            loss_streak = 0

            for _round in range(max_bets):
                if current_bet <= 0 or current_bet > balance:
                    busts += 1
                    break

                balance -= current_bet
                is_win = self.simulate_single_mines_round(mines_count, safe_picks)

                if is_win:
                    payout = current_bet * payout_multiplier
                    net_profit = payout - current_bet
                    balance += payout
                    session_profit += net_profit
                    loss_streak = 0
                    current_bet = base_bet
                else:
                    session_profit -= current_bet
                    loss_streak += 1
                    longest_loss_streak_seen = max(longest_loss_streak_seen, loss_streak)
                    current_bet = current_bet * (1 + inc_on_loss / 100.0)

            results.append(session_profit)
            if session_profit > 0:
                winning_sessions += 1

        avg_profit = statistics.mean(results) if results else 0.0
        median_profit = statistics.median(results) if results else 0.0
        best_session = max(results) if results else 0.0
        worst_session = min(results) if results else 0.0
        win_rate = (winning_sessions / sessions) * 100 if sessions else 0.0
        bust_rate = (busts / sessions) * 100 if sessions else 0.0

        return {
            "average_profit": avg_profit,
            "median_profit": median_profit,
            "best_session": best_session,
            "worst_session": worst_session,
            "win_rate": win_rate,
            "bust_rate": bust_rate,
            "longest_loss_streak": longest_loss_streak_seen,
            "payout_multiplier": payout_multiplier,
        }

    def evaluate_strategy(self, strat, bankroll, max_bets, sessions_per_strategy):
        result = self.run_mines_sessions(
            bankroll=bankroll,
            mines_count=strat["mines_count"],
            safe_picks=strat["safe_picks"],
            base_bet=strat["base_bet"],
            inc_on_loss=strat["loss_pct"],
            max_bets=max_bets,
            sessions=sessions_per_strategy,
        )

        score = self.compute_score(
            avg_profit=result["average_profit"],
            bust_rate=result["bust_rate"],
            win_rate=result["win_rate"]
        )

        return {
            "mines_count": strat["mines_count"],
            "safe_picks": strat["safe_picks"],
            "base_bet": strat["base_bet"],
            "loss_pct": strat["loss_pct"],
            "max_bets": max_bets,
            "avg_profit": result["average_profit"],
            "median_profit": result["median_profit"],
            "best_session": result["best_session"],
            "worst_session": result["worst_session"],
            "win_rate": result["win_rate"],
            "bust_rate": result["bust_rate"],
            "longest_ls": result["longest_loss_streak"],
            "payout_multiplier": result["payout_multiplier"],
            "score": score,
        }

    def save_evolved_strategy(self, item, rank):
        strategy = normalize_strategy({
            "name": f"MINES EVO | {item['mines_count']}M {item['safe_picks']}P B{item['base_bet']} L{item['loss_pct']}",
            "category": "Experimental",
            "game": "mines",
            "source": "evolution_engine",
            "bank": str(self.inputs["Bankroll"].text),
            "base": str(item["base_bet"]),
            "multi": str(round(item["payout_multiplier"], 2)),
            "win_action": "Reset",
            "loss_action": f"Increase {item['loss_pct']}%",
            "max_bets": str(item["max_bets"]),
            "notes": (
                f"Saved from Mines Evolution Engine | Rank #{rank} | "
                f"Mines {item['mines_count']} | Picks {item['safe_picks']} | "
                f"Avg {item['avg_profit']:.4f} | "
                f"Bust {item['bust_rate']:.2f}% | "
                f"Score {item['score']:.4f} | "
                f"Goal {self.goal_spinner.text}"
            )
        })

        GLOBAL_BANK.strategies.append(strategy)
        GLOBAL_BANK.save_strategies()

        Popup(
            title="Saved",
            content=Label(text=f"Saved:\n{strategy['name']}"),
            size_hint=(0.75, 0.25)
        ).open()

    def add_result_card(self, rank, item):
        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(174),
            padding=dp(8),
            spacing=dp(3)
        )

        def update_rect(instance, value):
            if hasattr(instance, '_bg_rect'):
                instance._bg_rect.pos = instance.pos
                instance._bg_rect.size = instance.size

        with card.canvas.before:
            Color(rgba=get_color_from_hex(STAKE_INPUT))
            card._bg_rect = Rectangle(pos=card.pos, size=card.size)

        card.bind(pos=update_rect, size=update_rect)

        title = Label(
            text=f"#{rank} | Avg {item['avg_profit']:.4f} | Bust {item['bust_rate']:.2f}%",
            color=get_color_from_hex(STAKE_GREEN),
            bold=True,
            font_size='12sp',
            size_hint_y=None,
            height=dp(24)
        )

        row1 = Label(
            text=f"Mines: {item['mines_count']} | Safe Picks: {item['safe_picks']} | Payout: {item['payout_multiplier']:.2f}x",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row2 = Label(
            text=f"Base: {item['base_bet']} | Loss+: {item['loss_pct']}% | Max Bets: {item['max_bets']}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row3 = Label(
            text=f"Win Rate: {item['win_rate']:.2f}% | Longest LS: {item['longest_ls']}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row4 = Label(
            text=f"Median: {item['median_profit']:.4f} | Best: {item['best_session']:.4f} | Worst: {item['worst_session']:.4f}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(22)
        )

        row5 = Label(
            text=f"Score: {item['score']:.4f} | Goal: {self.goal_spinner.text}",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='10sp',
            size_hint_y=None,
            height=dp(18)
        )

        save_btn = StyledButton(
            text="SAVE TO LIBRARY",
            bg_color="#2c3e50",
            height=dp(34)
        )
        save_btn.color = (1, 1, 1, 1)
        save_btn.bind(on_release=lambda x: self.save_evolved_strategy(item, rank))

        card.add_widget(title)
        card.add_widget(row1)
        card.add_widget(row2)
        card.add_widget(row3)
        card.add_widget(row4)
        card.add_widget(row5)
        card.add_widget(save_btn)

        self.results_grid.add_widget(card)

    def _set_progress(self, value, text):
        self.progress_bar.value = value
        self.status_lbl.text = text

    def _finish_evolution(self, unique_results, generations, top_results):
        self.run_btn.disabled = False
        self.progress_bar.value = self.progress_bar.max
        self.status_lbl.text = "Status: Complete"
        show_n = max(1, min(top_results, len(unique_results)))
        self.summary.text = f"Evolved Mines across {generations} generations | Showing top {show_n} | Goal: {self.goal_spinner.text}"
        self.results_grid.clear_widgets()
        for i, item in enumerate(unique_results[:show_n], start=1):
            self.add_result_card(i, item)

    def run_evolution(self, *args):
        self.results_grid.clear_widgets(); bankroll=safe_float(self.inputs['Bankroll'].text,20); population_size=safe_int(self.inputs['Population Size'].text,40); generations=safe_int(self.inputs['Generations'].text,5); elite_keep=safe_int(self.inputs['Elite Keep'].text,8); children_per_generation=safe_int(self.inputs['Children Per Generation'].text,40); sessions_per_strategy=safe_int(self.inputs['Sessions / Strategy'].text,2000); max_bets=safe_int(self.inputs['Max Bets / Session'].text,12); top_results=safe_int(self.inputs['Top Results'].text,10)
        if bankroll<=0: self.summary.text='Bankroll must be greater than 0'; return
        self.run_btn.disabled=True; self.progress_bar.max=max(1, generations*max(2,population_size)); self.progress_bar.value=0; self.status_lbl.text='Status: Running evolution...'
        def worker():
            population=[self.random_strategy(bankroll) for _ in range(max(2,population_size))]; best_overall=[]; progress=0
            for gen in range(max(1,generations)):
                evaluated=[]
                for s in population:
                    evaluated.append(self.evaluate_strategy(s, bankroll, max_bets, sessions_per_strategy)); progress += 1
                    if progress % max(1,self.progress_bar.max//100) == 0 or progress == self.progress_bar.max:
                        _ui_call(self._set_progress, progress, f'Status: Generation {gen+1}/{generations}')
                evaluated.sort(key=lambda x:x['score'], reverse=True); elites=evaluated[:max(1,elite_keep)]; best_overall.extend(elites)
                elite_strats=[{'mines_count':e['mines_count'],'safe_picks':e['safe_picks'],'base_bet':e['base_bet'],'loss_pct':e['loss_pct']} for e in elites]
                population=[]
                while len(population)<max(2,children_per_generation): population.append(self.mutate_strategy(random.choice(elite_strats), bankroll))
            best_overall.sort(key=lambda x:x['score'], reverse=True)
            seen=set(); unique_results=[]
            for item in best_overall:
                key=(item['mines_count'], item['safe_picks'], round(item['base_bet'],4), round(item['loss_pct'],2))
                if key not in seen: seen.add(key); unique_results.append(item)
            _ui_call(self._finish_evolution, unique_results, generations, top_results)
        threading.Thread(target=worker, daemon=True).start()
class SportsLabScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        outer = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))

        outer.add_widget(Label(
            text="SPORTS BETTING LAB",
            font_size='22sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(40)
        ))

        info = Label(
            text="Sports betting tools for bankroll sizing, parlays, value betting and simulations",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(30)
        )
        outer.add_widget(info)

        tools_layout = GridLayout(cols=1, spacing=dp(8), size_hint_y=None)
        tools_layout.bind(minimum_height=tools_layout.setter('height'))

        tools = [
            ("Kelly Bet Calculator", 'sports_kelly'),
            ("Parlay Analyzer", 'sports_parlay'),
            ("Value Bet Calculator", 'sports_value'),
            ("Arbitrage Calculator", 'sports_arb'),
        ]

        for name, sid in tools:
            btn = StyledButton(text=name, bg_color=STAKE_INPUT)
            btn.color = (1, 1, 1, 1)
            btn.bind(on_release=lambda x, s=sid: App.get_running_app().open_feature(s))
            tools_layout.add_widget(btn)

        scroll = ScrollView()
        scroll.add_widget(tools_layout)
        outer.add_widget(scroll)
        outer.add_widget(SimpleNav())
        self.add_widget(outer)

class SportsKellyScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        layout = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(6))
        self.inputs = {}

        layout.add_widget(Label(
            text="KELLY BET CALCULATOR",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(36)
        ))

        fields = [
            ("Bankroll", "100"),
            ("Decimal Odds", "2.10"),
            ("Estimated Win %", "55"),
        ]

        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for label_text, default in fields:
            grid.add_widget(Label(
                text=label_text,
                color=get_color_from_hex(STAKE_TEXT),
                font_size='12sp',
                size_hint_y=None,
                height=dp(36)
            ))
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(ti)

        layout.add_widget(grid)

        calc_btn = StyledButton(text="CALCULATE KELLY")
        calc_btn.bind(on_release=self.calculate)
        layout.add_widget(calc_btn)

        self.result_box = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        self.result_box.bind(minimum_height=self.result_box.setter('height'))

        scroll = ScrollView()
        scroll.add_widget(self.result_box)
        layout.add_widget(scroll)

        layout.add_widget(SimpleNav())
        self.add_widget(layout)

    def calculate(self, *args):
        self.result_box.clear_widgets()

        try:
            bankroll = float(self.inputs["Bankroll"].text)
            odds = float(self.inputs["Decimal Odds"].text)
            est_win_pct = float(self.inputs["Estimated Win %"].text)

            if bankroll <= 0 or odds <= 1.0 or est_win_pct <= 0 or est_win_pct >= 100:
                raise ValueError("Invalid input values")

            p = est_win_pct / 100.0
            q = 1 - p
            b = odds - 1.0

            implied_prob = 100.0 / odds
            edge_pct = (est_win_pct - implied_prob)

            kelly_fraction = ((b * p) - q) / b
            kelly_fraction = max(0.0, kelly_fraction)

            full_kelly_amt = bankroll * kelly_fraction
            half_kelly_amt = full_kelly_amt / 2.0
            quarter_kelly_amt = full_kelly_amt / 4.0

            expected_value_per_unit = (p * b) - q
            expected_profit_on_full = full_kelly_amt * expected_value_per_unit

            lines = [
                f"Implied Probability: {implied_prob:.2f}%",
                f"Your Edge: {edge_pct:.2f}%",
                f"Full Kelly: {kelly_fraction * 100:.2f}% of bankroll",
                f"Full Kelly Stake: {full_kelly_amt:.4f}",
                f"Half Kelly Stake: {half_kelly_amt:.4f}",
                f"Quarter Kelly Stake: {quarter_kelly_amt:.4f}",
                f"Expected Value / Unit Staked: {expected_value_per_unit:.4f}",
                f"Expected Profit at Full Kelly: {expected_profit_on_full:.4f}",
            ]

            for line in lines:
                color = get_color_from_hex(STAKE_GREEN) if ("Kelly" in line or "Edge" in line) else get_color_from_hex(STAKE_TEXT)
                self.result_box.add_widget(Label(
                    text=line,
                    color=color,
                    font_size='12sp',
                    size_hint_y=None,
                    height=dp(28)
                ))

        except Exception as e:
            self.result_box.add_widget(Label(
                text=f"Error: {e}",
                color=get_color_from_hex(STAKE_RED),
                font_size='12sp',
                size_hint_y=None,
                height=dp(28)
            ))

class SportsParlayScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        layout = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(6))
        self.inputs = {}

        layout.add_widget(Label(
            text="PARLAY ANALYZER",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(36)
        ))

        info = Label(
            text="Enter decimal odds and your estimated win probabilities for each leg",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(28)
        )
        layout.add_widget(info)

        fields = [
            ("Stake", "10"),
            ("Leg 1 Odds", "1.80"),
            ("Leg 1 Win %", "60"),
            ("Leg 2 Odds", "1.90"),
            ("Leg 2 Win %", "58"),
            ("Leg 3 Odds", "2.10"),
            ("Leg 3 Win %", "52"),
        ]

        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for label_text, default in fields:
            grid.add_widget(Label(
                text=label_text,
                color=get_color_from_hex(STAKE_TEXT),
                font_size='12sp',
                size_hint_y=None,
                height=dp(36)
            ))
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(ti)

        layout.add_widget(grid)

        calc_btn = StyledButton(text="ANALYZE PARLAY")
        calc_btn.bind(on_release=self.calculate)
        layout.add_widget(calc_btn)

        self.result_box = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        self.result_box.bind(minimum_height=self.result_box.setter('height'))

        scroll = ScrollView()
        scroll.add_widget(self.result_box)
        layout.add_widget(scroll)

        layout.add_widget(SimpleNav())
        self.add_widget(layout)

    def calculate(self, *args):
        self.result_box.clear_widgets()

        try:
            stake = float(self.inputs["Stake"].text)

            odds = [
                float(self.inputs["Leg 1 Odds"].text),
                float(self.inputs["Leg 2 Odds"].text),
                float(self.inputs["Leg 3 Odds"].text),
            ]

            probs_pct = [
                float(self.inputs["Leg 1 Win %"].text),
                float(self.inputs["Leg 2 Win %"].text),
                float(self.inputs["Leg 3 Win %"].text),
            ]

            if stake <= 0:
                raise ValueError("Stake must be greater than 0")

            for o in odds:
                if o <= 1.0:
                    raise ValueError("All decimal odds must be greater than 1.0")

            for p in probs_pct:
                if p <= 0 or p >= 100:
                    raise ValueError("All win percentages must be between 0 and 100")

            probs = [p / 100.0 for p in probs_pct]

            combined_odds = 1.0
            for o in odds:
                combined_odds *= o

            true_parlay_prob = 1.0
            for p in probs:
                true_parlay_prob *= p

            implied_parlay_prob = 1.0 / combined_odds
            edge_pct = (true_parlay_prob - implied_parlay_prob) * 100.0

            payout = stake * combined_odds
            net_profit_if_win = payout - stake
            expected_value = (true_parlay_prob * net_profit_if_win) - ((1 - true_parlay_prob) * stake)
            roi_pct = (expected_value / stake) * 100.0

            bust_prob = (1 - true_parlay_prob) * 100.0

            lines = [
                f"Combined Odds: {combined_odds:.4f}",
                f"True Parlay Win Probability: {true_parlay_prob * 100:.2f}%",
                f"Implied Parlay Probability: {implied_parlay_prob * 100:.2f}%",
                f"Edge: {edge_pct:.2f}%",
                f"Payout if Win: {payout:.4f}",
                f"Net Profit if Win: {net_profit_if_win:.4f}",
                f"Expected Value: {expected_value:.4f}",
                f"Expected ROI: {roi_pct:.2f}%",
                f"Bust Probability: {bust_prob:.2f}%",
            ]

            for line in lines:
                color = get_color_from_hex(STAKE_GREEN) if ("Edge" in line or "Expected" in line) else get_color_from_hex(STAKE_TEXT)
                self.result_box.add_widget(Label(
                    text=line,
                    color=color,
                    font_size='12sp',
                    size_hint_y=None,
                    height=dp(28)
                ))

        except Exception as e:
            self.result_box.add_widget(Label(
                text=f"Error: {e}",
                color=get_color_from_hex(STAKE_RED),
                font_size='12sp',
                size_hint_y=None,
                height=dp(28)
            ))
class SportsValueBetScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        layout = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(6))
        self.inputs = {}

        layout.add_widget(Label(
            text="VALUE BET CALCULATOR",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(36)
        ))

        info = Label(
            text="Compare bookmaker odds against your estimated true probability",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(28)
        )
        layout.add_widget(info)

        fields = [
            ("Stake", "10"),
            ("Decimal Odds", "2.10"),
            ("Estimated Win %", "55"),
        ]

        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for label_text, default in fields:
            grid.add_widget(Label(
                text=label_text,
                color=get_color_from_hex(STAKE_TEXT),
                font_size='12sp',
                size_hint_y=None,
                height=dp(36)
            ))
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(ti)

        layout.add_widget(grid)

        calc_btn = StyledButton(text="CALCULATE VALUE")
        calc_btn.bind(on_release=self.calculate)
        layout.add_widget(calc_btn)

        self.result_box = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        self.result_box.bind(minimum_height=self.result_box.setter('height'))

        scroll = ScrollView()
        scroll.add_widget(self.result_box)
        layout.add_widget(scroll)

        layout.add_widget(SimpleNav())
        self.add_widget(layout)

    def calculate(self, *args):
        self.result_box.clear_widgets()

        try:
            stake = float(self.inputs["Stake"].text)
            odds = float(self.inputs["Decimal Odds"].text)
            est_win_pct = float(self.inputs["Estimated Win %"].text)

            if stake <= 0:
                raise ValueError("Stake must be greater than 0")
            if odds <= 1.0:
                raise ValueError("Decimal odds must be greater than 1.0")
            if est_win_pct <= 0 or est_win_pct >= 100:
                raise ValueError("Estimated Win % must be between 0 and 100")

            p = est_win_pct / 100.0
            implied_prob = 1.0 / odds
            implied_pct = implied_prob * 100.0

            edge_pct = est_win_pct - implied_pct

            payout = stake * odds
            net_profit_if_win = payout - stake
            expected_value = (p * net_profit_if_win) - ((1 - p) * stake)
            roi_pct = (expected_value / stake) * 100.0

            fair_odds = 1.0 / p

            verdict = "POSITIVE EV" if expected_value > 0 else "NEGATIVE EV"
            verdict_color = get_color_from_hex(STAKE_GREEN if expected_value > 0 else STAKE_RED)

            lines = [
                (f"Implied Probability: {implied_pct:.2f}%", get_color_from_hex(STAKE_TEXT)),
                (f"Your Estimated Probability: {est_win_pct:.2f}%", get_color_from_hex(STAKE_TEXT)),
                (f"Fair Odds: {fair_odds:.4f}", get_color_from_hex(STAKE_TEXT)),
                (f"Edge: {edge_pct:.2f}%", get_color_from_hex(STAKE_GREEN if edge_pct > 0 else STAKE_RED)),
                (f"Payout if Win: {payout:.4f}", get_color_from_hex(STAKE_TEXT)),
                (f"Net Profit if Win: {net_profit_if_win:.4f}", get_color_from_hex(STAKE_TEXT)),
                (f"Expected Value: {expected_value:.4f}", get_color_from_hex(STAKE_GREEN if expected_value > 0 else STAKE_RED)),
                (f"Expected ROI: {roi_pct:.2f}%", get_color_from_hex(STAKE_GREEN if roi_pct > 0 else STAKE_RED)),
                (f"Verdict: {verdict}", verdict_color),
            ]

            for line, color in lines:
                self.result_box.add_widget(Label(
                    text=line,
                    color=color,
                    font_size='12sp',
                    size_hint_y=None,
                    height=dp(28)
                ))

        except Exception as e:
            self.result_box.add_widget(Label(
                text=f"Error: {e}",
                color=get_color_from_hex(STAKE_RED),
                font_size='12sp',
                size_hint_y=None,
                height=dp(28)
            ))
class SportsArbitrageScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        layout = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(6))
        self.inputs = {}

        layout.add_widget(Label(
            text="ARBITRAGE CALCULATOR",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(36)
        ))

        info = Label(
            text="Use odds from two opposite outcomes to check for guaranteed profit",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(28)
        )
        layout.add_widget(info)

        fields = [
            ("Total Stake", "100"),
            ("Outcome A Odds", "2.10"),
            ("Outcome B Odds", "2.10"),
        ]

        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for label_text, default in fields:
            grid.add_widget(Label(
                text=label_text,
                color=get_color_from_hex(STAKE_TEXT),
                font_size='12sp',
                size_hint_y=None,
                height=dp(36)
            ))
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(ti)

        layout.add_widget(grid)

        calc_btn = StyledButton(text="CHECK ARBITRAGE")
        calc_btn.bind(on_release=self.calculate)
        layout.add_widget(calc_btn)

        self.result_box = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        self.result_box.bind(minimum_height=self.result_box.setter('height'))

        scroll = ScrollView()
        scroll.add_widget(self.result_box)
        layout.add_widget(scroll)

        layout.add_widget(SimpleNav())
        self.add_widget(layout)

    def calculate(self, *args):
        self.result_box.clear_widgets()

        try:
            total_stake = float(self.inputs["Total Stake"].text)
            odds_a = float(self.inputs["Outcome A Odds"].text)
            odds_b = float(self.inputs["Outcome B Odds"].text)

            if total_stake <= 0:
                raise ValueError("Total Stake must be greater than 0")
            if odds_a <= 1.0 or odds_b <= 1.0:
                raise ValueError("All odds must be greater than 1.0")

            inv_sum = (1.0 / odds_a) + (1.0 / odds_b)
            arb_exists = inv_sum < 1.0

            stake_a = total_stake * ((1.0 / odds_a) / inv_sum)
            stake_b = total_stake * ((1.0 / odds_b) / inv_sum)

            payout_a = stake_a * odds_a
            payout_b = stake_b * odds_b
            locked_payout = min(payout_a, payout_b)
            guaranteed_profit = locked_payout - total_stake
            roi_pct = (guaranteed_profit / total_stake) * 100.0

            verdict = "ARBITRAGE FOUND" if arb_exists else "NO ARBITRAGE"
            verdict_color = get_color_from_hex(STAKE_GREEN if arb_exists else STAKE_RED)

            lines = [
                (f"Inverse Sum: {inv_sum:.6f}", get_color_from_hex(STAKE_TEXT)),
                (f"Outcome A Stake: {stake_a:.4f}", get_color_from_hex(STAKE_TEXT)),
                (f"Outcome B Stake: {stake_b:.4f}", get_color_from_hex(STAKE_TEXT)),
                (f"Outcome A Payout: {payout_a:.4f}", get_color_from_hex(STAKE_TEXT)),
                (f"Outcome B Payout: {payout_b:.4f}", get_color_from_hex(STAKE_TEXT)),
                (f"Locked Payout: {locked_payout:.4f}", get_color_from_hex(STAKE_TEXT)),
                (f"Guaranteed Profit: {guaranteed_profit:.4f}", get_color_from_hex(STAKE_GREEN if guaranteed_profit > 0 else STAKE_RED)),
                (f"Guaranteed ROI: {roi_pct:.2f}%", get_color_from_hex(STAKE_GREEN if roi_pct > 0 else STAKE_RED)),
                (f"Verdict: {verdict}", verdict_color),
            ]

            for line, color in lines:
                self.result_box.add_widget(Label(
                    text=line,
                    color=color,
                    font_size='12sp',
                    size_hint_y=None,
                    height=dp(28)
                ))

        except Exception as e:
            self.result_box.add_widget(Label(
                text=f"Error: {e}",
                color=get_color_from_hex(STAKE_RED),
                font_size='12sp',
                size_hint_y=None,
                height=dp(28)
            ))              
class MinesScreen(Screen):      
    def __init__(self, **kw):
        super().__init__(**kw)

        layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        self.m_in = StyledInput(text='5')
        self.p_in = StyledInput(text='1')

        layout.add_widget(Label(text="Mines / Picks:"))
        layout.add_widget(self.m_in)
        layout.add_widget(self.p_in)

        self.res = Label(text="Mult: --", font_size='18sp', color=get_color_from_hex(STAKE_GREEN))
        layout.add_widget(self.res)

        btn = StyledButton(text="Analyze")
        btn.bind(on_release=self.calc)
        layout.add_widget(btn)

        layout.add_widget(BoxLayout())
        layout.add_widget(SimpleNav())
        self.add_widget(layout)

    def calc(self, *args):
        try:
            m = int(self.m_in.text)
            p = int(self.p_in.text)

            prob = Decimal(1)
            for i in range(p):
                prob *= (Decimal(25 - m - i) / Decimal(25 - i))

            self.res.text = f"Prob: {prob * 100:.2f}% | Multiplier: {(Decimal(1) / prob):.2f}x"
        except Exception:
            pass


class CompoundScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        layout = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(5))
        self.p_in = StyledInput(text="10")
        self.r_in = StyledInput(text="20")
        self.t_in = StyledInput(text="5")
        self.target = StyledInput(text="30")

        for l, w in [("Capital:", self.p_in), ("Rate %:", self.r_in), ("Days:", self.t_in), ("Target:", self.target)]:
            layout.add_widget(Label(text=l, height=dp(20), size_hint_y=None))
            layout.add_widget(w)

        self.res_label = Label(text="Final: --", bold=True, height=dp(30), size_hint_y=None)
        layout.add_widget(self.res_label)

        c_btn = StyledButton(text="Calc Growth")
        c_btn.bind(on_release=self.calc)
        layout.add_widget(c_btn)

        self.breakdown = GridLayout(cols=1, spacing=2, size_hint_y=None)
        self.breakdown.bind(minimum_height=self.breakdown.setter('height'))

        scroll = ScrollView()
        scroll.add_widget(self.breakdown)
        layout.add_widget(scroll)

        layout.add_widget(SimpleNav())
        self.add_widget(layout)

    def calc(self, *args):
        self.breakdown.clear_widgets()

        try:
            p = float(self.p_in.text)
            r = float(self.r_in.text) / 100
            t = int(self.t_in.text)
            target = float(self.target.text)

            self.res_label.text = f"Final: {p * ((1 + r) ** t):,.2f}"

            for d in range(1, t + 1):
                val = p * ((1 + r) ** d)
                color = STAKE_GREEN if val >= target else STAKE_TEXT
                self.breakdown.add_widget(
                    Label(
                        text=f"Day {d}: {val:,.2f}",
                        height=dp(25),
                        size_hint_y=None,
                        color=get_color_from_hex(color)
                    )
                )
        except Exception:
            pass


class ConverterScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        self.last_edited = "crypto"
        layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))

        self.amt_crypto = StyledInput(text='1')
        self.amt_fiat = StyledInput(text='')

        self.amt_crypto.bind(text=lambda *a: self.set_last_edited("crypto"))
        self.amt_fiat.bind(text=lambda *a: self.set_last_edited("fiat"))

        self.c_spin = Spinner(
            text='bitcoin',
            values=('bitcoin', 'ethereum', 'litecoin', 'tether'),
            height=dp(40)
        )
        self.f_spin = Spinner(
            text='usd',
            values=('usd', 'inr', 'lkr'),
            height=dp(40)
        )

        layout.add_widget(Label(text="Crypto:"))
        layout.add_widget(self.amt_crypto)
        layout.add_widget(self.c_spin)
        layout.add_widget(Label(text="Fiat:"))
        layout.add_widget(self.amt_fiat)
        layout.add_widget(self.f_spin)

        self.res = Label(text="Price: --", color=get_color_from_hex(STAKE_GREEN))
        layout.add_widget(self.res)

        btn = StyledButton(text="Convert Now")
        btn.bind(on_release=self.convert)
        layout.add_widget(btn)

        layout.add_widget(SimpleNav())
        self.add_widget(layout)

    def set_last_edited(self, source):
        if self.amt_crypto.focus or self.amt_fiat.focus:
            self.last_edited = source

    def convert(self, *args):
        try:
            url = (
                "https://api.coingecko.com/api/v3/simple/price"
                f"?ids={self.c_spin.text}&vs_currencies={self.f_spin.text}"
            )
            r = requests.get(url, timeout=10, verify=certifi.where()).json()
            price = float(r[self.c_spin.text][self.f_spin.text])

            if self.last_edited == "crypto":
                self.amt_fiat.text = f"{(float(self.amt_crypto.text) * price):.2f}"
            else:
                self.amt_crypto.text = f"{(float(self.amt_fiat.text) / price):.8f}"

            self.res.text = f"1 {self.c_spin.text.upper()} = {price} {self.f_spin.text.upper()}"
        except Exception:
            self.res.text = "Error fetching price"


class BlackjackScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        self.player_cards = []
        self.dealer_cards = []

        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(5))

        self.p_cards_lbl = Label(
            text="P-Cards: []",
            color=get_color_from_hex(STAKE_GREEN),
            font_size='20sp',
            bold=True,
            size_hint_y=None,
            height=dp(40)
        )
        self.d_cards_lbl = Label(
            text="D-Cards: []",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='20sp',
            bold=True,
            size_hint_y=None,
            height=dp(40)
        )

        layout.add_widget(self.p_cards_lbl)
        layout.add_widget(self.d_cards_lbl)

        self.advice_lbl = Label(
            text="ADD CARDS",
            font_size='32sp',
            bold=True,
            color=get_color_from_hex(STAKE_GREEN),
            size_hint_y=None,
            height=dp(60)
        )
        layout.add_widget(self.advice_lbl)

        grid = GridLayout(cols=5, spacing=2, size_hint_y=None, height=dp(100))
        for c in ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'A']:
            btn = Button(text=c, background_color=get_color_from_hex(STAKE_INPUT), background_normal='')
            btn.bind(on_release=self.add_p)
            grid.add_widget(btn)
        layout.add_widget(grid)

        d_grid = GridLayout(cols=5, spacing=2, size_hint_y=None, height=dp(100))
        for c in ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'A']:
            btn = Button(text=c, background_color=get_color_from_hex('#2c3e50'), background_normal='')
            btn.bind(on_release=self.add_d)
            d_grid.add_widget(btn)
        layout.add_widget(d_grid)

        reset = StyledButton(text="RESET", bg_color='#440000')
        reset.bind(on_release=self.clear_bj)
        layout.add_widget(reset)

        layout.add_widget(SimpleNav())
        self.add_widget(layout)

    def add_p(self, b):
        self.player_cards.append(b.text)
        self.update()

    def add_d(self, b):
        self.dealer_cards.append(b.text)
        self.update()

    def clear_bj(self, *args):
        self.player_cards = []
        self.dealer_cards = []
        self.update()

    def get_info(self, cards):
        val = 0
        aces = 0

        for c in cards:
            if c == 'A':
                aces += 1
                val += 11
            elif c in ['10', 'J', 'Q', 'K']:
                val += 10
            else:
                val += int(c)

        while val > 21 and aces:
            val -= 10
            aces -= 1

        return val, (aces > 0 and val <= 21)

    def update(self):
        p_val, p_soft = self.get_info(self.player_cards)
        d_val, _ = self.get_info(self.dealer_cards)

        self.p_cards_lbl.text = f"P-Cards: {', '.join(self.player_cards)}"
        self.d_cards_lbl.text = f"D-Cards: {', '.join(self.dealer_cards)}"

        if p_val > 21:
            self.advice_lbl.text = "BUST"
        elif not self.player_cards or not self.dealer_cards:
            self.advice_lbl.text = "WAITING"
        else:
            self.advice_lbl.text = self.analyze(p_val, p_soft, d_val)

    def analyze(self, p, soft, d):
        if len(self.player_cards) == 2 and self.player_cards[0] == self.player_cards[1]:
            if self.player_cards[0] in ['A', '8']:
                return "SPLIT"

        if soft:
            if p >= 19:
                return "STAND"
            return "STAND" if p == 18 and d <= 8 else "HIT"

        if p >= 17:
            return "STAND"
        if p >= 13 and d <= 6:
            return "STAND"
        if p == 12 and 4 <= d <= 6:
            return "STAND"
        if p == 11:
            return "DOUBLE"
        if p == 10 and d <= 9:
            return "DOUBLE"
        return "DOUBLE" if p == 9 and 3 <= d <= 6 else "HIT"


class PatternScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        layout = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(5))
        self.base = StyledInput(text="0.001")
        self.grp = StyledInput(text="3")
        self.mult = StyledInput(text="100")
        self.cnt = StyledInput(text="50")

        grid = GridLayout(cols=2, spacing=dp(5), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for l, w in [("Base:", self.base), ("Grp:", self.grp), ("%:", self.mult), ("Qty:", self.cnt)]:
            grid.add_widget(Label(text=l))
            grid.add_widget(w)

        layout.add_widget(grid)

        self.total_lbl = Label(text="Total: --", height=dp(30))
        layout.add_widget(self.total_lbl)

        g_btn = StyledButton(text="Generate Pattern")
        g_btn.bind(on_release=self.generate)
        layout.add_widget(g_btn)

        self.res_grid = GridLayout(cols=3, spacing=2, size_hint_y=None)
        self.res_grid.bind(minimum_height=self.res_grid.setter('height'))

        scroll = ScrollView()
        scroll.add_widget(self.res_grid)
        layout.add_widget(scroll)

        layout.add_widget(SimpleNav())
        self.add_widget(layout)

    def generate(self, *args):
        self.res_grid.clear_widgets()

        try:
            b = float(self.base.text)
            g = int(self.grp.text)
            m = float(self.mult.text) / 100
            c = int(self.cnt.text)
            total = 0

            for i in range(1, c + 1):
                val = b * ((1 + m) ** ((i - 1) // g))
                total += val
                for txt in [str(i), f"{val:.6f}", str(int(val * 1000000))]:
                    self.res_grid.add_widget(
                        Label(text=txt, size_hint_y=None, height=dp(25), font_size='11sp')
                    )

            self.total_lbl.text = f"Total Sum: {total:.6f}"
        except Exception:
            pass





class StrategyStressTestScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        outer = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))

        title = Label(text="STRATEGY STRESS TEST", font_size='20sp', bold=True,
                      color=get_color_from_hex(STAKE_GREEN), size_hint_y=None, height=dp(36))
        outer.add_widget(title)

        scroll = ScrollView()
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        inner.bind(minimum_height=inner.setter('height'))

        self.inputs = {}
        fields = [
            ("Bankroll", "20"),
            ("Base Bet", "0.1"),
            ("Multiplier / Target", "3.5"),
            ("Win Chance %", "28.29"),
            ("Tiles", "6"),
            ("Target Hits", "2"),
            ("Mines Count", "3"),
            ("Safe Picks", "2"),
            ("Increase on Loss %", "50"),
            ("Max Bets / Session", "12"),
            ("Sessions", "5000"),
        ]
        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        for label_text, default in fields:
            grid.add_widget(Label(text=label_text, color=get_color_from_hex(STAKE_TEXT), font_size='12sp',
                                  size_hint_y=None, height=dp(36)))
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(ti)
        inner.add_widget(grid)

        game_row = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(40))
        game_row.add_widget(Label(text="Game", color=get_color_from_hex(STAKE_TEXT), font_size='12sp'))
        self.game_spinner = Spinner(
            text='dice', values=('dice', 'limbo', 'keno', 'mines'),
            size_hint_y=None, height=dp(38), background_normal='',
            background_color=get_color_from_hex(STAKE_INPUT), color=(1, 1, 1, 1)
        )
        game_row.add_widget(self.game_spinner)
        inner.add_widget(game_row)

        btn_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        self.run_btn = StyledButton(text="RUN STRESS TEST")
        self.run_btn.bind(on_release=self.start_test)
        btn_row.add_widget(self.run_btn)
        inner.add_widget(btn_row)

        self.status_lbl = Label(text="Status: Idle", color=get_color_from_hex(STAKE_TEXT), font_size='11sp',
                                size_hint_y=None, height=dp(22))
        self.progress_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(10))
        inner.add_widget(self.status_lbl)
        inner.add_widget(self.progress_bar)

        self.summary = Label(text="Results will appear here", color=get_color_from_hex(STAKE_GREEN),
                             font_size='14sp', size_hint_y=None, height=dp(80))
        inner.add_widget(self.summary)

        self.results_grid = GridLayout(cols=2, spacing=dp(4), size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        inner.add_widget(self.results_grid)

        scroll.add_widget(inner)
        outer.add_widget(scroll)
        outer.add_widget(SimpleNav())
        self.add_widget(outer)

        self._running = False

    def load_strategy(self, data):
        data = normalize_strategy(data)
        game = str(data.get("game", "dice")).lower().strip()
        if game not in ("dice", "limbo", "keno", "mines"):
            game = "dice"
        self.game_spinner.text = game
        self.inputs["Bankroll"].text = str(data.get("bank", "20") or "20")
        self.inputs["Base Bet"].text = str(data.get("base", "0.1") or "0.1")
        self.inputs["Multiplier / Target"].text = str(data.get("multi", "3.5") or "3.5")
        self.inputs["Increase on Loss %"].text = "50"
        try:
            loss = str(data.get("loss_action", ""))
            if "Increase" in loss:
                self.inputs["Increase on Loss %"].text = loss.split("Increase", 1)[1].replace("%", "").strip()
        except Exception:
            pass
        self.inputs["Max Bets / Session"].text = str(data.get("max_bets", "12") or "12")

        notes = str(data.get("notes", ""))
        if "Tiles " in notes:
            try:
                self.inputs["Tiles"].text = notes.split("Tiles ", 1)[1].split(" |", 1)[0].strip()
            except Exception:
                pass
        if "Target " in notes:
            try:
                self.inputs["Target Hits"].text = notes.split("Target ", 1)[1].split(" |", 1)[0].strip()
            except Exception:
                pass
        if "Mines " in notes:
            try:
                self.inputs["Mines Count"].text = notes.split("Mines ", 1)[1].split(" |", 1)[0].strip()
            except Exception:
                pass
        if "Picks " in notes:
            try:
                self.inputs["Safe Picks"].text = notes.split("Picks ", 1)[1].split(" |", 1)[0].strip()
            except Exception:
                pass

    def _reset_results(self):
        self.results_grid.clear_widgets()
        self._profits = []
        self._busts = 0
        self._wins = 0
        self._worst = None
        self._best = None
        self._longest_ls = 0
        self._done = 0

    def start_test(self, *args):
        if self._running:
            return
        self._running = True
        self.run_btn.disabled = True
        self.status_lbl.text = "Status: Initializing..."
        self._reset_results()

        self._game = self.game_spinner.text
        self._bankroll = safe_float(self.inputs["Bankroll"].text, 20)
        self._base = safe_float(self.inputs["Base Bet"].text, 0.1)
        self._multi = safe_float(self.inputs["Multiplier / Target"].text, 3.5)
        self._chance = safe_float(self.inputs["Win Chance %"].text, 28.29)
        self._tiles = safe_int(self.inputs["Tiles"].text, 6)
        self._target_hits = safe_int(self.inputs["Target Hits"].text, 2)
        self._mines = safe_int(self.inputs["Mines Count"].text, 3)
        self._safe_picks = safe_int(self.inputs["Safe Picks"].text, 2)
        self._loss_inc = safe_float(self.inputs["Increase on Loss %"].text, 50)
        self._max_bets = safe_int(self.inputs["Max Bets / Session"].text, 12)
        self._sessions = max(1, safe_int(self.inputs["Sessions"].text, 5000))
        self.progress_bar.max = self._sessions
        self.progress_bar.value = 0
        self.summary.text = "Running stress test..."
        Clock.schedule_interval(self._process_batch, 0)

    def _dice_session(self):
        balance = max(1e-8, self._bankroll)
        bet = max(1e-8, self._base)
        profit = 0.0
        ls = 0
        longest = 0
        busted = False
        for _ in range(max(1, self._max_bets)):
            if bet > balance or bet <= 0:
                busted = True
                break
            balance -= bet
            if random.uniform(0, 100) < self._chance:
                payout = bet * self._multi
                balance += payout
                profit += payout - bet
                bet = self._base
                ls = 0
            else:
                profit -= bet
                ls += 1
                longest = max(longest, ls)
                bet = bet * (1 + self._loss_inc / 100.0)
        return profit, busted, longest

    def _limbo_session(self):
        chance = max(0.01, min(99.0, 99.0 / max(1.01, self._multi)))
        balance = max(1e-8, self._bankroll)
        bet = max(1e-8, self._base)
        profit = 0.0
        ls = 0
        longest = 0
        busted = False
        for _ in range(max(1, self._max_bets)):
            if bet > balance or bet <= 0:
                busted = True
                break
            balance -= bet
            if random.uniform(0, 100) < chance:
                payout = bet * self._multi
                balance += payout
                profit += payout - bet
                bet = self._base
                ls = 0
            else:
                profit -= bet
                ls += 1
                longest = max(longest, ls)
                bet = bet * (1 + self._loss_inc / 100.0)
        return profit, busted, longest

    def _comb(self, n, r):
        if r < 0 or r > n:
            return 0
        return math.comb(n, r)

    def _keno_exact_prob(self, tiles, hits):
        total = self._comb(40, 10)
        ways = self._comb(tiles, hits) * self._comb(40 - tiles, 10 - hits)
        return ways / total if total else 0.0

    def _keno_win_prob(self, tiles, target_hits):
        p = 0.0
        for h in range(target_hits, min(tiles, 10) + 1):
            p += self._keno_exact_prob(tiles, h)
        return p

    def _keno_session(self):
        payout_mult = (1.0 / max(1e-6, self._keno_win_prob(self._tiles, self._target_hits))) * 0.94
        balance = max(1e-8, self._bankroll)
        bet = max(1e-8, self._base)
        profit = 0.0
        ls = 0
        longest = 0
        busted = False
        for _ in range(max(1, self._max_bets)):
            if bet > balance or bet <= 0:
                busted = True
                break
            balance -= bet
            hits = len(set(random.sample(range(40), self._tiles)) & set(random.sample(range(40), 10)))
            if hits >= self._target_hits:
                payout = bet * payout_mult
                balance += payout
                profit += payout - bet
                bet = self._base
                ls = 0
            else:
                profit -= bet
                ls += 1
                longest = max(longest, ls)
                bet = bet * (1 + self._loss_inc / 100.0)
        return profit, busted, longest

    def _mines_win_prob(self, mines_count, safe_picks):
        safe_tiles = 25 - mines_count
        prob = 1.0
        for i in range(safe_picks):
            prob *= (safe_tiles - i) / (25 - i)
        return prob

    def _mines_session(self):
        payout_mult = (1.0 / max(1e-6, self._mines_win_prob(self._mines, self._safe_picks))) * 0.94
        balance = max(1e-8, self._bankroll)
        bet = max(1e-8, self._base)
        profit = 0.0
        ls = 0
        longest = 0
        busted = False
        for _ in range(max(1, self._max_bets)):
            if bet > balance or bet <= 0:
                busted = True
                break
            balance -= bet
            tiles = list(range(25))
            mine_set = set(random.sample(tiles, self._mines))
            remaining = tiles[:]
            won = True
            for _p in range(self._safe_picks):
                pick = random.choice(remaining)
                remaining.remove(pick)
                if pick in mine_set:
                    won = False
                    break
            if won:
                payout = bet * payout_mult
                balance += payout
                profit += payout - bet
                bet = self._base
                ls = 0
            else:
                profit -= bet
                ls += 1
                longest = max(longest, ls)
                bet = bet * (1 + self._loss_inc / 100.0)
        return profit, busted, longest

    def _run_one(self):
        if self._game == 'dice':
            return self._dice_session()
        if self._game == 'limbo':
            return self._limbo_session()
        if self._game == 'keno':
            return self._keno_session()
        return self._mines_session()

    def _process_batch(self, dt):
        batch = min(50, self._sessions - self._done)
        for _ in range(batch):
            p, busted, longest = self._run_one()
            self._profits.append(p)
            if busted:
                self._busts += 1
            if p > 0:
                self._wins += 1
            self._best = p if self._best is None else max(self._best, p)
            self._worst = p if self._worst is None else min(self._worst, p)
            self._longest_ls = max(self._longest_ls, longest)
            self._done += 1

        self.progress_bar.value = self._done
        self.status_lbl.text = f"Status: Testing {self._done} / {self._sessions}"

        if self._done >= self._sessions:
            avg_profit = statistics.mean(self._profits) if self._profits else 0.0
            median_profit = statistics.median(self._profits) if self._profits else 0.0
            win_rate = (self._wins / self._sessions) * 100.0
            bust_rate = (self._busts / self._sessions) * 100.0

            self.results_grid.clear_widgets()
            lines = [
                ("Average Profit", f"{avg_profit:.4f}"),
                ("Median Profit", f"{median_profit:.4f}"),
                ("Best Session", f"{self._best:.4f}"),
                ("Worst Session", f"{self._worst:.4f}"),
                ("Profitable Sessions", f"{win_rate:.2f}%"),
                ("Bust Rate", f"{bust_rate:.2f}%"),
                ("Longest Loss Streak", str(self._longest_ls)),
                ("Game", self._game.upper()),
            ]
            for k, v in lines:
                self.results_grid.add_widget(Label(text=k, color=get_color_from_hex(STAKE_TEXT), size_hint_y=None, height=dp(24)))
                self.results_grid.add_widget(Label(text=v, color=get_color_from_hex(STAKE_GREEN), size_hint_y=None, height=dp(24)))

            self.summary.text = "Stress test complete."
            self.status_lbl.text = "Status: Complete"
            self.run_btn.disabled = False
            self._running = False
            return False
        return True


class BankrollSurvivalScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        outer = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))
        outer.add_widget(Label(text="BANKROLL SURVIVAL LAB", font_size='20sp', bold=True,
                               color=get_color_from_hex(STAKE_GREEN), size_hint_y=None, height=dp(36)))

        scroll = ScrollView()
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        inner.bind(minimum_height=inner.setter('height'))
        self.inputs = {}
        fields = [
            ("Bankroll", "20"),
            ("Base Bet", "0.1"),
            ("Win Chance %", "49.5"),
            ("Multiplier", "2.0"),
            ("Increase on Loss %", "50"),
            ("Max Bets / Session", "12"),
            ("Sessions", "5000"),
        ]
        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        for label_text, default in fields:
            grid.add_widget(Label(text=label_text, color=get_color_from_hex(STAKE_TEXT), font_size='12sp',
                                  size_hint_y=None, height=dp(36)))
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(ti)
        inner.add_widget(grid)

        self.run_btn = StyledButton(text="RUN SURVIVAL TEST")
        self.run_btn.bind(on_release=self.start_test)
        inner.add_widget(self.run_btn)

        self.status_lbl = Label(text="Status: Idle", color=get_color_from_hex(STAKE_TEXT), font_size='11sp',
                                size_hint_y=None, height=dp(22))
        self.progress_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(10))
        inner.add_widget(self.status_lbl)
        inner.add_widget(self.progress_bar)

        self.summary = Label(text="Results will appear here", color=get_color_from_hex(STAKE_GREEN),
                             font_size='14sp', size_hint_y=None, height=dp(80))
        inner.add_widget(self.summary)

        self.results_grid = GridLayout(cols=2, spacing=dp(4), size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        inner.add_widget(self.results_grid)

        scroll.add_widget(inner)
        outer.add_widget(scroll)
        outer.add_widget(SimpleNav())
        self.add_widget(outer)
        self._running = False

    def start_test(self, *args):
        if self._running:
            return
        self._running = True
        self.run_btn.disabled = True
        self.results_grid.clear_widgets()
        self._bankroll = safe_float(self.inputs["Bankroll"].text, 20)
        self._base = safe_float(self.inputs["Base Bet"].text, 0.1)
        self._chance = safe_float(self.inputs["Win Chance %"].text, 49.5)
        self._multi = safe_float(self.inputs["Multiplier"].text, 2.0)
        self._loss_inc = safe_float(self.inputs["Increase on Loss %"].text, 50)
        self._max_bets = safe_int(self.inputs["Max Bets / Session"].text, 12)
        self._sessions = max(1, safe_int(self.inputs["Sessions"].text, 5000))
        self._done = 0
        self._survived = 0
        self._profits = []
        self._worst = None
        self._best = None
        self.progress_bar.max = self._sessions
        self.progress_bar.value = 0
        self.summary.text = "Running survival simulation..."
        Clock.schedule_interval(self._process_batch, 0)

    def _process_batch(self, dt):
        batch = min(50, self._sessions - self._done)
        for _ in range(batch):
            result = MonteCarloEngine.run_sessions(
                bankroll=self._bankroll,
                base_bet=self._base,
                multiplier=self._multi,
                win_chance=self._chance,
                inc_on_win=0,
                inc_on_loss=self._loss_inc,
                stop_profit=0,
                stop_loss=0,
                max_bets=self._max_bets,
                sessions=1,
            )
            p = result["average_profit"]
            busted = result["bust_rate"] > 0
            if not busted:
                self._survived += 1
            self._profits.append(p)
            self._best = p if self._best is None else max(self._best, p)
            self._worst = p if self._worst is None else min(self._worst, p)
            self._done += 1

        self.progress_bar.value = self._done
        self.status_lbl.text = f"Status: Simulating {self._done} / {self._sessions}"

        if self._done >= self._sessions:
            survival = (self._survived / self._sessions) * 100.0
            bust = 100.0 - survival
            avg_profit = statistics.mean(self._profits) if self._profits else 0.0
            roi = (avg_profit / max(1e-8, self._bankroll)) * 100.0
            lines = [
                ("Survival Chance", f"{survival:.2f}%"),
                ("Bust Chance", f"{bust:.2f}%"),
                ("Average Profit", f"{avg_profit:.4f}"),
                ("Expected ROI", f"{roi:.2f}%"),
                ("Best Session", f"{self._best:.4f}"),
                ("Worst Session", f"{self._worst:.4f}"),
            ]
            for k, v in lines:
                self.results_grid.add_widget(Label(text=k, color=get_color_from_hex(STAKE_TEXT), size_hint_y=None, height=dp(24)))
                self.results_grid.add_widget(Label(text=v, color=get_color_from_hex(STAKE_GREEN), size_hint_y=None, height=dp(24)))

            self.summary.text = "Bankroll survival simulation complete."
            self.status_lbl.text = "Status: Complete"
            self.run_btn.disabled = False
            self._running = False
            return False
        return True


class StrategyForgeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        outer = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))
        outer.add_widget(Label(text="STRATEGY FORGE", font_size='20sp', bold=True,
                               color=get_color_from_hex(STAKE_GREEN), size_hint_y=None, height=dp(36)))

        scroll = ScrollView()
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        inner.bind(minimum_height=inner.setter('height'))
        self.inputs = {}
        fields = [
            ("Bankroll", "20"),
            ("Population Size", "24"),
            ("Generations", "6"),
            ("Elite Keep", "6"),
            ("Children Per Generation", "24"),
            ("Sessions / Strategy", "400"),
            ("Max Bets / Session", "12"),
            ("Top Results", "8"),
        ]
        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        for label_text, default in fields:
            grid.add_widget(Label(text=label_text, color=get_color_from_hex(STAKE_TEXT), font_size='12sp',
                                  size_hint_y=None, height=dp(36)))
            ti = StyledInput(text=default)
            self.inputs[label_text] = ti
            grid.add_widget(ti)
        inner.add_widget(grid)

        row1 = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(40))
        row1.add_widget(Label(text="Game", color=get_color_from_hex(STAKE_TEXT), font_size='12sp'))
        self.game_spinner = Spinner(text='dice', values=('dice', 'limbo', 'keno', 'mines'),
                                    size_hint_y=None, height=dp(38), background_normal='',
                                    background_color=get_color_from_hex(STAKE_INPUT), color=(1,1,1,1))
        row1.add_widget(self.game_spinner)
        inner.add_widget(row1)

        row2 = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(40))
        row2.add_widget(Label(text="Optimize For", color=get_color_from_hex(STAKE_TEXT), font_size='12sp'))
        self.goal_spinner = Spinner(text='Profit/Risk', values=('Profit', 'Safety', 'Profit/Risk'),
                                    size_hint_y=None, height=dp(38), background_normal='',
                                    background_color=get_color_from_hex(STAKE_INPUT), color=(1,1,1,1))
        row2.add_widget(self.goal_spinner)
        inner.add_widget(row2)

        self.run_btn = StyledButton(text="DISCOVER STRATEGY")
        self.run_btn.bind(on_release=self.start_forge)
        inner.add_widget(self.run_btn)

        self.status_lbl = Label(text="Status: Idle", color=get_color_from_hex(STAKE_TEXT), font_size='11sp',
                                size_hint_y=None, height=dp(22))
        self.progress_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(10))
        inner.add_widget(self.status_lbl)
        inner.add_widget(self.progress_bar)

        self.summary = Label(text="Best discovered strategies will appear here", color=get_color_from_hex(STAKE_GREEN),
                             font_size='14sp', size_hint_y=None, height=dp(80))
        inner.add_widget(self.summary)

        self.results_grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        inner.add_widget(self.results_grid)

        scroll.add_widget(inner)
        outer.add_widget(scroll)
        outer.add_widget(SimpleNav())
        self.add_widget(outer)
        self._running = False

    def compute_score(self, avg_profit, bust_rate, win_rate):
        goal = self.goal_spinner.text
        if goal == "Profit":
            return avg_profit
        elif goal == "Safety":
            return (win_rate * 0.2) - (bust_rate * 3.0)
        return avg_profit - (bust_rate * 0.25)

    def _comb(self, n, r):
        return math.comb(n, r) if 0 <= r <= n else 0

    def _keno_prob(self, tiles, target):
        total = self._comb(40, 10)
        p = 0.0
        for h in range(target, min(tiles, 10)+1):
            ways = self._comb(tiles, h) * self._comb(40-tiles, 10-h)
            p += ways / total if total else 0
        return p

    def _mines_prob(self, mines_count, safe_picks):
        safe_tiles = 25 - mines_count
        prob = 1.0
        for i in range(safe_picks):
            prob *= (safe_tiles - i) / (25 - i)
        return prob

    def random_strategy(self, bankroll):
        g = self.game_spinner.text
        if g == 'dice':
            return {"base_bet": round(random.uniform(0.01, min(0.25, bankroll*0.02)), 4),
                    "multiplier": round(random.uniform(1.5, 8.0), 2),
                    "loss_pct": round(random.uniform(5, 80), 2)}
        if g == 'limbo':
            return {"base_bet": round(random.uniform(0.01, min(0.25, bankroll*0.02)), 4),
                    "target_multiplier": round(random.uniform(1.5, 15.0), 2),
                    "loss_pct": round(random.uniform(5, 80), 2)}
        if g == 'keno':
            tiles = random.randint(1, 10)
            return {"tiles": tiles, "target_hits": random.randint(1, min(tiles, 6)),
                    "base_bet": round(random.uniform(0.01, min(0.25, bankroll*0.02)), 4),
                    "loss_pct": round(random.uniform(5, 80), 2)}
        mines = random.randint(1, 10)
        safe_picks = random.randint(1, max(1, min(10, 24-mines)))
        return {"mines_count": mines, "safe_picks": safe_picks,
                "base_bet": round(random.uniform(0.01, min(0.25, bankroll*0.02)), 4),
                "loss_pct": round(random.uniform(5, 80), 2)}

    def mutate_strategy(self, parent, bankroll):
        g = self.game_spinner.text
        if g == 'dice':
            return {
                "base_bet": max(0.01, min(round(parent["base_bet"] * random.uniform(0.85, 1.15), 4), min(0.25, bankroll*0.02))),
                "multiplier": max(1.2, min(round(parent["multiplier"] * random.uniform(0.9, 1.1), 2), 15.0)),
                "loss_pct": max(1.0, min(round(parent["loss_pct"] * random.uniform(0.85, 1.15), 2), 100.0)),
            }
        if g == 'limbo':
            return {
                "base_bet": max(0.01, min(round(parent["base_bet"] * random.uniform(0.85, 1.15), 4), min(0.25, bankroll*0.02))),
                "target_multiplier": max(1.2, min(round(parent["target_multiplier"] * random.uniform(0.9, 1.1), 2), 25.0)),
                "loss_pct": max(1.0, min(round(parent["loss_pct"] * random.uniform(0.85, 1.15), 2), 100.0)),
            }
        if g == 'keno':
            tiles = max(1, min(10, parent["tiles"] + random.choice([-1,0,1])))
            target = max(1, min(tiles, parent["target_hits"] + random.choice([-1,0,1])))
            return {
                "tiles": tiles,
                "target_hits": target,
                "base_bet": max(0.01, min(round(parent["base_bet"] * random.uniform(0.85, 1.15), 4), min(0.25, bankroll*0.02))),
                "loss_pct": max(1.0, min(round(parent["loss_pct"] * random.uniform(0.85, 1.15), 2), 100.0)),
            }
        mines = max(1, min(10, parent["mines_count"] + random.choice([-1,0,1])))
        safe_picks = max(1, min(24-mines, parent["safe_picks"] + random.choice([-1,0,1])))
        return {
            "mines_count": mines,
            "safe_picks": safe_picks,
            "base_bet": max(0.01, min(round(parent["base_bet"] * random.uniform(0.85, 1.15), 4), min(0.25, bankroll*0.02))),
            "loss_pct": max(1.0, min(round(parent["loss_pct"] * random.uniform(0.85, 1.15), 2), 100.0)),
        }

    def _eval(self, strat, bankroll, max_bets, sessions_per_strategy):
        g = self.game_spinner.text
        if g == 'dice':
            result = MonteCarloEngine.run_sessions(bankroll, strat["base_bet"], strat["multiplier"], 99/max(1.01,strat["multiplier"]), 0, strat["loss_pct"], 0, 0, max_bets, sessions_per_strategy)
            return {**strat, "label": f"B{strat['base_bet']} M{strat['multiplier']} L{strat['loss_pct']}",
                    "avg_profit": result["average_profit"], "median_profit": result["median_profit"], "best_session": result["best_session"], "worst_session": result["worst_session"],
                    "win_rate": result["win_rate"], "bust_rate": result["bust_rate"], "longest_ls": result["longest_loss_streak"],
                    "score": self.compute_score(result["average_profit"], result["bust_rate"], result["win_rate"])}
        if g == 'limbo':
            chance = 99.0 / max(1.01, strat["target_multiplier"])
            result = MonteCarloEngine.run_sessions(bankroll, strat["base_bet"], strat["target_multiplier"], chance, 0, strat["loss_pct"], 0, 0, max_bets, sessions_per_strategy)
            return {**strat, "label": f"B{strat['base_bet']} T{strat['target_multiplier']} L{strat['loss_pct']}",
                    "avg_profit": result["average_profit"], "median_profit": result["median_profit"], "best_session": result["best_session"], "worst_session": result["worst_session"],
                    "win_rate": result["win_rate"], "bust_rate": result["bust_rate"], "longest_ls": result["longest_loss_streak"],
                    "score": self.compute_score(result["average_profit"], result["bust_rate"], result["win_rate"])}
        if g == 'keno':
            p = self._keno_prob(strat["tiles"], strat["target_hits"])
            result = MonteCarloEngine.run_sessions(bankroll, strat["base_bet"], (1/max(1e-6,p))*0.94, p*100, 0, strat["loss_pct"], 0, 0, max_bets, sessions_per_strategy)
            return {**strat, "label": f"{strat['tiles']}T {strat['target_hits']}H B{strat['base_bet']} L{strat['loss_pct']}",
                    "avg_profit": result["average_profit"], "median_profit": result["median_profit"], "best_session": result["best_session"], "worst_session": result["worst_session"],
                    "win_rate": result["win_rate"], "bust_rate": result["bust_rate"], "longest_ls": result["longest_loss_streak"],
                    "score": self.compute_score(result["average_profit"], result["bust_rate"], result["win_rate"])}
        p = self._mines_prob(strat["mines_count"], strat["safe_picks"])
        result = MonteCarloEngine.run_sessions(bankroll, strat["base_bet"], (1/max(1e-6,p))*0.94, p*100, 0, strat["loss_pct"], 0, 0, max_bets, sessions_per_strategy)
        return {**strat, "label": f"{strat['mines_count']}M {strat['safe_picks']}P B{strat['base_bet']} L{strat['loss_pct']}",
                "avg_profit": result["average_profit"], "median_profit": result["median_profit"], "best_session": result["best_session"], "worst_session": result["worst_session"],
                "win_rate": result["win_rate"], "bust_rate": result["bust_rate"], "longest_ls": result["longest_loss_streak"],
                "score": self.compute_score(result["average_profit"], result["bust_rate"], result["win_rate"])}

    def start_forge(self, *args):
        if self._running:
            return
        self._running = True
        self.run_btn.disabled = True
        self.results_grid.clear_widgets()
        self._bankroll = safe_float(self.inputs["Bankroll"].text, 20)
        self._population_size = max(2, safe_int(self.inputs["Population Size"].text, 24))
        self._generations = max(1, safe_int(self.inputs["Generations"].text, 6))
        self._elite_keep = max(1, safe_int(self.inputs["Elite Keep"].text, 6))
        self._children_per_generation = max(2, safe_int(self.inputs["Children Per Generation"].text, 24))
        self._sessions_per_strategy = max(1, safe_int(self.inputs["Sessions / Strategy"].text, 400))
        self._max_bets = max(1, safe_int(self.inputs["Max Bets / Session"].text, 12))
        self._top_results = max(1, safe_int(self.inputs["Top Results"].text, 8))
        self._population = [self.random_strategy(self._bankroll) for _ in range(self._population_size)]
        self._generation = 0
        self._best_overall = []
        self.progress_bar.max = self._generations
        self.progress_bar.value = 0
        self.summary.text = "Searching for strong strategies..."
        Clock.schedule_interval(self._forge_step, 0)

    def _forge_step(self, dt):
        if self._generation >= self._generations:
            unique_results = []
            seen = set()
            for item in sorted(self._best_overall, key=lambda x: x["score"], reverse=True):
                key = item["label"]
                if key not in seen:
                    seen.add(key)
                    unique_results.append(item)
            self.results_grid.clear_widgets()
            for i, item in enumerate(unique_results[:self._top_results], start=1):
                card = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(148), padding=dp(8), spacing=dp(3))
                def _upd(inst, val):
                    if hasattr(inst, "_bg_rect"):
                        inst._bg_rect.pos = inst.pos
                        inst._bg_rect.size = inst.size
                with card.canvas.before:
                    Color(rgba=get_color_from_hex(STAKE_INPUT))
                    card._bg_rect = Rectangle(pos=card.pos, size=card.size)
                card.bind(pos=_upd, size=_upd)
                card.add_widget(Label(text=f"#{i} | Avg {item['avg_profit']:.4f} | Bust {item['bust_rate']:.2f}%",
                                      color=get_color_from_hex(STAKE_GREEN), bold=True, size_hint_y=None, height=dp(22), font_size='12sp'))
                card.add_widget(Label(text=item["label"], color=get_color_from_hex(STAKE_TEXT), size_hint_y=None, height=dp(20), font_size='11sp'))
                card.add_widget(Label(text=f"Win Rate: {item['win_rate']:.2f}% | Longest LS: {item['longest_ls']} | Score: {item['score']:.4f}",
                                      color=get_color_from_hex(STAKE_TEXT), size_hint_y=None, height=dp(20), font_size='11sp'))
                note = "Simulation result only. Real-world gambling results may differ."
                card.add_widget(Label(text=note, color=get_color_from_hex(SUBTITLE_TEXT), size_hint_y=None, height=dp(34), font_size='10sp'))
                save_btn = StyledButton(text="SAVE TO LIBRARY", bg_color=UTILITY_COLOR, height=dp(32))
                save_btn.bind(on_release=lambda x, data=item, rank=i: self.save_result(data, rank))
                card.add_widget(save_btn)
                self.results_grid.add_widget(card)
            self.status_lbl.text = "Status: Complete"
            self.summary.text = "Strategy discovery complete."
            self.run_btn.disabled = False
            self._running = False
            return False

        evaluated = [self._eval(s, self._bankroll, self._max_bets, self._sessions_per_strategy) for s in self._population]
        evaluated.sort(key=lambda x: x["score"], reverse=True)
        elites = evaluated[:self._elite_keep]
        self._best_overall.extend(elites)
        elite_strats = []
        for e in elites:
            e = dict(e)
            # strip derived keys
            for k in list(e.keys()):
                if k in ("label","avg_profit","median_profit","best_session","worst_session","win_rate","bust_rate","longest_ls","score"):
                    e.pop(k,None)
            elite_strats.append(e)
        new_population = []
        while len(new_population) < self._children_per_generation:
            parent = random.choice(elite_strats)
            new_population.append(self.mutate_strategy(parent, self._bankroll))
        self._population = new_population
        self._generation += 1
        self.progress_bar.value = self._generation
        top_score = elites[0]["score"] if elites else 0.0
        self.status_lbl.text = f"Status: Generation {self._generation} / {self._generations}"
        self.summary.text = f"Best score so far: {top_score:.4f}"
        return True

    def save_result(self, item, rank):
        game = self.game_spinner.text
        if game == 'dice':
            strategy = normalize_strategy({
                "name": f"FORGE DICE | {item['label']}",
                "category": "Experimental",
                "game": "dice",
                "source": "strategy_forge",
                "bank": str(self.inputs["Bankroll"].text),
                "base": str(item["base_bet"]),
                "multi": str(item["multiplier"]),
                "win_action": "Reset",
                "loss_action": f"Increase {item['loss_pct']}%",
                "max_bets": str(self.inputs["Max Bets / Session"].text),
                "notes": f"Saved from Strategy Forge | Rank #{rank} | Avg {item['avg_profit']:.4f} | Bust {item['bust_rate']:.2f}% | Score {item['score']:.4f}"
            })
        elif game == 'limbo':
            strategy = normalize_strategy({
                "name": f"FORGE LIMBO | {item['label']}",
                "category": "Experimental",
                "game": "limbo",
                "source": "strategy_forge",
                "bank": str(self.inputs["Bankroll"].text),
                "base": str(item["base_bet"]),
                "multi": str(item["target_multiplier"]),
                "win_action": "Reset",
                "loss_action": f"Increase {item['loss_pct']}%",
                "max_bets": str(self.inputs["Max Bets / Session"].text),
                "notes": f"Saved from Strategy Forge | Rank #{rank} | Avg {item['avg_profit']:.4f} | Bust {item['bust_rate']:.2f}% | Score {item['score']:.4f}"
            })
        elif game == 'keno':
            p = self._keno_prob(item["tiles"], item["target_hits"])
            strategy = normalize_strategy({
                "name": f"FORGE KENO | {item['label']}",
                "category": "Experimental",
                "game": "keno",
                "source": "strategy_forge",
                "bank": str(self.inputs["Bankroll"].text),
                "base": str(item["base_bet"]),
                "multi": str(round((1/max(1e-6,p))*0.94,2)),
                "win_action": "Reset",
                "loss_action": f"Increase {item['loss_pct']}%",
                "max_bets": str(self.inputs["Max Bets / Session"].text),
                "notes": f"Saved from Strategy Forge | Rank #{rank} | Tiles {item['tiles']} | Target {item['target_hits']} | Avg {item['avg_profit']:.4f} | Bust {item['bust_rate']:.2f}% | Score {item['score']:.4f}"
            })
        else:
            p = self._mines_prob(item["mines_count"], item["safe_picks"])
            strategy = normalize_strategy({
                "name": f"FORGE MINES | {item['label']}",
                "category": "Experimental",
                "game": "mines",
                "source": "strategy_forge",
                "bank": str(self.inputs["Bankroll"].text),
                "base": str(item["base_bet"]),
                "multi": str(round((1/max(1e-6,p))*0.94,2)),
                "win_action": "Reset",
                "loss_action": f"Increase {item['loss_pct']}%",
                "max_bets": str(self.inputs["Max Bets / Session"].text),
                "notes": f"Saved from Strategy Forge | Rank #{rank} | Mines {item['mines_count']} | Picks {item['safe_picks']} | Avg {item['avg_profit']:.4f} | Bust {item['bust_rate']:.2f}% | Score {item['score']:.4f}"
            })
        GLOBAL_BANK.strategies.append(strategy)
        GLOBAL_BANK.save_strategies()
        Popup(title="Saved", content=Label(text=f"Saved:\n{strategy['name']}"), size_hint=(0.75,0.25)).open()


class MainMenu(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        outer = BoxLayout(orientation='vertical', padding=[dp(14), dp(42), dp(14), dp(10)], spacing=dp(6))

        hero = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(160), padding=dp(10), spacing=dp(6))
        def _hero_update(instance, value):
            if hasattr(instance, "_bg_rect"):
                instance._bg_rect.pos = instance.pos
                instance._bg_rect.size = instance.size
            if hasattr(instance, "_strip_left"):
                w = instance.width / 3.0
                instance._strip_left.pos = instance.pos
                instance._strip_left.size = (w, dp(4))
                instance._strip_mid.pos = (instance.x + w, instance.y)
                instance._strip_mid.size = (w, dp(4))
                instance._strip_right.pos = (instance.x + (2 * w), instance.y)
                instance._strip_right.size = (w, dp(4))
        with hero.canvas.before:
            Color(rgba=get_color_from_hex(STAKE_INPUT))
            hero._bg_rect = Rectangle(pos=hero.pos, size=hero.size)
            Color(rgba=get_color_from_hex(DICE_COLOR))
            hero._strip_left = Rectangle(pos=hero.pos, size=(0, 0))
            Color(rgba=get_color_from_hex(KENO_COLOR))
            hero._strip_mid = Rectangle(pos=hero.pos, size=(0, 0))
            Color(rgba=get_color_from_hex(SPORTS_COLOR))
            hero._strip_right = Rectangle(pos=hero.pos, size=(0, 0))
        hero.bind(pos=_hero_update, size=_hero_update)

        self.bank_lbl = Label(
            text="PROFIT: $0.00 | TIME: 00:00",
            size_hint_y=None,
            height=dp(24),
            color=get_color_from_hex(STAKE_GREEN),
            bold=True
        )
        Clock.schedule_interval(self.update_header, 1)

        title = Label(
            text="Casino Tools Pro\n[size=22]v6.3[/size]",
            markup=True,
            font_size='28sp',
            bold=True,
            size_hint_y=None,
            height=dp(54),
            color=get_color_from_hex(STAKE_GREEN),
            halign='center'
        )

        subtitle = Label(
            text="Private gambling analytics toolkit",
            color=get_color_from_hex(SUBTITLE_TEXT),
            font_size='11sp',
            size_hint_y=None,
            height=dp(16)
        )

        self.demo_lbl = Label(
            text="",
            color=get_color_from_hex(STAKE_TEXT),
            font_size='10sp',
            size_hint_y=None,
            height=dp(18)
        )

        p_box = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(5))
        self.p_in = StyledInput(hint_text="Enter Win/Loss (+/-)")
        p_box.add_widget(self.p_in)
        u_btn = StyledButton(text="UPDATE", size_hint_x=0.32, bg_color=UTILITY_COLOR, height=dp(34))
        u_btn.bind(on_release=self.update_profit)
        p_box.add_widget(u_btn)

        hero.add_widget(self.bank_lbl)
        hero.add_widget(title)
        hero.add_widget(subtitle)
        hero.add_widget(self.demo_lbl)
        hero.add_widget(p_box)
        outer.add_widget(hero)

        scroll = ScrollView()
        tools_layout = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        tools_layout.bind(minimum_height=tools_layout.setter('height'))

        sections = [
            ("LIBRARY", [
                ("Strategies Library", 'strats', LIBRARY_COLOR),
            ]),
            ("CASINO CORE", [
                ("Dice Simulator", 'dice_sim', DICE_COLOR),
                ("Dice / Limbo Calculator", 'dice', DICE_COLOR),
                ("Monte Carlo Simulator", 'mc', DICE_COLOR),
                ("Dice Optimizer", 'dice_opt', DICE_COLOR),
                ("Dice Auto Generator", 'dice_gen', DICE_COLOR),
            ]),
            ("EVOLUTION LAB", [
                ("Strategy Forge", 'forge', DICE_COLOR),
                ("Dice Evolution Engine", 'dice_evo', DICE_COLOR),
                ("Limbo Evolution Engine", 'limbo_evo', LIMBO_COLOR),
                ("Keno Evolution Engine", 'keno_evo', KENO_COLOR),
                ("Mines Evolution Engine", 'mines_evo', MINES_COLOR),
            ]),
            ("RESEARCH LAB", [
                ("Strategy Stress Test", 'stress_lab', UTILITY_COLOR),
                ("Bankroll Survival Lab", 'survival_lab', UTILITY_COLOR),
            ]),
            ("GAME ANALYTICS", [
                ("Keno Monte Carlo", 'keno_mc', KENO_COLOR),
                ("Mines Analytics", 'mines', MINES_COLOR),
                ("Blackjack Strategy Hub", 'bj', UTILITY_COLOR),
            ]),
            ("SPORTS", [
                ("Sports Betting Lab", 'sports_lab', SPORTS_COLOR),
            ]),
            ("UTILITIES", [
                ("Compound Growth Pro", 'compound', UTILITY_COLOR),
                ("Pattern Sequence Master", 'pattern', UTILITY_COLOR),
                ("Live Crypto Converter", 'converter', UTILITY_COLOR),
            ]),
        ]

        for section_title, items in sections:
            section_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(34), spacing=dp(3))
            section_lbl = Label(
                text=section_title,
                color=get_color_from_hex(STAKE_TEXT),
                font_size='12sp',
                bold=True,
                size_hint_y=None,
                height=dp(18)
            )
            divider = Widget(size_hint_y=None, height=dp(4))
            with divider.canvas.before:
                Color(rgba=get_color_from_hex(DIVIDER_COLOR))
                divider._bg_rect = Rectangle(pos=divider.pos, size=divider.size)
            def _update_divider(instance, value):
                if hasattr(instance, "_bg_rect"):
                    instance._bg_rect.pos = instance.pos
                    instance._bg_rect.size = instance.size
            divider.bind(pos=_update_divider, size=_update_divider)

            section_box.add_widget(section_lbl)
            section_box.add_widget(divider)
            tools_layout.add_widget(section_box)

            for name, sid, color in items:
                btn = StyledButton(text=name, bg_color=color)
                btn.height = dp(42)
                btn.color = (0, 0, 0, 1) if color != UTILITY_COLOR else (1, 1, 1, 1)
                btn.bind(on_release=lambda x, s=sid: App.get_running_app().open_feature(s))
                tools_layout.add_widget(btn)

            tools_layout.add_widget(Widget(size_hint_y=None, height=dp(10)))

        scroll.add_widget(tools_layout)
        outer.add_widget(scroll)
        outer.add_widget(BoxLayout(size_hint_y=None, height=dp(8)))

        license_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        license_btn = StyledButton(text='LICENSE', bg_color=STAKE_GREEN)
        license_btn.bind(on_release=lambda *a: App.get_running_app().show_license_popup())
        license_row.add_widget(license_btn)
        outer.add_widget(license_row)

        action_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        about_btn = StyledButton(text='ABOUT', bg_color=UTILITY_COLOR, size_hint_x=0.28)
        about_btn.color = (1, 1, 1, 1)
        about_btn.bind(on_release=self.show_about)

        reset_tracker_btn = StyledButton(text='RESET TRACKER', bg_color=UTILITY_COLOR, size_hint_x=0.32)
        reset_tracker_btn.color = (1, 1, 1, 1)
        reset_tracker_btn.bind(on_release=self.reset_tracker)

        exit_btn = StyledButton(text='EXIT SYSTEM', bg_color=SOFT_RED, size_hint_x=0.40)
        exit_btn.bind(on_release=lambda *args: sys.exit())
        action_row.add_widget(about_btn)
        action_row.add_widget(reset_tracker_btn)
        action_row.add_widget(exit_btn)
        outer.add_widget(action_row)

        self.add_widget(outer)

    def show_about(self, *args):
        msg = (
            "Casino Tools Pro was shaped by real-life gambling experience, math, "
            "and millions of simulations. It is built to help people study risk, "
            "variance, discipline, and betting structures more clearly.\n\n"
            "This app is not a promise of income, and it should never be treated as "
            "a guaranteed way to earn money. Gambling can be unpredictable, and the "
            "purpose of these tools is analysis, not dream-chasing.\n\n"
            "Created by SH. Built with care by a small creator, not a huge company.\n\n\n\n"
            "SHirimuthugoda©"
        )
        content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
        body = Label(
            text=msg,
            color=get_color_from_hex(STAKE_TEXT),
            text_size=(Window.width - dp(80), None),
            halign='left',
            valign='middle'
        )
        close_btn = StyledButton(text='CLOSE', bg_color=STAKE_GREEN, height=dp(38))
        popup = Popup(title='About Casino Tools Pro', content=content, size_hint=(0.88, 0.62))
        close_btn.bind(on_release=lambda *a: popup.dismiss())
        content.add_widget(body)
        content.add_widget(close_btn)
        popup.open()

    def update_profit(self, *args):
        try:
            GLOBAL_BANK.session_profit += float(self.p_in.text)
            GLOBAL_BANK.save_tracker_state()
            self.p_in.text = ""
            self.update_header(0)
        except Exception:
            pass

    def reset_tracker(self, *args):
        content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
        content.add_widget(Label(
            text='Reset total profit and elapsed time tracker?',
            color=get_color_from_hex(STAKE_TEXT),
            size_hint_y=None,
            height=dp(40)
        ))
        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        yes_btn = StyledButton(text='RESET', bg_color=SOFT_RED)
        no_btn = StyledButton(text='CANCEL', bg_color=UTILITY_COLOR)
        no_btn.color = (1, 1, 1, 1)
        row.add_widget(yes_btn)
        row.add_widget(no_btn)
        content.add_widget(row)
        popup = Popup(title='Reset Tracker', content=content, size_hint=(0.82, 0.28))

        def do_reset(*args):
            GLOBAL_BANK.reset_tracker_state()
            self.update_header(0)
            popup.dismiss()

        yes_btn.bind(on_release=do_reset)
        no_btn.bind(on_release=lambda *a: popup.dismiss())
        popup.open()

    def update_header(self, dt):
        self.bank_lbl.text = f"PROFIT: ${GLOBAL_BANK.session_profit:.2f} | TIME: {GLOBAL_BANK.get_duration()}"
        try:
            self.demo_lbl.text = App.get_running_app().get_demo_status_line()
        except Exception:
            self.demo_lbl.text = ''




def _wrap_demo_method(cls, method_name, usage_key, title, amount=1):
    original = getattr(cls, method_name)
    @wraps(original)
    def demo_guard(self, *args, **kwargs):
        app = App.get_running_app()
        if app and app.get_tier() == DEMO:
            if not DEMO_USAGE.can_use(usage_key, amount):
                show_upgrade_popup(title, PRO, 'Demo limit reached.')
                return
            DEMO_USAGE.consume(usage_key, amount)
        return original(self, *args, **kwargs)
    demo_guard.__name__ = method_name
    demo_guard.__qualname__ = f"{cls.__name__}.{method_name}"
    setattr(cls, method_name, demo_guard)

def _wrap_dice_sim_execute_roll():
    original = DiceSimScreen.execute_roll
    @wraps(original)
    def demo_guard(self, *args, **kwargs):
        app = App.get_running_app()
        if app and app.get_tier() == DEMO:
            if DEMO_USAGE.remaining('dice_sim_rolls') <= 0:
                self.is_auto_running = False
                try:
                    self.auto_btn.text = 'START AUTO'
                except Exception:
                    pass
                show_upgrade_popup('Dice Simulator', PRO, 'Demo roll limit reached.')
                return 'stop'
            DEMO_USAGE.consume('dice_sim_rolls', 1)
        return original(self, *args, **kwargs)
    demo_guard.__name__ = 'execute_roll'
    demo_guard.__qualname__ = f"{DiceSimScreen.__name__}.execute_roll"
    DiceSimScreen.execute_roll = demo_guard

_wrap_dice_sim_execute_roll()
_wrap_demo_method(DiceScreen, 'calculate', 'dice', 'Dice / Limbo Calculator')
_wrap_demo_method(MonteCarloScreen, 'run_monte_carlo', 'mc', 'Monte Carlo Simulator')
_wrap_demo_method(StrategyStressTestScreen, 'start_test', 'stress_lab', 'Strategy Stress Test')
_wrap_demo_method(MinesScreen, 'calc', 'mines', 'Mines Analytics')
_wrap_demo_method(SportsKellyScreen, 'calculate', 'sports_kelly', 'Kelly Bet Calculator')
_wrap_demo_method(SportsParlayScreen, 'calculate', 'sports_parlay', 'Parlay Analyzer')
_wrap_demo_method(SportsValueBetScreen, 'calculate', 'sports_value', 'Value Bet Calculator')
_wrap_demo_method(SportsArbitrageScreen, 'calculate', 'sports_arb', 'Arbitrage Calculator')
_wrap_demo_method(CompoundScreen, 'calc', 'compound', 'Compound Growth Pro')
_wrap_demo_method(PatternScreen, 'generate', 'pattern', 'Pattern Sequence Master')

_original_bj_analyze = BlackjackScreen.analyze
@wraps(_original_bj_analyze)
def _bj_demo_guard(self, p, soft, d):
    app = App.get_running_app()
    if app and app.get_tier() == DEMO:
        if DEMO_USAGE.remaining('bj') <= 0:
            show_upgrade_popup('Blackjack Strategy Hub', PRO, 'Demo limit reached.')
            return 'UPGRADE'
        DEMO_USAGE.consume('bj', 1)
    return _original_bj_analyze(self, p, soft, d)
_bj_demo_guard.__name__ = 'analyze'
_bj_demo_guard.__qualname__ = f"{BlackjackScreen.__name__}.analyze"
BlackjackScreen.analyze = _bj_demo_guard

class CasinoApp(App):
    def get_tier(self):
        return LICENSE_STATE.tier

    def refresh_status_labels(self):
        try:
            menu = self.root.get_screen('menu')
            menu.update_header(0)
        except Exception:
            pass

    def get_demo_status_line(self):
        if self.get_tier() == PRO:
            return 'PRO ACTIVE'
        if self.get_tier() == PRO_PLUS:
            return 'PRO+ ACTIVE'
        return (
            f"DEMO  |  Dice {DEMO_USAGE.remaining('dice_sim_rolls')}  |  Calc {DEMO_USAGE.remaining('dice')}  |  "
            f"MC {DEMO_USAGE.remaining('mc')}  |  BJ {DEMO_USAGE.remaining('bj')}  |  Saves {DEMO_USAGE.remaining('strats_save')}"
        )

    def show_license_popup(self):
        content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
        tier_text = 'DEMO' if self.get_tier() == DEMO else ('PRO' if self.get_tier() == PRO else 'PRO+')
        info = Label(text=f"Current Tier: {tier_text}\nDevice Code:\n{get_device_code()}", color=get_color_from_hex(STAKE_TEXT), halign='center', valign='middle', size_hint_y=None, height=dp(100))
        info.bind(size=lambda instance, value: setattr(instance, 'text_size', value))
        key_input = StyledInput(hint_text='Paste activation key here')
        status = Label(text='', color=get_color_from_hex(STAKE_GREEN), size_hint_y=None, height=dp(22))
        row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        activate_btn = StyledButton(text='ACTIVATE', bg_color=STAKE_GREEN)
        close_btn = StyledButton(text='CLOSE', bg_color=UTILITY_COLOR)
        close_btn.color = (1,1,1,1)
        row.add_widget(activate_btn)
        row.add_widget(close_btn)
        content.add_widget(info)
        content.add_widget(key_input)
        content.add_widget(status)
        content.add_widget(row)
        popup = Popup(title='License Center', content=content, size_hint=(0.90, 0.48))
        def do_activate(*args):
            ok, tier = LICENSE_STATE.activate(key_input.text)
            if ok:
                status.text = 'License activated successfully'
                self.refresh_status_labels()
                Clock.schedule_once(lambda dt: popup.dismiss(), 0.6)
            else:
                status.color = get_color_from_hex(STAKE_RED)
                status.text = 'Invalid license key for this device'
        activate_btn.bind(on_release=do_activate)
        close_btn.bind(on_release=lambda *a: popup.dismiss())
        popup.open()

    def open_feature(self, sid):
        sid = str(sid)
        required = FEATURE_TIERS.get(sid, DEMO)
        title = TOOL_TITLES.get(sid, sid)
        tier = self.get_tier()

        if required == PRO_PLUS and tier != PRO_PLUS:
            show_upgrade_popup(title, PRO_PLUS, 'This is a Pro+ feature.')
            return

        usage_key = None
        if sid == 'dice_sim':
            usage_key = 'dice_sim_rolls'
        elif sid in DEMO_LIMITS:
            usage_key = sid

        if tier == DEMO and usage_key and DEMO_USAGE.remaining(usage_key) <= 0:
            show_upgrade_popup(title, PRO, 'Demo limit reached.')
            return

        if sid in self.root.screen_names:
            self.root.current = sid
        else:
            show_upgrade_popup(title, required, 'Preview mode only.')

    def build(self):
        sm = ScreenManager(transition=FadeTransition())

        screens = [
            (MainMenu, 'menu'),
            (StrategyLibraryScreen, 'strats'),
            (DiceScreen, 'dice'),
            (MonteCarloScreen, 'mc'),
            (KenoMonteCarloScreen, 'keno_mc'),
            (DiceOptimizerScreen, 'dice_opt'),
            (DiceAutoGeneratorScreen, 'dice_gen'),
            (DiceEvolutionScreen, 'dice_evo'),
            (LimboEvolutionScreen, 'limbo_evo'),
            (KenoEvolutionScreen, 'keno_evo'),
            (MinesEvolutionScreen, 'mines_evo'),
            (MinesScreen, 'mines'),
            (CompoundScreen, 'compound'),
            (PatternScreen, 'pattern'),
            (ConverterScreen, 'converter'),
            (BlackjackScreen, 'bj'),

            (SportsLabScreen, 'sports_lab'),
            (SportsKellyScreen, 'sports_kelly'),
            (SportsParlayScreen, 'sports_parlay'),
            (SportsValueBetScreen, 'sports_value'),
            (SportsArbitrageScreen, 'sports_arb'),
            (StrategyStressTestScreen, 'stress_lab'),
            (BankrollSurvivalScreen, 'survival_lab'),
            (StrategyForgeScreen, 'forge'),

            (DiceSimScreen, 'dice_sim')
        ]

        for cls, name in screens:
            sm.add_widget(cls(name=name))

        Clock.schedule_once(lambda dt: self.refresh_status_labels(), 0)
        return sm


if __name__ == '__main__':
    CasinoApp().run()
