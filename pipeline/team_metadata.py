import os
import sys
from collections import defaultdict
from pathlib import Path
import pandas as pd
import numpy as np
import ipdb
from nba_api.stats.endpoints import playbyplayv2
from nba_api.stats.endpoints import leaguegamefinder
hoops_dir = Path(os.path.abspath(__file__)).parent.parent
data_dir = hoops_dir / "data"
sys.path.append(hoops_dir.as_posix())

def get_game_by_game(season):
    pbps = [pd.read_csv(data_dir / "play_by_play" / season / file) for file in os.listdir(data_dir / "play_by_play" / season) if file.endswith(".csv")]
    game_results = pd.DataFrame(columns=['game_id', 'date', 'home', 'vis', 'home_score', 'vis_score'])
    for pbp in pbps:
        game_results.loc[len(game_results)] = pbp.iloc[-1][['game_id', 'date', 'home', 'vis', 'home_score', 'vis_score']]
    game_results['home_win'] = game_results['home_score'] > game_results['vis_score']
    game_results.sort_values(["date", 'game_id'], inplace=True)
    game_results.reset_index(drop=True, inplace=True)
    return game_results

def get_records_by_date(seasons):
    records_by_date = pd.DataFrame(columns=['date', 'game_id', 'home', 'vis', 'home_house_wins', 'home_house_losses', 'home_road_wins', 'home_road_losses', 'vis_house_wins', 'vis_house_losses', 'vis_road_wins', 'vis_road_losses'])
    for season in seasons:
        game_by_game = get_game_by_game(season)
        records = defaultdict(lambda: {'home_wins':0, 'home_losses':0, 'vis_wins':0, 'vis_losses':0})
        for _, vals in game_by_game.iterrows():
            date, game_id, home, vis, home_win = vals[['date', 'game_id', 'home', 'vis', 'home_win']]
            
            # Fill in records by date
            records_by_date.loc[len(records_by_date)] = [date, game_id,  home, vis] +  list(records[home].values()) + list(records[vis].values())
            
            # Update records
            if home_win:
                records[home]['home_wins'] += 1
                records[vis]['vis_losses'] += 1
            else:
                records[home]['home_losses'] += 1
                records[vis]['vis_wins'] += 1        

    # Clean records and return
    records_by_date['home_house_games'] = (records_by_date['home_house_wins'] + records_by_date['home_house_losses'])
    records_by_date['home_road_games'] = (records_by_date['home_road_wins'] + records_by_date['home_road_losses'])
    records_by_date['home_house_win_pct'] = records_by_date['home_house_wins'] / records_by_date['home_house_games'].replace(0, -1)
    records_by_date['home_road_win_pct'] = records_by_date['home_road_wins'] / records_by_date['home_road_games'].replace(0, -1)
    records_by_date.loc[records_by_date['home_house_games'] == 0, 'home_house_win_pct'] = np.nan
    records_by_date.loc[records_by_date['home_road_games'] == 0, 'home_road_win_pct'] = np.nan
    records_by_date['vis_house_games'] = (records_by_date['vis_house_wins'] + records_by_date['vis_house_losses'])
    records_by_date['vis_road_games'] = (records_by_date['vis_road_wins'] + records_by_date['vis_road_losses'])
    records_by_date['vis_house_win_pct'] = records_by_date['vis_house_wins'] / records_by_date['vis_house_games'].replace(0, -1)
    records_by_date['vis_road_win_pct'] = records_by_date['vis_road_wins'] / records_by_date['vis_road_games'].replace(0, -1)
    records_by_date.loc[records_by_date['vis_house_games'] == 0, 'home_house_win_pct'] = np.nan
    records_by_date.loc[records_by_date['vis_road_games'] == 0, 'home_road_win_pct'] = np.nan    
    return records_by_date