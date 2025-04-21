import json 
import requests 
import sqlite3
import itertools
import time
import os
import datetime
import pytz
import humanize
import calendar

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "arbitrage_opportunities.db")

# ========================= FILTER CONFIGURATION =========================
# Set to None or empty list to include all options

# Bookmakers to include in arbitrage search (set to None to include all)
ENABLED_BOOKMAKERS = None #["DraftKings", "BetMGM", "ESPN BET", "Fanduel", "Caesars"]
REGIONS = ["us"]

# Profit margin range (percentage)
MIN_PROFIT_MARGIN = 0.5  # Minimum profit margin to consider (%)
MAX_PROFIT_MARGIN = 10.0  # Maximum profit margin to consider (%) - very high margins might indicate errors

# Sports to include (set to None to include all)
ENABLED_SPORTS = ["americanfootball_nfl", "basketball_nba", "baseball_mlb", "soccer_uefa_champs_league", "icehockey_nhl"]

# Markets to include
MARKETS = ["totals", "h2h"]

# Bet types to include
ENABLED_BET_TYPES = ["Moneyline", "Over/Under"]

# Time criteria for events
MAX_HOURS_UNTIL_EVENT = 48  # Only consider events within this many hours

# Target frequency of checks (set to None to use all credits by the end of the month)
TARGET_CHECKS_PER_HOUR = 3 # Number of checks to perform per hour

# ====================================================================

TIMEZONE = pytz.timezone("America/Detroit")

# API Key for The-Odds-API
API_KEY = "97717d9a1f0e332a51437af3c2e669b8"
BASE_URL = "https://api.the-odds-api.com/v4/sports/{sport_key}/odds"

# List of sports and leagues to track
SPORTS = [
    # American Football
    "americanfootball_cfl", "americanfootball_ncaaf", "americanfootball_nfl", 
    "americanfootball_nfl_preseason", "americanfootball_ufl",
    
    # Aussie Rules
    "aussierules_afl",
    
    # Baseball
    "baseball_mlb", "baseball_milb", "baseball_npb", "baseball_kbo", "baseball_ncaa",
    
    # Basketball
    "basketball_euroleague", "basketball_nba", "basketball_wnba", "basketball_ncaab", 
    "basketball_wncaab", "basketball_nbl",
    
    # Ice Hockey
    "icehockey_nhl", "icehockey_ahl", "icehockey_liiga", "icehockey_mestis",
    "icehockey_sweden_hockey_league", "icehockey_sweden_allsvenskan",
    
    # Rugby League
    "rugbyleague_nrl",
    
    # Soccer
    "soccer_argentina_primera_division", "soccer_australia_aleague", "soccer_austria_bundesliga",
    "soccer_belgium_first_div", "soccer_brazil_campeonato", "soccer_brazil_serie_b",
    "soccer_chile_campeonato", "soccer_china_superleague", "soccer_denmark_superliga",
    "soccer_efl_champ", "soccer_england_efl_cup", "soccer_england_league1",
    "soccer_england_league2", "soccer_epl", "soccer_fa_cup", "soccer_fifa_world_cup",
    "soccer_fifa_world_cup_womens", "soccer_finland_veikkausliiga", "soccer_france_ligue_one",
    "soccer_france_ligue_two", "soccer_germany_bundesliga", "soccer_germany_bundesliga2",
    "soccer_germany_liga3", "soccer_greece_super_league", "soccer_italy_serie_a",
    "soccer_italy_serie_b", "soccer_japan_j_league", "soccer_korea_kleague1",
    "soccer_league_of_ireland", "soccer_mexico_ligamx", "soccer_netherlands_eredivisie",
    "soccer_norway_eliteserien", "soccer_poland_ekstraklasa", "soccer_portugal_primeira_liga",
    "soccer_spain_la_liga", "soccer_spain_segunda_division", "soccer_spl",
    "soccer_sweden_allsvenskan", "soccer_sweden_superettan", "soccer_switzerland_superleague",
    "soccer_turkey_super_league", "soccer_uefa_europa_conference_league", "soccer_uefa_champs_league",
    "soccer_uefa_champs_league_qualification", "soccer_uefa_europa_league", 
    "soccer_uefa_european_championship", "soccer_uefa_euro_qualification",
    "soccer_conmebol_copa_america", "soccer_conmebol_copa_libertadores", "soccer_usa_mls",
    
    # Tennis
    "tennis_atp_aus_open_singles", "tennis_atp_canadian_open", "tennis_atp_china_open",
    "tennis_atp_cincinnati_open", "tennis_atp_dubai", "tennis_atp_french_open",
    "tennis_atp_indian_wells", "tennis_atp_miami_open", "tennis_atp_paris_masters",
    "tennis_atp_qatar_open", "tennis_atp_shanghai_masters", "tennis_atp_us_open",
    "tennis_atp_wimbledon", "tennis_wta_aus_open_singles", "tennis_wta_canadian_open",
    "tennis_wta_china_open", "tennis_wta_cincinnati_open", "tennis_wta_dubai",
    "tennis_wta_french_open", "tennis_wta_indian_wells", "tennis_wta_miami_open",
    "tennis_wta_qatar_open", "tennis_wta_us_open", "tennis_wta_wimbledon",
    "tennis_wta_wuhan_open"
]


