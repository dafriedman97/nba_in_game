import pandas as pd
import os
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np
import json
import ipdb
import importlib
import matplotlib.pyplot as plt
import seaborn as sns

hoops_dir = Path(os.path.abspath(__file__)).parent.parent
data_dir = hoops_dir / "data"
sys.path.append(hoops_dir.as_posix())

pd.set_option("display.max_columns", 100)
pd.set_option("display.max_rows", 25)

from pipeline import team_metadata

def get_game_playstats(pbp, home, vis):
    # stats from here: http://www.espn.com/nba/hollinger/teamstats
    
    ## Events by team
    home_pbp = pbp.loc[pbp['team'] == home]
    vis_pbp = pbp.loc[pbp['team'] == vis]

    ## Points per minute
    home_points, vis_points, time = pbp.iloc[-1][['home_score', 'vis_score', 'time']]
    home_ppm = home_points/time
    vis_ppm = vis_points/time
    
    ## Pace factor (number of possessions per game)
    possessions = pbp.loc[pbp['pos'].notna(), 'pos']
    n_poss = (possessions != possessions.shift(1)).sum() / 2 # number of possessions per team

    ## Assists per possession 
    # skipping--don't have assists

    ## Turnovers
    home_tovs = (home_pbp['event'] == "tov").sum()
    vis_tovs = (vis_pbp['event'] == "tov").sum()
    home_tov_rate, vis_tov_rate = home_tovs/n_poss, vis_tovs/n_poss

    ## Rebound Rates
    home_orebs = len(pbp.loc[(pbp['team'] == home) & (pbp['event'] == "reb") & (pbp['pos'].shift(1) == home)])
    home_drebs = len(pbp.loc[(pbp['team'] == home) & (pbp['event'] == "reb") & (pbp['pos'].shift(1) == vis)])
    vis_orebs = len(pbp.loc[(pbp['team'] == vis) & (pbp['event'] == "reb") & (pbp['pos'].shift(1) == vis)])
    vis_drebs = len(pbp.loc[(pbp['team'] == vis) & (pbp['event'] == "reb") & (pbp['pos'].shift(1) == home)])
    home_oreb_rate = home_orebs/(home_orebs+vis_drebs)
    home_dreb_rate = home_drebs/(home_drebs+vis_orebs)
    vis_oreb_rate = vis_orebs/(vis_orebs+home_drebs)
    vis_dreb_rate = vis_drebs/(vis_drebs+home_orebs)
    home_reb_rate = (home_orebs + home_drebs)/(home_orebs + home_drebs + vis_orebs + vis_drebs)
    vis_reb_rate = (vis_orebs + vis_drebs)/(home_orebs + home_drebs + vis_orebs + vis_drebs)

    # Effective Field Goal Percentage
    home_fg_makes = (home_pbp.event == "fg_make").sum()
    home_fg_misses = (home_pbp.event == "fg_miss").sum()
    home_fg3_makes = (home_pbp.event == "fg3_make").sum()
    home_fg3_misses = (home_pbp.event == "fg3_miss").sum()
    vis_fg_makes = (vis_pbp.event == "fg_make").sum()
    vis_fg_misses = (vis_pbp.event == "fg_miss").sum()
    vis_fg3_makes = (vis_pbp.event == "fg3_make").sum()
    vis_fg3_misses = (vis_pbp.event == "fg3_miss").sum()
    home_efgp = (home_fg_makes + 1.5*home_fg3_makes)/(home_fg_makes + home_fg_misses + home_fg3_makes + home_fg3_misses)
    vis_efgp = (vis_fg_makes + 1.5*vis_fg3_makes)/(vis_fg_makes + vis_fg_misses + vis_fg3_makes + vis_fg3_misses)

    ## True shooting percentage
    home_fta = ((home_pbp.event == "ft_make") + (home_pbp.event == "ft_miss")).sum()
    vis_fta = ((vis_pbp.event == "ft_make") + (vis_pbp.event == "ft_miss")).sum()
    home_tsp = home_points*.5/(home_fg_makes + home_fg_misses + home_fg3_makes + home_fg3_misses + home_fta)
    vis_tsp = vis_points*.5/(vis_fg_makes + vis_fg_misses + vis_fg3_makes + vis_fg3_misses + vis_fta)

    ## Offensive Efficiency
    home_off_eff = home_points/n_poss
    vis_off_eff = vis_points/n_poss
    
    ## Defensive Efficiency
    home_def_eff = vis_points/n_poss
    vis_def_eff = home_points/n_poss    

    ## Return
    return pd.Series({
        'home_pts': home_points,
        'home_ppm': home_ppm,
        'home_poss': n_poss,
        'home_tov_rate': home_tov_rate,
        'home_reb_rate': home_reb_rate,
        'home_oreb_rate': home_oreb_rate,
        'home_dreb_rate': home_dreb_rate, 
        'home_efpg': home_efgp,
        'home_tsp': home_tsp,
        'home_off_eff': home_off_eff,
        'home_def_eff': home_def_eff,
        'vis_pts': vis_points,
        'vis_ppm': vis_ppm,
        'vis_poss': n_poss,
        'vis_tov_rate': vis_tov_rate,
        'vis_reb_rate': vis_reb_rate,
        'vis_oreb_rate': vis_oreb_rate,
        'vis_dreb_rate': vis_dreb_rate, 
        'vis_efpg': vis_efgp,
        'vis_tsp': vis_tsp,
        'vis_off_eff': vis_off_eff,
        'vis_def_eff': vis_def_eff
    })

