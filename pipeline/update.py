import os
import sys
from pathlib import Path
import pandas as pd

hoops_dir = Path(os.path.abspath(__file__)).parent.parent
data_dir = hoops_dir / "data"
sys.path.append(hoops_dir.as_posix())

from pipeline import play_by_play, score_by_score, playstats, rank

if __name__ == "__main__":
    season = sys.argv[1]
    # TODO: add in argparse
    print("play by play")
    play_by_play.get_season_pbp(season, overwrite=False)
    print("score by score")
    score_by_score.get_sbs(season)
    print("playstats")
    playstats.get_playstats_by_date(season)
    print("rankings")
    rank.get_rankings_by_date(season)