BOOKMAKER_LINKS = {
    "BetOnline.ag": "https://www.betonline.ag",
    "BetMGM": "https://sports.mi.betmgm.com",
    "BetRivers": "https://www.betrivers.com",
    "BetUS": "https://www.betus.com.pa",
    "Bovada": "https://www.bovada.lv",
    "Caesars": "https://www.williamhill.com",
    "DraftKings": "https://draftkings.com",
    "Fanatics": "https://sportsbook.fanatics.com",
    "FanDuel": "https://sportsbook.fanduel.com",
    "LowVig.ag": "https://www.lowvig.ag",
    "MyBookie.ag": "https://mybookie.ag",
    "Bally Bet": "https://play.ballybet.com",
    "BetAnySports": "https://betanysports.eu",
    "betPARX": "https://betparx.com",
    "ESPN BET": "https://espnbet.com",
    "Fliff": "https://www.getfliff.com",
    "Hard Rock Bet": "https://app.hardrock.bet",
    "Wind Creek (Betfred PA)": "https://play.windcreekcasino.com",
    "888sport": "https://www.888sport.com",
    "Betfair Exchange": "https://www.betfair.com",
    "Betfair Sportsbook": "https://www.betfair.com",
    "Bet Victor": "https://www.betvictor.com",
    "Betway": "https://betway.com",
    "BoyleSports": "https://boylesports.com",
    "Casumo": "https://casumo.com",
    "Coral": "https://sports.coral.co.uk",
    "Grosvenor": "https://www.grosvenorcasinos.com",
    "Ladbrokes": "https://www.ladbrokes.com",
    "LeoVegas": "https://www.leovegas.com",
    "LiveScore Bet": "https://www.livescorebet.com",
    "Matchbook": "https://www.matchbook.com",
    "Paddy Power": "https://www.paddypower.com",
    "Sky Bet": "https://m.skybet.com",
    "Smarkets": "https://smarkets.com",
    "Unibet": "https://www.unibet.co.uk",
    "Virgin Bet": "https://www.virginbet.com",
    "William Hill (UK)": "https://www.williamhill.com",
    "1xBet": "https://1xbet.com",
    "Betclic": "https://www.betclic.com"
}


