import os
import sys
from pathlib import Path
import pandas as pd
import ipdb
import argparse
from nba_api.stats.endpoints import playbyplayv2
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.library.parameters import SeasonNullable
hoops_dir = Path(os.path.abspath(__file__)).parent.parent
data_dir = hoops_dir / "data"
sys.path.append(hoops_dir.as_posix())


def get_game_pbp(game_id, date, home, vis):
    
    ## Get raw df
    renamer = {'player1_team_abbreviation':'p1_team', 'player2_team_abbreviation':'p2_team', 'player3_team_abbreviation':'p3_team', 'homedescription':f'{home}_desc', 'neutraldescription':'neut_desc', 'visitordescription':f'{vis}_desc', 'eventmsgtype':'event_code', 'eventmsgactiontype':'event_deets', 'pctimestring':'time'}
    pbp = playbyplayv2.PlayByPlayV2(game_id).play_by_play.get_data_frame()
    pbp.columns = [x.lower() for x in pbp.columns]
    pbp.rename(columns=renamer, inplace=True)

    ## Get scores
    pbp[[f'{vis}_score', f'{home}_score']] = pbp['score'].str.split(" - ", expand=True)
    pbp.loc[0, f'{home}_score'] = 0
    pbp.loc[0, f'{vis}_score'] = 0
    pbp[f'{home}_score'] = pbp[f'{home}_score'].fillna(method="ffill").astype(int)
    pbp[f'{vis}_score'] = pbp[f'{vis}_score'].fillna(method="ffill").astype(int)

    ## Get events — from https://github.com/swar/nba_api/blob/master/docs/examples/PlayByPlay.ipynb
    event_codes = {1:"fg_make", 2:"fg_miss", 3:"ft_make", 4:"reb", 5:"tov", 6: "foul", 7: "violation", 8: "substitution", 9: "timeout", 10: "jump_ball", 11: "ejection", 12: "period_start", 13: "period_end", 18: "replay"}
    pbp['event'] = pbp['event_code'].map(event_codes)
    pbp = pbp.loc[(pbp['event'] != "substitution") & (pbp['event'] != 'replay')].copy(deep=True) # can ignore these for now
    pbp.loc[(pbp['event'] == "ft_make") & (pbp[f'{home}_score'] == pbp[f'{home}_score'].shift(1)) & (pbp[f'{vis}_score'] == pbp[f'{vis}_score'].shift(1)), 'event'] = "ft_miss"
    pbp.loc[(pbp['event'] == "fg_miss") & ((pbp[f'{vis}_desc'].str.contains("3PT") == True) | (pbp[f'{home}_desc'].str.contains("3PT") == True)), 'event'] = "fg3_miss"
    pbp.loc[(pbp['event'] == "fg_make") & ((pbp[f'{vis}_desc'].str.contains("3PT") == True) | (pbp[f'{home}_desc'].str.contains("3PT") == True)), 'event'] = "fg3_make"

    ## Blocks and steals
    joint_desc = (pbp[f"{home}_desc"].fillna("") + pbp[f"{vis}_desc"].fillna("")).str.lower()
    pbp['block'] = ((pbp['event'] == "fg_miss") | (pbp['event'] == "fg3_miss")) & (joint_desc.str.contains("block") == True)
    pbp['steal'] = (pbp['event'] == "tov") & (joint_desc.str.contains("steal") == True)
    pbp.loc[(pbp['block'] == True) & (pbp[f"{home}_desc"].str.lower().str.contains("block")), f"{home}_desc"] = None
    pbp.loc[(pbp['block'] == True) & (pbp[f"{vis}_desc"].str.lower().str.contains("block")), f"{vis}_desc"] = None
    pbp.loc[(pbp['steal'] == True) & (pbp[f"{home}_desc"].str.lower().str.contains("steal")), f"{home}_desc"] = None
    pbp.loc[(pbp['steal'] == True) & (pbp[f"{vis}_desc"].str.lower().str.contains("steal")), f"{vis}_desc"] = None
    if len(pbp.loc[(pbp[f"{home}_desc"].notna()) & (pbp[f"{vis}_desc"].notna())]) != 0:
        raise Exception()

    ## Function to swap teams
    def get_other(team):
        if team == home:
            return vis
        else:
            return home
    
    ## Events
    # Play types
    offensive = ['fg_make', 'fg_miss', 'fg3_make', 'fg3_miss', 'ft_miss', 'tov', 'timeout']
    defensive = []
    unclear = ['reb', 'foul', 'violation']
    other = ['jump_ball']
    non_play = ['period_start', 'period_end', 'substitution', 'ejection'] # occur outside of regular play

    # Loop
    teams = list()
    poss = list()
    pos = None # initialize possession to be neither team
    for _, vals in pbp[['event', 'event_deets', f'{home}_desc', f'{vis}_desc', 'p3_team']].iterrows():
        event, home_desc, vis_desc = vals['event'], vals[f'{home}_desc'], vals[f'{vis}_desc']
        team = home if not pd.isnull(home_desc) else vis if not pd.isnull(vis_desc) else None
        if team is not None:
            if event in offensive:
                pos = team
            elif event in defensive:
                pos = get_other(team)
            elif event in unclear:
                if event == "reb":
                    pos = team
                elif event in ["foul", "violation"]:
                    pos = get_other(team) # TODO: this should depend on the type of foul
                else:
                    raise Exception("Unknown event")
            elif event in other:
                if event == "jump_ball":
                    pos = None
                else:
                    raise Exception("Unknown event")
            elif event in non_play:
                pos = pos # doesn't change
        else:
            pos = pos # possession doesn't change
        teams.append(team)
        poss.append(pos)

    # Fill in 
    pbp['team'] = teams
    pbp['pos'] = poss 
    
    ## Blocks + Steals
    steals = pbp.loc[pbp['steal'] == True].copy(deep=True)
    steals.loc[steals[f'{home}_desc'].notna(), f'{home}_desc'] = None
    steals.loc[steals[f'{vis}_desc'].notna(), f'{vis}_desc'] = None
    steals.loc[steals[f'{home}_desc'].isnull(), f'{home}_desc'] = "steal"
    steals.loc[steals[f'{vis}_desc'].isnull(), f'{vis}_desc'] = "steal"
    steals['team'] = steals['team'].apply(lambda x: get_other(x))
    steals['event'] = "steal"
    blocks = pbp.loc[pbp['block'] == True].copy(deep=True)
    blocks.loc[blocks[f'{home}_desc'].notna(), f'{home}_desc'] = None
    blocks.loc[blocks[f'{vis}_desc'].notna(), f'{vis}_desc'] = None
    blocks.loc[blocks[f'{home}_desc'].isnull(), f'{home}_desc'] = "block"
    blocks.loc[blocks[f'{vis}_desc'].isnull(), f'{vis}_desc'] = "block"
    blocks['team'] = blocks['team'].apply(lambda x: get_other(x))
    blocks['event'] = "block"
    pbp = pd.concat([pbp, blocks, steals], ignore_index=True).copy(deep=True)
    
    ## Time
    pbp[['mins', 'secs']] = pbp['time'].str.split(":", expand=True).astype(int)
    regulation_time = 12*(pbp['period']-1) + (11-pbp['mins']) + (60-pbp['secs'])/60
    overtime_time = 5*(pbp['period']-5) + (4-pbp['mins']) + (60-pbp['secs'])/60
    pbp['time'] = regulation_time*(pbp['period'] <= 4) + (pbp['period'] > 4)*(48+overtime_time)
    pbp['time'] = pbp['time'].round(2)
    pbp = pbp.sort_values(['time', 'eventnum']).reset_index(drop=True) 

    ## Final Touches
    pbp['home'] = home
    pbp['vis'] = vis
    pbp['date'] = date
    pbp['score'] = pbp[f'{home}_score'].astype(str) + "-" + pbp[f'{vis}_score'].astype(str)
    pbp = pbp[['game_id', 'date', 'home', 'vis', 'time', 'period', 'mins', 'secs', 'pos', 'team', 'event', 'event_deets', 'block', 'steal', f'{home}_desc', f'{vis}_desc', 'score', f'{home}_score', f'{vis}_score']].copy(deep=True)
    pbp.rename(columns={f'{home}_desc':'home_desc', f'{vis}_desc':'vis_desc', f'{home}_score':'home_score', f'{vis}_score':'vis_score'}, inplace=True)

    ## Return
    return pbp