def get_season_playstats(season, last_calculated_date="0"):
    
    ## Get pbps
    pbp_dir = data_dir / "play_by_play" / season
    pbps = dict([(file.replace('.csv', ''), pd.read_csv(pbp_dir / file)) for file in sorted(os.listdir(pbp_dir)) if file.endswith(".csv")])
    
    ## Playstats df
    game_by_game = team_metadata.get_game_by_game(season)
    # game_by_game = game_by_game.loc[game_by_game['date'] <= "2022-03-01"]
    game_by_game = game_by_game.loc[game_by_game['date'] > last_calculated_date]
    playstats = pd.DataFrame(columns=['team', 'gameid', 'date', 'home', 'pts', 'ppm', 'poss', 'tov_rate', 'reb_rate', 'oreb_rate', 'dreb_rate', 'efpg', 'tsp', 'off_eff', 'def_eff'])
    for _, game in game_by_game.iterrows():
        game_id, date, home, vis = game[['game_id', 'date', 'home', 'vis']]
        pbp = pbps['00' + str(game_id)]
        game_playstats = get_game_playstats(pbp, home, vis)
        playstats.loc[len(playstats)] = [home, game_id, date, True] + list(game_playstats.loc[game_playstats.index.str.startswith("home")])
        playstats.loc[len(playstats)] = [vis, game_id, date, False] + list(game_playstats.loc[game_playstats.index.str.startswith("vis")])
    return playstats

def get_playstats_by_date(season=None, season_playstats=None, write_out=True):
    playstats_dir = data_dir / "playstats"
    os.makedirs(playstats_dir, exist_ok=True)
    season_playstats_path = playstats_dir /  (season + ".csv")
    season_playstats_bygame_path = playstats_dir /  (season + "_by_game.csv")

    ## Check if playstats have already been created for this season
    if os.path.exists(season_playstats_bygame_path): # if it already exists for this season
        old_playstats_by_game = pd.read_csv(season_playstats_bygame_path) 
        last_calculated_date = old_playstats_by_game.date.dropna().max() # last date we calculated playstats for 
        season_playstats_by_game = get_season_playstats(season, last_calculated_date)
        if len(season_playstats_by_game) == 0:
            return old_playstats_by_game
        season_playstats_by_game = pd.concat([old_playstats_by_game, season_playstats_by_game])
        season_playstats_by_game.to_csv(season_playstats_bygame_path, index=False)
    else:
        season_playstats_by_game = get_season_playstats(season)
        season_playstats_by_game.to_csv(season_playstats_bygame_path, index=False)
        
    ## Get next date for each game
    season_playstats_by_game.sort_values(["team", "date"], inplace=True)
    season_playstats_by_game.reset_index(drop=True, inplace=True)
    season_playstats_by_game['next_date'] = season_playstats_by_game['date'].shift(-1)
    season_playstats_by_game.loc[season_playstats_by_game['team'] != season_playstats_by_game['team'].shift(-1), 'next_date'] = None
    
    ## Get avgs going into each game
    running_avgs = season_playstats_by_game.groupby("team").expanding().mean().reset_index().rename(columns={'level_1':'index'})
    running_avgs.set_index('index', inplace=True)
    playstats_by_date = season_playstats_by_game[['next_date']].rename(columns={'next_date':'date'}).merge(running_avgs, left_index=True, right_index=True)
    playstats_by_date.sort_index(inplace=True)

    ## Return 
    if write_out:
        playstats_by_date.to_csv(season_playstats_path, index=False)
    return playstats_by_date
    
    
if __name__ == "__main__":
    season = sys.argv[1]
    # TODO: add command line arguments
    get_playstats_by_date(season)