# Database setup
def setup_database():
    # Delete existing database if it exists
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("Removed existing database file.")
        except Exception as e:
            print(f"Error removing existing database: {e}")
    
    # Create new database with updated structure
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS opportunities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event TEXT,
                        sport TEXT,
                        league TEXT,
                        market TEXT,
                        bookmaker1 TEXT,
                        team1 TEXT,
                        odds1 REAL,
                        odds1_link TEXT,
                        bookmaker1_link TEXT,
                        bet1 TEXT,
                        bookmaker2 TEXT,
                        team2 TEXT,
                        odds2 REAL,
                        odds2_link TEXT,
                        bookmaker2_link TEXT,
                        bet2 TEXT,
                        profit_margin REAL,
                        total_line TEXT,
                        bet_type TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        commence_time DATETIME
                    )''')
    conn.commit()
    conn.close()
    print("Created new database with updated structure.")


def _call_odds_api(sport: str, market: str) -> list[dict]:
    """Thin wrapper around requests.get that hides all the repetitive
    error/credit‑handling noise."""
    url = BASE_URL.format(sport_key=sport)
    params = {
        "apiKey":      API_KEY,
        "regions":     REGIONS,
        "markets":     market,
        "oddsFormat":  "decimal",
        "includeLinks": "true",
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        print(f"{sport}/{market} – credits left: {r.headers.get('x-requests-remaining')}")
        return r.json()
    except requests.RequestException as exc:
        # one print is enough – no 30‑line stack traces while developing
        print(f"⚠️  {sport}/{market}: {exc}")
        return []

def _filter_bookmakers(bookmakers: list[dict]) -> list[dict]:
    """Keep only the bookmakers the user enabled (if any)."""
    if ENABLED_BOOKMAKERS:
        return [bm for bm in bookmakers if bm["title"] in ENABLED_BOOKMAKERS]
    return bookmakers


def _add_odds_row(buffer: list, *row):
    """Tiny helper so we can .append without the long line‑wraps everywhere."""
    buffer.append(tuple(row))



def fetch_odds() -> list[tuple]:
    """
    Pull odds from The‑Odds‑API and return them in the exact structure the
    original `find_arbitrage` expects – just with far less nesting / noise.
    """
    odds_rows: list[tuple] = []
    now = datetime.datetime.now(TIMEZONE)

    for sport in (ENABLED_SPORTS or SPORTS):
        for market in MARKETS:

            for event in _call_odds_api(sport, market):
                # ─── skip far‑away events ────────────────────────────────
                try:
                    commence = datetime.datetime.fromisoformat(
                        event["commence_time"].replace("Z", "+00:00")
                    ).astimezone(TIMEZONE)
                except (KeyError, ValueError):
                    continue

                if (commence - now).total_seconds() / 3600 > MAX_HOURS_UNTIL_EVENT:
                    continue

                # ─── common fields ───────────────────────────────────────
                sport_title = event["sport_title"]
                league      = event.get("sport_key", sport)
                home_team   = event.get("home_team", "")
                away_team   = event.get("away_team", "")
                event_name  = f"{sport_title} - {event['commence_time']}"

                for bm in _filter_bookmakers(event.get("bookmakers", [])):
                    bm_name = bm["title"]

                    for mkt in bm.get("markets", []):
                        key      = mkt.get("key")
                        outcomes = mkt.get("outcomes", [])

                        # ─── totals (Over/Under) ─────────────────────────
                        if key == "totals" and ("Over/Under" in (ENABLED_BET_TYPES or ["Over/Under"])):

                            over = next((o for o in outcomes if "Over"  in o["name"]), None)
                            under= next((o for o in outcomes if "Under" in o["name"]), None)
                            if not (over and under):
                                continue

                            total_line = str(over.get("point", ""))
                            _add_odds_row(
                                odds_rows,
                                event_name, sport_title, league, market,
                                bm_name,                        # bookmaker
                                home_team, over["price"], over.get("link","N/A"),
                                away_team, under["price"], under.get("link","N/A"),
                                total_line, "Over/Under", commence
                            )

                        # ─── h2h moneyline ───────────────────────────────
                        elif key == "h2h" and ("Moneyline" in (ENABLED_BET_TYPES or ["Moneyline"])):

                            if len(outcomes) != 2:          # ignore 3‑way
                                continue
                            home = next((o for o in outcomes if o["name"] == home_team), None)
                            away = next((o for o in outcomes if o["name"] == away_team), None)
                            if not (home and away):
                                continue

                            _add_odds_row(
                                odds_rows,
                                event_name, sport_title, league, key,
                                bm_name,
                                home_team, home["price"], home.get("link","N/A"),
                                away_team, away["price"], away.get("link","N/A"),
                                "N/A", "Moneyline", commence
                            )

    return odds_rows

# Function to find arbitrage opportunities
def find_arbitrage(odds_list):
    arbitrage_opportunities = []

    def canonical_event(home, away):
        # Put the two team names in a stable order, e.g. alphabetical
        # so that "CAR vs WSH" and "WSH vs CAR" collapse to the same key
        return ' / '.join(sorted([home.strip(), away.strip()]))
    
    # Group odds by event and market type
    grouped_events = {}
    for event, sport, league, market, bookmaker, home_team, odds1, home_link, away_team, odds2, away_link, total_line, bet_type, commence_time in odds_list:
        event_market_key = f"{canonical_event(home_team, away_team)} - {market}"
        
        if event_market_key not in grouped_events:
            grouped_events[event_market_key] = []
        
        grouped_events[event_market_key].append({
            'bookmaker': bookmaker,
            'home_team': home_team,
            'away_team': away_team,
            'home_odds': odds1,  # For h2h, this is home team odds; for totals, this is over odds
            'away_odds': odds2,  # For h2h, this is away team odds; for totals, this is under odds
            'home_link': home_link,
            'away_link': away_link,
            'sport': sport,
            'league': league,
            'market': market,
            'total_line': total_line,
            'bet_type': bet_type,
            'commence_time': commence_time,
        })
    
    # Find arbitrage opportunities (two-way only)
    for event_key, bookmakers in grouped_events.items():
        # Get common information from the first bookmaker
        market = bookmakers[0]['market']
        
        if market == 'totals':
            # Process two-way totals (over/under) markets
            for bm1, bm2 in itertools.combinations(bookmakers, 2):
                # Skip if same bookmaker
                if bm1['bookmaker'] == bm2['bookmaker']:
                    continue
                    
                # ignore books that hang different totals (212.5 vs 213.0, etc.)
                if bm1['total_line'] != bm2['total_line']:
                    continue
                
                best = None   # remember the best direction (“Over/Under” or “Under/Over”)
                
                for (odds1_key, odds2_key, dir1, dir2) in [
                        ('home_odds', 'away_odds', 'Over',  'Under'),   # bm1 Over, bm2 Under
                        ('away_odds', 'home_odds', 'Under', 'Over')     # bm1 Under, bm2 Over
                    ]:
                
                    odds1 = bm1[odds1_key]
                    odds2 = bm2[odds2_key]

                    # protect against bad or zero odds
                    if not odds1 or not odds2:
                        continue
                
                    total_prob = 1/odds1 + 1/odds2
                    if total_prob >= 1:
                        continue                         # no arb in this direction
                
                    margin = (1 - total_prob) * 100
                    if (MIN_PROFIT_MARGIN is not None and margin <  MIN_PROFIT_MARGIN) or \
                       (MAX_PROFIT_MARGIN is not None and margin >  MAX_PROFIT_MARGIN):
                        continue                         # outside user‑set range
                
                    if best is None or margin > best['margin']:
                        best = {
                            'odds1' : odds1,
                            'odds2' : odds2,
                            'bet1'  : f"{dir1} {bm1['total_line']}",
                            'bet2'  : f"{dir2} {bm2['total_line']}",
                            'link1' : bm1['home_link'] if dir1 == 'Over' else bm1['away_link'],
                            'link2' : bm2['home_link'] if dir2 == 'Over' else bm2['away_link'],
                            'margin': margin
                        }
                
                # after both directions have been tested, store only the best one
                if best:
                    home_team = bm1['home_team']
                    away_team = bm1['away_team']
                    arbitrage_opportunities.append((
                        event_key,                     # 0
                        bm1['sport'],                  # 1
                        bm1['league'],                 # 2
                        bm1['market'],                 # 3
                        bm1['bookmaker'],              # 4
                        f"{home_team} vs {away_team}", # 5  matchup
                        best['odds1'],                 # 6
                        best['link1'],                   # 7
                        best['bet1'],                  # 8
                        bm2['bookmaker'],              # 9
                        f"{home_team} vs {away_team}", # 10
                        best['odds2'],                 # 11
                        best['link2'],                   # 12
                        best['bet2'],                  # 13
                        best['margin'],                # 14
                        f"{best['bet1']} / {best['bet2']}",  # 15
                        "Over/Under",                  # 16
                        bm1['commence_time']           # 17
                    ))
                
        
        elif market == 'h2h':
            # Process two-way h2h (moneyline) markets
            for bm1, bm2 in itertools.combinations(bookmakers, 2):
                # Skip if same bookmaker
                if bm1['bookmaker'] == bm2['bookmaker']:
                    continue
                
                best = None
                for dir1, dir2 in [('home', 'away'), ('away', 'home')]:
                    # team names & odds that correspond to this direction
                    team1   = bm1[f'{dir1}_team']
                    team2   = bm2[f'{dir2}_team']
                    odds1   = bm1[f'{dir1}_odds']
                    odds2   = bm2[f'{dir2}_odds']
                
                    # protect against bad or zero odds
                    if not odds1 or not odds2:
                        continue
                
                    total_prob = 1/odds1 + 1/odds2
                    if total_prob >= 1:
                        continue                               # no arb in this direction
                
                    margin = (1 - total_prob) * 100
                    if (MIN_PROFIT_MARGIN is not None and margin <  MIN_PROFIT_MARGIN) or \
                       (MAX_PROFIT_MARGIN is not None and margin >  MAX_PROFIT_MARGIN):
                        continue                               # outside user‑set range
                
                    # keep the better of the two directions
                    if best is None or margin > best['margin']:

                        best = {
                            'team1' : team1,
                            'team2' : team2,
                            'odds1' : odds1,
                            'odds2' : odds2,
                            'link1' : bm1['home_link'] if dir1 == 'home' else bm1['away_link'],
                            'link2' : bm2['home_link'] if dir2 == 'home' else bm2['away_link'],
                            'bet1'  : f"{team1} (Win)",
                            'bet2'  : f"{team2} (Win)",
                            'margin': margin
                        }
                
                # after both directions have been tested, store only the best one
                if best:
                    arbitrage_opportunities.append((
                        event_key,                 # 0
                        bm1['sport'],              # 1
                        bm1['league'],             # 2
                        bm1['market'],             # 3
                        bm1['bookmaker'],          # 4
                        f"{best['team1']} vs {best['team2']}",   # 5  matchup
                        best['odds1'],             # 6
                        best['link1'],               # 7
                        best['bet1'],              # 8
                        bm2['bookmaker'],          # 9
                        f"{best['team1']} vs {best['team2']}",   # 10 matchup again
                        best['odds2'],             # 11
                        best['link2'],               # 12
                        best['bet2'],              # 13
                        best['margin'],            # 14 profit margin
                        f"{best['bet1']} / {best['bet2']}",      # 15
                        "Moneyline",               # 16
                        bm1['commence_time']       # 17
                    ))
    
    # Sort opportunities by profit margin (highest first)
    arbitrage_opportunities.sort(key=lambda x: x[14], reverse=True)
    
    return arbitrage_opportunities

def update_arbitrage_opportunities():
    """Fetch odds, find arbs, then upsert them – same behaviour, less boiler‑plate."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        all_odds      = fetch_odds()
        opportunities = find_arbitrage(all_odds)

        existing = {(e, b1, b2) for e, b1, b2 in cur.execute(
            "SELECT event, bookmaker1, bookmaker2 FROM opportunities"
        )}

        new = 0
        for (
            event, sport, league, market, bm1, team1, odds1, link1, bet1,
            bm2, team2, odds2, link2, bet2, profit, total_line, bet_type, commence
        ) in opportunities:

            bm1_link = BOOKMAKER_LINKS.get(bm1, "N/A")
            bm2_link = BOOKMAKER_LINKS.get(bm2, "N/A")

            if (event, bm1, bm2) in existing:
                cur.execute("""
                    UPDATE opportunities SET
                        odds1=?, odds2=?, profit_margin=?, timestamp=CURRENT_TIMESTAMP,
                        total_line=?, bet_type=?, bet1=?, bet2=?
                    WHERE event=? AND bookmaker1=? AND bookmaker2=? AND commence_time=?""",
                    (odds1, odds2, profit, total_line, bet_type, bet1, bet2,
                     event, bm1, bm2, commence)
                )
            else:
                cur.execute("""
                    INSERT INTO opportunities (
                        event, sport, league, market,
                        bookmaker1, team1, odds1, odds1_link, bookmaker1_link, bet1,
                        bookmaker2, team2, odds2, odds2_link, bookmaker2_link, bet2,
                        profit_margin, total_line, bet_type, commence_time
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (event, sport, league, market,
                     bm1, team1, odds1, link1, bm1_link, bet1,
                     bm2, team2, odds2, link2, bm2_link, bet2,
                     profit, total_line, bet_type, commence)
                )
                new += 1

        # clean up anything older than 10 min
        cur.execute("DELETE FROM opportunities WHERE timestamp < DATETIME('now','-10 minutes')")

        # simple, readable status output
        print(f"Stored {len(opportunities)} arbs "
              f"({new} new, {len(opportunities)-new} updated) "
              f"— filters: Books={ENABLED_BOOKMAKERS or 'All'}, "
              f"Sports={ENABLED_SPORTS or 'All'}, Types={ENABLED_BET_TYPES or 'All'}, "
              f"Profit {MIN_PROFIT_MARGIN}‑{MAX_PROFIT_MARGIN}%, "
              f"≤{MAX_HOURS_UNTIL_EVENT} h to start")



def get_remaining_credits():
    try:
        response = requests.get('https://api.the-odds-api.com/v4/sports/',
            params = {
                "apiKey": API_KEY,
                "regions": "us",
            }
        )
        if response.status_code == 200:
            return int(response.headers["x-requests-remaining"])
        else:
            print("Error fetching credits from API")
            print(response.text)
            return None
    except requests.RequestException as e:
        print(f"Error making request to API: {e}")
        return None

def calculate_sleep_time(credits_left: int, days_left: int) -> int | None:
    """Return the ideal sleep‑seconds between checks or None if we should stop."""

    print(f"Days left in month: {days_left}")

    per_day = credits_left / days_left
    if per_day <= 0:
        print("No credits left for this month.")
        return None

    sports_n   = len(ENABLED_SPORTS or SPORTS)
    books_n    = 1                                     # 1 credit / 10 books – or so they say, doesn't seem to be true
    cost_check = len(MARKETS) * len(REGIONS) * sports_n * books_n

    if per_day < cost_check:
        print("Not enough credits for even one full check per day.")
        return None

    print(f"Arb-finder uses {cost_check} credits per check ({len(MARKETS)} markets, {len(REGIONS)} regions, {sports_n} sports)")

    checks_per_day = per_day / cost_check
    seconds = max(300, (24 * 3600) / checks_per_day)   # ≥5 min
    return int(seconds)

def calculate_max_time_running(credits_left: int, frequency: int) -> int | None:
    """Return the max time we can run this script with the given credits and frequency."""
    if credits_left <= 0 or frequency <= 0:
        return None

    # Calculate the number of checks we can perform
    checks_possible = credits_left // frequency

    # Calculate the total time in seconds
    total_time_seconds = checks_possible * (3600 / TARGET_CHECKS_PER_HOUR)
    
    return int(total_time_seconds)


if __name__ == "__main__":

    print("Calculating max requests...")
    remaining_credits = get_remaining_credits()
    if remaining_credits is None:
        print("Failed to retrieve remaining credits. Exiting...")
        quit()

    print(f"Credits remaining: {remaining_credits}")

    # Calculate sleep time based on remaining credits and target checks
    today = datetime.datetime.now()
    _, days_in_month = calendar.monthrange(today.year, today.month)
    days_left = days_in_month - today.day + 1          # incl. today

    # Calculate target checks per hour
    target_checks = TARGET_CHECKS_PER_HOUR
    if target_checks is None:
        sleep_time = calculate_sleep_time(remaining_credits, days_left)
        if sleep_time is None:
            print("No sleep time calculated. Exiting...")
            quit()
    else:
        # Calculate sleep time based on target checks per hour
        sleep_time = 3600 / target_checks

    sleep_time_human = humanize.precisedelta(datetime.timedelta(seconds=sleep_time))
    print(f"Sleeping for {sleep_time_human} between checks")

    # Calculate max time running based on remaining credits and frequency
    max_time_running = calculate_max_time_running(remaining_credits, target_checks)
    if max_time_running is None:
        print("No max time calculated. Exiting...")
        quit()
    max_time_human = humanize.precisedelta(datetime.timedelta(seconds=max_time_running))
    print(f"Max time running: {max_time_human}")

    # print warning if max time running is less than days left in the month
    if max_time_running < (days_left-1) * 24 * 3600:  # this might not be mathematically correct, but it's a good approximation
        print(f"⚠️ Warning: Max time running ({max_time_human}) is less than days left in the month ({days_left} days).")
        print("\tThis means the script will run out of credits before the end of the month and fail.")
    
    # ask the user if this is okay, hit enter to continue, or anything else to quit
    print("Press Enter to continue or CTRL+C to quit...")
    user_input = input()
    if user_input:
        print("Exiting...")
        quit()


    print("Starting arbitrage opportunity finder...")
    setup_database()
    max_retries = 3
    retry_count = 0
    
    while True:
        try:
            update_arbitrage_opportunities()

            print("Arbitrage opportunities updated successfully.")
            left = get_remaining_credits()
            if left is None:
                print("Failed to retrieve remaining credits. Exiting...")
                break
            print(f"Used {remaining_credits - left} credits.")

            retry_count = 0  # Reset counter on successful run
            print(f"Sleeping for {sleep_time_human}...")
            time.sleep(sleep_time)  # Sleep for calculated time

        except requests.RequestException as e:
            print(f"API Request Error: {e}")
            retry_count += 1
        except sqlite3.Error as e:
            print(f"Database Error: {e}")
            retry_count += 1
        except Exception as e:
            print(f"Unexpected Error: {e}")
            retry_count += 1
        
        if retry_count >= max_retries:
            print("Maximum retry attempts reached. Exiting...")
            break
        
        print(f"Retrying in 320 seconds... (Attempt {retry_count}/{max_retries})")
        time.sleep(320)
