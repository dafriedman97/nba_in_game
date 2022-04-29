import os
import sys
from collections import defaultdict
from pathlib import Path
import pandas as pd
import numpy as np
import ipdb
from scipy.stats import norm
hoops_dir = Path(os.path.abspath(__file__)).parent.parent
data_dir = hoops_dir / "data"
sys.path.append(hoops_dir.as_posix())

from pipeline import team_metadata


def sigmoid(x, a=0, b=1):
    return 1/(1+np.exp(-(a + b*x)))

def get_rankings(season=None, n_iters=2, mu0=0, sigma0=1, sigmoid_a=0.28, sigmoid_b=1, shrinkage=1.5, games=None):
    ## Get games (if not provided)
    if games is None: 
        games = team_metadata.get_game_by_game(season)

    ## Get ranking
    ranking_distns = defaultdict(lambda: {'mu':mu0, 'sigma':sigma0}) # team ranking distributions
    games_by_team = defaultdict(lambda: 0)
    for i in range(n_iters):
        for _, game in games.iterrows():
            home, vis, home_win = game[['home', 'vis', 'home_win']]
            games_by_team[home] += 1
            games_by_team[vis] += 1

            # Get prior dist'ns
            w = .01
            h_shrinkage_factor = 1-np.exp(-games_by_team[home]/shrinkage)
            v_shrinkage_factor = 1-np.exp(-games_by_team[home]/shrinkage)
            qh = np.arange(-5, 5, w)*h_shrinkage_factor
            qv = np.arange(-5, 5, w)*v_shrinkage_factor
            h_prior = norm.pdf(qh, loc=ranking_distns[home]['mu'], scale=ranking_distns[home]['sigma'])
            v_prior = norm.pdf(qv, loc=ranking_distns[vis]['mu'], scale=ranking_distns[vis]['sigma'])

            # Get posterior
            meshgrid = np.meshgrid(qh, qv)
            qh_minus_qv = meshgrid[0] - meshgrid[1] # matrix of quality differences
            outcome_probs = sigmoid(qh_minus_qv, a=sigmoid_a, b=sigmoid_b) # row represents qv (lowest to highest), col represents qh (lowest to highest)
            outcome_probs = outcome_probs if home_win else 1-outcome_probs
            h_post_over_v = h_prior * outcome_probs # posteriors—row represents qv, column represents qh
            v_post_over_h = v_prior[:,np.newaxis] * outcome_probs # posteriors—row represents qv, column represents qh        
            h_post = (h_post_over_v * v_prior[:, np.newaxis]).sum(0)
            v_post = (v_post_over_h * h_prior).sum(1)
            h_post /= (h_post*w).sum()
            v_post /= (v_post*w).sum()
            ranking_distns[home] = {'mu': w*(qh*h_post).sum(), 'sigma': np.sqrt(w*np.sum((qh**2)*h_post) - (w*np.sum(qh*h_post))**2)}
            ranking_distns[vis] = {'mu': w*(qv*v_post).sum(), 'sigma': np.sqrt(w*np.sum((qv**2)*v_post) - (w*np.sum(qv*v_post))**2)}
    return dict(sorted({k:v['mu'] for k, v in ranking_distns.items()}.items(), key=lambda x: x[1]))

def get_rankings_by_date(season=None, n_iters=2, mu0=0, sigma0=1, sigmoid_a=0.28, sigmoid_b=1, shrinkage=1.5, games=None, write_out=True):
    rankings_dir = data_dir / "rankings"
    os.makedirs(rankings_dir , exist_ok=True)

    ## Get games (if not provided)
    if games is None: 
        games = team_metadata.get_game_by_game(season)
    dates = sorted(games['date'].unique())[1:]

    ## Get existing rankings (if any)
    previous_rankings = False
    if season is not None:
        if os.path.exists(data_dir / "rankings" / (season + ".csv")):
            rankings_by_date = pd.read_csv(data_dir / "rankings" / (season + ".csv"))
            dates = [date for date in dates if date > rankings_by_date.date.max()]
            previous_rankings = True

    ## Loop through dates
    date_rankings = list()
    for date in dates:
        # print(date)
        try:
            previous_games = games.loc[games['date'] < date]
            rankings = get_rankings(games=previous_games, n_iters=n_iters, mu0=mu0, sigma0=sigma0, sigmoid_a=sigmoid_a, sigmoid_b=sigmoid_b, shrinkage=shrinkage)
            rankings = pd.Series(rankings).reset_index().rename(columns={'index':'team', 0:'ranking'})
            rankings['date'] = date
            date_rankings.append(rankings)
        except KeyboardInterrupt:
            break
        except:
            pass
    if previous_rankings:
        rankings_by_date = pd.concat([rankings_by_date] + date_rankings).reset_index(drop=True)
    else:
        rankings_by_date = pd.concat(date_rankings).reset_index(drop=True)
    
    ## Write out and return
    if write_out:
        rankings_by_date.to_csv(rankings_dir / (season + ".csv"), index=False)
    return rankings_by_date
    
if __name__ == "__main__":
    season = sys.argv[1]
    # TODO: add command line argument for n_iters, mu0/sigma0, sigmoids
    get_rankings_by_date(season)
