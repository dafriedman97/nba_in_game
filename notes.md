- In game model: XGBoost with one obs per minute, game-state predictors (score, time), predict binary outcome of home team wins
  - Have to (heavily) incorporate pre-game predictors
  - Add trend predictors—last 5 minutes score, last 5 scores, etc.



- TODO
  - Get more team stats
    - List of the basics http://www.espn.com/nba/hollinger/teamstats



- Team quality is normally distributed, starting at 0 based
- Assume team A beats team B with probability that is a function of qA-qB (sigmoid function of qA-qB)
- After A and B play, update qA and qB Bayesianally 


$$
\begin{aligned}
QA, QB &\sim \mathcal{N}(0, \sigma^2) \\
VA &\sim \text{Bern}(p), \hspace{1mm} p = S(QA-QB) \\ 
f_{QA|VA=1}(qa) & \propto  f_{QA}(qa) S(qa-QB) \\
f_{QB|VA=1}(qb) & \propto  f_{QB}(qb) S(QA-qb)  \\

\end{aligned}
$$