def get_season_pbp(season, overwrite):
    ## Get games
    pbp_dir = data_dir / "play_by_play" / season
    os.makedirs(pbp_dir , exist_ok=True)
    completed_games = os.listdir(pbp_dir)
    games = leaguegamefinder.LeagueGameFinder(season_nullable=season, season_type_nullable="Regular Season", league_id_nullable='00')
    games = games.get_data_frames()[0][['GAME_ID', 'GAME_DATE', 'MATCHUP']]
    games = games.loc[games['MATCHUP'].str.contains(" @ ")]
    games[['vis', 'home']] = games['MATCHUP'].str.split(" @ ", expand=True)
    games = games[['GAME_ID', 'GAME_DATE', 'home', 'vis']].rename(columns={'GAME_ID':'game_id', 'GAME_DATE':'date'}).sort_values("game_id").reset_index(drop=True)

    ## Get pbp
    for _, game in games.iterrows():
        filename = game['game_id'] + ".csv"
        if filename in completed_games and not overwrite:
            continue
        try:
            pbp = get_game_pbp(game['game_id'], game['date'], game['home'], game['vis'])
            pbp.to_csv(pbp_dir / filename, index=False)
        except:
            print(game['game_id'], game['home'], game['vis'])
            break


if __name__ == "__main__":

    ## Get Args
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--season", type=str, default=None)
    parser.add_argument("-o", "--overwrite", action='store_true')
    args = parser.parse_args()
    season = args.season if args.season else SeasonNullable.current_season
    overwrite = args.overwrite

    ## Run season pbp
    get_season_pbp(season, overwrite)
