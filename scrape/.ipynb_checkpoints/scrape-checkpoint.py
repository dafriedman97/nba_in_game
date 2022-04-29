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

def track_lines(url, sleep=30, max_iter=1000):
    all_lines = pd.DataFrame(columns=['home', 'vis', 'home_score', 'vis_score', 'quarter', 'time', 'home_mline', 'vis_mline'])
    start_time = datetime.now().strftime("%m-%d-%Y_%H:%M:%S")
    print(start_time)

    for i in range(max_iter):
        try:
            ## Parse the page
            page = requests.get(url)
            soup = BeautifulSoup(page.content, "html.parser")

            # ## Get today's lines
            # lines_by_day = soup.find_all("div", class_="parlay-card-10-a")
            # if len(lines_by_day[0].find_all("span", text="Today")) > 0: # we have lines left for today
            #     todays_lines = lines_by_day[0]
            # else: # no more lines for today (or potentially it's past midnight and the lines are listed as yesterday's) 
            #     hour = datetime.now().hour
            #     if hour < 3 and len(lines_by_day) > 1: # past midnight and we have two sections of lines
            #         # TODO: should replace <len(lines_by_day)> with some search for a tag that the first section is a date (representing the day that just finished)
            #         todays_lines = lines_by_day[0]
            #     else:
            #         print("no more lines")
            #         break
            
            ## Get today's lines
            first_lines = soup.find_all("div", class_="parlay-card-10-a")[0]
            if len(first_lines.find_all("span", text="Today")) > 0:
                todays_lines = first_lines
            else:
                hour = datetime.now().hour
                if hour < 8: # before 8am
                    print("no more lines")
                    break
                else:
                    continue                

            ## Get all Lines
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
            mlines = [line.find("span", class_="sportsbook-odds american no-margin default-color") for line in lines]        
            mlines = [line.text.replace("+", "") if line else None for line in mlines]

            ## Update lines
            iter_lines = pd.DataFrame(columns=['home', 'vis', 'home_score', 'vis_score', 'quarter', 'time', 'home_mline', 'vis_mline'])
            iter_lines['home'] = teams[1::2]
            iter_lines['vis'] = teams[::2]
            iter_lines['home_score'] = scores[1::2]
            iter_lines['vis_score'] = scores[::2]
            iter_lines['quarter'] = quarters
            iter_lines['time'] = times
            iter_lines['home_mline'] = mlines[1::2]
            iter_lines['vis_mline'] = mlines[::2]        
            all_lines = pd.concat([all_lines, iter_lines]).drop_duplicates()
            all_lines.to_csv(lines_dir / (start_time + ".csv"), index=False)
            print(datetime.now().strftime("%H:%M:%S"), end=" | ")
        except:
            pass
            
        ## Sleep
        time.sleep(sleep)
        
    
    ## Return
    return all_lines

if __name__ == "__main__":

    ## Get args
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--sleep", type=int, default=30)
    parser.add_argument("-i", "--max_iter", type=int, default=1000)
    args = parser.parse_args()

    ## Run it
    url = "https://sportsbook.draftkings.com/leagues/basketball/88670846"
    sleep = args.sleep
    max_iter = args.max_iter
    lines = track_lines(url, sleep=sleep, max_iter=max_iter)
