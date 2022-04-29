import os
import sys
from pathlib import Path
from collections import defaultdict
import pandas as pd
import numpy as np

hoops_dir = Path(os.path.abspath(__file__)).parent.parent
data_dir = hoops_dir / "data"
sys.path.append(hoops_dir.as_posix())

def merge(first_season, last_season):
    # Get seasons
    seasons = [f"20{year}-{year+1}" for year in range(int(first_season[-5:-3]), int(last_season[-5:-3])+1)]
    
    # Get score by score
    sbss = list()
    for season in seasons:
        season_sbs = pd.read_csv(data_dir / "score_by_score" / (season + ".csv"))
        sbss.append(season_sbs)
    sbs = pd.concat(sbss).reset_index(drop=True)
    sbs['ppm'] = (sbs['home_score'] + sbs['vis_score']) /sbs['time']

    # Get Rankings
    rbds = list()
    for season in seasons:
        season_rbd = pd.read_csv(data_dir / "rankings" / (season + ".csv"))
        rbds.append(season_rbd)
    rbd = pd.concat(rbds).reset_index(drop=True)

    # Get playstats
    pbds = list()
    for season in seasons:
        season_pbd = pd.read_csv(data_dir / "playstats" / (season + ".csv"))
        season_pbd = season_pbd.loc[season_pbd['date'].notna()]
        pbds.append(season_pbd)
    pbd = pd.concat(pbds).reset_index(drop=True)
    pbd.rename(columns={'ppm': 'avg_ppm'}, inplace=True)
    pbd_stats = [col for col in pbd.columns if col not in ['date', 'team']]

    # Merge
    sbs_sub = sbs[['game_id', 'date', 'home', 'vis', 'home_win', 'time', 'home_score', 'vis_score', 'ppm']]
    m = pd.merge(left=sbs_sub, right=rbd, left_on=['home', 'date'], right_on=['team', 'date']).rename(columns={'ranking':'home_ranking'}).drop(columns='team')
    m = pd.merge(left=m, right=rbd, left_on=['vis', 'date'], right_on=['team', 'date']).rename(columns={'ranking':'vis_ranking'}).drop(columns='team')
    m = pd.merge(left=m, right=pbd, left_on=['home', 'date'], right_on=['team', 'date']).rename(columns={stat: "home_"+stat for stat in pbd_stats}).drop(columns='team')
    m = pd.merge(left=m, right=pbd, left_on=['home', 'date'], right_on=['team', 'date']).rename(columns={stat: "vis_"+stat for stat in pbd_stats}).drop(columns='team')
    m['home_lead'] = m['home_score'] - m['vis_score']
    m['mins'] = m['time'] // 1

    # Return
    return m

