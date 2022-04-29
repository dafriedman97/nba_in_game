import os 
import sys
from pathlib import Path
import argparse
from bs4 import BeautifulSoup
import json
import requests
import time
from datetime import datetime
import pandas as pd
import numpy as np 

hoops_dir = Path(os.path.abspath(__file__)).parent.parent
data_dir = hoops_dir / "data"
lines_dir = data_dir / "lines"
sys.path.append(hoops_dir.as_posix())

def track_lines(url, sleep=30, max_iter=660):
    all_lines = pd.DataFrame(columns=['home', 'vis', 'home_score', 'vis_score', 'quarter', 'time', 'home_mline', 'vis_mline'])
    start_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    start_time_ = time.time()
    date = datetime.now().strftime("%Y-%m-%d")
    print(start_time)

    i = 0
    while True:
        ## Parse the page
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")

        ## Get today's lines
        day_lines = soup.find_all("div", class_="parlay-card-10-a")
        if day_lines:
            todays_lines = day_lines[0]
        else:
            time.sleep(sleep)

        ## Get all lines
        lines = todays_lines.find_all("tbody", class_="sportsbook-table__body")[0].find_all("tr")

        ## Get the teams
        teams = [line.find("div", class_="event-cell__name-text").text.split(" ")[0] for line in lines]
        
        ## Get the time
        clocks = [line.find("div", class_='event-cell__clock') for line in lines[::2]]
        times = [clock.find_all("span")[0].string if clock else None for clock in clocks]
        quarters = [clock.find_all("span")[1].string[0] if clock else None for clock in clocks]

        ## Get the scores
        scores = [line.find("span", class_="event-cell__score") for line in lines]
        scores = [score.text if score else None for score in scores]

        ## Get the lines
        mlines = [line.find_all("td", class_="sportsbook-table__column-row")[-1] for line in lines]
        active_mlines = [mline.find("div", class_="sportsbook-outcome-cell__body no-label") for mline in mlines]
        mlines = [mline.find("span", class_="sportsbook-odds american no-margin default-color") if mline else None for mline in active_mlines]
        mlines = [line.text.replace("+", "") if line else None for line in mlines]        
        lines_open = [mline is not None for mline in mlines[::2]]

        ## Update lines
        iter_lines = pd.DataFrame(columns=['home', 'vis', 'date', 'home_score', 'vis_score', 'quarter', 'time', 'home_mline', 'vis_mline'])
        iter_lines['home'] = teams[1::2]
        iter_lines['vis'] = teams[::2]
        iter_lines['date'] = date
        iter_lines['home_score'] = scores[1::2]
        iter_lines['vis_score'] = scores[::2]
        iter_lines['quarter'] = quarters
        iter_lines['time'] = times
        iter_lines['home_mline'] = mlines[1::2]
        iter_lines['vis_mline'] = mlines[::2]
        iter_lines = iter_lines.loc[pd.Series(lines_open) == True]
        all_lines = pd.concat([all_lines, iter_lines]).drop_duplicates()
        all_lines.to_csv(lines_dir / (start_time + ".csv"), index=False)
        print(datetime.now().strftime("%H:%M:%S"), end=" | ")
            
        ## Check if we're done
        if i == max_iter:
            if any(lines_open): # we've reached max_iter but lines are still open
                i -= 100
            else:
                print("finished")
                break
        i += 1
        ## Sleep
        time.sleep(sleep)
        
    
    ## Return
    return all_lines

if __name__ == "__main__":

    ## Get args
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--sleep", type=int, default=30)
    parser.add_argument("-i", "--max_iter", type=int, default=2500)
    args = parser.parse_args()

    ## Run it
    url = "https://sportsbook.draftkings.com/leagues/basketball/88670846"
    sleep = args.sleep
    max_iter = args.max_iter
    lines = track_lines(url, sleep=sleep, max_iter=max_iter)
